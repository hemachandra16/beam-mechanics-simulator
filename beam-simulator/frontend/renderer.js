/**
 * Beam Mechanics Simulator — Renderer Process
 * =============================================
 * Handles all UI logic: Chart.js plots, SVG beam diagram,
 * slider events, animation, material selection, and AI explain.
 */

/* global Chart */

const { ipcRenderer } = require('electron');

// ---------------------------------------------------------------------------
// STATE
// ---------------------------------------------------------------------------
let currentMaterial = 'Steel';
let lastResults = null;
let animTimer = null;
let animStep = 0;
let animTarget = 0;
const ANIM_STEPS = 50;
let prevSafe = true;
let breakWarningTimeout = null;

// ---------------------------------------------------------------------------
// CHART.JS SETUP — created once on load
// ---------------------------------------------------------------------------
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
        legend: { display: false }
    }
};

const axisStyle = {
    grid: { color: '#1e1e1e', lineWidth: 0.5 },
    ticks: { color: '#9E9E9E', font: { size: 9, family: "'Courier New'" } },
    border: { color: '#2a2a2a' }
};

const tooltipStyle = {
    backgroundColor: '#111',
    borderColor: '#E8A838',
    borderWidth: 1,
    titleColor: '#E8A838',
    bodyColor: '#F5F5F5',
    titleFont: { size: 9, family: "'Courier New'" },
    bodyFont: { size: 9, family: "'Courier New'" },
    displayColors: false
};

// SFD Chart
const sfdChart = new Chart(document.getElementById('sfd-chart'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Positive SFD',
                data: [],
                fill: true,
                backgroundColor: 'rgba(79,195,247,0.25)',
                borderColor: '#4FC3F7',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0,
                spanGaps: true
            },
            {
                label: 'Negative SFD',
                data: [],
                fill: true,
                backgroundColor: 'rgba(239,83,80,0.2)',
                borderColor: '#EF5350',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0,
                spanGaps: true
            }
        ]
    },
    options: {
        ...chartDefaults,
        scales: {
            x: {
                ...axisStyle,
                title: { display: true, text: 'Position (m)',
                         color: '#9E9E9E', font: { size: 9 } }
            },
            y: {
                ...axisStyle,
                title: { display: true, text: 'Shear Force (N)',
                         color: '#9E9E9E', font: { size: 9 } }
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                ...tooltipStyle,
                callbacks: {
                    title: function(items) {
                        return 'x = ' + items[0].label + ' m';
                    },
                    label: function(ctx) {
                        return 'V = ' + ctx.parsed.y.toFixed(1) + ' N';
                    }
                }
            }
        }
    }
});

// BMD Chart
const bmdChart = new Chart(document.getElementById('bmd-chart'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'BMD',
                data: [],
                fill: true,
                backgroundColor: 'rgba(102,187,106,0.25)',
                borderColor: '#66BB6A',
                borderWidth: 1.5,
                pointRadius: 0,
                tension: 0
            }
        ]
    },
    options: {
        ...chartDefaults,
        scales: {
            x: {
                ...axisStyle,
                title: { display: true, text: 'Position (m)',
                         color: '#9E9E9E', font: { size: 9 } }
            },
            y: {
                ...axisStyle,
                title: { display: true, text: 'Moment (N\u00b7m)  [Indian convention: sagging ↓]',
                         color: '#9E9E9E', font: { size: 9 } }
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                ...tooltipStyle,
                callbacks: {
                    title: function(items) {
                        return 'x = ' + items[0].label + ' m';
                    },
                    label: function(ctx) {
                        // M is already negated (Indian convention), so display abs value
                        return 'M = ' + Math.abs(ctx.parsed.y).toFixed(1) + ' N\u00b7m (sagging)';
                    }
                }
            }
        }
    }
});

