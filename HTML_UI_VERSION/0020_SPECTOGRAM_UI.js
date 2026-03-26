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
		dbRange: 60,
		scale: "mel",
		windowFunc: 'hann',
	
    });
    
    const wavesurfer = window.WaveSurfer.create({
        container: "#spectrogramCanvas",
        url: url,  // The audio blob URL
        sampleRate: 44100,
        height: 0, //HIDE WAVEFORM, this is for displaying the spectrogram only.
        plugins: [spectrogramPlugin],
    });

	//Zoom functionality for spectrogram
	wavesurfer.once('decode', () => {
		const slider = document.querySelector('input[type="range"]')
		slider.addEventListener('input', (e) => {
			const minPxPerSec = e.target.valueAsNumber
			wavesurfer.zoom(minPxPerSec)
		})
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
