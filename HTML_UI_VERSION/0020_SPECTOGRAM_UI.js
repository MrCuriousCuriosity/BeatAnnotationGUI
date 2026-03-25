// Module-level variables
let wavesurfer = null;
let currentAudioUrl = null;
let currentAudioName = null;
let liveUpdateTimer = null;
let renderWatchdogTimer = null;
let fileInput = null;
let waveformEl = null;
let spectrogramEl = null;
let playbackCursorEl = null;
let timeRulerEl = null;
let layoutSyncListenerBound = false;
let interactionsBound = false;
let timelineScrollBoundEl = null;
let currentMinPxPerSec = 4;
let calculatedMinZoom = 2; // Stores the full-audio zoom level (max zoom out)
const TIME_RULER_HEIGHT_PX = 24;
const ZOOM_MIN_PX_PER_SEC = 2;  // Fallback minimum (original default)
const ZOOM_MAX_PX_PER_SEC = 320;
const ZOOM_FACTOR = 1.15;

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

function ensurePlaybackCursor() {
	if (!spectrogramEl) {
		return;
	}
	if (playbackCursorEl && playbackCursorEl.isConnected) {
		return;
	}
	playbackCursorEl = document.createElement("div");
	playbackCursorEl.className = "spectrogram-playback-cursor";
	spectrogramEl.appendChild(playbackCursorEl);
}

function updatePlaybackCursor() {
	if (!wavesurfer || !spectrogramEl) {
		return;
	}
	ensurePlaybackCursor();
	if (!playbackCursorEl) {
		return;
	}
	const duration = wavesurfer.getDuration();
	if (!duration || duration <= 0) {
		playbackCursorEl.style.left = "0px";
		return;
	}
	const scrollTarget = getTimelineScrollElement();
	const scrollLeft = scrollTarget ? scrollTarget.scrollLeft : 0;
	const currentTime = wavesurfer.getCurrentTime();
	const worldX = currentTime * Math.max(1, currentMinPxPerSec);
	const x = Math.round(worldX - scrollLeft);
	playbackCursorEl.style.left = `${x}px`;
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
		spectrogramEl.querySelector('.scroll'),
		spectrogramEl.querySelector('[class*="scroll"]'),
		spectrogramEl.querySelector('canvas')?.parentElement,
	];
	for (const el of candidates) {
		if (el && el.scrollWidth > el.clientWidth) {
			return el;
		}
	}
	// Fallback
	return spectrogramEl;
}

let lastScrollLeft = 0;
let scrollSyncAnimationFrame = null;

function bindTimelineScrollSync() {
	const nextEl = getTimelineScrollElement();
	if (!nextEl) {
		return;
	}
	if (timelineScrollBoundEl === nextEl) {
		return;
	}
	if (timelineScrollBoundEl) {
		timelineScrollBoundEl.removeEventListener("scroll", handleTimelineScroll);
	}
	timelineScrollBoundEl = nextEl;
	nextEl.addEventListener("scroll", handleTimelineScroll);
	lastScrollLeft = nextEl.scrollLeft || 0;
	
	// Add backup continuous sync for when scroll events don't fire reliably
	if (scrollSyncAnimationFrame) {
		cancelAnimationFrame(scrollSyncAnimationFrame);
	}
	function continuousScrollSync() {
		if (timelineScrollBoundEl) {
			const currentScroll = timelineScrollBoundEl.scrollLeft || 0;
			if (Math.abs(currentScroll - lastScrollLeft) > 0.5) {
				lastScrollLeft = currentScroll;
				// renderTimeRuler();
				// updatePlaybackCursor();
			}
		}
		scrollSyncAnimationFrame = requestAnimationFrame(continuousScrollSync);
	}
	scrollSyncAnimationFrame = requestAnimationFrame(continuousScrollSync);
}

function handleTimelineScroll() {
	// renderTimeRuler();
	// updatePlaybackCursor();
}

