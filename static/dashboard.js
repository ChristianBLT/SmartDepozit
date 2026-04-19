// static/dashboard.js
function initDashboardCharts(statsData) {
    const categories = ['Pantofi', 'Haine', 'Altele'];
    const colors = ['#6366f1', '#10b981', '#f59e0b'];

    // Loop prin toate depozitele primite în obiectul statsData
    Object.keys(statsData).forEach(depozitId => {
        const canvas = document.getElementById(`chart-${depozitId}`);
        if (!canvas) return; // Dacă nu găsește canvas-ul, trece mai departe

        const ctx = canvas.getContext('2d');
        const data = statsData[depozitId];

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: categories,
                datasets: [{
                    data: [data.Pantof || 0, data.Haine || 0, data.Altele || 0],
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 15
                }]
            },
            options: {
                plugins: {
                    legend: {
                        display: true,
                        position: 'right', // Mutat la dreapta ca să nu mai stea strivit sub cerc
                        labels: { 
                            boxWidth: 12, 
                            padding: 20,
                            font: { size: 13, weight: '600', family: 'Inter' } 
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        padding: 12,
                        callbacks: {
                            label: (item) => ` ${item.label}: ${item.raw} articole`
                        }
                    }
                },
                cutout: '72%',
                responsive: true,
                maintainAspectRatio: false,
                animation: { animateScale: true, duration: 1000 }
            }
        });
    });
}