// Chart.js wrapper pour éviter les erreurs
window.createMiniChart = function(canvasId, data, color) {
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded yet');
        return;
    }
    
    // Détruire le chart existant s'il y en a un
    const existingChart = Chart.getChart(canvasId);
    if (existingChart) {
        existingChart.destroy();
    }
    
    const ctx = document.getElementById(canvasId).getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['', '', '', '', '', ''],
            datasets: [{
                data: data,
                borderColor: color,
                borderWidth: 2,
                fill: false,
                tension: 0.4,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: { display: false },
                y: { display: false }
            }
        }
    });
};