// ---------------------------------------------------------------------------
// SVG BEAM DIAGRAM
// ---------------------------------------------------------------------------
function drawBeam(results) {
    const svg = document.getElementById('beam-svg');
    const rect = svg.getBoundingClientRect();
    const W = rect.width;
    const H = rect.height;

    // Clear
    svg.innerHTML = '';

    const L = results.L;
    const P = results.P;
    const a = results.a;
    const w = results.w;
    const R_A = results.R_A;
    const R_B = results.R_B;

    // Coordinate mapping: 7.5% margin on each side
    const marginX = W * 0.075;
    const beamW = W - 2 * marginX;
    const beamY = H * 0.5;

    function xPos(xVal) {
        return marginX + (xVal / L) * beamW;
    }

    function svgEl(tag, attrs) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [k, v] of Object.entries(attrs)) {
            el.setAttribute(k, v);
        }
        return el;
    }

    function svgText(x, y, text, opts) {
        const el = svgEl('text', {
            x: x, y: y,
            fill: opts.fill || '#9E9E9E',
            'font-size': opts.size || '8',
            'font-family': "'Courier New', monospace",
            'font-weight': opts.bold ? '700' : '400',
            'text-anchor': opts.anchor || 'middle',
            'dominant-baseline': opts.baseline || 'auto'
        });
        el.textContent = text;
        return el;
    }

    // -- Beam line --
    const beam = svgEl('line', {
        x1: xPos(0), y1: beamY,
        x2: xPos(L), y2: beamY,
        stroke: '#4FC3F7', 'stroke-width': '5',
        'stroke-linecap': 'round'
    });
    svg.appendChild(beam);

    // -- Support triangles --
    const triH = 16;
    const triW = 14;
    for (const sx of [0, L]) {
        const cx = xPos(sx);
        const points = [
            (cx - triW) + ',' + (beamY + triH),
            (cx + triW) + ',' + (beamY + triH),
            cx + ',' + beamY
        ].join(' ');
        svg.appendChild(svgEl('polygon', {
            points: points,
            fill: '#E8A838',
            stroke: '#E8A838',
            'stroke-width': '1'
        }));
    }

    // -- UDL arrows --
    if (w > 0) {
        const nArrows = Math.min(20, Math.max(8, Math.round(L * 3)));
        const udlTop = beamY - 38;

        // Top bar
        svg.appendChild(svgEl('line', {
            x1: xPos(0.02 * L), y1: udlTop,
            x2: xPos(0.98 * L), y2: udlTop,
            stroke: '#4FC3F7', 'stroke-width': '1.5'
        }));

        // Arrows
        for (let i = 0; i < nArrows; i++) {
            const xi = L * (0.02 + 0.96 * i / (nArrows - 1));
            const px = xPos(xi);

            // Arrow line
            svg.appendChild(svgEl('line', {
                x1: px, y1: udlTop,
                x2: px, y2: beamY - 4,
                stroke: '#4FC3F7', 'stroke-width': '1'
            }));
            // Arrow head
            const headSize = 4;
            const headPts = [
                (px - headSize) + ',' + (beamY - 4 - headSize),
                (px + headSize) + ',' + (beamY - 4 - headSize),
                px + ',' + (beamY - 4)
            ].join(' ');
            svg.appendChild(svgEl('polygon', {
                points: headPts,
                fill: '#4FC3F7'
            }));
        }

        // UDL label
        svg.appendChild(svgText(xPos(L / 2), udlTop - 6,
            'UDL = ' + w.toFixed(0) + ' N/m',
            { fill: '#4FC3F7', size: '9', bold: true }
        ));
    }

    // -- Point load arrow --
    if (P > 0) {
        const px = xPos(a);
        const arrowTop = beamY - 42 - (w > 0 ? 30 : 0);
        const arrowBottom = beamY - 4;

        // Arrow shaft
        svg.appendChild(svgEl('line', {
            x1: px, y1: arrowTop,
            x2: px, y2: arrowBottom,
            stroke: '#EF5350', 'stroke-width': '2.5'
        }));
        // Arrow head
        const hs = 6;
        const headPts = [
            (px - hs) + ',' + (arrowBottom - hs),
            (px + hs) + ',' + (arrowBottom - hs),
            px + ',' + arrowBottom
        ].join(' ');
        svg.appendChild(svgEl('polygon', {
            points: headPts,
            fill: '#EF5350'
        }));
        // Label
        svg.appendChild(svgText(px, arrowTop - 4,
            'P = ' + P.toFixed(0) + ' N',
            { fill: '#EF5350', size: '9', bold: true }
        ));
    }

    // -- Reaction labels --
    svg.appendChild(svgText(xPos(0), beamY + triH + 14,
        'A', { fill: '#E8A838', size: '9', bold: true }
    ));
    svg.appendChild(svgText(xPos(0), beamY + triH + 25,
        'R_A=' + R_A.toFixed(1) + 'N',
        { fill: '#E8A838', size: '7' }
    ));
    svg.appendChild(svgText(xPos(L), beamY + triH + 14,
        'B', { fill: '#E8A838', size: '9', bold: true }
    ));
    svg.appendChild(svgText(xPos(L), beamY + triH + 25,
        'R_B=' + R_B.toFixed(1) + 'N',
        { fill: '#E8A838', size: '7' }
    ));

    // -- Dimension line --
    const dimY = beamY + triH + 38;
    svg.appendChild(svgEl('line', {
        x1: xPos(0), y1: dimY,
        x2: xPos(L), y2: dimY,
        stroke: '#555', 'stroke-width': '0.8'
    }));
    // End ticks
    for (const sx of [0, L]) {
        svg.appendChild(svgEl('line', {
            x1: xPos(sx), y1: dimY - 3,
            x2: xPos(sx), y2: dimY + 3,
            stroke: '#555', 'stroke-width': '0.8'
        }));
    }
    svg.appendChild(svgText(xPos(L / 2), dimY + 12,
        'L = ' + L.toFixed(1) + ' m',
        { fill: '#9E9E9E', size: '8' }
    ));

    // -- Crack at failure point --
    if (!results.safe) {
        const cx = xPos(results.x_crit);
        const crackH = 18;
        const seg = 6;
        let d = 'M ' + cx + ' ' + (beamY - crackH);
        for (let i = 0; i < 6; i++) {
            const dir = i % 2 === 0 ? 8 : -8;
            d += ' l ' + dir + ' ' + (crackH * 2 / 6);
        }
        const crack = svgEl('path', {
            d: d,
            stroke: '#EF5350',
            'stroke-width': '2.5',
            fill: 'none',
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round',
            opacity: '0.9'
        });
        svg.appendChild(crack);
    }
}

