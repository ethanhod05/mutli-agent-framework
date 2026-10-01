// ============================================================================
// Retro sound effects - synthesized with the Web Audio API, no audio files.
// Tied to the same real events as everything else (tool calls, task
// completions, retries, completion) - no sound plays that isn't backed by a
// real thing that just happened, live or during replay.
// ============================================================================

let audioCtx = null;
let soundEnabled = localStorage.getItem('scs_sound') !== 'off';

function ensureAudioCtx() {
  if (!soundEnabled) return null;
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
  } catch (e) {
    return null;
  }
}

function beep(freq, startOffset, duration, type = 'square', volume = 0.06) {
  const ctx = ensureAudioCtx();
  if (!ctx) return;
  try {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    const t0 = ctx.currentTime + startOffset;
    gain.gain.setValueAtTime(volume, t0);
    gain.gain.exponentialRampToValueAtTime(0.001, t0 + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t0);
    osc.stop(t0 + duration);
  } catch (e) { /* sound is a nice-to-have, never let it break the run */ }
}

const sfx = {
  toolCall: () => beep(740, 0, 0.06, 'square', 0.045),
  taskComplete: () => { beep(660, 0, 0.05, 'triangle', 0.05); beep(880, 0.06, 0.07, 'triangle', 0.05); },
  retry: () => { beep(440, 0, 0.1, 'sawtooth', 0.05); beep(220, 0.12, 0.16, 'sawtooth', 0.05); },
  complete: () => { beep(523, 0, 0.08, 'square', 0.06); beep(659, 0.09, 0.08, 'square', 0.06); beep(784, 0.18, 0.2, 'square', 0.07); },
  error: () => beep(170, 0, 0.3, 'sawtooth', 0.06),
  drop: () => { beep(300, 0, 0.04, 'square', 0.04); beep(220, 0.03, 0.05, 'square', 0.035); },
};

const soundToggle = document.getElementById('sound-toggle');
function updateSoundToggleUI() {
  soundToggle.textContent = soundEnabled ? '\u{1F50A}' : '\u{1F507}';
  soundToggle.classList.toggle('muted', !soundEnabled);
}
updateSoundToggleUI();
soundToggle.addEventListener('click', () => {
  soundEnabled = !soundEnabled;
  localStorage.setItem('scs_sound', soundEnabled ? 'on' : 'off');
  updateSoundToggleUI();
  if (soundEnabled) ensureAudioCtx();
});

// ============================================================================
// Pixel sprite rendering
// ============================================================================
// Every sprite is drawn on a <canvas> from a small pixel grid, not an image
// file - so the "art" is just data. GRID_W x GRID_H cells, HEAD_ROOM rows of
// empty space above the body for accessories (crown, antenna) to sit in.

const CELL = 8;
const GRID_W = 16;
const HEAD_ROOM = 4;
const BODY_H = 16;
const GRID_H = HEAD_ROOM + BODY_H;

// [startCol, endCol] per body row - a simple filled-blob silhouette shared
// by all four agents, like a species family; accessories + color tell them apart.
const BLOB_ROWS = [
  [5, 10], [3, 12], [2, 13], [1, 14], [1, 14], [0, 15], [0, 15], [0, 15],
  [0, 15], [0, 15], [0, 15], [1, 14], [1, 14], [2, 13], [3, 12], [5, 10],
];

function r(row) { return row + HEAD_ROOM; }

function drawBlob(ctx, colors) {
  ctx.fillStyle = colors.dark;
  BLOB_ROWS.forEach(([s, e], row) => {
    for (let col = s; col <= e; col++) ctx.fillRect(col * CELL, r(row) * CELL, CELL, CELL);
  });
  ctx.fillStyle = colors.body;
  BLOB_ROWS.forEach(([s, e], row) => {
    if (row === 0 || row === 15) return;
    for (let col = s + 1; col <= e - 1; col++) ctx.fillRect(col * CELL, r(row) * CELL, CELL, CELL);
  });
}

function drawEyes(ctx) {
  ctx.fillStyle = '#1a1730';
  ctx.fillRect(4 * CELL, r(6) * CELL, 2 * CELL, 2 * CELL);
  ctx.fillRect(10 * CELL, r(6) * CELL, 2 * CELL, 2 * CELL);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(4 * CELL, r(6) * CELL, CELL, CELL);
  ctx.fillRect(10 * CELL, r(6) * CELL, CELL, CELL);
}

function drawMagnifyingGlass(ctx) {
  ctx.fillStyle = '#2b2b40';
  ctx.fillRect(12 * CELL, r(11) * CELL, 2 * CELL, 2 * CELL);
  ctx.fillRect(13 * CELL, r(12) * CELL, 2 * CELL, 2 * CELL);
  ctx.fillRect(10 * CELL, r(8) * CELL, 4 * CELL, CELL);
  ctx.fillRect(10 * CELL, r(11) * CELL, 4 * CELL, CELL);
  ctx.fillRect(10 * CELL, r(8) * CELL, CELL, 4 * CELL);
  ctx.fillRect(13 * CELL, r(8) * CELL, CELL, 4 * CELL);
  ctx.fillStyle = '#bfe9ff';
  ctx.fillRect(11 * CELL, r(9) * CELL, 2 * CELL, 2 * CELL);
}

