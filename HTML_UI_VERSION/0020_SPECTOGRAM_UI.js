// Module-level variables
let wavesurfer = null;
let currentAudioUrl = null;
let currentAudioName = null;
let liveUpdateTimer = null;
let fileInput = null;
let waveformEl = null;
let spectrogramEl = null;
let cursorEl = null;
let zoomSliderEl = null;
let scrollSyncEl = null;
let currentMinPxPerSec = 4;
const FIXED_PX_PER_SEC = 4;

function sendInfo(text) {
	const infoText = document.getElementById("infoText");
	if (infoText) {
		infoText.textContent = text;
	}
}

function mapColorSchemeToWaveSurfer(colormap) {
	const key = String(colormap || "").toLowerCase();
	if (key === "gray" || key === "igray" || key === "roseus") {
		return key;
	}
	return "roseus";
}

function clearTimers() {
	if (liveUpdateTimer) {
		clearTimeout(liveUpdateTimer);
		liveUpdateTimer = null;
	}
}

function handleTimelineScroll() {
	updatePlaybackCursor();
}

function destroyWaveSurfer() {
	clearTimers();
	if (scrollSyncEl) {
		scrollSyncEl.removeEventListener("scroll", handleTimelineScroll);
		scrollSyncEl = null;
	}
	if (wavesurfer) {
		wavesurfer.destroy();
		wavesurfer = null;
	}
	if (cursorEl) cursorEl.hidden = true;
}

function updatePlaybackCursor() {
	if (!cursorEl || !wavesurfer || !spectrogramEl) {
		return;
	}
	const scrollTarget = getTimelineScrollElement();
	if (!scrollTarget) {
		return;
	}
	const time = wavesurfer.getCurrentTime() || 0;
	const duration = wavesurfer.getDuration() || 0;
	let worldX = time * currentMinPxPerSec;
	if (duration > 0 && scrollTarget.scrollWidth > 0) {
		const timeRatio = Math.max(0, Math.min(1, time / duration));
		worldX = timeRatio * scrollTarget.scrollWidth;
	}
	const viewportX = worldX - scrollTarget.scrollLeft;
	const maxX = Math.max(0, spectrogramEl.clientWidth - 2);
	cursorEl.style.left = `${Math.max(0, Math.min(maxX, viewportX))}px`;
	cursorEl.hidden = false;
}

function bindZoomSlider() {
	if (!zoomSliderEl || zoomSliderEl.dataset.bound === "1") {
		return;
	}
	zoomSliderEl.dataset.bound = "1";
	zoomSliderEl.addEventListener("input", (event) => {
		if (!wavesurfer) {
			return;
		}
		const minPxPerSec = event.target.valueAsNumber;
		if (!Number.isFinite(minPxPerSec)) {
			return;
		}
		currentMinPxPerSec = minPxPerSec;
		if (typeof wavesurfer.zoom === "function") {
			wavesurfer.zoom(minPxPerSec);
		} else if (typeof wavesurfer.setOptions === "function") {
			wavesurfer.setOptions({ minPxPerSec });
		}
		requestAnimationFrame(() => {
			bindScrollCursorSync();
			updatePlaybackCursor();
		});
	});
}

function getTimelineScrollElement() {
	if (!spectrogramEl) {
		return null;
	}
	// Try shadow DOM first
	if (spectrogramEl.shadowRoot) {
		const shadowEl = spectrogramEl.shadowRoot.querySelector('[part="scroll"], .scroll, [class*="scroll"]');
		if (shadowEl && shadowEl.scrollWidth > shadowEl.clientWidth) {
			return shadowEl;
		}
	}
	// Try regular DOM queries
	const candidates = [
		spectrogramEl.querySelector('[part="scroll"]'),
		spectrogramEl.querySelector(".scroll"),
		spectrogramEl.querySelector('[class*="scroll"]'),
		spectrogramEl.querySelector("canvas")?.parentElement,
	];
	for (const el of candidates) {
		if (el && el.scrollWidth > el.clientWidth) {
			return el;
		}
	}
	// Fallback
	return spectrogramEl;
}

function bindScrollCursorSync() {
	const nextScrollEl = getTimelineScrollElement();
	if (!nextScrollEl) {
		return;
	}
	if (scrollSyncEl && scrollSyncEl !== nextScrollEl) {
		scrollSyncEl.removeEventListener("scroll", handleTimelineScroll);
	}
	if (scrollSyncEl !== nextScrollEl) {
		scrollSyncEl = nextScrollEl;
		scrollSyncEl.addEventListener("scroll", handleTimelineScroll, { passive: true });
	}
}