// ---------------------------------------------------------------------------
// UPDATE CHARTS
// ---------------------------------------------------------------------------
function updateCharts(results) {
    const x = results.x;
    const V = results.V;
    const M = results.M;

    // Subsample for performance — take every 5th point
    const step = 5;
    const labels = [];
    const Vpos = [];
    const Vneg = [];
    const Mdata = [];

    for (let i = 0; i < x.length; i += step) {
        labels.push(x[i].toFixed(2));
        Vpos.push(V[i] >= 0 ? V[i] : null);
        Vneg.push(V[i] < 0 ? V[i] : null);
        Mdata.push(M[i]);
    }

    sfdChart.data.labels = labels;
    sfdChart.data.datasets[0].data = Vpos;
    sfdChart.data.datasets[1].data = Vneg;
    sfdChart.update('none');

    bmdChart.data.labels = labels;
    bmdChart.data.datasets[0].data = Mdata;
    bmdChart.update('none');
}

// ---------------------------------------------------------------------------
// UPDATE UI — INPUTS + RESULTS
// ---------------------------------------------------------------------------
function updateUI(results) {
    // Do NOT change the panel label here — it is controlled by
    // animate (sets Outputs) and reset/slider (sets Inputs)

    // Inputs panel values
    document.getElementById('inp-L').textContent = results.L.toFixed(1) + ' m';
    document.getElementById('inp-P').textContent =
        results.P.toFixed(0) + ' N @ ' + results.a.toFixed(1) + ' m';
    document.getElementById('inp-UDL').textContent = results.w.toFixed(0) + ' N/m';
    document.getElementById('inp-D').textContent = results.D_mm.toFixed(0) + ' mm';
    document.getElementById('inp-mat').textContent = results.material;

    // Results strip
    document.getElementById('res-RA').textContent = results.R_A + ' N';
    document.getElementById('res-RB').textContent = results.R_B + ' N';

    var absVmax = Math.max(Math.abs(results.V_max), Math.abs(results.V_min));
    document.getElementById('res-Vmax').textContent = absVmax.toFixed(1) + ' N';
    document.getElementById('res-Mmax').textContent = results.M_max + ' N*m';
    document.getElementById('res-sigma').textContent = results.sigma_mpa + ' MPa';
    document.getElementById('res-yield').textContent = results.yield_mpa + ' MPa';
    document.getElementById('res-fos').textContent = results.FOS;

    var badge = document.getElementById('res-safety');
    var stressCard = document.getElementById('stress-card');

    if (results.safe) {
        badge.textContent = '[SAFE]';
        badge.className = 'safety-badge safe';
        stressCard.classList.remove('fail-bg');
        hideBreakAnimation();
    } else {
        badge.textContent = '[FAIL]';
        badge.className = 'safety-badge fail';
        stressCard.classList.add('fail-bg');
        // Show break animation on EVERY transition into fail,
        // or if it's the first time we see fail
        showBreakAnimation(results);
    }
    prevSafe = results.safe;
    lastResults = results;
}

