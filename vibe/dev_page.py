"""Dev mode page — sidebar pane list + ttyd iframe."""


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

  /* ── Sidebar ── */
  .term-sidebar {
    width: 200px; border-right: 1px solid var(--border);
    display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden;
    background: var(--panel);
  }
  .term-sidebar-header {
    padding: 10px 14px 10px 14px;
    display: flex; align-items: center; justify-content: space-between;
    font-size: 10px; color: var(--muted);
    font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .term-new-btn {
    background: none; border: 1px solid var(--border);
    color: var(--muted); width: 20px; height: 20px;
    border-radius: var(--radius-sm); font-size: 14px; line-height: 1;
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    padding: 0; transition: color .12s, border-color .12s;
  }
  .term-new-btn:hover { color: var(--accent); border-color: var(--accent); }
  #term-pane-list { flex: 1; overflow-y: auto; }
  .term-pane-row {
    padding: 10px 14px; display: flex; align-items: flex-start; gap: 8px;
    cursor: pointer; border-left: 2px solid transparent; transition: background .12s, border-color .12s;
  }
  .term-pane-row:hover { background: rgba(255,255,255,.03); }
  .term-pane-row.active { background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }
  .term-pane-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 3px;
    transition: background .25s, box-shadow .25s;
  }
  .term-pane-dot.inactive { background: var(--border); }
  .term-pane-dot.idle     { background: var(--muted); opacity: .45; }
  .term-pane-dot.running  { background: var(--green); box-shadow: 0 0 6px rgba(63,185,80,.6); animation: pane-pulse .9s ease-in-out infinite; }
  .term-pane-dot.confirm  { background: var(--orange); box-shadow: 0 0 6px var(--orange); animation: pane-pulse 1.4s ease-in-out infinite; }
  .term-pane-dot.done     { background: var(--green); }
  .term-pane-dot.error    { background: var(--red); }
  @keyframes pane-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  .term-pane-info { min-width: 0; flex: 1; }
  .term-pane-name { font-size: 12px; color: var(--text); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-pane-proj { font-size: 10px; color: var(--sub); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-pane-cmd  { font-size: 9px; color: var(--muted); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-empty-sidebar { padding: 32px 16px; font-size: 12px; color: var(--muted); line-height: 1.8; }
  .term-empty-sidebar code { color: var(--sub); }

  /* ── ttyd iframe ── */
  .term-main {
    flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden;
  }
  .term-placeholder {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: var(--muted); font-size: 13px; text-align: center; gap: 10px; line-height: 1.7;
  }
  .term-placeholder code { color: var(--sub); font-size: 11px; }
  #ttyd-frame {
    flex: 1; border: none; display: none; background: #0d1117;
  }
  #ttyd-frame.visible { display: block; }

  /* ── Mobile ── */
  @media (max-width: 900px) {
    .dev-page { height: calc(100dvh - 48px); }
    .term-sidebar { width: 100%; flex: 1; border-right: none; }
    .term-sidebar-header { padding: 14px 16px 10px; font-size: 11px; letter-spacing: .5px; text-transform: none; font-weight: 700; }
    #term-pane-list { padding: 0; }
    .term-pane-row {
      position: relative; padding: 14px 48px 14px 16px;
      border-left: none; border-bottom: 1px solid var(--border);
    }
    .term-pane-row::after {
      content: '›'; position: absolute; right: 16px; top: 50%;
      transform: translateY(-50%); color: var(--muted); font-size: 22px; line-height: 1;
    }
    .term-pane-dot { margin-top: 6px; }
    .term-pane-name { font-size: 14px; }
    .term-pane-proj { font-size: 12px; margin-top: 3px; }
    .term-main { display: none; flex: 1; }
    .dev-page.detail-open .term-sidebar { display: none; }
    .dev-page.detail-open .term-main { display: flex; }
  }
"""

    page_js = r"""
// ── Helpers ────────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── State ──────────────────────────────────────────────────────────────────────
let _currentTarget = null;
const _paneState = {};

// ── State detection (for sidebar dots) ────────────────────────────────────────
function _detectState(text) {
  if (!text || !text.trim()) return 'idle';
  const lines = text.trimEnd().split('\n').filter(l => l.trim());
  if (!lines.length) return 'idle';
  const last = lines[lines.length - 1];
  const tail = lines.slice(-6).join('\n');
  if (/\(y\/n\)|\[Y\/n\]|\[y\/N\]|yes\/no|Do you want|Shall I|Would you like|proceed\?|continue\?|Are you sure/i.test(tail))
    return 'confirm';
  if (/\b(Error:|ERROR:|✗|FAILED|Exception:|Traceback|SyntaxError|TypeError|ValueError|ModuleNotFound)\b/.test(tail))
    return 'error';
  if (/✓|✅|\bDone\b|\bCompleted\b|\bAll done\b|\bSuccess\b|\bfinished\b|\* \w+ for \d/i.test(tail))
    return 'done';
  if (/[$❯>%#]\s*$/.test(last))
    return 'idle';
  return 'running';
}

function _onStateChange(target, newState) {
  const prev = _paneState[target];
  _paneState[target] = newState;
  if (newState === prev) return;
  const row = document.querySelector(`.term-pane-row[data-target="${CSS.escape(target)}"]`);
  if (row) {
    const dot = row.querySelector('.term-pane-dot');
    if (dot) dot.className = 'term-pane-dot ' + (newState || 'inactive');
  }
  if (newState === 'confirm' || newState === 'done' || newState === 'error') {
    _maybeNotify(target, newState);
  }
}

// ── Notifications ─────────────────────────────────────────────────────────────
function _maybeNotify(target, state) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const label = { confirm: '需要你确认操作', done: '任务完成了', error: '遇到了错误' }[state];
  if (!label) return;
  new Notification('Mira · ' + target, { body: label, silent: false });
}
document.addEventListener('click', function() {
  if ('Notification' in window && Notification.permission === 'default')
    Notification.requestPermission();
}, { once: true });

// ── Background polling (sidebar dots only) ────────────────────────────────────
let _bgPollTimer = null;
async function _bgPoll() {
  const rows = document.querySelectorAll('.term-pane-row');
  for (const row of rows) {
    const target = row.dataset.target;
    if (_paneState[target] !== 'running') continue;
    try {
      const res = await fetch(
        '/api/terminals/' + encodeURIComponent(target) + '/output?lines=30',
        { headers: _authHeaders() });
      if (!res.ok) continue;
      const data = await res.json();
      _onStateChange(target, _detectState(data.output || ''));
    } catch(e) {}
  }
  _bgPollTimer = setTimeout(_bgPoll, 5000);
}

// ── Pane list ─────────────────────────────────────────────────────────────────
async function loadPanes() {
  if (!_isAdmin) { openLoginModal(init); return; }
  try {
    const res = await fetch('/api/dev/panes', { headers: _authHeaders() });
    if (res.status === 401) { openLoginModal(init); return; }
    if (!res.ok) return;
    const panes = await res.json();
    const list = document.getElementById('term-pane-list');
    if (!panes.length) {
      list.innerHTML = `<div class="term-empty-sidebar">暂无活跃终端<br><br><code>mira term &lt;project&gt;</code><br>启动新会话</div>`;
      return;
    }
    list.innerHTML = panes.map(function(p) {
      const st = _paneState[p.target] || 'inactive';
      return `<div class="term-pane-row${_currentTarget === p.target ? ' active' : ''}"
           data-target="${escHtml(p.target)}"
           data-cmd="${escHtml(p.command || '')}">
        <div class="term-pane-dot ${st}"></div>
        <div class="term-pane-info">
          <div class="term-pane-name">${escHtml(p.label)}</div>
          <div class="term-pane-proj">${escHtml(p.project_id || p.target)}</div>
          ${p.command ? `<div class="term-pane-cmd">${escHtml(p.command)}</div>` : ''}
        </div>
      </div>`;
    }).join('');
    list.querySelectorAll('.term-pane-row').forEach(row => {
      row.addEventListener('click', () => selectPane(row.dataset.target, row.dataset.cmd));
    });
    // If current pane disappeared, clear
    const targets = new Set(panes.map(p => p.target));
    if (_currentTarget && !targets.has(_currentTarget)) {
      _currentTarget = null;
      showPlaceholder();
    }
  } catch(e) { console.warn('dev panes:', e); }
}

// ── Pane selection ────────────────────────────────────────────────────────────
async function selectPane(target, cmd) {
  _currentTarget = target;
  document.querySelectorAll('.term-pane-row').forEach(r =>
    r.classList.toggle('active', r.dataset.target === target));
  document.getElementById('dev-page').classList.add('detail-open');

  // Tell tmux to switch to this pane
  try {
    await fetch('/api/terminal/focus', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify({ target })
    });
  } catch(e) {}

  // Show iframe (already loaded)
  showTerminal();
}

function showTerminal() {
  document.getElementById('term-placeholder').style.display = 'none';
  document.getElementById('ttyd-frame').classList.add('visible');
}

function showPlaceholder() {
  document.getElementById('ttyd-frame').classList.remove('visible');
  document.getElementById('term-placeholder').style.display = '';
  document.getElementById('dev-page').classList.remove('detail-open');
}

// ── New window ────────────────────────────────────────────────────────────────
async function newWindow(cwd) {
  try {
    await fetch('/api/terminal/new-window', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify({ cwd: cwd || null })
    });
    setTimeout(loadPanes, 600);
  } catch(e) { console.warn('new-window:', e); }
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await _initAuth();
  if (!_isAdmin) { openLoginModal(init); return; }
  // Load ttyd iframe immediately (background, so it's ready when user clicks a pane)
  const frame = document.getElementById('ttyd-frame');
  frame.src = '/terminal/';
  await loadPanes();
  setInterval(loadPanes, 5000);
  _bgPoll();
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
        '<link rel="stylesheet" href="/static/fonts/fonts.css">\n'
        "<style>\n"
        + theme_vars_css()
        + topbar_css()
        + page_css
        + "</style>\n</head>\n<body>\n\n"
        + topbar_html(title="Dev", back_url="javascript:history.back()", hide_dev=True) + "\n\n"
        + """\
<div class="dev-page" id="dev-page">
  <!-- Sidebar: pane list -->
  <div class="term-sidebar">
    <div class="term-sidebar-header">
      <span>所有终端</span>
      <button class="term-new-btn" onclick="newWindow(null)" title="新建终端窗口">+</button>
    </div>
    <div id="term-pane-list">
      <div class="term-empty-sidebar">正在加载…</div>
    </div>
  </div>

  <!-- Main: ttyd iframe -->
  <div class="term-main">
    <div id="term-placeholder" class="term-placeholder">
      <div style="font-size:28px;opacity:.3">⬛</div>
      <div>从左侧选择一个终端</div>
      <div><code>mira term &lt;project&gt;</code> 启动新会话</div>
    </div>
    <iframe id="ttyd-frame" allow="clipboard-read; clipboard-write"></iframe>
  </div>
</div>

"""
        + settings_overlay_html() + "\n\n"
        + "<script>\n"
        + topbar_js() + "\n"
        + page_js
        + "</script>\n</body>\n</html>\n"
    )
