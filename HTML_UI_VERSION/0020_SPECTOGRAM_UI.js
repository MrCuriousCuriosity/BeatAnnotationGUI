// Module-level variables
let spectrogramEl = null;

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
    const containerHeight = document.getElementById("spectrogramCanvas").offsetHeight;

    const spectrogramPlugin = window.WaveSurfer.Spectrogram.create({
        container: "#spectrogramCanvas",
		useWebWorker: true,
        height: containerHeight,
        labels: true,
        labelsColor: "#ffffff",
        labelsHzColor: "#ffd400",
		frequencyMax: 4000,
		frequencyMin: 20,
		//fftSamples: 1024,
		gainDB: 20,
		scale: "mel",
		windowFunc: 'hann',
		maxCanvasWidth: 30000,
    });
    
    const wavesurfer = window.WaveSurfer.create({
        container: "#spectrogramCanvas",
        url: url,  // The audio blob URL
        sampleRate: 44100,
        height: 0, //HIDE WAVEFORM, this is for displaying the spectrogram only.
        plugins: [spectrogramPlugin],
    });
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
