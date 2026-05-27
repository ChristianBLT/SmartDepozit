// static/dashboard.js
function initDashboardCharts(statsData) {
    const categories = ['Pantofi', 'Haine', 'Altele'];
    const colors = ['#6366f1', '#10b981', '#f59e0b'];

    const safeNumber = (value) => Number(value || 0);
    const percentOf = (part, total) => (total ? Math.round((part / total) * 100) : 0);

    // Loop prin toate depozitele primite în obiectul statsData
    for (const depozitId of Object.keys(statsData)) {
        const canvas = document.getElementById(`chart-${depozitId}`);
        if (!canvas) continue; // Dacă nu găsește canvas-ul, trece mai departe

        const ctx = canvas.getContext('2d');
        const data = statsData[depozitId];
        const pantof = safeNumber(data.Pantof);
        const haine = safeNumber(data.Haine);
        const altele = safeNumber(data.Altele);
        const total = pantof + haine + altele;

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: categories,
                datasets: [{
                    data: [pantof, haine, altele],
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
                            label: (item) => {
                                const percent = percentOf(item.raw, total);
                                return ` ${item.label}: ${item.raw} articole (${percent}%)`;
                            }
                        }
                    }
                },
                cutout: '72%',
                responsive: true,
                maintainAspectRatio: false,
                animation: { animateScale: true, duration: 1000, easing: 'easeOutBack' }
            }
        });
    }
}