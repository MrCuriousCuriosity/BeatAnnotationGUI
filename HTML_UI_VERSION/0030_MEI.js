// Load MEI HTML from 0031_MEI.html
fetch('0031_MEI.html')
	.then(response => response.text())
	.then(html => {
		document.getElementById('meiContainer').innerHTML = html;
	})
	.catch(error => console.error('Error loading MEI:', error));