// ---------------------------------------------------------------------------
// BREAK ANIMATION
// ---------------------------------------------------------------------------
function showBreakAnimation(results) {
    var overlay = document.getElementById('break-overlay');
    var warning = document.getElementById('break-warning');

    // Always update the warning text
    document.getElementById('warn-sub-text').textContent =
        'sigma = ' + results.sigma_mpa + ' MPa exceeds yield ' + results.yield_mpa + ' MPa';
    document.getElementById('warn-detail-text').textContent =
        'Critical section at x = ' + results.x_crit + ' m | FOS = ' + results.FOS;

    // Only show the big flash + popup on the first fail transition,
    // not on every slider tick while in fail state
    if (prevSafe) {
        overlay.style.display = 'block';
        // Reset CSS animation so it replays
        overlay.style.animation = 'none';
        void overlay.offsetHeight;
        overlay.style.animation = 'flashRed 0.5s ease-in-out 3';

        warning.style.display = 'block';

        if (breakWarningTimeout) clearTimeout(breakWarningTimeout);
        breakWarningTimeout = setTimeout(function() {
            warning.style.display = 'none';
            // Keep the red border overlay visible (just hide popup)
        }, 4000);
    }
}

function hideBreakAnimation() {
    document.getElementById('break-overlay').style.display = 'none';
    document.getElementById('break-warning').style.display = 'none';
    if (breakWarningTimeout) {
        clearTimeout(breakWarningTimeout);
        breakWarningTimeout = null;
    }
}

// ---------------------------------------------------------------------------
// SLIDER LABELS + FILL
// ---------------------------------------------------------------------------
function updateSliderLabels(L, P, a, w, D) {
    document.getElementById('lbl-L').textContent = L.toFixed(1) + ' m';
    document.getElementById('lbl-P').textContent = P + ' N';
    document.getElementById('lbl-pos').textContent = a.toFixed(1) + ' m';
    document.getElementById('lbl-udl').textContent = w + ' N/m';
    document.getElementById('lbl-dia').textContent = D + ' mm';

    var ids = ['sl-L', 'sl-P', 'sl-pos', 'sl-udl', 'sl-dia'];
    for (var i = 0; i < ids.length; i++) {
        var el = document.getElementById(ids[i]);
        var pct = ((el.value - el.min) / (el.max - el.min)) * 100;
        el.style.setProperty('--fill-pct', pct + '%');
    }
}

// ---------------------------------------------------------------------------
// MAIN CALCULATE — calls Flask backend
// ---------------------------------------------------------------------------
// Helper to set panel label
function setPanelLabel(mode) {
    var panelTitle = document.getElementById('panel-title');
    if (mode === 'Outputs') {
        panelTitle.textContent = 'Outputs';
        panelTitle.style.color = '#4FC3F7';
    } else {
        panelTitle.textContent = 'Inputs';
        panelTitle.style.color = '#E8A838';
    }
}

async function calculate() {
    var slL = document.getElementById('sl-L');
    var slP = document.getElementById('sl-P');
    var slPos = document.getElementById('sl-pos');
    var slUdl = document.getElementById('sl-udl');
    var slDia = document.getElementById('sl-dia');

    var L = slL.value / 100;
    var P = parseInt(slP.value);
    var maxPos = parseInt(slL.value);
    var posVal = parseInt(slPos.value);
    var a = (posVal / maxPos) * L;
    var w = parseInt(slUdl.value);
    var D = parseInt(slDia.value);

    updateSliderLabels(L, P, a, w, D);

    try {
        var resp = await fetch('http://127.0.0.1:5000/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                L: L, P: P, a: a, w: w, D: D,
                material: currentMaterial
            })
        });
        var results = await resp.json();
        drawBeam(results);
        updateCharts(results);
        updateUI(results);
    } catch (e) {
        console.error('Calculate error:', e);
    }
}

