"""Dev mode page — sidebar pane list + ttyd iframe."""


def render_dev_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js

    page_css = r"""
  /* ── Page reset (lock body to viewport, terminal handles its own scroll) ── */
  :root { --app-h: 100vh; }
  html, body { margin: 0; padding: 0; height: 100vh; overflow: hidden; overscroll-behavior: none; width: 100%; max-width: 100vw; }
  /* Lock scroll when mobile terminal detail is open */
  body.detail-locked { position: fixed; width: 100%; touch-action: none; }

  /* ── Main layout ── */
  .dev-page {
    height: calc(var(--app-h) - 52px);
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
  #term-pane-list { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }
  .term-pane-row {
    padding: 10px 14px; display: flex; align-items: flex-start; gap: 8px;
    cursor: pointer; border-left: 2px solid transparent; transition: background .12s, border-color .12s;
  }
  .term-pane-row:hover { background: rgba(255,255,255,.03); }
  .term-pane-row.active { background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }
  .term-pane-kill {
    opacity: 0; flex-shrink: 0; cursor: pointer;
    width: 18px; height: 18px; border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    color: var(--muted); font-size: 12px; line-height: 1;
    transition: opacity .12s, color .12s, background .12s;
    margin-left: 4px;
  }
  .term-pane-row:hover .term-pane-kill { opacity: 0.7; }
  .term-pane-kill:hover {
    opacity: 1 !important;
    color: var(--red, #ef4444);
    background: rgba(239, 68, 68, 0.12);
  }
  .term-pane-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 3px;
    transition: background .25s, box-shadow .25s;
  }
  .term-pane-dot.inactive { background: var(--border); }
  .term-pane-dot.idle     { background: var(--green); }
  .term-pane-dot.running  { background: var(--green); box-shadow: 0 0 6px rgba(63,185,80,.6); animation: pane-pulse .9s ease-in-out infinite; }
  .term-pane-dot.confirm  { background: var(--orange); box-shadow: 0 0 6px var(--orange); animation: pane-pulse 1.4s ease-in-out infinite; }
  .term-pane-dot.done     { background: var(--green); }
  .term-pane-dot.error    { background: var(--red); }
  @keyframes pane-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  .term-pane-info { min-width: 0; flex: 1; }
  .term-pane-name { font-size: 12px; color: var(--text); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 6px; }
  .term-pane-name-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  /* rename UI temporarily disabled */
  .term-pane-sub  { font-size: 10px; color: var(--sub); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-empty-sidebar { padding: 32px 16px; font-size: 12px; color: var(--muted); line-height: 1.8; }
  .term-empty-sidebar code { color: var(--sub); }

  /* ── Group headers ── */
  .term-group-header {
    padding: 8px 14px; display: flex; align-items: center; gap: 6px;
    cursor: pointer; user-select: none;
    border-bottom: 1px solid rgba(255,255,255,.04);
    transition: background .12s;
  }
  .term-group-header:hover { background: rgba(255,255,255,.03); }
  .term-group-arrow {
    font-size: 10px; color: var(--muted); width: 12px; text-align: center;
    transition: transform .15s;
  }
  .term-group-arrow.collapsed { transform: rotate(-90deg); }
  .term-group-name {
    font-size: 11px; font-weight: 600; color: var(--sub);
    flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .term-group-count {
    font-size: 10px; color: var(--muted); background: rgba(255,255,255,.06);
    padding: 0 5px; border-radius: 8px; line-height: 16px;
  }
  .term-group-body { overflow: hidden; }
  .term-group-body.collapsed { display: none; }
  .term-group-body .term-pane-row { padding-left: 26px; }

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
  .term-iframe-wrap {
    flex: 1; position: relative; min-height: 0; overflow: hidden;
  }
  #ttyd-frame {
    border: none; display: none; background: #0d1117;
    width: 100%; max-width: 100%; height: 100%;
    overflow: hidden;
  }
  #ttyd-frame.visible { display: block; }
  /* Touch overlay + scroll badge: mobile-only (hidden on desktop) */
  .term-touch-overlay { display: none; }
  .term-scroll-badge { display: none; }
  /* Mobile-only elements hidden on desktop */
  .mobile-term-output { display: none; }
  .mobile-input-bar { display: none; }

  /* ── Empty-state new terminal button ── */
  .term-placeholder-btn {
    margin-top: 12px; padding: 10px 28px;
    background: none; border: 1px solid var(--border);
    color: var(--sub); font-family: var(--mono); font-size: 13px;
    border-radius: var(--radius-sm); cursor: pointer;
    transition: color .15s, border-color .15s;
  }
  .term-placeholder-btn:hover { color: var(--accent); border-color: var(--accent); }

  /* ── New terminal dialog overlay ── */
  .new-term-overlay {
    position: fixed; inset: 0; z-index: 400;
    background: rgba(0,0,0,.55); backdrop-filter: blur(4px);
    display: flex; align-items: center; justify-content: center;
  }
  .new-term-dialog {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; width: 380px; max-height: 70vh;
    display: flex; flex-direction: column; overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,.4);
  }
  .new-term-dialog-header {
    padding: 16px 20px; display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .new-term-dialog-header span {
    font-size: 14px; font-weight: 600; color: var(--text);
  }
  .new-term-dialog-close {
    background: none; border: none; color: var(--muted); font-size: 18px;
    cursor: pointer; padding: 2px 6px; border-radius: 4px;
    transition: color .12s, background .12s; line-height: 1;
  }
  .new-term-dialog-close:hover { color: var(--text); background: rgba(255,255,255,.06); }
  .new-term-dialog-list {
    flex: 1; overflow-y: auto; padding: 6px 0;
  }
  .new-term-item {
    padding: 10px 20px; cursor: pointer; transition: background .1s;
  }
  .new-term-item:hover { background: rgba(var(--accent-rgb),.1); }
  .new-term-item-name {
    font-size: 13px; font-weight: 600; color: var(--text);
  }
  .new-term-item-path {
    font-size: 11px; color: var(--muted); margin-top: 2px;
  }
  .new-term-item-sep {
    height: 1px; background: var(--border); margin: 0 20px;
  }

  /* ── Mobile detail header (replaces topbar when a pane is open) ── */
  .term-detail-header { display: none; }

  /* ── Mobile input bar (hidden on desktop) ── */
  .mobile-input-bar { display: none; }

  /* ── Mobile ── */
  @media (max-width: 900px) {
    .term-detail-header {
      display: flex; align-items: center; gap: 10px;
      height: 40px; padding: 0 12px; flex-shrink: 0;
      background: var(--panel); border-bottom: 1px solid var(--border);
    }
    .term-detail-back {
      background: none; border: 1px solid var(--border);
      border-radius: 6px; color: var(--text);
      padding: 6px 10px; font-size: 14px; cursor: pointer;
      line-height: 1; flex-shrink: 0;
    }
    .term-detail-back:active { background: var(--bg); }
    .term-detail-title {
      font-size: 15px; font-weight: 600; color: var(--text);
      flex: 1; min-width: 0;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    /* Hide desktop term-detail-header by default; it only shows on mobile */
    .dev-page:not(.detail-open) .term-detail-header { display: none; }

    /* When detail is open: hide topbar, use full viewport */
    body:has(.dev-page.detail-open) .topbar { display: none !important; }
    .dev-page.detail-open { height: var(--app-h, 100dvh); }

    .dev-page { height: calc(var(--app-h) - 52px); }
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
    .term-group-header { padding: 12px 16px; }
    .term-group-body .term-pane-row { padding-left: 28px; }
    .term-main { display: none; flex-direction: column; }
    .dev-page.detail-open .term-sidebar { display: none; }
    .dev-page.detail-open .term-main {
      display: flex; position: fixed; inset: 0; top: 0;
      height: var(--app-h, 100dvh); z-index: 200;
      background: var(--bg);
      overscroll-behavior: none;
      overflow: hidden; max-width: 100vw;
    }
    /* Mobile: hide iframe completely — use independent WebSocket + ANSI renderer */
    #ttyd-frame { display: none !important; }
    .term-touch-overlay { display: none !important; }
    .term-scroll-badge { display: none !important; }
    .term-iframe-wrap { flex: none; height: 0; min-height: 0; overflow: hidden; }

    /* Mobile terminal text output (WebSocket-fed, ANSI-colored) */
    .mobile-term-output.visible {
      display: block; flex: 1; min-height: 0;
      background: #0d1117; color: #abb2bf;
      font-family: var(--mono); font-size: 12px; line-height: 1.4;
      padding: 6px 8px; margin: 0;
      overflow-y: auto; -webkit-overflow-scrolling: touch;
      white-space: pre-wrap; word-break: break-all; overflow-wrap: break-word;
      overscroll-behavior: contain;
    }

    /* ── Mobile input bar ── */
    .mobile-input-bar {
      display: flex; flex-direction: column; flex-shrink: 0;
      background: var(--panel); border-top: 1px solid var(--border);
      padding: 0; z-index: 210;
    }
    /* Special keys toolbar */
    .mobile-keys-row {
      display: flex; gap: 0; padding: 4px 8px;
      overflow-x: auto; -webkit-overflow-scrolling: touch;
      border-bottom: 1px solid rgba(255,255,255,.04);
    }
    .mobile-key-btn {
      background: rgba(255,255,255,.06); border: 1px solid var(--border);
      color: var(--sub); font-family: var(--mono); font-size: 11px;
      padding: 4px 10px; border-radius: 4px; cursor: pointer;
      white-space: nowrap; flex-shrink: 0; margin-right: 4px;
      line-height: 1.2; transition: color .12s, border-color .12s, background .12s;
      -webkit-tap-highlight-color: transparent;
    }
    .mobile-key-btn:active { background: rgba(var(--accent-rgb),.2); border-color: var(--accent); color: var(--accent); }
    /* Input row */
    .mobile-input-row {
      display: flex; align-items: flex-end; gap: 8px;
      padding: 8px 10px; padding-bottom: max(8px, env(safe-area-inset-bottom));
    }
    .mobile-cmd-input {
      flex: 1; min-height: 36px; max-height: 120px;
      background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
      color: var(--text); font-family: var(--mono); font-size: 16px;
      padding: 8px 12px; outline: none; resize: none;
      line-height: 1.4; overflow-y: auto;
    }
    .mobile-cmd-input:focus { border-color: var(--accent); }
    .mobile-cmd-input::placeholder { color: var(--muted); }
    .mobile-send-btn {
      width: 36px; height: 36px; flex-shrink: 0;
      background: var(--accent); border: none; border-radius: 8px;
      color: #fff; font-size: 18px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: opacity .12s;
      -webkit-tap-highlight-color: transparent;
    }
    .mobile-send-btn:active { opacity: .7; }
    .mobile-send-btn:disabled { opacity: .3; }
  }
"""

    page_js = r"""
// ── Mobile detection ──────────────────────────────────────────────────────────
var _isMobile = window.matchMedia('(max-width: 900px)').matches;

// ── Visual viewport tracking (mobile keyboard adaptation) ─────────────────────
(function() {
  var _debounceTimer = null;
  var _lastH = 0;
  function u() {
    var h;
    if (window.visualViewport) {
      h = Math.round(window.visualViewport.height);
    } else {
      h = window.innerHeight;
    }
    // Skip if height hasn't changed (avoid unnecessary layout recalcs)
    if (h === _lastH) return;
    _lastH = h;
    // On mobile detail view, debounce to avoid thrashing during keyboard animation
    var inDetail = document.getElementById('dev-page') &&
                   document.getElementById('dev-page').classList.contains('detail-open');
    if (_isMobile && inDetail) {
      clearTimeout(_debounceTimer);
      _debounceTimer = setTimeout(function() {
        document.documentElement.style.setProperty('--app-h', h + 'px');
        window.scrollTo(0, 0);
      }, 150);
    } else {
      document.documentElement.style.setProperty('--app-h', h + 'px');
      window.scrollTo(0, 0);
    }
  }
  u();
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', u);
    window.visualViewport.addEventListener('scroll', u);
  }
  window.addEventListener('resize', u);
})();

// ── Helpers ────────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── State ──────────────────────────────────────────────────────────────────────
let _currentTarget = null;
const _paneState = {};
const _groupCollapsed = {};  // project_id -> bool
const _filterProject = new URLSearchParams(location.search).get('project') || null;

// ── State detection (for sidebar dots) ────────────────────────────────────────
function _detectState(text) {
  if (!text || !text.trim()) return 'idle';
  // Filter out status-bar lines (e.g. Claude Code ⏵⏵, tmux status)
  const lines = text.trimEnd().split('\n')
    .filter(l => l.trim())
    .filter(l => !/[⏵⏴]\s*\S/.test(l) && !/^─+$/.test(l.trim()));
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
  if (state === 'confirm') playNotificationSound();
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
  var inDetail = document.getElementById('dev-page').classList.contains('detail-open');
  // On mobile detail view: skip ALL polling to avoid any interference with IME/input
  if (_isMobile && inDetail) {
    _bgPollTimer = setTimeout(_bgPoll, 30000);
    return;
  }
  var rows = inDetail && _currentTarget
    ? document.querySelectorAll('.term-pane-row[data-target="' + CSS.escape(_currentTarget) + '"]')
    : document.querySelectorAll('.term-pane-row');
  for (const row of rows) {
    const target = row.dataset.target;
    try {
      const res = await fetch(
        '/api/terminals/' + encodeURIComponent(target) + '/output?lines=30',
        { headers: _authHeaders() });
      if (!res.ok) continue;
      const data = await res.json();
      _onStateChange(target, _detectState(data.output || ''));
    } catch(e) {}
  }
  _bgPollTimer = setTimeout(_bgPoll, inDetail ? 15000 : 10000);
}

// ── Pane list (grouped by project) ────────────────────────────────────────────
let _firstLoad = true;
async function loadPanes(forceRebuild) {
  if (!_isAdmin) { openLoginModal(init); return; }
  // On mobile detail view: skip entirely to protect iframe focus/IME
  var inDetail = document.getElementById('dev-page').classList.contains('detail-open');
  if (_isMobile && inDetail && !_firstLoad && !forceRebuild) return;
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

    // Group panes by project_id
    const groups = new Map();
    for (const p of panes) {
      const pid = p.project_id || '_ungrouped';
      if (!groups.has(pid)) groups.set(pid, { name: p.project_name || p.project_id || '未分组', panes: [] });
      groups.get(pid).panes.push(p);
    }

    // On first load with ?project=xxx, collapse all other groups
    if (_firstLoad && _filterProject) {
      for (const [pid] of groups) {
        _groupCollapsed[pid] = (pid !== _filterProject);
      }
    }
    _firstLoad = false;

    let html = '';
    for (const [pid, grp] of groups) {
      const collapsed = !!_groupCollapsed[pid];
      html += `<div class="term-group-header" data-group="${escHtml(pid)}" onclick="toggleGroup('${escHtml(pid)}')">
        <span class="term-group-arrow${collapsed ? ' collapsed' : ''}">▾</span>
        <span class="term-group-name">${escHtml(grp.name)}</span>
        <span class="term-group-count">${grp.panes.length}</span>
      </div>
      <div class="term-group-body${collapsed ? ' collapsed' : ''}" data-group-body="${escHtml(pid)}">`;
      for (const p of grp.panes) {
        const st = _paneState[p.target] || 'inactive';
        html += `<div class="term-pane-row${_currentTarget === p.target ? ' active' : ''}"
             data-target="${escHtml(p.target)}"
             data-cmd="${escHtml(p.command || '')}"
             data-project-id="${escHtml(p.project_id || '')}">
          <div class="term-pane-dot ${st}"></div>
          <div class="term-pane-info">
            <div class="term-pane-name">
              <span class="term-pane-name-text">${escHtml(p.label || p.target)}</span>
              <span class="term-pane-kill" title="关闭终端" onclick="event.stopPropagation(); killPane(this);">×</span>
            </div>
            <div class="term-pane-sub">${escHtml(p.command || '')}</div>
          </div>
        </div>`;
      }
      html += '</div>';
    }
    // Skip DOM rebuild if user is in detail view (mobile terminal active)
    // to avoid interrupting IME/voice input in the iframe
    var inDetail = document.getElementById('dev-page').classList.contains('detail-open');
    if (inDetail && !forceRebuild) {
      // Only update status dots without touching DOM structure
      for (const p of panes) {
        const row = document.querySelector('.term-pane-row[data-target="' + CSS.escape(p.target) + '"]');
        if (row) {
          var dot = row.querySelector('.term-pane-dot');
          var st = _paneState[p.target] || 'inactive';
          if (dot) dot.className = 'term-pane-dot ' + st;
        }
      }
    } else {
      list.innerHTML = html;
    }

    // If current pane disappeared, clear
    const targets = new Set(panes.map(p => p.target));
    if (_currentTarget && !targets.has(_currentTarget)) {
      _currentTarget = null;
      showPlaceholder();
    }

    // Auto-select first pane of filtered project on first load
    if (_filterProject && !_currentTarget) {
      const grp = groups.get(_filterProject);
      if (grp && grp.panes.length) {
        selectPane(grp.panes[0].target, grp.panes[0].command || '');
      }
    }
  } catch(e) { console.warn('dev panes:', e); }
}

function toggleGroup(pid) {
  _groupCollapsed[pid] = !_groupCollapsed[pid];
  const collapsed = _groupCollapsed[pid];
  const header = document.querySelector(`.term-group-header[data-group="${CSS.escape(pid)}"]`);
  const body = document.querySelector(`.term-group-body[data-group-body="${CSS.escape(pid)}"]`);
  if (header) header.querySelector('.term-group-arrow').classList.toggle('collapsed', collapsed);
  if (body) body.classList.toggle('collapsed', collapsed);
}

// ── Kill pane ─────────────────────────────────────────────────────────────────
async function killPane(killEl) {
  const row = killEl.closest('.term-pane-row');
  const target = row.dataset.target;
  if (!target) return;
  const name = row.querySelector('.term-pane-name-text')?.textContent || target;
  if (!confirm(`确认关闭终端 "${name}" ?\n\n该 tmux pane 会被 kill，shell 进程退出，无法恢复。`)) return;
  try {
    const res = await fetch(`/api/dev/panes/${encodeURIComponent(target)}`, {
      method: 'DELETE',
      headers: _authHeaders(),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status} ${detail}`);
    }
    // If we were viewing this pane, hide the iframe placeholder
    if (_currentTarget === target) {
      _currentTarget = null;
      showPlaceholder();
    }
    await loadPanes();
  } catch(e) {
    alert('关闭失败: ' + e.message);
  }
}

// ── Inline rename (temporarily disabled) ─────────────────────────────────────

// ── Pane selection ────────────────────────────────────────────────────────────
async function selectPane(target, cmd) {
  _currentTarget = target;
  const rows = document.querySelectorAll('.term-pane-row');
  rows.forEach(r => r.classList.toggle('active', r.dataset.target === target));
  document.getElementById('dev-page').classList.add('detail-open');
  // Lock body scroll on mobile to prevent iOS rubber-banding
  if (_isMobile) document.body.classList.add('detail-locked');

  // Update mobile detail header title with project_name from the row
  const activeRow = document.querySelector(`.term-pane-row[data-target="${CSS.escape(target)}"]`);
  const titleEl = document.getElementById('term-detail-title');
  if (activeRow && titleEl) {
    const txt = activeRow.querySelector('.term-pane-name-text');
    titleEl.textContent = txt ? txt.textContent : target;
  }

  // Desktop: tell tmux to switch focus (affects ttyd iframe).
  // Mobile: skip — uses independent WebSocket stream, no shared state.
  if (!_isMobile) {
    try {
      var focusRes = await fetch('/api/terminal/focus', {
        method: 'POST',
        headers: _authHeaders({'Content-Type': 'application/json'}),
        body: JSON.stringify({ target })
      });
      if (!focusRes.ok) console.warn('focus failed:', focusRes.status);
    } catch(e) { console.warn('focus error:', e); }
  }

  showTerminal();
}

async function _copyTmuxBuffer() {
  try {
    const res = await fetch('/api/terminal/buffer', { headers: _authHeaders() });
    if (!res.ok) return;
    const { text } = await res.json();
    if (!text) return;
    // Try modern clipboard API first, fall back to execCommand
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try { await navigator.clipboard.writeText(text); return; } catch(e) {}
    }
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  } catch(e) { console.warn('copy buffer:', e); }
}

function showTerminal() {
  document.getElementById('term-placeholder').style.display = 'none';

  if (_isMobile) {
    // Mobile: show ANSI-rendered output + start WebSocket stream
    document.getElementById('mobile-term-output').classList.add('visible');
    if (_currentTarget) _connectTermWs(_currentTarget);
    return;
  }

  // Desktop: load ttyd iframe
  const frame = document.getElementById('ttyd-frame');
  if (!frame.src) {
    frame.src = '/terminal/';
    frame.addEventListener('load', () => {
      try {
        frame.contentWindow.addEventListener('beforeunload', e => {
          e.stopImmediatePropagation();
        }, true);
        frame.contentWindow.document.addEventListener('keydown', e => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'c' && !e.shiftKey) {
            _copyTmuxBuffer();
          }
        }, true);
      } catch(e) {}
    });
  }
  frame.classList.add('visible');
}

function showPlaceholder() {
  document.getElementById('ttyd-frame').classList.remove('visible');
  document.getElementById('mobile-term-output').classList.remove('visible');
  _disconnectTermWs();
  document.getElementById('term-placeholder').style.display = '';
  document.getElementById('dev-page').classList.remove('detail-open');
  document.body.classList.remove('detail-locked');
}

// ── New window ────────────────────────────────────────────────────────────────
async function newWindow(cwd) {
  try {
    // Snapshot existing targets before creating
    var oldTargets = new Set(
      Array.from(document.querySelectorAll('.term-pane-row')).map(r => r.dataset.target)
    );
    await fetch('/api/terminal/new-window', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify({ cwd: cwd || null })
    });
    // Poll until the new pane appears (tmux needs a moment)
    for (var _attempt = 0; _attempt < 6; _attempt++) {
      await new Promise(r => setTimeout(r, 500));
      var res2 = await fetch('/api/dev/panes', { headers: _authHeaders() });
      if (!res2.ok) continue;
      var panes2 = await res2.json();
      var newPane = panes2.find(p => !oldTargets.has(p.target));
      if (newPane) {
        await loadPanes(true);
        selectPane(newPane.target, newPane.command || '');
        return;
      }
    }
    // Fallback: just reload list
    await loadPanes(true);
  } catch(e) { console.warn('new-window:', e); }
}

// ── New terminal dialog ───────────────────────────────────────────────────────
async function openNewTermDialog() {
  const overlay = document.getElementById('new-term-overlay');
  const list = document.getElementById('new-term-list');
  // Static home option
  let html = `<div class="new-term-item" data-cwd="">
    <div class="new-term-item-name">~ 主目录</div>
    <div class="new-term-item-path">在用户 home 目录打开</div>
  </div>`;
  // Fetch projects (sorted by last activity, same as homepage)
  try {
    const res = await fetch('/api/projects', { headers: _authHeaders() });
    if (res.ok) {
      const projects = await res.json();
      projects.sort((a, b) => {
        const ta = (a.claude_activity && a.claude_activity.last_session) || '';
        const tb = (b.claude_activity && b.claude_activity.last_session) || '';
        return tb.localeCompare(ta);
      });
      for (const p of projects) {
        if (!p.path) continue;
        html += `<div class="new-term-item-sep"></div>`;
        html += `<div class="new-term-item" data-cwd="${escHtml(p.path)}">
          <div class="new-term-item-name">${escHtml(p.name || p.project_id)}</div>
          <div class="new-term-item-path">${escHtml(p.path)}</div>
        </div>`;
      }
    }
  } catch(e) { console.warn('fetch projects:', e); }
  list.innerHTML = html;
  list.querySelectorAll('.new-term-item').forEach(el => {
    el.addEventListener('click', () => pickNewTerm(el.dataset.cwd || null));
  });
  overlay.style.display = '';
}

function closeNewTermDialog() {
  document.getElementById('new-term-overlay').style.display = 'none';
}

function pickNewTerm(cwd) {
  closeNewTermDialog();
  newWindow(cwd);
}

// ── Mobile input bar ─────────────────────────────────────────────────────────
var _cmdHistory = JSON.parse(localStorage.getItem('mira-cmd-history') || '[]');
var _historyIdx = -1;

var _SPECIAL_KEYS = {
  'Tab':    '\t',
  'Ctrl+C': '\x03',
  'Ctrl+D': '\x04',
  'Ctrl+Z': '\x1a',
  'Ctrl+L': '\x0c',
  'Ctrl+A': '\x01',
  'Ctrl+E': '\x05',
  'Ctrl+U': '\x15',
  'Esc':    '\x1b',
  'Up':     '\x1b[A',
  'Down':   '\x1b[B',
};

// ── ANSI-to-HTML converter (supports 16/256/truecolor + bold) ────────────────
var _ANSI16 = [
  '#1a1a2e','#e06c75','#98c379','#e5c07b','#61afef','#c678dd','#56b6c2','#abb2bf',
  '#5c6370','#f47067','#8ae234','#fce94f','#729fcf','#d4a0e8','#34e2e2','#ffffff'
];
function _ansi256(n) {
  if (n < 16) return _ANSI16[n];
  if (n >= 232) { var g = (n - 232) * 10 + 8; return 'rgb('+g+','+g+','+g+')'; }
  n -= 16;
  return 'rgb('+(Math.floor(n/36)*51)+','+(Math.floor((n%36)/6)*51)+','+((n%6)*51)+')';
}
function _stripAnsi(text) { return text.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, ''); }
function _ansiToHtml(raw) {
  // 1. Strip non-SGR escape sequences FIRST (so they don't interfere with blank-line detection)
  var text = raw.replace(/\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g, ''); // OSC
  text = text.replace(/\x1b\[[\?]?[0-9;]*[A-LN-Za-ln-z]/g, '');    // CSI non-SGR
  // 2. Strip trailing whitespace per line (tmux pads to full terminal width)
  text = text.split('\n').map(function(l) { return l.replace(/[\s\x1b]+$/, ''); }).join('\n');
  // 3. Collapse consecutive blank lines and trim trailing blanks
  text = text.replace(/\n{3,}/g, '\n\n').replace(/\n+$/, '\n');
  // Split on SGR sequences
  var parts = text.split(/\x1b\[([0-9;]*)m/);
  var html = '', fg = '', bg = '', bold = false;
  for (var i = 0; i < parts.length; i++) {
    if (i % 2 === 0) {
      var t = escHtml(parts[i]);
      if (!t) continue;
      if (fg || bg || bold) {
        var s = '';
        if (fg) s += 'color:' + fg + ';';
        if (bg) s += 'background:' + bg + ';';
        if (bold) s += 'font-weight:700;';
        html += '<span style="' + s + '">' + t + '</span>';
      } else {
        html += t;
      }
    } else {
      var codes = parts[i] ? parts[i].split(';').map(Number) : [0];
      for (var j = 0; j < codes.length; j++) {
        var c = codes[j];
        if (c === 0) { fg = ''; bg = ''; bold = false; }
        else if (c === 1) bold = true;
        else if (c === 22) bold = false;
        else if (c >= 30 && c <= 37) fg = _ANSI16[c - 30 + (bold ? 8 : 0)];
        else if (c >= 40 && c <= 47) bg = _ANSI16[c - 40];
        else if (c >= 90 && c <= 97) fg = _ANSI16[c - 82];
        else if (c >= 100 && c <= 107) bg = _ANSI16[c - 92];
        else if (c === 39) fg = '';
        else if (c === 49) bg = '';
        else if (c === 38 && codes[j+1] === 5) { fg = _ansi256(codes[j+2]||0); j += 2; }
        else if (c === 48 && codes[j+1] === 5) { bg = _ansi256(codes[j+2]||0); j += 2; }
        else if (c === 38 && codes[j+1] === 2) { fg = 'rgb('+(codes[j+2]||0)+','+(codes[j+3]||0)+','+(codes[j+4]||0)+')'; j += 4; }
        else if (c === 48 && codes[j+1] === 2) { bg = 'rgb('+(codes[j+2]||0)+','+(codes[j+3]||0)+','+(codes[j+4]||0)+')'; j += 4; }
      }
    }
  }
  return html;
}

// ── Mobile WebSocket terminal stream ────────────────────────────────────────
var _termWs = null;

function _connectTermWs(target) {
  _disconnectTermWs();
  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var url = proto + '//' + location.host + '/ws/terminal/' + encodeURIComponent(target)
            + '/stream?token=' + encodeURIComponent(_adminToken);
  _termWs = new WebSocket(url);
  var output = document.getElementById('mobile-term-output');

  _termWs.onmessage = function(e) {
    if (!output) return;
    var wasAtBottom = (output.scrollHeight - output.scrollTop - output.clientHeight) < 40;
    output.innerHTML = _ansiToHtml(e.data);
    if (wasAtBottom) output.scrollTop = output.scrollHeight;
    // Update state dot from WebSocket data
    if (_currentTarget) _onStateChange(_currentTarget, _detectState(_stripAnsi(e.data)));
  };

  _termWs.onclose = function() {
    _termWs = null;
    // Auto-reconnect if still viewing this pane
    if (_currentTarget === target && _isMobile &&
        document.getElementById('dev-page').classList.contains('detail-open')) {
      setTimeout(function() { _connectTermWs(target); }, 2000);
    }
  };
  _termWs.onerror = function() {};
}

function _disconnectTermWs() {
  if (_termWs) {
    _termWs.onclose = null;  // prevent auto-reconnect
    try { _termWs.close(); } catch(e) {}
    _termWs = null;
  }
}

async function _sendToTerminal(keys) {
  if (!_currentTarget) return;
  try {
    await fetch('/api/terminals/' + encodeURIComponent(_currentTarget) + '/send', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify({ keys: keys })
    });
  } catch(e) { console.warn('send error:', e); }
}

var _inScrollMode = false;
var _scrollBadgeTimer = null;

async function _scrollTerminal(direction, lines) {
  if (!_currentTarget) return;
  try {
    await fetch('/api/terminals/' + encodeURIComponent(_currentTarget) + '/scroll', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify({ direction: direction, lines: lines || 5 })
    });
    // Show scroll badge briefly
    _inScrollMode = (direction !== 'exit');
    var badge = document.getElementById('term-scroll-badge');
    if (badge) {
      badge.classList.toggle('visible', _inScrollMode);
      clearTimeout(_scrollBadgeTimer);
      if (_inScrollMode) {
        _scrollBadgeTimer = setTimeout(function() {
          badge.classList.remove('visible');
        }, 1500);
      }
    }
  } catch(e) { console.warn('scroll error:', e); }
}

function _initMobileInput() {
  if (!_isMobile) return;
  var input = document.getElementById('mobile-cmd-input');
  var sendBtn = document.getElementById('mobile-send-btn');
  if (!input || !sendBtn) return;

  // ── Touch-to-scroll on terminal overlay ──
  var overlay = document.getElementById('term-touch-overlay');
  if (overlay) {
    var _touchStartY = 0;
    var _touchAccum = 0;
    var _scrollThreshold = 30; // px per scroll step

    overlay.addEventListener('touchstart', function(e) {
      _touchStartY = e.touches[0].clientY;
      _touchAccum = 0;
    }, { passive: true });

    overlay.addEventListener('touchmove', function(e) {
      var dy = _touchStartY - e.touches[0].clientY; // positive = scroll up (see older)
      _touchStartY = e.touches[0].clientY;
      _touchAccum += dy;
      if (Math.abs(_touchAccum) >= _scrollThreshold) {
        var steps = Math.floor(Math.abs(_touchAccum) / _scrollThreshold);
        _touchAccum = _touchAccum % _scrollThreshold;
        _scrollTerminal(dy > 0 ? 'up' : 'down', steps * 3);
      }
    }, { passive: true });

    overlay.addEventListener('touchend', function() {
      _touchAccum = 0;
    }, { passive: true });

    // Double-tap to exit scroll mode
    var _lastTap = 0;
    overlay.addEventListener('touchend', function(e) {
      var now = Date.now();
      if (now - _lastTap < 300 && _inScrollMode) {
        _scrollTerminal('exit');
      }
      _lastTap = now;
    });
  }

  // Auto-resize textarea height
  function autoResize() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  }
  input.addEventListener('input', autoResize);

  // Send on Enter (without Shift); Shift+Enter = newline
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      _sendMobileCmd();
    }
    // Up/Down arrow for history when input is empty
    if (e.key === 'ArrowUp' && !input.value.trim()) {
      e.preventDefault();
      _navigateHistory(-1);
    }
    if (e.key === 'ArrowDown' && !input.value.trim()) {
      e.preventDefault();
      _navigateHistory(1);
    }
  });

  // Send button
  sendBtn.addEventListener('click', function() {
    _sendMobileCmd();
  });

  // Special key buttons + scroll buttons
  document.getElementById('mobile-keys-row').addEventListener('click', function(e) {
    var btn = e.target.closest('.mobile-key-btn');
    if (!btn) return;
    // Scroll buttons — on mobile, scroll the text output natively
    var scrollDir = btn.dataset.scroll;
    if (scrollDir) {
      if (_isMobile) {
        var output = document.getElementById('mobile-term-output');
        if (output) {
          var h = output.clientHeight * 0.8;
          output.scrollBy({ top: scrollDir.includes('up') ? -h : h, behavior: 'smooth' });
        }
      } else {
        _scrollTerminal(scrollDir);
      }
      return;
    }
    // Regular special keys
    var keyName = btn.dataset.key;
    var seq = _SPECIAL_KEYS[keyName];
    if (seq) {
      if (!_isMobile && _inScrollMode) _scrollTerminal('exit');
      _sendToTerminal(seq);
    }
  });
}

async function _sendMobileCmd() {
  var input = document.getElementById('mobile-cmd-input');
  var text = input.value;
  if (!text) return;
  // Exit scroll mode first
  if (_inScrollMode) await _scrollTerminal('exit');
  // Add to history (dedup, max 100)
  _cmdHistory = _cmdHistory.filter(function(c) { return c !== text; });
  _cmdHistory.push(text);
  if (_cmdHistory.length > 100) _cmdHistory = _cmdHistory.slice(-100);
  localStorage.setItem('mira-cmd-history', JSON.stringify(_cmdHistory));
  _historyIdx = -1;
  // Send: each line as separate command
  await _sendToTerminal(text + '\n');
  input.value = '';
  input.style.height = 'auto';
  input.focus();
}

function _navigateHistory(dir) {
  var input = document.getElementById('mobile-cmd-input');
  if (!_cmdHistory.length) return;
  if (_historyIdx === -1) {
    if (dir === -1) _historyIdx = _cmdHistory.length - 1;
    else return;
  } else {
    _historyIdx += dir;
    if (_historyIdx < 0) _historyIdx = 0;
    if (_historyIdx >= _cmdHistory.length) { _historyIdx = -1; input.value = ''; return; }
  }
  input.value = _cmdHistory[_historyIdx];
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await _initAuth();
  if (!_isAdmin) { openLoginModal(init); return; }
  // Event delegation: bind click once on the container, survives innerHTML rebuilds
  document.getElementById('term-pane-list').addEventListener('click', function(e) {
    var row = e.target.closest('.term-pane-row');
    if (!row) return;
    // Ignore clicks on kill button (has its own handler)
    if (e.target.closest('.term-pane-kill')) return;
    selectPane(row.dataset.target, row.dataset.cmd);
  });
  // Init mobile input bar
  _initMobileInput();
  // ttyd iframe is loaded lazily on first pane click (avoids basic-auth dialog on page load)
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
        '<meta name="viewport" content="width=device-width, initial-scale=1, interactive-widget=resizes-visual">\n'
        "<title>Dev · Mira</title>\n"
        "<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>\n"
        '<link rel="stylesheet" href="/static/fonts/fonts.css">\n'
        "<style>\n"
        + theme_vars_css()
        + topbar_css()
        + page_css
        + "</style>\n</head>\n<body>\n\n"
        + topbar_html(title="Dev", hide_dev=True) + "\n\n"
        + """\
