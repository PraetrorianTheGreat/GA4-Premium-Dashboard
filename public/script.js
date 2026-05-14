/* ============================================================
   INSIGHT PRO — Frontend Logic
   ============================================================ */

const BASE_API_URL = 'https://ga4-dashboard-117247725878.us-central1.run.app';
const API_URL = `${BASE_API_URL}/api/dashboard`;
const AI_URL  = `${BASE_API_URL}/api/ai-insights`;
const REFRESH_MS = 300000; // 5 minutes
const AI_REFRESH_MS = 600000; // 10 minutes

const DEVICE_COLORS = ['#00eeff', '#7c3aed', '#f472b6', '#34d399'];

let trendChart = null;
let deviceChart = null;

// ── Utility ──────────────────────────────────────────────────

function animateValue(el, from, to, duration = 800) {
    const start = performance.now();
    const update = (time) => {
        const p = Math.min((time - start) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(from + (to - from) * eased).toLocaleString();
        if (p < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
}

function setLive(isLive) {
    const badge = document.getElementById('live-badge');
    const label = document.getElementById('live-label');
    if (isLive) {
        badge.classList.add('live');
        label.textContent = 'Live';
    } else {
        badge.classList.remove('live');
        label.textContent = 'Demo';
    }
}

function setLastUpdated() {
    const el = document.getElementById('last-updated');
    if (el) el.textContent = 'Updated ' + new Date().toLocaleTimeString();
}

// ── Charts ───────────────────────────────────────────────────

function buildTrendChart(labels, values) {
    const ctx = document.getElementById('trendChart');
    if (!ctx) return;

    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(0,238,255,0.25)');
    gradient.addColorStop(1, 'rgba(0,238,255,0)');

    const cfg = {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Sessions',
                data: values,
                borderColor: '#00eeff',
                backgroundColor: gradient,
                borderWidth: 2.5,
                tension: 0.42,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: '#00eeff',
                pointBorderColor: '#050508',
                pointBorderWidth: 2,
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 900, easing: 'easeOutQuart' },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(10,10,20,0.9)',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    titleColor: '#fff',
                    bodyColor: '#00eeff',
                    padding: 12,
                    callbacks: {
                        label: ctx => ' ' + ctx.parsed.y.toLocaleString() + ' sessions'
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 12 } },
                    border: { display: false }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.04)' },
                    ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 12 } },
                    border: { display: false }
                }
            }
        }
    };

    if (trendChart) {
        trendChart.data.labels = labels;
        trendChart.data.datasets[0].data = values;
        trendChart.update('active');
    } else {
        trendChart = new Chart(ctx, cfg);
    }
}

function buildDeviceChart(devices) {
    const ctx = document.getElementById('deviceChart');
    if (!ctx) return;

    const labels = devices.map(d => d.category);
    const values = devices.map(d => d.percentage);
    const colors = devices.map((_, i) => DEVICE_COLORS[i % DEVICE_COLORS.length]);

    const cfg = {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '72%',
            animation: { duration: 900 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(10,10,20,0.9)',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: ctx => ' ' + ctx.label + ': ' + ctx.parsed + '%'
                    }
                }
            }
        }
    };

    if (deviceChart) {
        deviceChart.data.labels = labels;
        deviceChart.data.datasets[0].data = values;
        deviceChart.update('active');
    } else {
        deviceChart = new Chart(ctx, cfg);
    }

    // Custom legend
    const legend = document.getElementById('device-legend');
    if (legend) {
        legend.innerHTML = devices.map((d, i) => `
            <div class="legend-item">
                <span class="legend-dot" style="background:${colors[i]}"></span>
                <span class="legend-label">${d.category}</span>
                <span class="legend-pct" style="color:${colors[i]}">${d.percentage}%</span>
            </div>
        `).join('');
    }
}

function buildPageList(pages) {
    const container = document.getElementById('page-list');
    if (!container) return;
    const max = Math.max(...pages.map(p => p.views), 1);
    container.innerHTML = pages.map(p => `
        <div class="page-item">
            <span class="page-url">${p.page}</span>
            <div class="page-bar-wrap">
                <div class="page-bar-bg">
                    <div class="page-bar-fill" data-pct="${p.views / max}"></div>
                </div>
                <span class="page-views">${p.views.toLocaleString()}</span>
            </div>
        </div>
    `).join('');

    // Trigger bar animations next frame
    requestAnimationFrame(() => {
        document.querySelectorAll('.page-bar-fill').forEach(el => {
            el.style.transform = `scaleX(${el.dataset.pct})`;
        });
    });
}

async function fetchAIInsights() {
    const el = document.getElementById('ai-insights');
    if (!el) return;
    
    try {
        const res = await fetch(AI_URL, {
            headers: { 'x-api-key': sessionStorage.getItem('dashboard_pwd') || '' }
        });
        if (res.status === 401) return; // Handled by main fetch
        const data = await res.json();
        
        if (data.insights) {
            el.innerHTML = data.insights;
        }
    } catch (err) {
        console.error('AI fetch failed:', err);
    }
}

// ── KPI updates ──────────────────────────────────────────────