function drawChartBars(ctx) {
  ctx.fillStyle = '#123';
  const heights = [2, 3, 4, 3];
  heights.forEach((h, i) => {
    const col = 4 + i * 2;
    ctx.fillRect(col * CELL, r(13 - h) * CELL, CELL, h * CELL);
  });
  ctx.fillStyle = '#f4ffb0';
  heights.forEach((h, i) => {
    const col = 4 + i * 2;
    ctx.fillRect(col * CELL, r(13 - h) * CELL, CELL, CELL);
  });
}

function drawAntenna(ctx) {
  ctx.fillStyle = '#2b2b40';
  ctx.fillRect(7 * CELL, 0, 2 * CELL, 3 * CELL);
  ctx.fillStyle = '#ff8ad1';
  ctx.fillRect(6 * CELL, 0, 2 * CELL, 2 * CELL);
  ctx.fillStyle = '#2b2b40';
  ctx.fillRect(2 * CELL, 1 * CELL, 2 * CELL, CELL);
  ctx.fillRect(12 * CELL, 1 * CELL, 2 * CELL, CELL);
}

function drawCrown(ctx) {
  ctx.fillStyle = '#a3760a';
  ctx.fillRect(4 * CELL, 1 * CELL, 8 * CELL, CELL);
  ctx.fillStyle = '#ffd24d';
  ctx.fillRect(4 * CELL, 2 * CELL, 2 * CELL, CELL);
  ctx.fillRect(7 * CELL, 1 * CELL, 2 * CELL, 2 * CELL);
  ctx.fillRect(10 * CELL, 2 * CELL, 2 * CELL, CELL);
  ctx.fillRect(4 * CELL, 3 * CELL, 8 * CELL, CELL);
  ctx.fillStyle = '#ff5c5c';
  ctx.fillRect(7 * CELL, 3 * CELL, 2 * CELL, CELL);
}

const AGENTS = [
  {
    key: 'quality',
    role: 'Financial Data Quality Specialist',
    label: 'SCOUT',
    colors: { body: '#5cc8ff', dark: '#1f5f8b' },
    accessory: drawMagnifyingGlass,
    glow: '#5cc8ff',
  },
  {
    key: 'fundamentals',
    role: 'Quantitative Financial Analyst',
    label: 'ANALYST',
    colors: { body: '#5ce87a', dark: '#1f7a3a' },
    accessory: drawChartBars,
    glow: '#5ce87a',
  },
  {
    key: 'news',
    role: 'Market Intelligence Analyst',
    label: 'SCANNER',
    colors: { body: '#c97cff', dark: '#6a2f96' },
    accessory: drawAntenna,
    glow: '#c97cff',
  },
  {
    key: 'portfolio',
    role: 'Senior Portfolio Manager',
    label: 'MANAGER',
    colors: { body: '#ffd24d', dark: '#a3760a' },
    accessory: drawCrown,
    glow: '#ffd24d',
  },
];

const AGENT_BY_ROLE = Object.fromEntries(AGENTS.map(a => [a.role, a]));

function renderSprite(canvas, agent) {
  canvas.width = GRID_W * CELL;
  canvas.height = GRID_H * CELL;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawBlob(ctx, agent.colors);
  drawEyes(ctx);
  agent.accessory(ctx);
}

// ============================================================================
// Office furniture & background - same pixel-grid-via-canvas technique as
// the agent sprites, just smaller grids.
// ============================================================================

const DESK_CELL = 4;

function drawDesk(canvas, monitorColor) {
  canvas.width = 18 * DESK_CELL;
  canvas.height = 11 * DESK_CELL;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  const c = DESK_CELL;

  // Legs
  ctx.fillStyle = '#3a2817';
  ctx.fillRect(1 * c, 6 * c, 2 * c, 5 * c);
  ctx.fillRect(15 * c, 6 * c, 2 * c, 5 * c);

  // Desktop surface
  ctx.fillStyle = '#6b4a2f';
  ctx.fillRect(0, 5 * c, 18 * c, 2 * c);
  ctx.fillStyle = '#8a6440';
  ctx.fillRect(0, 5 * c, 18 * c, c);

  // Monitor
  ctx.fillStyle = '#1a1730';
  ctx.fillRect(7 * c, 0, 4 * c, 4 * c);
  ctx.fillStyle = monitorColor;
  ctx.fillRect(8 * c, 1 * c, 2 * c, 2 * c);
  ctx.fillStyle = '#1a1730';
  ctx.fillRect(8 * c, 4 * c, 2 * c, c);
}

function drawPapers(canvas) {
  canvas.width = 8 * 2;
  canvas.height = 8 * 2;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  const c = 2;
  ctx.fillStyle = '#d8d4f0';
  ctx.fillRect(0, 1 * c, 6 * c, 6 * c);
  ctx.fillStyle = '#f4f0ff';
  ctx.fillRect(1 * c, 0, 6 * c, 6 * c);
  ctx.fillStyle = '#9691bb';
  ctx.fillRect(2 * c, 2 * c, 4 * c, c);
  ctx.fillRect(2 * c, 3 * c, 4 * c, c);
  ctx.fillRect(2 * c, 4 * c, 3 * c, c);
}