function formatTimeLabel(totalSeconds) {
	const sec = Math.max(0, Math.floor(totalSeconds));
	const hours = Math.floor(sec / 3600);
	const minutes = Math.floor((sec % 3600) / 60);
	const seconds = sec % 60;
	if (hours > 0) {
		return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
	}
	return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function calculateFullAudioZoom() {
	if (!spectrogramEl || !wavesurfer) {
		return ZOOM_MIN_PX_PER_SEC;
	}
	const duration = wavesurfer.getDuration();
	const containerWidth = spectrogramEl.clientWidth;
	if (duration <= 0 || containerWidth <= 0) {
		return ZOOM_MIN_PX_PER_SEC;
	}
	// Calculate pxPerSec needed to fit entire audio in container
	const fullAudioZoom = containerWidth / duration;
	// Clamp to reasonable bounds
	return Math.max(ZOOM_MIN_PX_PER_SEC, Math.min(ZOOM_MAX_PX_PER_SEC, fullAudioZoom));
}

function pickTickStep(durationSec) {
	const steps = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 20, 30, 60, 120, 300, 600, 900, 1800];
	const targetTicks = 16;
	const desired = Math.max(0.1, durationSec / targetTicks);
	for (const step of steps) {
		if (step >= desired) {
			return step;
		}
	}
	return steps[steps.length - 1];
}

function ensureTimeRuler() {
	if (!spectrogramEl) {
		return;
	}
	if (timeRulerEl && timeRulerEl.isConnected) {
		return;
	}
	timeRulerEl = document.createElement("div");
	timeRulerEl.className = "spectrogram-time-ruler";
	spectrogramEl.appendChild(timeRulerEl);
}

function renderTimeRuler() {
	if (!spectrogramEl || !wavesurfer) {
		return;
	}
	ensureTimeRuler();
	if (!timeRulerEl) {
		return;
	}
	const duration = wavesurfer.getDuration();
	const width = spectrogramEl.clientWidth;
	const scrollTarget = getTimelineScrollElement();
	const scrollLeft = scrollTarget ? scrollTarget.scrollLeft : 0;
	timeRulerEl.innerHTML = "";
	if (!duration || duration <= 0 || width <= 0) {
		return;
	}
	const pxPerSec = Math.max(1, currentMinPxPerSec);
	const visibleStartTime = Math.max(0, scrollLeft / pxPerSec);
	const visibleEndTime = Math.min(duration, (scrollLeft + width) / pxPerSec);
	const visibleDuration = Math.max(0.001, visibleEndTime - visibleStartTime);

	const step = pickTickStep(visibleDuration);
	const pixelsPerStep = step * pxPerSec;
	const labelEvery = Math.max(1, Math.ceil(72 / Math.max(1, pixelsPerStep)));
	let index = 0;
	const startTickTime = Math.floor(visibleStartTime / step) * step;

	for (let t = startTickTime; t <= visibleEndTime + step * 0.5; t += step) {
		const timeSec = Math.min(duration, t);
		const x = Math.round(timeSec * pxPerSec - scrollLeft);

		const tick = document.createElement("div");
		tick.className = "spectrogram-time-tick";
		tick.style.left = `${x}px`;
		timeRulerEl.appendChild(tick);

		const isFinalTick = duration - timeSec < step * 0.5;
		if (index % labelEvery === 0 || isFinalTick) {
			const label = document.createElement("span");
			label.className = "spectrogram-time-label";
			label.style.left = `${x}px`;
			label.textContent = formatTimeLabel(timeSec);
			timeRulerEl.appendChild(label);
		}

		if (isFinalTick) {
			break;
		}
		index += 1;
	}
}

