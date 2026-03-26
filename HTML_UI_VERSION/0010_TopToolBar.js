// Load toolbar HTML from 0011_TopToolBar.html
fetch('0011_TopToolBar.html')
    .then(response => response.text())
    .then(html => {
        document.getElementById('toolbarContainer').innerHTML = html;
        attachToolbarEventListeners();
    })
    .catch(error => console.error('Error loading toolbar:', error));

// Global variable to store selected audio file
window.userSelectedAudio = null;

//Action/Text display on toolbar
function sendInfo(text) {
	const infoText = document.getElementById("infoText");
	if (infoText) {
		infoText.textContent = text;
	}
}
function handleCommand(command) {
	switch (command) {
		case "open-file":
			document.getElementById("audioFileInput")?.click();
			break;
		case "youtube":
			sendInfo("YouTube loading was not implemented yet");
			break;
		case "open-settings":
			sendInfo("Settings menu is disabled.");
			break;
		case "play-toggle":
			sendInfo("Play/pause button hit.");
			break;
		case "stop":
			sendInfo("Add your WaveSurfer stop logic here.");
			break;
		case "quit":
			sendInfo("Select an audio file to render spectrogram.");
			break;
		default:
			break;
	}
}

window.BA_spectrogramCommand = handleCommand;

function openFilePicker() {
    const audioInput = document.getElementById("audioFileInput");
    if (!audioInput) {
        console.error("Audio input element is not ready.");
        return;
    }
    audioInput.click();
}

function openMeiFilePicker() {
    const meiInput = document.getElementById("meiFileInput");
    if (!meiInput) {
        console.error("MEI input element is not ready.");
        return;
    }
    meiInput.click();
}

function attachToolbarEventListeners() {
    document.getElementById("openAudioBtn").addEventListener("click", () => {
        openFilePicker();
    });

    document.getElementById("openMeiBtn").addEventListener("click", () => {
        openMeiFilePicker();
    });

    document.getElementById("youtubeBtn").addEventListener("click", () => {
        window.BA_spectrogramCommand?.("youtube");
    });

    document.getElementById("spectogramSettingsBtn").addEventListener("click", () => {
        window.BA_spectrogramCommand?.("open-settings");
    });

    document.getElementById("playBtn").addEventListener("click", () => {
        window.BA_spectrogramCommand?.("play-toggle");
    });

    document.getElementById("stopBtn").addEventListener("click", () => {
        window.BA_spectrogramCommand?.("stop");
    });
    
    document.getElementById("quitBtn").addEventListener("click", () => {
        window.BA_spectrogramCommand?.("quit");
    });

    // Set up MEI file input handler
    const meiFileInput = document.getElementById("meiFileInput");
    if (meiFileInput) {
        meiFileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                handleMeiFileSelection(file);
            }
        });
    }

    // Set up audio file input handler
    const audioFileInput = document.getElementById("audioFileInput");
    if (audioFileInput) {
        audioFileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                // Revoke old URL if it exists
                if (window.userSelectedAudio && window.userSelectedAudio.startsWith("blob:")) {
                    URL.revokeObjectURL(window.userSelectedAudio);
                }
                // Store new audio file URL and notify listeners
                window.userSelectedAudio = URL.createObjectURL(file);
                window.dispatchEvent(new CustomEvent("audioFileSelected", { 
                    detail: { url: window.userSelectedAudio, name: file.name } 
                }));
                audioFileInput.value = "";
            }
        });
    }
}