function drawOfficeBackground(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth || 600;
  const h = canvas.clientHeight || 375;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const skyH = h * 0.55;
  const wallH = h * 0.12;

  // Sky seen through the office windows.
  const sky = ctx.createLinearGradient(0, 0, 0, skyH);
  sky.addColorStop(0, '#1a1740');
  sky.addColorStop(1, '#2d2763');
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, w, skyH);

  // Distant skyline silhouettes with a few lit windows - the "highrise" view.
  const buildings = [
    { x: 0.02, bw: 0.10, bh: 0.55 }, { x: 0.14, bw: 0.07, bh: 0.8 },
    { x: 0.23, bw: 0.09, bh: 0.4 }, { x: 0.35, bw: 0.08, bh: 0.65 },
    { x: 0.46, bw: 0.11, bh: 0.9 }, { x: 0.60, bw: 0.07, bh: 0.5 },
    { x: 0.70, bw: 0.09, bh: 0.72 }, { x: 0.82, bw: 0.08, bh: 0.45 },
    { x: 0.92, bw: 0.07, bh: 0.6 },
  ];
  ctx.fillStyle = '#120f28';
  buildings.forEach(b => {
    const bw = b.bw * w, bh = b.bh * skyH, bx = b.x * w, by = skyH - bh;
    ctx.fillRect(bx, by, bw, bh);
    ctx.fillStyle = '#e8c75c';
    for (let wy = by + 6; wy < skyH - 6; wy += 10) {
      for (let wx = bx + 4; wx < bx + bw - 4; wx += 8) {
        if ((wx + wy) % 3 === 0) ctx.fillRect(wx, wy, 3, 3);
      }
    }
    ctx.fillStyle = '#120f28';
  });

  // Office window mullions over the skyline.
  ctx.fillStyle = '#0d0b1a';
  for (let x = 0; x < w; x += w / 6) ctx.fillRect(x - 2, 0, 4, skyH);
  ctx.fillRect(0, skyH - 4, w, 4);

  // Wall band.
  ctx.fillStyle = '#241f42';
  ctx.fillRect(0, skyH, w, wallH);
  ctx.fillStyle = '#2d2755';
  ctx.fillRect(0, skyH, w, 3);

  // Floor.
  const floorY = skyH + wallH;
  ctx.fillStyle = '#15122a';
  ctx.fillRect(0, floorY, w, h - floorY);
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  for (let y = floorY + 14; y < h; y += 16) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // A couple of potted plants for office life.
  function plant(px, py) {
    ctx.fillStyle = '#7a4a2f';
    ctx.fillRect(px, py, 14, 10);
    ctx.fillStyle = '#3d8a4f';
    ctx.fillRect(px - 2, py - 14, 18, 14);
    ctx.fillStyle = '#4fae63';
    ctx.fillRect(px + 2, py - 18, 10, 8);
  }
  plant(w * 0.02, h - 12);
  plant(w * 0.93, h - 12);
}

// ============================================================================
// Arena setup - an office scene: desks stay put, agents sit at them and walk
// over to the manager's desk to drop off real results when a task finishes.
// ============================================================================

const arena = document.getElementById('arena');
const officeBg = document.getElementById('office-bg');
const slots = {};

// Desk/seat positions as % of the office-scene box (left, top = center of the
// seated agent). The manager sits apart, near the biggest window - the
// corner office. DELIVERY_SPOT is where workers stand to hand off results.
const DESK_POSITIONS = {
  quality: { left: 13, top: 72 },
  fundamentals: { left: 37, top: 72 },
  news: { left: 61, top: 72 },
  portfolio: { left: 85, top: 42 },
};
const DELIVERY_SPOT = { left: 72, top: 58 };
const STAND_LIFT = 6; // % risen while standing/walking vs sitting

function renderOfficeBackground() {
  drawOfficeBackground(officeBg);
}
renderOfficeBackground();
window.addEventListener('resize', renderOfficeBackground);

AGENTS.forEach(agent => {
  const pos = DESK_POSITIONS[agent.key];

  const desk = document.createElement('div');
  desk.className = 'desk';
  desk.style.left = pos.left + '%';
  desk.style.top = (pos.top + 10) + '%';
  desk.innerHTML = '<canvas></canvas>';
  arena.appendChild(desk);
  drawDesk(desk.querySelector('canvas'), agent.glow);

  const wrap = document.createElement('div');
  wrap.className = 'agent-wrap';
  wrap.style.setProperty('--slot-glow', agent.glow);
  wrap.style.left = pos.left + '%';
  wrap.style.top = pos.top + '%';
  wrap.title = agent.role;
  wrap.innerHTML = `
    <div class="speech-bubble" data-bubble></div>
    <div class="sprite-label">${agent.label}</div>
    <div class="sprite-canvas-wrap">
      <canvas class="papers-icon" data-papers></canvas>
      <canvas class="agent-canvas"></canvas>
    </div>
  `;
  arena.appendChild(wrap);
  renderSprite(wrap.querySelector('.agent-canvas'), agent);
  drawPapers(wrap.querySelector('[data-papers]'));
  slots[agent.key] = wrap;
});

function setActive(key, message) {
  Object.values(slots).forEach(s => s.classList.remove('active'));
  const slot = slots[key];
  if (!slot) return;
  slot.classList.add('active');
  showBubble(key, message);
}

function showBubble(key, text) {
  const slot = slots[key];
  if (!slot) return;
  const bubble = slot.querySelector('[data-bubble]');
  bubble.textContent = text;
  bubble.classList.add('visible');
}

function hideBubble(key) {
  const slot = slots[key];
  if (!slot) return;
  slot.querySelector('[data-bubble]').classList.remove('visible');
}

function resetToDesk(key) {
  const slot = slots[key];
  const home = DESK_POSITIONS[key];
  if (!slot || !home) return;
  slot.classList.remove('walking');
  slot.style.left = home.left + '%';
  slot.style.top = home.top + '%';
  const papers = slot.querySelector('[data-papers]');
  if (papers) papers.classList.remove('visible');
}