function getSafeSettings(raw) {
	const frequencyMin = Math.max(0, Number(raw.frequencyMin) || 20);
	const frequencyMax = Math.max(frequencyMin + 1, Number(raw.frequencyMax) || 6000);
	const fftSamples = Math.max(256, Math.min(4096, Number(raw.fftSamples) || 2048));
	const renderCols = Math.max(512, Math.min(4096, Number(raw.renderCols) || 2048));
	const melRows = Math.max(128, Math.min(1536, Number(raw.melRows) || 768));
	const noverlap = Math.max(0, Math.min(Math.floor(fftSamples / 2), Number(raw.noverlap) || 0));
	const rangeDB = Math.max(20, Math.min(150, Number(raw.rangeDB) || 60));
	const allowedScales = ["linear", "logarithmic", "mel", "bark", "erb"];
	const scale = allowedScales.includes(raw.scale) ? raw.scale : "mel";

	return {
		frequencyMin,
		frequencyMax,
		fftSamples,
		renderCols,
		melRows,
		noverlap,
		rangeDB,
		scale,
		normalize: raw.normalize !== false,
		colormap: raw.colormap || "roseus",
	};
}

function createWaveSurfer(audioUrl, startAtSec = 0, autoplay = false) {
	if (!window.WaveSurfer || !window.WaveSurfer.Spectrogram) {
		sendInfo("WaveSurfer Spectrogram plugin failed to load.");
		return;
	}
	if (!spectrogramEl || !waveformEl) {
		sendInfo("Spectrogram DOM is not ready.");
		return;
	}

	const rawSettings =
		window.BA_spectrogramSettings?.read?.() ?? {
			colormap: "roseus",
			frequencyMin: 20,
			frequencyMax: 6000,
			fftSamples: 2048,
			rangeDB: 60,
			normalize: true,
			scale: "mel",
			melRows: 768,
			renderCols: 4096,
			noverlap: 1536,
		};

	const settings = getSafeSettings(rawSettings);
	destroyWaveSurfer();
	currentMinPxPerSec = Number(zoomSliderEl?.valueAsNumber) || FIXED_PX_PER_SEC;

	waveformEl.hidden = true;
	spectrogramEl.hidden = false;

	const spectrogramHeight = Math.max(80, spectrogramEl.clientHeight);
	const spectrogramPlugin = window.WaveSurfer.Spectrogram.create({
		container: "#spectrogramCanvas",
		height: spectrogramHeight,
		labels: true,
		labelsColor: "#ffffff",
		labelsHzColor: "#ffd400",
		splitChannels: false,
		useWebWorker: true,
		scale: settings.scale,
		frequencyMin: settings.frequencyMin,
		frequencyMax: settings.frequencyMax,
		fftSamples: settings.fftSamples,
		noverlap: settings.noverlap,
		rangeDB: settings.rangeDB,
		gainDB: settings.normalize ? 20 : 0,
		colorMap: mapColorSchemeToWaveSurfer(settings.colormap),
		windowFunc: "hann",
		maxCanvasWidth: Math.max(1024, settings.renderCols),
	});

	try {
		wavesurfer = window.WaveSurfer.create({
			container: "#spectrogramCanvas",
			url: audioUrl,
			sampleRate: 44100,
			height: 0,
			waveColor: "rgba(0,0,0,0)",
			progressColor: "rgba(0,0,0,0)",
			cursorColor: "rgba(0,0,0,0)",
			cursorWidth: 0,
			minPxPerSec: currentMinPxPerSec,
			autoScroll: true,
			plugins: [spectrogramPlugin],
		});
	} catch (error) {
		sendInfo(`Spectrogram render failed: ${String(error)}`);
		console.error("WaveSurfer initialization failed:", error);
		return;
	}

	wavesurfer.on("ready", () => {
		bindScrollCursorSync();
		if (startAtSec > 0) {
			wavesurfer.setTime(startAtSec);
		}
		if (autoplay) {
			wavesurfer.play();
		}
		if (currentAudioName) {
			sendInfo(`Loaded: ${currentAudioName}`);
		} else {
			sendInfo("Audio loaded.");
		}
		if (zoomSliderEl) {
			zoomSliderEl.value = String(Math.round(currentMinPxPerSec));
		}
		updatePlaybackCursor();

	});



	wavesurfer.on("loading", (percent) => {
		sendInfo(`Loading audio... ${Math.max(0, Math.min(100, Math.round(percent)))}%`);
	});

	wavesurfer.on("timeupdate", () => {
		updatePlaybackCursor();
	});

	wavesurfer.on("seek", () => {
		updatePlaybackCursor();
	});

	wavesurfer.on("pause", () => {
		updatePlaybackCursor();
	});

	wavesurfer.on("finish", () => {
		updatePlaybackCursor();
	});

	wavesurfer.on("error", (err) => {
		sendInfo(`Audio load error: ${String(err)}`);
	});
}

