// Load toolbar HTML from 0011_TopToolBar.html
fetch('0011_TopToolBar.html')
    .then(response => response.text())
    .then(html => {
        document.getElementById('toolbarContainer').innerHTML = html;
        attachToolbarEventListeners();
    })
    .catch(error => console.error('Error loading toolbar:', error));

function attachToolbarEventListeners() {
    document.getElementById("openAudioBtn").addEventListener("click", () => {
        window.BA_spectrogramCommand?.("open-file");
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
}