// Module-level variables
let wavesurfer = null;
let currentAudioUrl = null;
let currentAudioName = null;
let liveUpdateTimer = null;
let renderWatchdogTimer = null;
let fileInput = null;
let waveformEl = null;
let spectrogramEl = null;

function sendInfo(text) {
	const infoText = document.getElementById("infoText");
	if (infoText) {
		infoText.textContent = text;
	}
}

function mapColorSchemeToWaveSurfer(colormap) {
	const key = String(colormap || "").toLowerCase();
	if (key === "gray" || key === "greys" || key === "bone") {
		return "gray";
	}
	if (key === "hot" || key === "inferno" || key === "magma" || key === "plasma") {
		return "roseus";
	}
	return "igray";
}

function clearTimers() {
	if (liveUpdateTimer) {
		clearTimeout(liveUpdateTimer);
		liveUpdateTimer = null;
	}
	if (renderWatchdogTimer) {
		clearTimeout(renderWatchdogTimer);
		renderWatchdogTimer = null;
	}
}

function destroyWaveSurfer() {
	clearTimers();
	if (wavesurfer) {
		wavesurfer.destroy();
		wavesurfer = null;
	}
}

function getSafeSettings(raw, qualityMode) {
	const isLite = qualityMode === "lite";
	const frequencyMin = Math.max(0, Number(raw.frequencyMin) || 20);
	const frequencyMax = Math.max(frequencyMin + 1, Number(raw.frequencyMax) || 6000);
	const fftSamples = isLite ? 512 : Math.max(256, Math.min(4096, Number(raw.fftSamples) || 2048));
	const renderCols = isLite ? 1024 : Math.max(512, Math.min(4096, Number(raw.renderCols) || 2048));
	const melRows = isLite ? 256 : Math.max(128, Math.min(1536, Number(raw.melRows) || 768));
	const noverlap = isLite
		? 256
		: Math.max(0, Math.min(Math.floor(fftSamples / 2), Number(raw.noverlap) || 0));
	const rangeDB = Math.max(20, Math.min(150, Number(raw.rangeDB) || 60));
	const allowedScales = ["linear", "logarithmic", "mel", "bark", "erb"];
	const scale = allowedScales.includes(raw.scale) ? raw.scale : "mel";

	return {
		isLite,
		frequencyMin,
		frequencyMax,
		fftSamples,
		renderCols,
		melRows,
		noverlap,
		rangeDB,
		scale,
		normalize: raw.normalize !== false,
		colormap: raw.colormap || "magma",
	};
}

function createWaveSurfer(audioUrl, startAtSec = 0, autoplay = false, qualityMode = "normal") {
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
			colormap: "magma",
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

	const settings = getSafeSettings(rawSettings, qualityMode);
	destroyWaveSurfer();

	waveformEl.hidden = true;
	spectrogramEl.hidden = false;

	const spectrogramPlugin = window.WaveSurfer.Spectrogram.create({
		container: "#spectrogramCanvas",
		height: spectrogramEl.clientHeight,
		labels: !settings.isLite,
		labelsColor: "#ffffff",
		labelsBackground: "rgba(0,0,0,0.45)",
		labelsHzColor: "#ffd400",
		splitChannels: false,
		useWebWorker: true,
		scale: settings.isLite ? "linear" : settings.scale,
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
			minPxPerSec: Math.max(4, Math.min(12, Math.round(settings.renderCols / 512))),
			autoScroll: false,
			plugins: [spectrogramPlugin],
		});
	} catch (error) {
		sendInfo(`Spectrogram render failed: ${String(error)}`);
		console.error("WaveSurfer initialization failed:", error);
		return;
	}

	spectrogramPlugin.on("ready", () => {
		if (renderWatchdogTimer) {
			clearTimeout(renderWatchdogTimer);
			renderWatchdogTimer = null;
		}
	});

	renderWatchdogTimer = setTimeout(() => {
		if (qualityMode === "normal" && currentAudioUrl === audioUrl) {
			sendInfo("Spectrogram rendering is heavy; retrying in compatibility mode...");
			createWaveSurfer(audioUrl, startAtSec, autoplay, "lite");
		}
	}, 7000);

	wavesurfer.on("ready", () => {
		if (startAtSec > 0) {
			wavesurfer.setTime(startAtSec);
		}
		if (autoplay) {
			wavesurfer.play();
		}
		if (currentAudioName) {
			sendInfo(`Loaded: ${currentAudioName}${qualityMode === "lite" ? " (compatibility mode)" : ""}`);
		} else {
			sendInfo("Audio loaded.");
		}
	});

	wavesurfer.on("loading", (percent) => {
		sendInfo(`Loading audio... ${Math.max(0, Math.min(100, Math.round(percent)))}%`);
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

// Load spectrogram HTML from 0021_SPECTOGRAM.html
fetch("0021_SPECTOGRAM.html")
	.then((response) => response.text())
	.then((html) => {
		document.getElementById("spectrogramContainer").innerHTML = html;

		fileInput = document.getElementById("audioFileInput");
		waveformEl = document.getElementById("waveform");
		spectrogramEl = document.getElementById("spectrogramCanvas");

		attachSpectrogramListeners();
		sendInfo("Select an audio file to render spectrogram.");
	})
	.catch((error) => console.error("Error loading spectrogram:", error));
