"""Dev mode page — all active tmux sessions across all projects."""


def render_dev_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js

    page_css = r"""
  /* ── Main layout ── */
  .dev-page {
    height: calc(100vh - 52px);
    display: flex;
    overflow: hidden;
    background: var(--bg);
  }

  /* ── Sidebar (pane list) ── */
  .term-sidebar {
    width: 200px; border-right: 1px solid var(--border);
    display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden;
    background: var(--panel);
  }
  .term-sidebar-header {
    padding: 10px 14px; font-size: 10px; color: var(--muted);
    font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  #term-pane-list { flex: 1; overflow-y: auto; }
  .term-pane-row {
    padding: 10px 14px; display: flex; align-items: flex-start; gap: 8px;
    cursor: pointer; border-left: 2px solid transparent; transition: background .12s, border-color .12s;
  }
  .term-pane-row:hover { background: rgba(255,255,255,.03); }
  .term-pane-row.active { background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }
  .term-pane-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
  .term-pane-dot.running { background: var(--green); box-shadow: 0 0 5px rgba(63,185,80,.5); }
  .term-pane-dot.waiting { background: var(--yellow); }
  .term-pane-info { min-width: 0; flex: 1; }
  .term-pane-name { font-size: 12px; color: var(--text); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-pane-proj { font-size: 10px; color: var(--sub); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-pane-cmd  { font-size: 9px; color: var(--muted); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-sidebar-footer {
    padding: 8px 14px; font-size: 10px; color: var(--muted);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
  .term-empty-sidebar { padding: 32px 16px; font-size: 12px; color: var(--muted); line-height: 1.8; }
  .term-empty-sidebar code { color: var(--sub); }

  /* ── Terminal main ── */
  .term-main { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; background: var(--bg); }
  .term-titlebar {
    padding: 7px 14px; display: flex; align-items: center;
    justify-content: space-between; border-bottom: 1px solid var(--border);
    flex-shrink: 0; gap: 8px;
  }
  .term-title-left { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
  .term-back-btn {
    display: none;
    background: none; border: none; color: var(--accent);
    font-size: 16px; padding: 0 6px 0 0; cursor: pointer; flex-shrink: 0;
    line-height: 1;
  }
  #term-title { font-size: 11px; color: var(--sub); font-family: var(--mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-quickbtns { display: flex; gap: 6px; flex-shrink: 0; }
  .term-qbtn {
    background: var(--panel); border: 1px solid var(--border);
    color: var(--muted); font-size: 10px; padding: 2px 8px;
    border-radius: var(--radius-sm); cursor: pointer; font-family: var(--mono); transition: all .12s;
  }
  .term-qbtn:hover { border-color: var(--accent); color: var(--accent); }
  /* ── ANSI 16-color palette: references theme vars wherever possible ── */
  :root {
    --ansi-k: #3a3f4b;          /* black  */
    --ansi-r: var(--red);       /* red    */
    --ansi-g: var(--green);     /* green  */
    --ansi-y: var(--yellow);    /* yellow */
    --ansi-b: #4e9eff;          /* blue   */
    --ansi-m: #c792ea;          /* magenta */
    --ansi-c: #56b6c2;          /* cyan   */
    --ansi-w: var(--text);      /* white  */
    --ansi-K: var(--muted);     /* bright black  */
    --ansi-R: var(--red);       /* bright red    */
    --ansi-G: var(--green);     /* bright green  */
    --ansi-Y: var(--orange);    /* bright yellow */
    --ansi-B: #82aaff;          /* bright blue   */
    --ansi-M: #d9a0f5;          /* bright magenta */
    --ansi-C: #89ddff;          /* bright cyan   */
    --ansi-W: #ffffff;          /* bright white  */
  }

  /* ── Terminal output (editor layout) ── */
  .term-output {
    flex: 1; overflow-y: auto;
    font-family: var(--mono); font-size: 12px;
    background: var(--bg); color: var(--text);
    /* white-space/word-break handled per-line in .out-code */
  }
  .out-line {
    display: flex; align-items: baseline;
    min-height: 1.6em; line-height: 1.6;
    transition: background .08s;
  }
  .out-line:hover { background: rgba(255,255,255,.028); }
  .out-ln {
    flex-shrink: 0;
    width: 3.2em;
    padding: 0 .6em 0 .5em;
    text-align: right;
    color: var(--muted);
    font-size: .82em;
    user-select: none;
    border-right: 1px solid var(--border);
    line-height: 1.6;
    white-space: pre;
    opacity: .7;
  }
  .out-code {
    flex: 1; min-width: 0;
    padding: 0 14px;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.6;
  }

  .term-empty {
    height: 100%; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: var(--muted); font-size: 13px; text-align: center; gap: 10px; line-height: 1.7;
  }
  .term-empty code { color: var(--sub); font-size: 11px; }
  .term-inputbar {
    padding: 8px 12px; border-top: 1px solid var(--border);
    display: flex; flex-direction: column; gap: 0;
    flex-shrink: 0; background: var(--panel);
  }
  .term-input-row {
    display: flex; gap: 8px; align-items: flex-end;
  }
  .term-input {
    flex: 1; background: rgba(255,255,255,.04); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 7px 10px; color: var(--text);
    font-family: var(--mono); font-size: 12px; outline: none; transition: border-color .15s;
    resize: none; overflow-y: hidden; line-height: 1.5;
    min-height: 34px; max-height: 120px;
    display: block; box-sizing: border-box;
  }
  .term-input.scrollable { overflow-y: auto; }
  .term-input:focus { border-color: var(--accent); }
  .term-input:disabled { opacity: .4; cursor: not-allowed; }
  .term-send-btn {
    background: var(--accent); border: none; color: #fff;
    padding: 7px 16px; border-radius: var(--radius-sm); font-size: 12px;
    cursor: pointer; font-family: var(--mono); transition: opacity .12s; flex-shrink: 0;
    height: 34px; /* matches single-line input height */
  }
  .term-send-btn:hover { opacity: .85; }
  .term-send-btn:disabled { opacity: .4; cursor: not-allowed; }

  /* ── Attachment previews ── */
  .term-attachments {
    display: flex; flex-wrap: wrap; gap: 6px;
    padding: 8px 10px 2px;
  }
  .term-attachments:empty { display: none; }
  .attach-item {
    position: relative; width: 64px; height: 64px;
    border-radius: var(--radius-sm); border: 1px solid var(--border);
    overflow: hidden; flex-shrink: 0; background: var(--panel);
  }
  .attach-img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .attach-rm {
    position: absolute; top: 2px; right: 2px;
    width: 17px; height: 17px;
    background: rgba(0,0,0,.75); color: #fff; border: none;
    border-radius: 50%; font-size: 12px; line-height: 17px;
    text-align: center; cursor: pointer; padding: 0; display: block;
    transition: background .1s;
  }
  .attach-rm:hover { background: var(--red); }

  /* iOS paste tip */
  .attach-tip {
    font-size: 11px; color: var(--sub); text-align: center;
    max-height: 0; overflow: hidden; opacity: 0;
    transition: max-height .2s, opacity .2s, padding .2s;
    padding: 0 10px;
  }
  .attach-tip.visible { max-height: 2em; opacity: 1; padding: 5px 10px 0; }

  /* Attach button (image icon, left of textarea) */
  .term-attach-btn {
    flex-shrink: 0; background: none;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    color: var(--muted); width: 34px; height: 34px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; padding: 0; transition: color .12s, border-color .12s;
  }
  .term-attach-btn:hover:not(:disabled) { color: var(--text); border-color: var(--sub); }
  .term-attach-btn:disabled { opacity: .35; cursor: not-allowed; }

  /* Drop-zone overlay on output area */
  .term-output { position: relative; }
  .term-output.drag-over::after {
    content: '拖放图片';
    position: absolute; inset: 0;
    background: rgba(var(--accent-rgb), .1);
    border: 2px dashed var(--accent);
    border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    color: var(--accent); font-size: 13px;
    pointer-events: none; z-index: 5;
  }

  /* ── Mobile: master-detail (≤ 900px) ── */
  @media (max-width: 900px) {
    .topbar { padding: 0 14px; gap: 8px; height: 48px; }
    .topbar-logo { letter-spacing: 1px; }
    .topbar-logo .logo-m { font-size: 20px; }
    .topbar-logo .logo-ira { font-size: 14px; }
    .topbar-logo .logo-cursor { font-size: 16px; }
    .topbar-page-title { display: none; }
    .topbar-sep { display: none; }
    .dev-page { height: calc(100dvh - 48px); }

    .term-sidebar { width: 100%; flex: 1; border-right: none; }
    .term-sidebar-header { padding: 14px 16px 10px; font-size: 11px; letter-spacing: .5px; text-transform: none; font-weight: 700; }
    .term-sidebar-footer { display: none; }
    #term-pane-list { padding: 0; }
    .term-pane-row {
      position: relative;
      padding: 14px 48px 14px 16px;
      border-left: none;
      border-bottom: 1px solid var(--border);
      border-radius: 0;
      gap: 10px;
    }
    .term-pane-row::after {
      content: '›';
      position: absolute; right: 16px; top: 50%;
      transform: translateY(-50%);
      color: var(--muted); font-size: 22px; line-height: 1;
    }
    .term-pane-row:hover { border-left-color: transparent; }
    .term-pane-row.active { border-left-color: transparent; background: rgba(var(--accent-rgb),.08); }
    .term-pane-dot { margin-top: 6px; }
    .term-pane-name { font-size: 14px; }
    .term-pane-proj { font-size: 12px; margin-top: 3px; }
    .term-pane-cmd  { font-size: 10px; }

    .term-main { display: none; }
    .dev-page.detail-open .term-sidebar { display: none; }
    .dev-page.detail-open .term-main { display: flex; flex: 1; }
    .term-back-btn { display: inline-flex; align-items: center; }

    /* titlebar quick buttons hidden on mobile */
    .term-quickbtns { display: none; }

    /* output area — bottom padding set by JS to avoid inputbar overlap */
    .term-output { font-size: 11px; }
    .out-ln { width: 2.6em; font-size: .78em; padding: 0 .4em 0 .3em; }
    .out-code { padding: 0 10px; }

    /* ── Fixed input bar above keyboard ── */
    .dev-page.detail-open .term-inputbar {
      position: fixed;
      left: 0; right: 0; bottom: 0;
      z-index: 40;
      padding: 0 0 max(8px, env(safe-area-inset-bottom, 8px));
      flex-direction: column;
      gap: 0;
    }

    /* input row inside inputbar */
    .term-input-row {
      display: flex;
      gap: 8px;
      padding: 6px 10px 0;
      align-items: flex-end;
    }
    .term-input {
      font-size: 16px; /* prevent iOS zoom */
      padding: 10px 12px;
      max-height: 160px;
    }
    .term-send-btn { font-size: 14px; height: 44px; padding: 0 20px; }
    .term-attach-btn { width: 44px; height: 44px; }
    .attach-item { width: 56px; height: 56px; }
  }
"""

    page_js = r"""
// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── ANSI renderer ─────────────────────────────────────────────────────────────
const _FG = {
  30:'var(--ansi-k)', 31:'var(--ansi-r)', 32:'var(--ansi-g)', 33:'var(--ansi-y)',
  34:'var(--ansi-b)', 35:'var(--ansi-m)', 36:'var(--ansi-c)', 37:'var(--ansi-w)',
  90:'var(--ansi-K)', 91:'var(--ansi-R)', 92:'var(--ansi-G)', 93:'var(--ansi-Y)',
  94:'var(--ansi-B)', 95:'var(--ansi-M)', 96:'var(--ansi-C)', 97:'var(--ansi-W)',
};
const _BG = {
  40:'var(--ansi-k)', 41:'var(--ansi-r)', 42:'var(--ansi-g)', 43:'var(--ansi-y)',
  44:'var(--ansi-b)', 45:'var(--ansi-m)', 46:'var(--ansi-c)', 47:'var(--ansi-w)',
  100:'var(--ansi-K)', 101:'var(--ansi-R)', 102:'var(--ansi-G)', 103:'var(--ansi-Y)',
  104:'var(--ansi-B)', 105:'var(--ansi-M)', 106:'var(--ansi-C)', 107:'var(--ansi-W)',
};

function _256color(n) {
  if (n < 8)   return _FG[n + 30];
  if (n < 16)  return _FG[n + 82];  // bright: 90-97
  if (n < 232) {
    n -= 16;
    const b = n % 6, g = Math.floor(n / 6) % 6, r = Math.floor(n / 36);
    const c = v => v ? v * 40 + 55 : 0;
    return 'rgb(' + c(r) + ',' + c(g) + ',' + c(b) + ')';
  }
  const v = Math.round((n - 232) * 10.2 + 8);
  return 'rgb(' + v + ',' + v + ',' + v + ')';
}

// Convert one line of terminal output (may contain ANSI escapes) → safe HTML.
function _ansiLine(line) {
  const RE = /\x1b\[([0-9;]*)([A-Za-z])/g;
  let out = '', last = 0, spanOpen = false;
  let fg = null, bg = null, bold = false, dim = false, ital = false, ul = false;

  function _hasStyle() { return fg || bg || bold || dim || ital || ul; }
  function _close() { if (spanOpen) { out += '</span>'; spanOpen = false; } }
  function _open() {
    if (spanOpen || !_hasStyle()) return;
    const s = [];
    if (fg)   s.push('color:' + fg);
    if (bg)   s.push('background:' + bg);
    if (bold) s.push('font-weight:700');
    if (dim)  s.push('opacity:.55');
    if (ital) s.push('font-style:italic');
    if (ul)   s.push('text-decoration:underline');
    out += '<span style="' + s.join(';') + '">';
    spanOpen = true;
  }

  let m;
  while ((m = RE.exec(line)) !== null) {
    if (m.index > last) { _open(); out += escHtml(line.slice(last, m.index)); }
    last = RE.lastIndex;
    if (m[2] !== 'm') continue;  // only handle SGR
    _close();
    const ps = m[1] ? m[1].split(';') : ['0'];
    let i = 0;
    while (i < ps.length) {
      const p = +ps[i] || 0;
      if (p === 0)  { fg = bg = null; bold = dim = ital = ul = false; }
      else if (p === 1)  bold = true;
      else if (p === 2)  dim  = true;
      else if (p === 3)  ital = true;
      else if (p === 4)  ul   = true;
      else if (p === 22) { bold = false; dim = false; }
      else if (p === 23) ital = false;
      else if (p === 24) ul   = false;
      else if (_FG[p])   fg   = _FG[p];
      else if (p === 38) {
        if (ps[i+1] === '5')            { fg = _256color(+ps[i+2]); i += 2; }
        else if (ps[i+1] === '2')       { fg = 'rgb('+ps[i+2]+','+ps[i+3]+','+ps[i+4]+')'; i += 4; }
      }
      else if (p === 39) fg = null;
      else if (_BG[p])   bg = _BG[p];
      else if (p === 48) {
        if (ps[i+1] === '5')            { bg = _256color(+ps[i+2]); i += 2; }
        else if (ps[i+1] === '2')       { bg = 'rgb('+ps[i+2]+','+ps[i+3]+','+ps[i+4]+')'; i += 4; }
      }
      else if (p === 49) bg = null;
      i++;
    }
  }
  if (last < line.length) { _open(); out += escHtml(line.slice(last)); }
  _close();
  return out;
}

// Render full output text as editor lines with line numbers.
function _renderOutput(text) {
  if (!text || !text.trim()) return '';
  const lines = text.split('\n');
  if (lines.length && lines[lines.length - 1] === '') lines.pop();
  if (!lines.length) return '';
  const pad = String(lines.length).length;
  return lines.map(function(line, i) {
    return '<div class="out-line">' +
      '<span class="out-ln">' + String(i + 1).padStart(pad, '\u00a0') + '</span>' +
      '<span class="out-code">' + _ansiLine(line) + '</span>' +
      '</div>';
  }).join('');
}

// ── State ─────────────────────────────────────────────────────────────────────
let _currentTarget = null;
let _pollTimer = null;
let _pollGen = 0;
let _autoScroll = true;

// ── Pane list ─────────────────────────────────────────────────────────────────
async function loadPanes() {
  if (!_isAdmin) { openLoginModal(init); return; }
  try {
    const res = await fetch('/api/dev/panes', {headers: _authHeaders()});
    if (res.status === 401) { openLoginModal(init); return; }
    if (!res.ok) return;
    const panes = await res.json();
    const list = document.getElementById('term-pane-list');
    if (!panes.length) {
      list.innerHTML = `<div class="term-empty-sidebar">暂无活跃终端<br><br><code>mira term &lt;project&gt;</code><br>启动新会话</div>`;
      return;
    }
    list.innerHTML = panes.map(p => `
      <div class="term-pane-row${_currentTarget === p.target ? ' active' : ''}"
           data-target="${escHtml(p.target)}"
           data-cmd="${escHtml(p.command || '')}">
        <div class="term-pane-dot ${p.waiting ? 'waiting' : 'running'}"></div>
        <div class="term-pane-info">
          <div class="term-pane-name">${escHtml(p.label)}</div>
          <div class="term-pane-proj">${escHtml(p.project_id || p.target)}</div>
          ${p.command ? `<div class="term-pane-cmd">${escHtml(p.command)}</div>` : ''}
        </div>
      </div>`).join('');
    list.querySelectorAll('.term-pane-row').forEach(row => {
      row.addEventListener('click', () => selectPane(row.dataset.target, row.dataset.cmd));
    });
    const targets = new Set(panes.map(p => p.target));
    if (_currentTarget && !targets.has(_currentTarget)) {
      _currentTarget = null; stopPoll();
    }
  } catch(e) { console.warn('dev panes:', e); }
}

// ── Pane selection ────────────────────────────────────────────────────────────
function selectPane(target, cmd) {
  _pollGen++;
  _currentTarget = target;
  _autoScroll = true;
  document.querySelectorAll('.term-pane-row').forEach(r =>
    r.classList.toggle('active', r.dataset.target === target));
  document.getElementById('term-title').textContent = target + (cmd ? '  ·  ' + cmd : '');
  document.getElementById('term-input').disabled = false;
  document.getElementById('term-send-btn').disabled = false;
  document.getElementById('btn-attach').disabled = false;
  document.getElementById('term-output').textContent = '';
  _clearAttachments();
  document.getElementById('dev-page').classList.add('detail-open');
  stopPoll();
  startPoll();
  // mobile: update bar position then focus input
  setTimeout(() => {
    _updateInputBarPos();
    if (_isMobile()) {
      const inp = document.getElementById('term-input');
      if (inp && !inp.disabled) inp.focus();
    }
  }, 50);
}

function goBackToList() {
  stopPoll();
  _currentTarget = null;
  document.getElementById('dev-page').classList.remove('detail-open');
  document.getElementById('term-input').disabled = true;
  document.getElementById('term-send-btn').disabled = true;
  document.getElementById('btn-attach').disabled = true;
  document.getElementById('term-title').textContent = '';
  _clearAttachments();
  document.getElementById('term-output').innerHTML =
    `<div class="term-empty"><div style="font-size:28px;opacity:.3">⬛</div><div>从左侧选择一个终端</div><div><code>mira term &lt;project&gt;</code> 启动新会话</div></div>`;
}

// ── Output polling ────────────────────────────────────────────────────────────
function startPoll() {
  if (_pollTimer) return;
  _pollTimer = setTimeout(runPoll, 0);
}
function stopPoll() {
  if (_pollTimer) { clearTimeout(_pollTimer); _pollTimer = null; }
  _pollGen++;
}
async function runPoll() {
  if (!_pollTimer) return;
  await fetchOutput();
  if (_pollTimer) _pollTimer = setTimeout(runPoll, 500);
}
async function fetchOutput() {
  if (!_currentTarget) return;
  const gen = _pollGen;
  try {
    const res = await fetch(
      `/api/terminals/${encodeURIComponent(_currentTarget)}/output?lines=200`,
      {headers: _authHeaders()});
    if (_pollGen !== gen) return;
    if (!res.ok) return;
    const data = await res.json();
    const el = document.getElementById('term-output');
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop;
    const html = _renderOutput(data.output || '');
    if (html) {
      el.innerHTML = html;
    } else if (!el.querySelector('.out-line')) {
      el.innerHTML = '<div class="term-empty" style="padding:40px 16px"><div style="font-size:22px;opacity:.25">▋</div><div>等待输出…</div></div>';
    }
    if (_autoScroll) {
      el.scrollTop = el.scrollHeight;
    } else {
      el.scrollTop = el.scrollHeight - distFromBottom;
    }
  } catch(e) {}
}

document.getElementById('term-output').addEventListener('scroll', function() {
  _autoScroll = Math.abs(this.scrollHeight - this.scrollTop - this.clientHeight) < 60;
});

// ── Textarea auto-resize ─────────────────────────────────────────────────────
function _resizeInput() {
  const ta = document.getElementById('term-input');
  if (!ta) return;
  ta.style.height = 'auto';
  const maxH = _isMobile() ? 160 : 120;
  const newH = Math.min(ta.scrollHeight, maxH);
  ta.style.height = newH + 'px';
  ta.classList.toggle('scrollable', ta.scrollHeight > maxH);
  _updateInputBarPos();
}

(function _bindTextarea() {
  const ta = document.getElementById('term-input');
  ta.addEventListener('input', _resizeInput);
  ta.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendKeys();
    }
  });
})();

// ── Send ──────────────────────────────────────────────────────────────────────
function sendKeys() {
  const ta = document.getElementById('term-input');
  const keys = ta.value.trimEnd();
  if (!keys || !_currentTarget) return;
  ta.value = '';
  ta.style.height = '';
  ta.classList.remove('scrollable');
  fetch(`/api/terminals/${encodeURIComponent(_currentTarget)}/send`, {
    method: 'POST',
    headers: _authHeaders({'Content-Type': 'application/json'}),
    body: JSON.stringify({keys: keys + '\n'})
  }).catch(() => {});
  _clearAttachments();
  // keep keyboard open on mobile
  if (_isMobile()) { ta.focus(); _updateInputBarPos(); }
}
function sendRaw(keys) {
  if (!_currentTarget) return;
  fetch(`/api/terminals/${encodeURIComponent(_currentTarget)}/send`, {
    method: 'POST',
    headers: _authHeaders({'Content-Type': 'application/json'}),
    body: JSON.stringify({keys})
  }).catch(() => {});
}
document.getElementById('btn-ctrlc').addEventListener('click', () => sendRaw('C-c'));
document.getElementById('btn-enter').addEventListener('click', () => sendRaw('\n'));

// ── Image attachments ─────────────────────────────────────────────────────────
let _attachments = [];
let _attachSeq = 0;

function _addAttachment(file) {
  if (!file || !file.type.startsWith('image/')) return;
  const id = ++_attachSeq;
  const url = URL.createObjectURL(file);
  _attachments.push({id, url, name: file.name});
  _renderAttachments();
  _updateInputBarPos();
}

function _removeAttachment(id) {
  const idx = _attachments.findIndex(function(a) { return a.id === id; });
  if (idx >= 0) { URL.revokeObjectURL(_attachments[idx].url); _attachments.splice(idx, 1); }
  _renderAttachments();
  _updateInputBarPos();
}

function _clearAttachments() {
  _attachments.forEach(function(a) { URL.revokeObjectURL(a.url); });
  _attachments = [];
  _renderAttachments();
}

function _renderAttachments() {
  const el = document.getElementById('term-attachments');
  if (!_attachments.length) { el.innerHTML = ''; return; }
  el.innerHTML = _attachments.map(function(a) {
    return '<div class="attach-item">' +
      '<img class="attach-img" src="' + a.url + '" alt="' + escHtml(a.name) + '">' +
      '<button class="attach-rm" onclick="_removeAttachment(' + a.id + ')" title="移除">×</button>' +
      '</div>';
  }).join('');
}

// paste image from clipboard (Cmd+V with screenshot)
document.getElementById('term-input').addEventListener('paste', function(e) {
  const items = e.clipboardData && e.clipboardData.items;
  if (!items) return;
  for (let i = 0; i < items.length; i++) {
    if (items[i].type.startsWith('image/')) {
      e.preventDefault();
      _addAttachment(items[i].getAsFile());
    }
  }
});

// iOS detection — file picker always triggers action sheet, use paste instead
function _isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

// Attach button: open file picker on Android/desktop; show paste tip on iOS
document.getElementById('btn-attach').addEventListener('click', function() {
  if (_isIOS()) {
    _showAttachTip('截图后在输入框长按 → 粘贴');
    return;
  }
  document.getElementById('term-file-input').click();
});
document.getElementById('term-file-input').addEventListener('change', function() {
  Array.from(this.files).forEach(_addAttachment);
  this.value = '';
});

// Transient tip near the inputbar (iOS paste guidance)
let _attachTipTimer = null;
function _showAttachTip(msg) {
  let el = document.getElementById('attach-tip');
  el.textContent = msg;
  el.classList.add('visible');
  clearTimeout(_attachTipTimer);
  _attachTipTimer = setTimeout(function() { el.classList.remove('visible'); }, 2400);
}

// drag & drop onto output area
(function() {
  const out = document.getElementById('term-output');
  out.addEventListener('dragover', function(e) {
    e.preventDefault(); e.dataTransfer.dropEffect = 'copy';
    this.classList.add('drag-over');
  });
  out.addEventListener('dragleave', function(e) {
    if (!this.contains(e.relatedTarget)) this.classList.remove('drag-over');
  });
  out.addEventListener('drop', function(e) {
    e.preventDefault(); this.classList.remove('drag-over');
    Array.from(e.dataTransfer.files).forEach(_addAttachment);
  });
})();

// ── Mobile: fix inputbar above keyboard ──────────────────────────────────────
function _isMobile() { return window.innerWidth <= 900; }

function _updateInputBarPos() {
  if (!_isMobile()) return;
  const bar = document.querySelector('.term-inputbar');
  const out = document.getElementById('term-output');
  if (!bar || !out) return;

  if (window.visualViewport) {
    const vvTop    = window.visualViewport.offsetTop;
    const vvHeight = window.visualViewport.height;
    const pageH    = document.documentElement.scrollHeight;
    // distance from bottom of visualViewport to bottom of page
    const fromBottom = pageH - (vvTop + vvHeight);
    bar.style.transform = fromBottom > 10
      ? `translateY(-${window.innerHeight - vvHeight - vvTop}px)`
      : '';
  }

  // keep output from going under the fixed bar
  const barH = bar.offsetHeight;
  out.style.paddingBottom = barH + 8 + 'px';
}

if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', _updateInputBarPos);
  window.visualViewport.addEventListener('scroll', _updateInputBarPos);
}
window.addEventListener('resize', function() {
  _updateInputBarPos();
  _updatePlaceholder();
});

function _updatePlaceholder() {
  const ta = document.getElementById('term-input');
  if (!ta) return;
  ta.placeholder = _isMobile() ? '发送命令…' : '发送命令…   Shift+Enter 换行';
}
_updatePlaceholder();

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await _initAuth();
  if (!_isAdmin) { openLoginModal(init); return; }
  await loadPanes();
  setInterval(loadPanes, 5000);
  _updateInputBarPos();
}
init();
"""

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Dev · Mira</title>\n"
        "<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>\n"
        "<style>\n"
        "  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Noto+Sans+SC:wght@400;700&display=swap');\n"
        + theme_vars_css()
        + topbar_css()
        + page_css
        + "</style>\n</head>\n<body>\n\n"
        + topbar_html(title="Dev", back_url="/") + "\n\n"
        + """\
<div class="dev-page" id="dev-page">
  <!-- Sidebar: pane list -->
  <div class="term-sidebar">
    <div class="term-sidebar-header">所有终端</div>
    <div id="term-pane-list">
      <div class="term-empty-sidebar">正在加载…</div>
    </div>
    <div class="term-sidebar-footer">每 5 秒刷新列表</div>
  </div>

  <!-- Main: terminal output -->
  <div class="term-main">
    <div class="term-titlebar">
      <div class="term-title-left">
        <button class="term-back-btn" onclick="goBackToList()">‹</button>
        <span id="term-title"></span>
      </div>
      <div class="term-quickbtns">
        <button class="term-qbtn" id="btn-ctrlc">Ctrl+C</button>
        <button class="term-qbtn" id="btn-enter">↵ Enter</button>
      </div>
    </div>
    <div class="term-output" id="term-output">
      <div class="term-empty">
        <div style="font-size:28px;opacity:.3">⬛</div>
        <div>从左侧选择一个终端</div>
        <div><code>mira term &lt;project&gt;</code> 启动新会话</div>
      </div>
    </div>
    <div class="term-inputbar">
      <div class="attach-tip" id="attach-tip"></div>
      <div class="term-attachments" id="term-attachments"></div>
      <div class="term-input-row">
        <button class="term-attach-btn" id="btn-attach" disabled title="添加图片（或直接粘贴截图）">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
            <path d="m21 15-5-5L5 21"/>
          </svg>
        </button>
        <textarea class="term-input" id="term-input" placeholder="发送命令…" disabled
                  autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
                  rows="1"></textarea>
        <button class="term-send-btn" id="term-send-btn" onclick="sendKeys()" disabled>发送</button>
      </div>
      <input type="file" id="term-file-input"
             accept="image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif"
             multiple style="display:none">
    </div>
  </div>
</div>

"""
        + settings_overlay_html() + "\n\n"
        + "<script>\n"
        + topbar_js() + "\n"
        + page_js
        + "</script>\n</body>\n</html>\n"
    )