function clearAllActive() {
  Object.keys(slots).forEach(key => {
    slots[key].classList.remove('active');
    slots[key].classList.remove('flagged');
    hideBubble(key);
    resetToDesk(key);
  });
  Object.keys(walkQueues).forEach(k => { walkQueues[k] = Promise.resolve(); });
}

function flag(key) {
  const slot = slots[key];
  if (slot) slot.classList.add('flagged');
}

// ----------------------------------------------------------------------------
// Walking: get up, carry papers to the manager's desk, drop them, walk back,
// sit down. Triggered only by a real task_complete event for a worker agent -
// the "papers" being delivered are that worker's actual real output.
// ----------------------------------------------------------------------------

const walkQueues = {};

function queueWalk(key, fn) {
  const prev = walkQueues[key] || Promise.resolve();
  const next = prev.then(fn).catch(() => {});
  walkQueues[key] = next;
  return next;
}

async function walkToManagerAndDeliver(key) {
  const wrap = slots[key];
  const home = DESK_POSITIONS[key];
  if (!wrap || !home || key === 'portfolio') return;

  const papers = wrap.querySelector('[data-papers]');
  wrap.classList.add('walking');

  wrap.style.top = (home.top - STAND_LIFT) + '%';
  await sleep(220);

  papers.classList.add('visible');
  wrap.style.left = DELIVERY_SPOT.left + '%';
  wrap.style.top = (DELIVERY_SPOT.top - STAND_LIFT) + '%';
  await sleep(650);

  papers.classList.remove('visible');
  sfx.drop();
  log(`\u{1F4C4} ${AGENTS.find(a => a.key === key).label} drops results on the Manager's desk`, 'log-system');
  await sleep(300);

  wrap.style.left = home.left + '%';
  wrap.style.top = (home.top - STAND_LIFT) + '%';
  await sleep(650);

  wrap.style.top = home.top + '%';
  await sleep(220);

  wrap.classList.remove('walking');
}

// ============================================================================
// Battle log
// ============================================================================

const logEl = document.getElementById('battle-log');

function log(text, cls) {
  const line = document.createElement('div');
  if (cls) line.className = cls;
  line.textContent = text;
  logEl.appendChild(line);
  logEl.scrollTop = logEl.scrollHeight;
}

function clearLog() {
  logEl.innerHTML = '';
}

// ============================================================================
// Minimal markdown renderer (no external dependency, tailored to our reports)
// ============================================================================

