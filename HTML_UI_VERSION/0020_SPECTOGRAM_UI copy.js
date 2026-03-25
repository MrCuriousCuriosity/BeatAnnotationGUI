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
		case "stop":

// Minimal function: load audio file and create object URL
function loadAudioFileInput(fileInputElement, onLoad) {
	fileInputElement.addEventListener("change", (event) => {
		const file = event.target.files && event.target.files[0];
		if (!file) return;
		const audioUrl = URL.createObjectURL(file);
		if (typeof onLoad === "function") {
			onLoad(audioUrl, file);
		}
	});
}
	// Try regular DOM queries