function applyZoom(nextMinPxPerSec, anchorClientX) {
	if (!wavesurfer || !spectrogramEl) {
		return;
	}
	const clamped = Math.max(calculatedMinZoom, Math.min(ZOOM_MAX_PX_PER_SEC, nextMinPxPerSec));
	if (Math.abs(clamped - currentMinPxPerSec) < 0.001) {
		return;
	}

	const rect = spectrogramEl.getBoundingClientRect();
	const anchorX = Math.max(0, Math.min(rect.width, anchorClientX - rect.left));
	const previousZoom = currentMinPxPerSec;
	const scrollTarget = getTimelineScrollElement();
	if (!scrollTarget) {
		return;
	}
	const previousScrollLeft = scrollTarget.scrollLeft;
	const anchorWorldBefore = previousScrollLeft + anchorX;

	if (typeof wavesurfer.zoom === "function") {
		wavesurfer.zoom(clamped);
	} else if (typeof wavesurfer.setOptions === "function") {
		wavesurfer.setOptions({ minPxPerSec: clamped });
	}
	currentMinPxPerSec = clamped;

	requestAnimationFrame(() => {
		const activeScrollTarget = getTimelineScrollElement();
		if (!spectrogramEl || !activeScrollTarget) {
			return;
		}
			const zoomRatio = clamped / Math.max(0.0001, previousZoom);
		activeScrollTarget.scrollLeft = Math.max(0, anchorWorldBefore * zoomRatio - anchorX);
		// renderTimeRuler();
		// updatePlaybackCursor();
	});
}

function bindZoomAndPanInteractions() {
	if (interactionsBound || !spectrogramEl) {
		return;
	}
	interactionsBound = true;

	spectrogramEl.addEventListener(
		"wheel",
		(event) => {
			if (!wavesurfer) {
				return;
			}
			event.preventDefault();
			const zoomIn = event.deltaY < 0;
			const factor = zoomIn ? ZOOM_FACTOR : 1 / ZOOM_FACTOR;
			applyZoom(currentMinPxPerSec * factor, event.clientX);
		},
		{ passive: false }
	);
}

function ensureLayoutSyncListener() {
	if (layoutSyncListenerBound) {
		return;
	}
	layoutSyncListenerBound = true;
	window.addEventListener("resize", () => {
		// renderTimeRuler();
		// updatePlaybackCursor();
	});
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
	currentMinPxPerSec = Math.max(4, Math.min(12, Math.round(settings.renderCols / 512)));

	waveformEl.hidden = true;
	spectrogramEl.hidden = false;
	// ensurePlaybackCursor();
	// ensureTimeRuler();
	ensureLayoutSyncListener();
	bindZoomAndPanInteractions();

	const spectrogramPlugin = window.WaveSurfer.Spectrogram.create({
		container: "#spectrogramCanvas",
		height: Math.max(80, spectrogramEl.clientHeight - TIME_RULER_HEIGHT_PX),
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
			minPxPerSec: currentMinPxPerSec,
			autoScroll: false,
			plugins: [spectrogramPlugin],
		});
	} catch (error) {
		sendInfo(`Spectrogram render failed: ${String(error)}`);
		console.error("WaveSurfer initialization failed:", error);
		return;
	}

	requestAnimationFrame(() => {
		bindTimelineScrollSync();
		// renderTimeRuler();
		// updatePlaybackCursor();
	});

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
		bindTimelineScrollSync();
		// Calculate and apply the full-audio zoom as the maximum zoom-out point
		calculatedMinZoom = calculateFullAudioZoom();
		const fullAudioZoomPixelsPerSec = calculatedMinZoom;
		if (Math.abs(fullAudioZoomPixelsPerSec - currentMinPxPerSec) > 0.001) {
			applyZoom(fullAudioZoomPixelsPerSec, 0);
		}
		// renderTimeRuler();
		// updatePlaybackCursor();
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

	wavesurfer.on("audioprocess", () => {
		// updatePlaybackCursor();
	});

	wavesurfer.on("seek", () => {
		// renderTimeRuler();
		// updatePlaybackCursor();
	});

	wavesurfer.on("finish", () => {
		// updatePlaybackCursor();
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