function openFilePicker() {
	if (!fileInput) {
		sendInfo("Audio input element is not ready.");
		return;
	}
	fileInput.click();
}

function rebuildSpectrogramPreservingState() {
	const isPlaying = wavesurfer ? wavesurfer.isPlaying() : false;
	const currentTime = wavesurfer ? wavesurfer.getCurrentTime() : 0;
	if (currentAudioUrl) {
		createWaveSurfer(currentAudioUrl, currentTime, isPlaying);
	}
}

function scheduleLiveSpectrogramRebuild() {
	// Rebuilding on each slider movement can lock the UI on long tracks.
	// Spectrogram updates are applied when user clicks Enter in settings.
}

function attachSpectrogramListeners() {
	if (!fileInput) {
		console.error("audioFileInput element not found.");
		return;
	}

	fileInput.addEventListener("change", (event) => {
		const file = event.target.files && event.target.files[0];
		if (!file) {
			return;
		}

		if (currentAudioUrl && currentAudioUrl.startsWith("blob:")) {
			URL.revokeObjectURL(currentAudioUrl);
		}

		currentAudioName = file.name;
		currentAudioUrl = URL.createObjectURL(file);
		sendInfo("Loading audio...");
		createWaveSurfer(currentAudioUrl);
		fileInput.value = "";
	});

	Promise.resolve(window.BA_spectrogramSettings?.ready).then(() => {
		window.BA_spectrogramSettings?.setOnApply?.(() => {
			rebuildSpectrogramPreservingState();
		});

		window.BA_spectrogramSettings?.setOnChange?.(() => {
			scheduleLiveSpectrogramRebuild();
		});
	});
}

function handleCommand(command) {
	switch (command) {
		case "open-file":
			openFilePicker();
			break;
		case "youtube":
			sendInfo("YouTube loading is pending Python backend wiring.");
			break;
		case "open-settings":
			window.BA_spectrogramSettings?.open?.();
			break;
		case "play-toggle":
			if (!wavesurfer) {
				sendInfo("Open an audio file first.");
				break;
			}
			wavesurfer.playPause();
			break;
		case "stop":
			if (!wavesurfer) {
				break;
			}
			wavesurfer.pause();
			wavesurfer.setTime(0);
			break;
		case "quit":
			destroyWaveSurfer();
			if (currentAudioUrl && currentAudioUrl.startsWith("blob:")) {
				URL.revokeObjectURL(currentAudioUrl);
			}
			currentAudioUrl = null;
			currentAudioName = null;
			if (waveformEl) {
				waveformEl.hidden = true;
			}
			if (spectrogramEl) {
				spectrogramEl.hidden = true;
			}
			window.BA_spectrogramSettings?.close?.();
			sendInfo("Select an audio file to render spectrogram.");
			break;
		default:
			break;
	}
}

window.BA_spectrogramCommand = handleCommand;

window.BA_spectrogram = {
	seek(time) { wavesurfer?.setTime(time); },
	getDuration() { return wavesurfer?.getDuration() ?? 0; },
	isPlaying() { return wavesurfer?.isPlaying() ?? false; },
};

// Load spectrogram HTML from 0021_SPECTOGRAM.html
fetch("0021_SPECTOGRAM.html")
	.then((response) => response.text())
	.then((html) => {
		document.getElementById("spectrogramContainer").innerHTML = html;

		fileInput = document.getElementById("audioFileInput");
		waveformEl = document.getElementById("waveform");
		spectrogramEl = document.getElementById("spectrogramCanvas");
		cursorEl = document.getElementById("spectrogramCursor");
		zoomSliderEl = document.getElementById("spectrogramZoom");

		bindZoomSlider();
		attachSpectrogramListeners();
		sendInfo("Select an audio file to render spectrogram.");
	})
	.catch((error) => console.error("Error loading spectrogram:", error));