// ---------------------------------------------------------------------------
// MATERIAL SELECTION
// ---------------------------------------------------------------------------
function setMaterial(mat) {
    currentMaterial = mat;
    var materials = ['Steel', 'Aluminum', 'Timber'];
    for (var i = 0; i < materials.length; i++) {
        var m = materials[i];
        var dot = document.getElementById('dot-' + m);
        var name = document.getElementById('name-' + m);
        if (m === mat) {
            dot.className = 'mat-dot active';
            name.className = 'mat-name active';
        } else {
            dot.className = 'mat-dot';
            name.className = 'mat-name';
        }
    }
    calculate();
}

// ---------------------------------------------------------------------------
// ANIMATE
// ---------------------------------------------------------------------------
function startAnimate() {
    if (animTimer) return;
    animTarget = parseInt(document.getElementById('sl-P').value);
    animStep = 0;
    document.getElementById('sl-P').value = 0;
    document.getElementById('btn-animate').disabled = true;

    animTimer = setInterval(function() {
        animStep++;
        var val = Math.round(animTarget * animStep / ANIM_STEPS);
        document.getElementById('sl-P').value = val;
        calculate();
        if (animStep >= ANIM_STEPS) {
            clearInterval(animTimer);
            animTimer = null;
            document.getElementById('sl-P').value = animTarget;
            document.getElementById('btn-animate').disabled = false;
            // ONLY here we switch to Outputs
            setPanelLabel('Outputs');
            calculate();
        }
    }, 30);
}

// ---------------------------------------------------------------------------
// RESET
// ---------------------------------------------------------------------------
function resetAll() {
    document.getElementById('sl-L').value = 500;
    document.getElementById('sl-P').value = 1000;
    document.getElementById('sl-pos').value = 200;
    document.getElementById('sl-udl').value = 200;
    document.getElementById('sl-dia').value = 100;
    setMaterial('Steel');
    hideBreakAnimation();
    prevSafe = true;
    document.getElementById('explain-text').textContent = '';
    document.getElementById('explain-placeholder').style.display = 'block';
    // Always show Inputs on reset
    setPanelLabel('Inputs');
    calculate();
}

// ---------------------------------------------------------------------------
// AI EXPLAIN — streaming response from Groq via Flask
// ---------------------------------------------------------------------------
async function explainResults() {
    if (!lastResults) return;

    var btn = document.getElementById('explain-btn');
    var textEl = document.getElementById('explain-text');
    var placeholder = document.getElementById('explain-placeholder');

    btn.disabled = true;
    placeholder.style.display = 'none';
    textEl.innerHTML =
        '<div class="thinking-indicator">' +
        '<div class="thinking-dot"></div>' +
        '<div class="thinking-dot"></div>' +
        '<div class="thinking-dot"></div>' +
        ' Analyzing...</div>';

    try {
        var resp = await fetch('http://127.0.0.1:5000/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(lastResults)
        });

        textEl.innerHTML = '';
        var fullText = '';
        var reader = resp.body.getReader();
        var decoder = new TextDecoder();

        while (true) {
            var result = await reader.read();
            if (result.done) break;

            var chunk = decoder.decode(result.value, { stream: true });
            var lines = chunk.split('\n');

            for (var i = 0; i < lines.length; i++) {
                var line = lines[i];
                if (line.startsWith('data: ') && line !== 'data: [DONE]') {
                    try {
                        var data = JSON.parse(line.slice(6));
                        if (data.text) {
                            fullText += data.text;
                            // Strip <think>...</think> blocks from display
                            var displayText = fullText.replace(/<think>[\s\S]*?<\/think>/g, '');
                            // Also strip incomplete <think>... blocks (still streaming)
                            displayText = displayText.replace(/<think>[\s\S]*/g, '');
                            displayText = displayText.trim();
                            // Escape HTML entities first
                            var safe = displayText
                                .replace(/&/g, '&amp;')
                                .replace(/</g, '&lt;')
                                .replace(/>/g, '&gt;');
                            // Render **bold** as <b>
                            safe = safe.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
                            textEl.innerHTML = safe;
                            // Auto-scroll
                            document.getElementById('explain-panel').scrollTop =
                                document.getElementById('explain-panel').scrollHeight;
                        }
                    } catch (parseErr) {
                        // skip malformed JSON
                    }
                }
            }
        }
    } catch (e) {
        textEl.textContent =
            'Error connecting to AI service.\n' +
            'Make sure GROQ_API_KEY is set in environment variables.';
    }

    btn.disabled = false;
}

