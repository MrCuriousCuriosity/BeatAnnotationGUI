let fileInput = null;

fetch('0021_SPECTOGRAM.html')
	.then(response => response.text())
	.then(html => {
		document.getElementById('spectrogramContainer').innerHTML = html;

		const ws = WaveSurfer.create({
			container: '#spectrogramCanvas',
			waveColor: 'rgb(200, 0, 200)',
			progressColor: 'rgb(100, 0, 100)',
			url: "/Users/fernando/Documents/ANTONIO!/BT-Tests/Peças de Piano/ClairDeLune/DEBUSSY ClairDeLune.wav",
			sampleRate: 44100,
		});

		ws.registerPlugin(
			Spectrogram.create({
				container: "#spectrogramCanvas",
				labels: true,
				height: 200,
				scale: "mel",
				frequencyMax: 22050,
				frequencyMin: 20,
				colorMap: "roseus",
				useWebWorker: true,
			}),
		);
	})
	.catch(error => console.error('Error loading Audio:', error));

