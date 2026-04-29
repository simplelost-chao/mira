"""Dev mode page — sidebar pane list + ttyd iframe."""


def render_dev_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js

    page_css = r"""
  /* ── Page reset (lock body to viewport, terminal handles its own scroll) ── */
  :root { --app-h: 100vh; }
  html, body { margin: 0; padding: 0; height: 100vh; overflow: hidden; }

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
  #term-pane-list { flex: 1; overflow-y: auto; }
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
  .term-pane-pencil {
    opacity: 0; font-size: 14px; color: var(--sub); cursor: pointer;
    padding: 2px 6px; transition: opacity .12s, color .12s, background .12s;
    border-radius: 3px; line-height: 1; flex-shrink: 0;
  }
  .term-pane-row:hover .term-pane-pencil { opacity: 1; }
  .term-pane-pencil:hover { color: var(--accent); background: rgba(var(--accent-rgb,99,179,237), 0.1); }
  .term-pane-name-input { flex: 1; min-width: 0; background: var(--bg); border: 1px solid var(--accent); border-radius: 3px; color: var(--text); font-family: inherit; font-size: 12px; font-weight: 600; padding: 1px 4px; outline: none; }
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
  #ttyd-frame {
    flex: 1; border: none; display: none; background: #0d1117;
  }
  #ttyd-frame.visible { display: block; }

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

  /* ── Mobile ── */
  @media (max-width: 900px) {
    .term-detail-header {
      display: flex; align-items: center; gap: 10px;
      height: 36px; padding: 0 12px; flex-shrink: 0;
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
    .term-main { display: none; flex: 1; }
    .dev-page.detail-open .term-sidebar { display: none; }
    .dev-page.detail-open .term-main { display: flex; }
  }
"""

    page_js = r"""
// ── Visual viewport tracking (mobile keyboard adaptation) ─────────────────────
(function() {
  function u() {
    var h = window.visualViewport ? window.visualViewport.height : window.innerHeight;
    document.documentElement.style.setProperty('--app-h', h + 'px');
  }
  u();
  if (window.visualViewport) window.visualViewport.addEventListener('resize', u);
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
  const rows = document.querySelectorAll('.term-pane-row');
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
  _bgPollTimer = setTimeout(_bgPoll, 10000);
}

// ── Pane list (grouped by project) ────────────────────────────────────────────
let _firstLoad = true;
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
              <span class="term-pane-pencil" title="重命名" onclick="event.stopPropagation(); startRename(this);">✎</span>
              <span class="term-pane-kill" title="关闭终端" onclick="event.stopPropagation(); killPane(this);">×</span>
            </div>
            <div class="term-pane-sub">${escHtml(p.command || '')}</div>
          </div>
        </div>`;
      }
      html += '</div>';
    }
    list.innerHTML = html;

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

// ── Inline rename ────────────────────────────────────────────────────────────
async function startRename(pencilEl) {
  const row = pencilEl.closest('.term-pane-row');
  const projectId = row.dataset.projectId;
  if (!projectId) return;
  const nameEl = row.querySelector('.term-pane-name');
  const textEl = nameEl.querySelector('.term-pane-name-text');
  const original = textEl.textContent;

  const input = document.createElement('input');
  input.className = 'term-pane-name-input';
  input.value = original;
  input.maxLength = 64;

  nameEl.innerHTML = '';
  nameEl.appendChild(input);
  input.focus();
  input.select();

  let done = false;
  async function commit() {
    if (done) return; done = true;
    const newName = input.value.trim();
    if (!newName || newName === original) {
      await loadPanes();
      return;
    }
    try {
      const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/name`, {
        method: 'POST',
        headers: _authHeaders({'Content-Type': 'application/json'}),
        body: JSON.stringify({ name: newName }),
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status} ${detail}`);
      }
    } catch(e) {
      alert('重命名失败: ' + e.message);
    }
    await loadPanes();
  }
  function cancel() {
    if (done) return; done = true;
    loadPanes();
  }

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); commit(); }
    else if (e.key === 'Escape') { e.preventDefault(); cancel(); }
  });
  input.addEventListener('blur', commit);
}

// ── Pane selection ────────────────────────────────────────────────────────────
async function selectPane(target, cmd) {
  _currentTarget = target;
  const rows = document.querySelectorAll('.term-pane-row');
  rows.forEach(r => r.classList.toggle('active', r.dataset.target === target));
  document.getElementById('dev-page').classList.add('detail-open');

  // Update mobile detail header title with project_name from the row
  const activeRow = document.querySelector(`.term-pane-row[data-target="${CSS.escape(target)}"]`);
  const titleEl = document.getElementById('term-detail-title');
  if (activeRow && titleEl) {
    const txt = activeRow.querySelector('.term-pane-name-text');
    titleEl.textContent = txt ? txt.textContent : target;
  }

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
  const frame = document.getElementById('ttyd-frame');
  if (!frame.src) {
    frame.src = '/terminal/';   // lazy-load on first show
    // Suppress beforeunload dialog from ttyd iframe
    frame.addEventListener('load', () => {
      try {
        // Suppress beforeunload dialog from ttyd iframe
        frame.contentWindow.addEventListener('beforeunload', e => {
          e.stopImmediatePropagation();
        }, true);
        // Cmd+C clipboard bridge: read tmux paste buffer → system clipboard
        // (navigator.clipboard is unavailable on HTTP, so we use execCommand)
        frame.contentWindow.document.addEventListener('keydown', e => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'c' && !e.shiftKey) {
            _copyTmuxBuffer();
          }
        }, true);
      } catch(e) {}
    });
  }
  document.getElementById('term-placeholder').style.display = 'none';
  frame.classList.add('visible');
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

// ── New terminal dialog ───────────────────────────────────────────────────────
async function openNewTermDialog() {
  const overlay = document.getElementById('new-term-overlay');
  const list = document.getElementById('new-term-list');
  // Static home option
  let html = `<div class="new-term-item" data-cwd="">
    <div class="new-term-item-name">~ 主目录</div>
    <div class="new-term-item-path">在用户 home 目录打开</div>
  </div>`;
  // Fetch projects
  try {
    const res = await fetch('/api/projects', { headers: _authHeaders() });
    if (res.ok) {
      const projects = await res.json();
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

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await _initAuth();
  if (!_isAdmin) { openLoginModal(init); return; }
  // Event delegation: bind click once on the container, survives innerHTML rebuilds
  document.getElementById('term-pane-list').addEventListener('click', function(e) {
    var row = e.target.closest('.term-pane-row');
    if (!row) return;
    // Ignore clicks on pencil/kill/input elements (they have their own handlers)
    if (e.target.closest('.term-pane-pencil, .term-pane-kill, .term-pane-name-input')) return;
    selectPane(row.dataset.target, row.dataset.cmd);
  });
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
      <div style="font-size:28px;opacity:.3">⬛</div>
      <div>从左侧选择一个项目，或者：</div>
      <button class="term-placeholder-btn" onclick="openNewTermDialog()">+ 新建终端窗口</button>
    </div>
    <iframe id="ttyd-frame" allow="clipboard-read; clipboard-write"></iframe>
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
