let trendChart, deviceChart;

async function fetchData() {
    try {
        const response = await fetch('http://localhost:8000/api/dashboard');
        const data = await response.json();
        
        updateUI(data);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

function updateUI(data) {
    // 1. Update Real-time
    document.getElementById('active-users').innerText = data.realtime_active_users;
    
    // 2. Demo Mode Banner
    const banner = document.getElementById('alert-banner');
    banner.style.display = data.is_mock ? 'block' : 'none';

    // 3. Update Trend Chart
    const trendLabels = data.sessions_7d.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    });
    const trendValues = data.sessions_7d.map(d => d.sessions);

    if (trendChart) {
        trendChart.data.labels = trendLabels;
        trendChart.data.datasets[0].data = trendValues;
        trendChart.update();
    } else {
        initTrendChart(trendLabels, trendValues);
    }

    // 4. Update Top Pages
    const pageList = document.getElementById('page-list');
    const maxViews = Math.max(...data.top_pages.map(p => p.views));
    
    pageList.innerHTML = data.top_pages.map(p => `
        <div class="page-item-container">
            <div class="page-item">
                <span class="page-path">${p.page}</span>
                <span class="page-views">${p.views.toLocaleString()}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${(p.views / maxViews) * 100}%"></div>
            </div>
        </div>
    `).join('');

    // 5. Update Device Chart
    const deviceLabels = data.devices.map(d => d.category);
    const deviceValues = data.devices.map(d => d.percentage);

    if (deviceChart) {
        deviceChart.data.labels = deviceLabels;
        deviceChart.data.datasets[0].data = deviceValues;
        deviceChart.update();
    } else {
        initDeviceChart(deviceLabels, deviceValues);
    }
}

function initTrendChart(labels, values) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    trendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sessions',
                data: values,
                borderColor: '#00f2ff',
                backgroundColor: 'rgba(0, 242, 255, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: '#00f2ff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: 'rgba(255,255,255,0.5)' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: 'rgba(255,255,255,0.5)' } }
            }
        }
    });
}

function initDeviceChart(labels, values) {
    const ctx = document.getElementById('deviceChart').getContext('2d');
    deviceChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: ['#00f2ff', '#7000ff', '#ff00d4'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: 'rgba(255,255,255,0.8)', usePointStyle: true, padding: 20 }
                }
            },
            cutout: '70%'
        }
    });
}

// Initial Fetch
fetchData();

// Poll every 10 seconds for real-time feel
setInterval(fetchData, 10000);