let prevActiveUsers = 0;
let prevTotalSessions = 0;
let prevTopViews = 0;

function updateKPIs(data) {
    const activeEl = document.getElementById('active-users');
    const sessEl   = document.getElementById('total-sessions');
    const topEl    = document.getElementById('top-page-views');
    const mobEl    = document.getElementById('mobile-share');

    const total = data.sessions_7d.reduce((a, d) => a + d.sessions, 0);
    const topViews = data.top_pages[0]?.views ?? 0;
    const mobile = data.devices.find(d => d.category.toLowerCase() === 'mobile')?.percentage ?? 0;

    animateValue(activeEl, prevActiveUsers, data.realtime_active_users);
    animateValue(sessEl, prevTotalSessions, total);
    animateValue(topEl, prevTopViews, topViews);
    mobEl.textContent = mobile + '%';

    prevActiveUsers  = data.realtime_active_users;
    prevTotalSessions = total;
    prevTopViews = topViews;

    // Trend badge
    const badge = document.getElementById('trend-badge');
    if (badge && data.sessions_7d.length >= 2) {
        const last = data.sessions_7d[data.sessions_7d.length - 1].sessions;
        const prev = data.sessions_7d[data.sessions_7d.length - 2].sessions;
        const pct = prev > 0 ? Math.round(((last - prev) / prev) * 100) : 0;
        badge.textContent = (pct >= 0 ? '▲ ' : '▼ ') + Math.abs(pct) + '% vs prev day';
        badge.style.background = pct >= 0 ? 'hsla(142,80%,55%,0.12)' : 'hsla(0,80%,55%,0.12)';
        badge.style.color = pct >= 0 ? '#34d399' : '#f87171';
    }
}

// ── Main fetch ────────────────────────────────────────────────

async function fetchAndRender() {
    try {
        const res = await fetch(API_URL, {
            headers: { 'x-api-key': sessionStorage.getItem('dashboard_pwd') || '' }
        });
        
        if (res.status === 401) {
            throw new Error('Unauthorized');
        }
        const data = await res.json();

        if (data.error && !data.is_mock) {
            console.error('API error:', data.error);
            return;
        }

        // Demo banner
        const banner = document.getElementById('demo-banner');
        if (data.is_mock) {
            banner?.classList.add('show');
            setLive(false);
        } else {
            banner?.classList.remove('show');
            setLive(true);
        }

        updateKPIs(data);

        const trendLabels = data.sessions_7d.map(d => {
            const [y, m, day] = d.date.split('');
            const dt = new Date(d.date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'));
            return dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        });
        buildTrendChart(trendLabels, data.sessions_7d.map(d => d.sessions));
        buildDeviceChart(data.devices);
        buildPageList(data.top_pages);
        setLastUpdated();

    } catch (err) {
        console.error('Fetch failed:', err);
        document.getElementById('live-label').textContent = 'Error';
    }
}

// ── Auth & Init ────────────────────────────────────────────────
const loginModal = document.getElementById('login-modal');
const dashContainer = document.getElementById('dashboard-container');
const loginBtn = document.getElementById('login-btn');
const pwdInput = document.getElementById('password-input');
const loginErr = document.getElementById('login-error');

async function attemptLogin(pwd) {
    sessionStorage.setItem('dashboard_pwd', pwd);
    try {
        const res = await fetch(API_URL, { headers: { 'x-api-key': pwd } });
        if (res.status === 401) {
            loginErr.textContent = "Incorrect password.";
            sessionStorage.removeItem('dashboard_pwd');
            return false;
        }
        return true;
    } catch (e) {
        loginErr.textContent = "Connection error.";
        return false;
    }
}

async function init() {
    const savedPwd = sessionStorage.getItem('dashboard_pwd');
    if (savedPwd) {
        loginModal.style.display = 'none';
        dashContainer.style.display = 'block';
        fetchAndRender();
        fetchAIInsights();
        setInterval(fetchAndRender, REFRESH_MS);
        setInterval(fetchAIInsights, AI_REFRESH_MS);
    } else {
        loginModal.style.display = 'flex';
        dashContainer.style.display = 'none';
    }
}

loginBtn?.addEventListener('click', async () => {
    const pwd = pwdInput.value.trim();
    if (!pwd) return;
    
    loginBtn.textContent = "Checking...";
    const success = await attemptLogin(pwd);
    loginBtn.textContent = "Unlock Dashboard";
    
    if (success) {
        loginModal.style.display = 'none';
        dashContainer.style.display = 'block';
        fetchAndRender();
        fetchAIInsights();
        setInterval(fetchAndRender, REFRESH_MS);
        setInterval(fetchAIInsights, AI_REFRESH_MS);
    }
});

pwdInput?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loginBtn.click();
});

document.getElementById('refresh-btn')?.addEventListener('click', () => {
    const btn = document.getElementById('refresh-btn');
    btn.classList.add('loading');
    Promise.all([fetchAndRender(), fetchAIInsights()]).finally(() => {
        setTimeout(() => btn.classList.remove('loading'), 800);
    });
});

init();
