// Module-level variables
let spectrogramEl = null;
let wheelZoomHandler = null;
const SPECTROGRAM_VERTICAL_PADDING = 15; //Pad necessary to make the panning slider visible and interactive

function sendInfo(text) {
	const infoText = document.getElementById("infoText");
	if (infoText) {
		infoText.textContent = text;
	}
}

// Listen for audio file selection from toolbar
window.addEventListener("audioFileSelected", (event) => {
    const { url, name } = event.detail;
    sendInfo(`Loaded: ${name}`);

	//set height of spectrogram to match container
	const canvasEl = document.getElementById("spectrogramCanvas");
	const containerHeight = canvasEl ? canvasEl.clientHeight : 0;
	const spectrogramHeight = Math.max(
		120,
		containerHeight - SPECTROGRAM_VERTICAL_PADDING * 2,
	);

    const spectrogramPlugin = window.WaveSurfer.Spectrogram.create({
        container: "#spectrogramCanvas",
		useWebWorker: true,
		height: spectrogramHeight,
        labels: true,
		colorMap: "roseus",
        labelsColor: "#ffffff",
        labelsHzColor: "#ffd400",
		frequencyMax: 4000,
		frequencyMin: 20,
		fftSamples: 1024,
		dbRange: 60,
		scale: "mel",
		windowFunc: 'hann',
		normalize: true,
		maxCanvasWidth: 2048,
    });

	if (canvasEl) {
		canvasEl.style.paddingBlock = `${SPECTROGRAM_VERTICAL_PADDING}px`;
	}


	const TimelinePlugin = window.WaveSurfer.Timeline; 

    const wavesurfer = window.WaveSurfer.create({
        container: "#spectrogramCanvas",
        url: url,  // The audio blob URL
		progressColor: "#ffffff",
		cursorWidth: 3,
        sampleRate: 44100,
        height: 0, //HIDE WAVEFORM, this is for displaying the spectrogram only.
		dragToSeek: true,
        plugins: [
			spectrogramPlugin,
			TimelinePlugin.create({
				height: 30,
				timeInterval: 0.1,
				primaryLabelInterval: 5,
				secondaryLabelInterval: 1,
				style: {
					fontSize: "20px",
					color: "#33ff00",
				},
			}),
		],
    });

	wavesurfer.on("interaction", () => {
    		wavesurfer.playPause();
	});

	//Zoom functionality for spectrogram
	wavesurfer.once('decode', () => {
		const zoomTarget = document.getElementById("spectrogramCanvas");
		if (!zoomTarget) return;
		let currentZoom = 100;
		const minZoom = 10;
		const maxZoom = 1000;
		const zoomStep = 30;
		if (wheelZoomHandler) {
			zoomTarget.removeEventListener('wheel', wheelZoomHandler);
		}
		wheelZoomHandler = (e) => {
			e.preventDefault();
			const direction = e.deltaY < 0 ? -1 : 1;
			currentZoom = Math.min(maxZoom, Math.max(minZoom, currentZoom + direction * zoomStep));
			wavesurfer.zoom(currentZoom);
		};
		zoomTarget.addEventListener('wheel', wheelZoomHandler, { passive: false });
	})

	// Track loading progress, keep coments in line, i prefer this like it is
	wavesurfer.on('loading', (percent) => {console.log(`Audio loading: ${percent}%`);});
	wavesurfer.on('ready', () => {console.log("✓ WaveSurfer ready, decoding audio...");});
	wavesurfer.on('decode', () => {console.log("✓ Audio decoded, spectrogram rendering complete");});
});


// Load spectrogram HTML from 0021_SPECTOGRAM.html
fetch("0021_SPECTOGRAM.html")
	.then((response) => response.text())
	.then((html) => {
		document.getElementById("spectrogramContainer").innerHTML = html;
		spectrogramEl = document.getElementById("spectrogramCanvas");
		sendInfo("Select an audio file to render spectrogram.");
	})
	.catch((error) => console.error("Error loading spectrogram:", error));
