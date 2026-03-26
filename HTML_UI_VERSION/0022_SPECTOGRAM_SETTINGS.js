const BA_spectrogramSettings = (() => {
	const elements = {
		modalBackdrop: document.getElementById("settingsModalBackdrop"),
		settingsEnterBtn: null,
		colormap: null,
		minFreq: null,
		maxFreq: null,
		dbRange: null,
	};

	let onApply = null;
	let onChange = null;
	let ready = null;

	function read() {
		if (!elements.colormap) {
			return {
				colormap: "roseus",
				frequencyMin: 20,
				frequencyMax: 4000,
				rangeDB: 60,
				normalize: true,
				scale: "linear",
			};
		}

		const minFreq = Math.max(0, Number(elements.minFreq.value) || 0);
		let maxFreq = Math.max(0, Number(elements.maxFreq.value) || 0);
		if (maxFreq <= minFreq) {
			maxFreq = minFreq + 1;
		}

		return {
			colormap: elements.colormap.value,
			frequencyMin: minFreq,
			frequencyMax: maxFreq,
			rangeDB: Number(elements.dbRange.value),
			normalize: true,
			scale: "linear",
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
		elements.dbRange = document.getElementById("dbRange");
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
