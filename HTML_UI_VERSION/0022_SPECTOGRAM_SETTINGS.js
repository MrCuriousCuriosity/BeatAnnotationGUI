const BA_spectrogramSettings = (() => {
	const elements = {
		modalBackdrop: document.getElementById("settingsModalBackdrop"),
		settingsEnterBtn: null,
		colormap: null,
		minFreq: null,
		maxFreq: null,
		winLen: null,
		hopLen: null,
		dbRange: null,
		normalize: null,
		melView: null,
		melRows: null,
		renderCols: null,
	};

	let onApply = null;
	let onChange = null;
	let ready = null;

	function nearestPowerOfTwo(value, min, max) {
		const clamped = Math.max(min, Math.min(max, Number(value) || min));
		const exponent = Math.round(Math.log2(clamped));
		const pow = 2 ** exponent;
		return Math.max(min, Math.min(max, pow));
	}

	function read() {
		if (!elements.colormap) {
			return {
				colormap: "magma",
				frequencyMin: 20,
				frequencyMax: 6000,
				fftSamples: 2048,
				rangeDB: 60,
				normalize: true,
				scale: "linear",
				melRows: 768,
				renderCols: 4096,
				noverlap: 1536,
			};
		}

		const minFreq = Math.max(0, Number(elements.minFreq.value) || 0);
		let maxFreq = Math.max(0, Number(elements.maxFreq.value) || 0);
		if (maxFreq <= minFreq) {
			maxFreq = minFreq + 1;
		}

		const winLenRaw = Number(elements.winLen.value);
		const hopLenRaw = Number(elements.hopLen.value);
		const fftSamples = nearestPowerOfTwo(winLenRaw, 256, 8192);
		const hopLen = Math.max(1, Math.min(fftSamples - 1, hopLenRaw));
		const noverlap = Math.max(0, fftSamples - hopLen);
		const scale = elements.melView.checked ? "mel" : "linear";

		return {
			colormap: elements.colormap.value,
			frequencyMin: minFreq,
			frequencyMax: maxFreq,
			fftSamples,
			rangeDB: Number(elements.dbRange.value),
			normalize: elements.normalize.checked,
			scale,
			melRows: Number(elements.melRows.value),
			renderCols: Number(elements.renderCols.value),
			noverlap,
		};
	}

	function open() {
		if (!elements.settingsEnterBtn) {
			return;
		}
		elements.modalBackdrop.classList.add("open");
		elements.modalBackdrop.setAttribute("aria-hidden", "false");
	}

	function close() {
		if (!elements.settingsEnterBtn) {
			return;
		}
		elements.modalBackdrop.classList.remove("open");
		elements.modalBackdrop.setAttribute("aria-hidden", "true");
	}

	function setOnApply(callback) {
		onApply = callback;
	}

	function setOnChange(callback) {
		onChange = callback;
	}

	function emitChange() {
		if (typeof onChange === "function") {
			onChange(read());
		}
	}

	function bindSliderValueLabels() {
		document.querySelectorAll("input[type='range'][data-value-target]").forEach((slider) => {
			const targetId = slider.getAttribute("data-value-target");
			const valueLabel = document.getElementById(targetId);

			function syncValue() {
				valueLabel.textContent = slider.value;
			}

			slider.addEventListener("input", syncValue);
			syncValue();
		});
	}

	function cacheElements() {
		elements.settingsEnterBtn = document.getElementById("settingsEnterBtn");
		elements.colormap = document.getElementById("colormap");
		elements.minFreq = document.getElementById("minFreq");
		elements.maxFreq = document.getElementById("maxFreq");
		elements.winLen = document.getElementById("winLen");
		elements.hopLen = document.getElementById("hopLen");
		elements.dbRange = document.getElementById("dbRange");
		elements.normalize = document.getElementById("normalize");
		elements.melView = document.getElementById("melView");
		elements.melRows = document.getElementById("melRows");
		elements.renderCols = document.getElementById("renderCols");
	}

	async function loadModalMarkup() {
		const mount = document.getElementById("settingsModalMount");
		if (!mount) {
			return;
		}

		const response = await fetch("0023_SPECTOGRAM_SETTINGS.html");
		if (!response.ok) {
			throw new Error(`Failed to load 0023_SPECTOGRAM_SETTINGS.html (${response.status})`);
		}

		mount.innerHTML = await response.text();
	}

	function bindEvents() {
		bindSliderValueLabels();

		document.querySelectorAll(".settings-modal input, .settings-modal select").forEach((control) => {
			if (control.id === "settingsEnterBtn") {
				return;
			}

			control.addEventListener("input", emitChange);
			control.addEventListener("change", emitChange);
		});

		elements.settingsEnterBtn.addEventListener("click", () => {
			if (typeof onApply === "function") {
				onApply(read());
			}
			close();
		});

		elements.modalBackdrop.addEventListener("click", (event) => {
			if (event.target === elements.modalBackdrop) {
				close();
			}
		});

		document.addEventListener("keydown", (event) => {
			if (event.key === "Escape" && elements.modalBackdrop.classList.contains("open")) {
				close();
			}
		});
	}

	async function init() {
		try {
			await loadModalMarkup();
			cacheElements();
			bindEvents();
		} catch (error) {
			console.error("Spectrogram settings initialization failed:", error);
		}
	}

	ready = init();

	return {
		elements,
		read,
		open,
		close,
		setOnApply,
		setOnChange,
		ready,
	};
})();

window.BA_spectrogramSettings = BA_spectrogramSettings;