<div class="dev-page" id="dev-page">
  <!-- Sidebar: pane list -->
  <div class="term-sidebar">
    <div class="term-sidebar-header">
      <span>所有终端</span>
      <button class="term-new-btn" onclick="openNewTermDialog()" title="新建终端窗口">+</button>
    </div>
    <div id="term-pane-list">
      <div class="term-empty-sidebar">正在加载…</div>
    </div>
  </div>

  <!-- Main: ttyd iframe -->
  <div class="term-main">
    <!-- Mobile-only header (back to list + project name) -->
    <div class="term-detail-header" id="term-detail-header">
      <button class="term-detail-back" onclick="showPlaceholder()" title="返回列表">← 列表</button>
      <span class="term-detail-title" id="term-detail-title">终端</span>
    </div>
    <div id="term-placeholder" class="term-placeholder">
      <div>从左侧选择一个项目，或者：</div>
      <button class="term-placeholder-btn" onclick="openNewTermDialog()">+ 新建终端窗口</button>
    </div>
    <div class="term-iframe-wrap" id="term-iframe-wrap">
      <div class="term-touch-overlay" id="term-touch-overlay"></div>
      <div class="term-scroll-badge" id="term-scroll-badge">滚动模式</div>
      <iframe id="ttyd-frame" allow="clipboard-read; clipboard-write"></iframe>
    </div>
    <!-- Mobile: independent terminal output via WebSocket (ANSI-rendered) -->
    <div class="mobile-term-output" id="mobile-term-output"></div>
    <!-- Mobile input bar: bypasses iframe input issues via tmux send-keys -->
    <div class="mobile-input-bar" id="mobile-input-bar">
      <div class="mobile-keys-row" id="mobile-keys-row">
        <button class="mobile-key-btn" data-key="Tab">Tab</button>
        <button class="mobile-key-btn" data-key="Ctrl+C">⌃C</button>
        <button class="mobile-key-btn" data-key="Ctrl+D">⌃D</button>
        <button class="mobile-key-btn" data-key="Ctrl+Z">⌃Z</button>
        <button class="mobile-key-btn" data-key="Esc">Esc</button>
        <button class="mobile-key-btn" data-key="Up">↑</button>
        <button class="mobile-key-btn" data-key="Down">↓</button>
        <button class="mobile-key-btn" data-key="Ctrl+L">清屏</button>
        <button class="mobile-key-btn" data-key="Ctrl+A">行首</button>
        <button class="mobile-key-btn" data-key="Ctrl+E">行尾</button>
        <button class="mobile-key-btn" data-key="Ctrl+U">删行</button>
        <button class="mobile-key-btn" data-scroll="page-up">PgUp</button>
        <button class="mobile-key-btn" data-scroll="page-down">PgDn</button>
      </div>
      <div class="mobile-input-row">
        <textarea class="mobile-cmd-input" id="mobile-cmd-input" rows="1"
          placeholder="输入命令…" autocomplete="off" autocorrect="off"
          autocapitalize="off" spellcheck="false" enterkeyhint="send"></textarea>
        <button class="mobile-send-btn" id="mobile-send-btn" title="发送">↵</button>
      </div>
    </div>
  </div>
</div>

<!-- New terminal dialog (hidden by default) -->
<div class="new-term-overlay" id="new-term-overlay" style="display:none" onclick="if(event.target===this)closeNewTermDialog()">
  <div class="new-term-dialog">
    <div class="new-term-dialog-header">
      <span>新建终端窗口</span>
      <button class="new-term-dialog-close" onclick="closeNewTermDialog()">&times;</button>
    </div>
    <div class="new-term-dialog-list" id="new-term-list"></div>
  </div>
</div>

"""
        + settings_overlay_html() + "\n\n"
        + "<script>\n"
        + topbar_js() + "\n"
        + page_js
        + "</script>\n</body>\n</html>\n"
    )
