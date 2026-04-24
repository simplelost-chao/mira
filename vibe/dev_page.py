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
  .term-output {
    flex: 1; padding: 12px 16px; font-family: var(--mono);
    font-size: 12px; line-height: 1.6; overflow-y: auto;
    white-space: pre-wrap; word-break: break-all; color: var(--text);
    background: var(--bg);
  }
  .term-empty {
    height: 100%; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: var(--muted); font-size: 13px; text-align: center; gap: 10px; line-height: 1.7;
  }
  .term-empty code { color: var(--sub); font-size: 11px; }
  .term-inputbar {
    padding: 8px 12px; border-top: 1px solid var(--border);
    display: flex; gap: 8px; flex-shrink: 0; background: var(--panel);
  }
  .term-input {
    flex: 1; background: rgba(255,255,255,.04); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 7px 10px; color: var(--text);
    font-family: var(--mono); font-size: 12px; outline: none; transition: border-color .15s;
  }
  .term-input:focus { border-color: var(--accent); }
  .term-input:disabled { opacity: .4; cursor: not-allowed; }
  .term-send-btn {
    background: var(--accent); border: none; color: #fff;
    padding: 7px 16px; border-radius: var(--radius-sm); font-size: 12px;
    cursor: pointer; font-family: var(--mono); transition: opacity .12s; flex-shrink: 0;
  }
  .term-send-btn:hover { opacity: .85; }
  .term-send-btn:disabled { opacity: .4; cursor: not-allowed; }

  /* ── Mobile: master-detail (≤ 900px) ── */
  @media (max-width: 900px) {
    .topbar { padding: 0 14px; gap: 8px; height: 48px; }
    .topbar-logo { letter-spacing: 1px; }
    .topbar-logo .logo-m { font-size: 20px; }
    .topbar-logo .logo-ira { font-size: 14px; }
    .topbar-logo .logo-cursor { font-size: 16px; }
    .topbar-page-title { display: none; }
    .topbar-sep { display: none; }
    .dev-page { height: calc(100vh - 48px); }

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

    .term-output { font-size: 11px; padding: 8px 12px; }
    .term-input { font-size: 14px; padding: 8px 10px; }
    .term-send-btn { padding: 8px 16px; font-size: 13px; }
    .term-inputbar { padding: 8px 10px; }
    .term-qbtn { padding: 4px 10px; }
  }
"""

    page_js = r"""
// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
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
  document.getElementById('term-output').textContent = '';
  document.getElementById('dev-page').classList.add('detail-open');
  stopPoll();
  startPoll();
}

function goBackToList() {
  stopPoll();
  _currentTarget = null;
  document.getElementById('dev-page').classList.remove('detail-open');
  document.getElementById('term-input').disabled = true;
  document.getElementById('term-send-btn').disabled = true;
  document.getElementById('term-title').textContent = '';
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
    el.textContent = data.output || '';
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

// ── Send ──────────────────────────────────────────────────────────────────────
function sendKeys() {
  const inp = document.getElementById('term-input');
  const keys = inp.value.trim();
  if (!keys || !_currentTarget) return;
  inp.value = '';
  fetch(`/api/terminals/${encodeURIComponent(_currentTarget)}/send`, {
    method: 'POST',
    headers: _authHeaders({'Content-Type': 'application/json'}),
    body: JSON.stringify({keys: keys + '\n'})
  }).catch(() => {});
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

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await _initAuth();
  if (!_isAdmin) { openLoginModal(init); return; }
  await loadPanes();
  setInterval(loadPanes, 5000);
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
      <input class="term-input" id="term-input" placeholder="发送按键…" disabled
             onkeydown="if(event.key==='Enter')sendKeys()">
      <button class="term-send-btn" id="term-send-btn" onclick="sendKeys()" disabled>发送</button>
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
