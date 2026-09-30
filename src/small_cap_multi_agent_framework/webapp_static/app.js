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
// Arena setup
// ============================================================================

const arena = document.getElementById('arena');
const slots = {};

AGENTS.forEach(agent => {
  const slot = document.createElement('div');
  slot.className = 'sprite-slot';
  slot.style.setProperty('--slot-glow', agent.glow);
  slot.innerHTML = `
    <div class="speech-bubble" data-bubble></div>
    <div class="sprite-canvas-wrap"><canvas></canvas></div>
    <div class="sprite-label">${agent.label}</div>
    <div class="sprite-role">${agent.role}</div>
  `;
  arena.appendChild(slot);
  renderSprite(slot.querySelector('canvas'), agent);
  slots[agent.key] = slot;
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

function clearAllActive() {
  Object.entries(slots).forEach(([key, s]) => {
    s.classList.remove('active');
    s.classList.remove('flagged');
    hideBubble(key);
  });
}

function flag(key) {
  const slot = slots[key];
  if (slot) slot.classList.add('flagged');
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
      log(`Party assembled. Targets: ${evt.tickers.join(', ')}`, 'log-system');
      statusLine.textContent = `Analyzing ${evt.tickers.join(', ')}...`;
      break;
    }
    case 'tool_call': {
      sessionToolCalls++;
      statToolCalls.textContent = sessionToolCalls;
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
        hideBubble(agent.key);
        const ticker = tickerFromDescription(evt.description);
        const label = ticker ? `${agent.label} finished ${ticker}` : `${agent.label} finished`;
        log(`✓ ${label}`, 'log-task');
      }
      break;
    }
    case 'retry_started': {
      log(`⚠ Report failed its own grounding check! Manager is redoing the synthesis...`, 'log-warn');
      setActive('portfolio', 'Redoing\nmy work...');
      flag('portfolio');
      break;
    }
    case 'grounding_result': {
      updateGroundingMeter(evt);
      break;
    }
    case 'analysis_complete': {
      clearAllActive();
      sessionRuns++;
      statRuns.textContent = sessionRuns;
      statusLine.textContent = 'Quest complete.';
      log('Quest complete - report ready.', 'log-system');
      loadReport(currentExecutionId);
      setButtonsEnabled(true);
      break;
    }
    case 'analysis_failed': {
      clearAllActive();
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

function setButtonsEnabled(enabled) {
  analyzeBtn.disabled = !enabled;
  analyzeBtn.textContent = enabled ? 'ANALYZE!' : 'WORKING...';
}

async function startAnalysis() {
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
  clearLog();
  clearAllActive();
  groundingWrap.classList.add('hidden');
  reportContent.classList.add('hidden');
  downloadBtn.classList.add('hidden');
  currentReportText = '';
  reportEmpty.classList.remove('hidden');
  reportEmpty.textContent = 'Working on it...';
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
    return `<div class="history-row ${passed ? 'passed' : 'failed'}">
      <span>${(r.source || '').slice(0, 22)}</span><span>${pct}</span>
    </div>`;
  }).join('');
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
