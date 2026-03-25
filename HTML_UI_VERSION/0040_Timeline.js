// Load timeline HTML from 0041_Timeline.html
fetch('0041_Timeline.html')
    .then(response => response.text())
    .then(html => {
        document.getElementById('timelineContainer').innerHTML = html;
    })
    .catch(error => console.error('Error loading timeline:', error));