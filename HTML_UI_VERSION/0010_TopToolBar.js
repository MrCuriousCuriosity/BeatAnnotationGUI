// Load toolbar HTML from 0011_TopToolBar.html
fetch('0011_TopToolBar.html')
    .then(response => response.text())
    .then(html => {
        document.getElementById('toolbarContainer').innerHTML = html;
        attachToolbarEventListeners();
    })
    .catch(error => console.error('Error loading toolbar:', error));

function openFilePicker() {
    if (typeof window.BA_spectrogramCommand !== "function") {
        console.error("Spectrogram command handler is not ready.");
        return;
    }
    window.BA_spectrogramCommand("open-file");
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
}