function extractCallStamps(md) {
  // One BUY/HOLD/SELL per '## TICKER' section, in document order, parallel
  // to the <h2> tags renderMarkdown produces (null if a section has no call).
  const parts = md.split(/\n(?=##\s)/);
  const calls = [];
  for (const part of parts) {
    if (!/^##\s/.test(part)) continue;
    const m = /\b(BUY|HOLD|SELL)\b/i.exec(part);
    calls.push(m ? m[1].toUpperCase() : null);
  }
  return calls;
}

function renderMarkdown(md) {
  const lines = md.split('\n');
  let html = '';
  let inList = false;

  const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };
  const inline = (s) => s
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (/^---+$/.test(line.trim())) { closeList(); html += '<hr>'; continue; }
    if (/^##\s+/.test(line)) { closeList(); html += `<h2>${inline(line.replace(/^##\s+/, ''))}</h2>`; continue; }
    if (/^#\s+/.test(line)) { closeList(); html += `<h1>${inline(line.replace(/^#\s+/, ''))}</h1>`; continue; }
    if (/^\s*[-*]\s+/.test(line)) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${inline(line.replace(/^\s*[-*]\s+/, ''))}</li>`;
      continue;
    }
    closeList();
    if (line.trim() === '') continue;
    html += `<p>${inline(line)}</p>`;
  }
  closeList();

  const calls = extractCallStamps(md);
  let callIndex = 0;
  html = html.replace(/<h2>(.*?)<\/h2>/g, (match) => {
    const call = calls[callIndex++];
    if (!call) return match;
    const cls = call === 'BUY' ? 'buy' : call === 'SELL' ? 'sell' : 'hold';
    return `${match}<div class="call-stamp ${cls}">${call}</div>`;
  });

  return html;
}

// ============================================================================
// Ticker / tool-input parsing helpers
// ============================================================================

function agentKeyFromToolInput(toolInput) {
  if (!toolInput) return null;
  if (toolInput.includes('"fundamental"')) return 'fundamentals';
  if (toolInput.includes('"news"')) return 'news';
  return null;
}

function tickerFromToolInput(toolInput) {
  const m = /"ticker"\s*:\s*"([A-Z.\-]+)"/.exec(toolInput || '');
  return m ? m[1] : '?';
}

function tickerFromDescription(desc) {
  const m = /ticker '([A-Z.\-]+)'/.exec(desc || '');
  return m ? m[1] : null;
}

// ============================================================================
// Controls
// ============================================================================

const modeCustomBtn = document.getElementById('mode-custom');
const modeDefaultBtn = document.getElementById('mode-default');
const tickerInputRow = document.getElementById('ticker-input-row');
const tickerInput = document.getElementById('ticker-input');
const analyzeBtn = document.getElementById('analyze-btn');
const statusLine = document.getElementById('status-line');

let mode = 'custom';
modeCustomBtn.addEventListener('click', () => {
  mode = 'custom';
  modeCustomBtn.classList.add('active');
  modeDefaultBtn.classList.remove('active');
  tickerInputRow.style.display = '';
});
modeDefaultBtn.addEventListener('click', () => {
  mode = 'default';
  modeDefaultBtn.classList.add('active');
  modeCustomBtn.classList.remove('active');
  tickerInputRow.style.display = 'none';
});

// A curated pool of real small-cap tickers (including the default CSV's own
// 5) to draw a fresh 5-ticker squad from. This is deliberately NOT an LLM
// "discovery" step - every ticker here is a real, named company, so a draw
// can only ever be a random sample of real tickers, never an invented one.
// If a drawn ticker happens to be stale/thinly covered, the existing
// "no data available" handling covers it honestly, same as any other ticker.
// Verified live against yfinance before shipping - 3 originally-considered
// tickers (CARA, CPRX, VLD) came back with no price history (delisted/
// acquired) and were dropped rather than left in as dead weight.
const SMALL_CAP_POOL = [
  'SMLR', 'HROW', 'AGFY', 'VERX', 'MDXG',
  'OSUR', 'KOPN', 'GEVO', 'CDXS', 'SPOK',
  'UEIC', 'ASTS', 'BKSY', 'IONQ', 'RKLB',
  'PLSE', 'NX',
];

function drawRandomSquad(n = 5) {
  const pool = [...SMALL_CAP_POOL];
  const picked = [];
  while (picked.length < n && pool.length) {
    const i = Math.floor(Math.random() * pool.length);
    picked.push(pool.splice(i, 1)[0]);
  }
  return picked;
}

const shuffleBtn = document.getElementById('shuffle-btn');
shuffleBtn.addEventListener('click', () => {
  const squad = drawRandomSquad(5);
  tickerInput.value = squad.join(', ');
  modeCustomBtn.click();
  statusLine.textContent = `New squad drawn: ${squad.join(', ')} — click ANALYZE to run them.`;
});

const groundingWrap = document.getElementById('grounding-meter-wrap');
const groundingBar = document.getElementById('grounding-bar');
const groundingText = document.getElementById('grounding-text');

function updateGroundingMeter(evalResult) {
  groundingWrap.classList.remove('hidden');
  const numeric = evalResult.numeric_grounding_rate ?? 1;
  const ticker = evalResult.ticker_grounding_rate ?? 1;
  const combined = Math.min(numeric, ticker) * 100;

  groundingBar.style.width = `${combined}%`;
  groundingBar.classList.remove('warn', 'bad');
  if (combined < 70) groundingBar.classList.add('bad');
  else if (combined < 100) groundingBar.classList.add('warn');

  groundingText.textContent =
    `tickers ${(ticker * 100).toFixed(0)}%  |  numbers ${(numeric * 100).toFixed(0)}%` +
    (evalResult.retried ? '  (after retry)' : '');

  if (evalResult.ungrounded_tickers && evalResult.ungrounded_tickers.length) {
    log(`⚠ ungrounded tickers detected: ${evalResult.ungrounded_tickers.join(', ')}`, 'log-warn');
    flag('portfolio');
  }
}

const thesisWrap = document.getElementById('thesis-meter-wrap');
const thesisBar = document.getElementById('thesis-bar');
const thesisText = document.getElementById('thesis-text');

function updateThesisMeter(thesisResult) {
  thesisWrap.classList.remove('hidden');
  const rate = (thesisResult.thesis_consistency_rate ?? 1) * 100;

  thesisBar.style.width = `${rate}%`;
  thesisBar.classList.remove('warn', 'bad');
  if (rate < 70) thesisBar.classList.add('bad');
  else if (rate < 100) thesisBar.classList.add('warn');

  const applicableCount = (thesisResult.per_ticker || []).filter(t => t.applicable).length;
  thesisText.textContent = applicableCount
    ? `${rate.toFixed(0)}% of calls match their own fundamentals`
    : 'not enough real data to check this run';

  if (thesisResult.inconsistent_tickers && thesisResult.inconsistent_tickers.length) {
    log(`⚠ thesis doesn't match fundamentals for: ${thesisResult.inconsistent_tickers.join(', ')}`, 'log-warn');
    flag('portfolio');
  }
}

const reportEmpty = document.getElementById('report-empty');
const reportContent = document.getElementById('report-content');
const downloadBtn = document.getElementById('download-btn');
let currentReportText = '';

async function loadReport(executionId) {
  const res = await fetch(`/api/report/${executionId}`);
  if (!res.ok) {
    log('Could not load report.', 'log-error');
    return;
  }
  const data = await res.json();
  currentReportText = data.report;
  reportEmpty.classList.add('hidden');
  reportContent.classList.remove('hidden');
  reportContent.innerHTML = renderMarkdown(data.report);
  downloadBtn.classList.remove('hidden');
}

downloadBtn.addEventListener('click', () => {
  if (!currentReportText) return;
  const blob = new Blob([currentReportText], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `alpha_investment_report_${currentExecutionId || 'latest'}.md`;
  a.click();
  URL.revokeObjectURL(url);
});

// ============================================================================
// Session stats (real counts, not decoration - reinforces "every event here
// corresponds to something the pipeline actually did")
// ============================================================================

const statToolCalls = document.getElementById('stat-tool-calls');
const statRuns = document.getElementById('stat-runs');
let sessionToolCalls = 0;
let sessionRuns = 0;

// ============================================================================
// Run + SSE stream handling
// ============================================================================

function handleEvent(evt) {
  switch (evt.type) {
    case 'analysis_started': {
      currentTickers = evt.tickers;
      log(`Party assembled. Targets: ${evt.tickers.join(', ')}`, 'log-system');
      statusLine.textContent = `Analyzing ${evt.tickers.join(', ')}...`;
      break;
    }
    case 'tool_call': {
      sessionToolCalls++;
      statToolCalls.textContent = sessionToolCalls;
      sfx.toolCall();
      const key = agentKeyFromToolInput(evt.tool_input);
      const ticker = tickerFromToolInput(evt.tool_input);
      if (key) {
        const verb = key === 'fundamentals' ? 'crunching numbers for' : 'scanning news for';
        setActive(key, `${verb.split(' ')[0]}\n${ticker}`);
        log(`[${AGENTS.find(a => a.key === key).label}] ${verb} ${ticker}`, 'log-tool');
      }
      break;
    }
    case 'task_complete': {
      const agent = AGENT_BY_ROLE[evt.agent];
      if (agent) {
        sfx.taskComplete();
        hideBubble(agent.key);
        const ticker = tickerFromDescription(evt.description);
        const label = ticker ? `${agent.label} finished ${ticker}` : `${agent.label} finished`;
        log(`✓ ${label}`, 'log-task');
        if (agent.key !== 'portfolio') {
          queueWalk(agent.key, () => walkToManagerAndDeliver(agent.key));
        }
      }
      break;
    }
    case 'retry_started': {
      sfx.retry();
      log(`⚠ Report failed its own grounding check! Manager is redoing the synthesis...`, 'log-warn');
      setActive('portfolio', 'Redoing\nmy work...');
      flag('portfolio');
      break;
    }
    case 'grounding_result': {
      updateGroundingMeter(evt);
      break;
    }
    case 'thesis_result': {
      updateThesisMeter(evt);
      break;
    }
    case 'analysis_complete': {
      clearAllActive();
      sessionRuns++;
      statRuns.textContent = sessionRuns;
      sfx.complete();
      statusLine.textContent = 'Quest complete.';
      log('Quest complete - report ready.', 'log-system');
      loadReport(currentExecutionId);
      renderPriceCharts(currentTickers);
      loadTrackRecord();
      setButtonsEnabled(true);
      break;
    }
    case 'analysis_failed': {
      clearAllActive();
      sfx.error();
      statusLine.textContent = 'Analysis failed.';
      log(`✗ ${evt.error}`, 'log-error');
      setButtonsEnabled(true);
      break;
    }
    default:
      break;
  }
}

let currentExecutionId = null;
let currentTickers = [];

function setButtonsEnabled(enabled) {
  analyzeBtn.disabled = !enabled;
  analyzeBtn.textContent = enabled ? 'ANALYZE!' : 'WORKING...';
}

function resetRunUI() {
  clearLog();
  clearAllActive();
  groundingWrap.classList.add('hidden');
  thesisWrap.classList.add('hidden');
  reportContent.classList.add('hidden');
  downloadBtn.classList.add('hidden');
  currentReportText = '';
  reportEmpty.classList.remove('hidden');
  reportEmpty.textContent = 'Working on it...';
  chartsPanel.classList.add('hidden');
  chartsGrid.innerHTML = '';
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function replayRun(executionId) {
  ensureAudioCtx();
  const res = await fetch(`/api/replay/${executionId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    statusLine.textContent = `Replay error: ${err.error || res.statusText}`;
    return;
  }
  const data = await res.json();

  setButtonsEnabled(false);
  resetRunUI();
  currentExecutionId = executionId;
  statusLine.textContent = `REPLAYING ${executionId} (recorded run, no new API calls)...`;
  log(`▶ Replaying saved run ${executionId}`, 'log-system');

  for (const evt of data.events) {
    handleEvent(evt);
    await sleep(evt.type === 'tool_call' || evt.type === 'task_complete' ? 500 : 700);
  }

  setButtonsEnabled(true);
}

async function startAnalysis() {
  ensureAudioCtx();
  let payload = {};
  if (mode === 'custom') {
    const raw = tickerInput.value.trim();
    if (!raw) {
      statusLine.textContent = 'Enter at least one ticker first.';
      return;
    }
    payload.tickers = raw.split(',').map(t => t.trim().toUpperCase()).filter(Boolean);
  }

  setButtonsEnabled(false);
  resetRunUI();
  statusLine.textContent = 'Starting...';
  log('Casting ANALYZE... (spinning up the party)', 'log-system');

  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    statusLine.textContent = `Error: ${err.error || res.statusText}`;
    setButtonsEnabled(true);
    return;
  }

  const data = await res.json();
  currentExecutionId = data.execution_id;

  const source = new EventSource(`/api/stream/${currentExecutionId}`);
  source.onmessage = (msg) => {
    const evt = JSON.parse(msg.data);
    if (evt.type === 'stream_end') {
      source.close();
      return;
    }
    handleEvent(evt);
  };
  source.onerror = () => {
    source.close();
  };
}

analyzeBtn.addEventListener('click', startAnalysis);
tickerInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') startAnalysis(); });

// ============================================================================
// Run history
// ============================================================================

const historyToggle = document.getElementById('history-toggle');
const historyPanel = document.getElementById('history-panel');
let historyLoaded = false;

historyToggle.addEventListener('click', async () => {
  historyPanel.classList.toggle('hidden');
  if (historyPanel.classList.contains('hidden') || historyLoaded) return;

  const res = await fetch('/api/history');
  const records = await res.json();
  historyLoaded = true;

  if (!records.length) {
    historyPanel.innerHTML = '<div class="history-row">No runs yet.</div>';
    return;
  }

  historyPanel.innerHTML = records.map(r => {
    const passed = r.grounding_passed;
    const pct = r.numeric_grounding_rate != null ? `${Math.round(r.numeric_grounding_rate * 100)}%` : 'n/a';
    return `<div class="history-row ${passed ? 'passed' : 'failed'}" data-execution-id="${r.execution_id}">
      <span>${(r.source || '').slice(0, 20)}</span><span>${pct}</span><span class="replay-btn" title="Replay this run">&#9654;</span>
    </div>`;
  }).join('');
});

historyPanel.addEventListener('click', (e) => {
  const row = e.target.closest('.history-row[data-execution-id]');
  if (row) replayRun(row.dataset.executionId);
});

// Seed the header stats with real totals from all prior runs, not just this
// browser session, so the numbers mean something the moment the page loads.
(async function seedStats() {
  const res = await fetch('/api/history?limit=1000');
  const records = await res.json();
  sessionRuns = records.length;
  sessionToolCalls = records.reduce((sum, r) => sum + (r.tool_calls_made || 0), 0);
  statRuns.textContent = sessionRuns;
  statToolCalls.textContent = sessionToolCalls;
})();

// ============================================================================
// Price history charts - real weekly closes from /api/price-history, drawn as
// a retro pixel line chart. A single series needs no legend (the card header
// names it); the line color is a status signal (up/down over the period),
// not a categorical identity, which is why reusing green/red here is fine.
// ============================================================================

const chartsPanel = document.getElementById('charts-panel');
const chartsGrid = document.getElementById('charts-grid');
const PERIODS = ['6mo', '1y', '2y'];

function layoutChart(canvas, closes) {
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 280;
  const cssH = canvas.clientHeight || 140;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;

  const marginLeft = 46, marginRight = 8, marginTop = 8, marginBottom = 8;
  const plotW = cssW - marginLeft - marginRight;
  const plotH = cssH - marginTop - marginBottom;

  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const pad = (max - min) * 0.1 || Math.max(1, min * 0.05);
  const yMin = min - pad, yMax = max + pad;

  const x = i => marginLeft + (closes.length === 1 ? 0 : (i / (closes.length - 1)) * plotW);
  const y = v => marginTop + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  return { ctx: canvas.getContext('2d'), dpr, cssW, cssH, marginLeft, marginTop, plotW, plotH, x, y, yMin, yMax };
}

function drawChart(canvas, closes, color) {
  const L = layoutChart(canvas, closes);
  const { ctx, dpr, cssW, cssH, marginLeft, x, y, yMin, yMax } = L;

  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);

  // Recessive gridlines, one step off the surface color - hairline, solid.
  ctx.strokeStyle = '#2a2650';
  ctx.lineWidth = 1;
  ctx.font = '11px VT323, monospace';
  ctx.fillStyle = '#6f699a';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  const steps = 3;
  for (let s = 0; s <= steps; s++) {
    const v = yMin + (s / steps) * (yMax - yMin);
    const yy = Math.round(y(v)) + 0.5;
    ctx.beginPath();
    ctx.moveTo(marginLeft, yy);
    ctx.lineTo(cssW - 8, yy);
    ctx.stroke();
    ctx.fillText('$' + v.toFixed(0), marginLeft - 6, yy);
  }

  // Area wash under the line at ~10% opacity.
  ctx.beginPath();
  ctx.moveTo(x(0), y(closes[0]));
  closes.forEach((c, i) => ctx.lineTo(x(i), y(c)));
  ctx.lineTo(x(closes.length - 1), y(yMin));
  ctx.lineTo(x(0), y(yMin));
  ctx.closePath();
  ctx.fillStyle = color + '1a';
  ctx.fill();

  // The line itself - the only loud element on the card.
  ctx.beginPath();
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.lineWidth = 2.5;
  ctx.strokeStyle = color;
  closes.forEach((c, i) => (i === 0 ? ctx.moveTo(x(i), y(c)) : ctx.lineTo(x(i), y(c))));
  ctx.stroke();

  // End marker: a filled dot with a surface-color ring so it reads where it
  // crosses the line, per the mark spec (>= 8px, 2px ring).
  const lastX = x(closes.length - 1), lastY = y(closes[closes.length - 1]);
  ctx.beginPath();
  ctx.arc(lastX, lastY, 6, 0, Math.PI * 2);
  ctx.fillStyle = '#0d0b1a';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
}

function attachChartHover(canvas, data, color, tooltip) {
  const closes = data.closes;
  const onMove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const L = layoutChart(canvas, closes);
    const mouseX = e.clientX - rect.left;
    const relX = (mouseX - L.marginLeft) / L.plotW;
    const idx = Math.max(0, Math.min(closes.length - 1, Math.round(relX * (closes.length - 1))));

    drawChart(canvas, closes, color);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(L.dpr, 0, 0, L.dpr, 0, 0);

    // Crosshair: a vertical hairline snapped to the nearest real data point -
    // readers aim at a date, never at a 2px line.
    const cx = L.x(idx);
    ctx.beginPath();
    ctx.strokeStyle = '#4a4470';
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 3]);
    ctx.moveTo(cx, L.marginTop);
    ctx.lineTo(cx, L.marginTop + L.plotH);
    ctx.stroke();
    ctx.setLineDash([]);

    const cy = L.y(closes[idx]);
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#0d0b1a';
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cx, cy, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    // Tooltip: value leads (large, bold), date follows (small, secondary).
    tooltip.innerHTML = `<span class="tt-price">$${closes[idx].toFixed(2)}</span><span class="tt-date"></span>`;
    tooltip.querySelector('.tt-date').textContent = data.dates[idx];
    tooltip.style.left = `${cx}px`;
    tooltip.style.top = `${cy}px`;
    tooltip.classList.add('visible');
  };

  const onLeave = () => {
    tooltip.classList.remove('visible');
    drawChart(canvas, closes, color);
  };

  canvas.addEventListener('mousemove', onMove);
  canvas.addEventListener('mouseleave', onLeave);
}

async function fetchPriceHistory(ticker, period) {
  const res = await fetch(`/api/price-history/${ticker}?period=${period}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

function buildChartCard(ticker) {
  const card = document.createElement('div');
  card.className = 'chart-card';
  card.innerHTML = `
    <div class="chart-card-header">
      <span class="chart-ticker">${ticker}</span>
      <span class="chart-change"></span>
    </div>
    <div class="chart-body"><div class="chart-loading">loading chart...</div></div>
    <div class="chart-period-toggle">
      ${PERIODS.map(p => `<button class="chart-period-btn${p === '2y' ? ' active' : ''}" data-period="${p}">${p.toUpperCase()}</button>`).join('')}
    </div>
  `;
  return card;
}

async function loadChartInto(card, ticker, period) {
  const body = card.querySelector('.chart-body');
  const changeEl = card.querySelector('.chart-change');
  body.innerHTML = '<div class="chart-loading">loading chart...</div>';

  let data;
  try {
    data = await fetchPriceHistory(ticker, period);
  } catch (e) {
    body.innerHTML = `<div class="chart-error">${e.message}</div>`;
    changeEl.textContent = '';
    return;
  }

  const closes = data.closes;
  const changePct = ((closes[closes.length - 1] - closes[0]) / closes[0]) * 100;
  const up = changePct >= 0;
  const color = up ? '#5ce87a' : '#ff5c5c';

  changeEl.textContent = `${up ? '+' : ''}${changePct.toFixed(1)}%`;
  changeEl.className = `chart-change ${up ? 'up' : 'down'}`;

  body.innerHTML = '';
  body.style.position = 'relative';
  const canvas = document.createElement('canvas');
  const tooltip = document.createElement('div');
  tooltip.className = 'chart-tooltip';
  body.appendChild(canvas);
  body.appendChild(tooltip);

  // Let the canvas settle into its CSS-driven size before computing scales.
  requestAnimationFrame(() => {
    drawChart(canvas, closes, color);
    attachChartHover(canvas, data, color, tooltip);
  });
}

function renderPriceCharts(tickers) {
  if (!tickers || !tickers.length) return;
  chartsGrid.innerHTML = '';
  chartsPanel.classList.remove('hidden');

  tickers.forEach(ticker => {
    const card = buildChartCard(ticker);
    chartsGrid.appendChild(card);
    loadChartInto(card, ticker, '2y');

    card.querySelectorAll('.chart-period-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        card.querySelectorAll('.chart-period-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        loadChartInto(card, ticker, btn.dataset.period);
      });
    });
  });
}

// ============================================================================
// Track record - the real "is this system good at picking stocks" signal.
// A call is only scored once it's at least 7 days old (see evals/outcomes.py)
// - there is no honest way to grade a call made minutes ago, so on a fresh
// install this will mostly say "nothing scoreable yet" and that's correct,
// not broken.
// ============================================================================

const trackContent = document.getElementById('track-content');

async function loadTrackRecord() {
  let data;
  try {
    const res = await fetch('/api/outcomes');
    data = await res.json();
  } catch (e) {
    trackContent.innerHTML = '<p class="report-empty">Could not load track record.</p>';
    return;
  }

  const accuracyText = data.accuracy != null ? `${Math.round(data.accuracy * 100)}%` : 'n/a';
  const scored = (data.results || []).filter(r => 'correct' in r);

  let html = `
    <div class="track-summary">
      <div class="track-stat"><span class="big-number">${data.total_logged}</span><span class="stat-caption">calls logged</span></div>
      <div class="track-stat"><span class="big-number">${data.total_scored}</span><span class="stat-caption">old enough to score</span></div>
      <div class="track-stat"><span class="big-number">${accuracyText}</span><span class="stat-caption">accuracy</span></div>
      <div class="track-stat"><span class="big-number">${data.too_recent_to_score}</span><span class="stat-caption">too recent to score</span></div>
    </div>
  `;

  if (scored.length) {
    html += `
      <table class="track-table">
        <thead><tr><th>Ticker</th><th>Call</th><th>Price at call</th><th>Price now</th><th>Change</th><th>Held</th><th>Result</th></tr></thead>
        <tbody>
          ${scored.slice(0, 15).map(r => `
            <tr>
              <td>${r.ticker}</td>
              <td>${r.call}</td>
              <td>$${r.price_at_call.toFixed(2)}</td>
              <td>$${r.price_now.toFixed(2)}</td>
              <td class="${r.correct ? 'correct' : 'wrong'}">${r.pct_change >= 0 ? '+' : ''}${r.pct_change.toFixed(1)}%</td>
              <td>${r.days_held}d</td>
              <td class="${r.correct ? 'correct' : 'wrong'}">${r.correct ? 'CORRECT' : 'WRONG'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } else {
    html += '<p class="report-empty">No calls are old enough to score yet - check back after they\'re at least a week old.</p>';
  }

  trackContent.innerHTML = html;
}

loadTrackRecord();