// ---------------------------------------------------------------------------
// POSITION SLIDER MAX SYNC
// ---------------------------------------------------------------------------
function syncPosSliderMax() {
    var slL = document.getElementById('sl-L');
    var slPos = document.getElementById('sl-pos');
    var newMax = parseInt(slL.value);
    slPos.max = newMax;
    if (parseInt(slPos.value) > newMax) {
        slPos.value = Math.floor(newMax / 2);
    }
}

// ---------------------------------------------------------------------------
// EVENT LISTENERS
// ---------------------------------------------------------------------------

// Sliders — keep label as Inputs while user drags
var sliderIds = ['sl-L', 'sl-P', 'sl-pos', 'sl-udl', 'sl-dia'];
for (var i = 0; i < sliderIds.length; i++) {
    document.getElementById(sliderIds[i]).addEventListener('input', function() {
        setPanelLabel('Inputs');
        calculate();
    });
}
// Beam length also syncs position slider max
document.getElementById('sl-L').addEventListener('input', syncPosSliderMax);

// Material rows
document.querySelectorAll('.mat-row').forEach(function(row) {
    row.addEventListener('click', function() {
        setMaterial(this.dataset.mat);
    });
});

// Buttons
document.getElementById('btn-animate').addEventListener('click', startAnimate);
document.getElementById('btn-reset').addEventListener('click', resetAll);
document.getElementById('explain-btn').addEventListener('click', explainResults);

// Window controls via IPC
document.getElementById('btn-min').addEventListener('click', function() {
    ipcRenderer.send('win-minimize');
});
document.getElementById('btn-max').addEventListener('click', function() {
    ipcRenderer.send('win-maximize');
});
document.getElementById('btn-close').addEventListener('click', function() {
    ipcRenderer.send('win-close');
});

// ---------------------------------------------------------------------------
// ZOOM — Ctrl+Plus / Ctrl+Minus / Ctrl+0
// ---------------------------------------------------------------------------
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && (e.key === '=' || e.key === '+')) {
        e.preventDefault();
        ipcRenderer.send('zoom-in');
    } else if (e.ctrlKey && e.key === '-') {
        e.preventDefault();
        ipcRenderer.send('zoom-out');
    } else if (e.ctrlKey && e.key === '0') {
        e.preventDefault();
        ipcRenderer.send('zoom-reset');
    }
});

// Also support Ctrl+Scroll for zoom
document.addEventListener('wheel', function(e) {
    if (e.ctrlKey) {
        e.preventDefault();
        if (e.deltaY < 0) {
            ipcRenderer.send('zoom-in');
        } else {
            ipcRenderer.send('zoom-out');
        }
    }
}, { passive: false });

// ---------------------------------------------------------------------------
// RESIZABLE PANELS
// ---------------------------------------------------------------------------
(function() {
    // Horizontal resizer: between plots-area and right-panel
    var resizerH = document.getElementById('resizer-h');
    var rightPanel = document.getElementById('right-panel');
    var draggingH = false;

    resizerH.addEventListener('mousedown', function(e) {
        e.preventDefault();
        draggingH = true;
        resizerH.classList.add('active');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    // Vertical resizer: between main/results and controls-bar
    var resizerV = document.getElementById('resizer-v');
    var controlsBar = document.getElementById('controls-bar');
    var draggingV = false;

    resizerV.addEventListener('mousedown', function(e) {
        e.preventDefault();
        draggingV = true;
        resizerV.classList.add('active');
        document.body.style.cursor = 'row-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', function(e) {
        if (draggingH) {
            // Right panel width = window width - mouseX
            var newWidth = window.innerWidth - e.clientX;
            if (newWidth >= 160 && newWidth <= 400) {
                rightPanel.style.width = newWidth + 'px';
            }
        }
        if (draggingV) {
            // Controls bar height = window height - mouseY
            var newHeight = window.innerHeight - e.clientY;
            if (newHeight >= 100 && newHeight <= 350) {
                controlsBar.style.height = newHeight + 'px';
            }
        }
    });

    document.addEventListener('mouseup', function() {
        if (draggingH) {
            draggingH = false;
            resizerH.classList.remove('active');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
        if (draggingV) {
            draggingV = false;
            resizerV.classList.remove('active');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });
})();

// ---------------------------------------------------------------------------
// INIT — first calculate on load
// ---------------------------------------------------------------------------
window.addEventListener('load', function() {
    // Set initial slider fills
    updateSliderLabels(5.0, 1000, 2.0, 200, 100);
    // Wait a moment for Flask to be ready, then calculate
    setTimeout(function() {
        calculate();
    }, 300);
});
