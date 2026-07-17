// ── Mobile detection ──────────────────────────────────────────────────────────
var _isMobile = window.matchMedia('(max-width: 900px)').matches;

// ── Visual viewport tracking (mobile keyboard adaptation) ─────────────────────
(function() {
  var _debounceTimer = null;
  var _lastH = 0;
  var _appliedH = 0;   // 上次真正应用到 --app-h 的高度(判断键盘是弹出还是收起)
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
        var grew = h > _appliedH;
        _appliedH = h;
        document.documentElement.style.setProperty('--app-h', h + 'px');
        window.scrollTo(0, 0);
        // Keep terminal output scrolled to bottom when keyboard changes
        var output = document.getElementById('mobile-term-output');
        if (output) output.scrollTop = output.scrollHeight;
        // iOS 软键盘只触发 visualViewport.resize,不触发 window.resize,所以 _ptyFitResize
        // (绑在 window.resize 上)收不到键盘收起事件 → xterm 行数停在被键盘压扁时的旧值,
        // --app-h 虽恢复了容器高度但终端不复原。这里补一次 fit,把行数重算回全高。
        // 只在高度变大(键盘收起/恢复)时补:若弹出/iOS 建议栏抖动也触发,
        // 打字期间会反复 resize+全量重绘,输入内容被重绘吞掉(用户报的 bug)。
        if (grew && typeof _ptyFitResize === 'function') _ptyFitResize();
      }, 100);
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
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// 子账号开的进程标识:优先头像,无头像回退到名字首字(圆形 badge)
function subBadge(p) {
  if (!p.sub) return '';
  var nm = (p.sub_name || '').trim();
  var title = escHtml('子账号开的进程' + (nm ? ': ' + nm : ''));
  if (p.sub_avatar) {
    return `<img class="term-sub-badge term-sub-av" src="${escHtml(p.sub_avatar)}" title="${title}" alt="">`;
  }
  return `<span class="term-sub-badge" title="${title}">${escHtml(nm ? nm.charAt(0) : '子')}</span>`;
}

// ── State ──────────────────────────────────────────────────────────────────────
let _currentTarget = null;
let _currentIsRemote = false;
const _groupCollapsed = {};
const _paneToolMap = {};  // target -> tool type
var _focusProjects = JSON.parse(localStorage.getItem('mira-focus-projects') || '[]');  // project_id -> bool
const _paneHostMap = {};     // target -> host alias (远程 pane 映射)
const _filterProject = new URLSearchParams(location.search).get('project') || null;

// ── Dev 侧栏:合并文件夹 + 自定义命名(纯展示,后端 vibe.yaml)────────────────
var _devGroups = [];     // [{id,name,projects:[pid,...]}]
var _devNames = {};      // pid -> 自定义显示名
var _devOrder = [];      // 顶层项排序 [key,...](项目=pid,文件夹='folder:'+id)
var _pidToFolder = {};   // pid -> folder 对象
var _lastGroupPids = []; // 本次渲染出现的顶层项目 [{pid,name}],供"合并到…"选择器用
var _topLevelKeys = [];  // 本次渲染的顶层项 key 顺序,供拖拽排序计算
async function loadDevGroups() {
  try {
    const res = await fetch('/api/dev/groups', { headers: _authHeaders() });
    if (!res.ok) return;
    const d = await res.json();
    _devGroups = d.groups || [];
    _devNames = d.names || {};
    _devOrder = d.order || [];
    _pidToFolder = {};
    for (const f of _devGroups) for (const pid of (f.projects || [])) _pidToFolder[pid] = f;
  } catch(e) { /* non-fatal */ }
}
function _projName(pid, fallback) { return _devNames[pid] || fallback; }

// ── State detection / polling removed — dots are static green ────────────────

// ── Pane row renderer ─────────────────────────────────────────────────────────
function _renderPaneRow(p, st) {
  var _pid = p.project_id || '';
  var _isFocused = _focusProjects.indexOf(_pid) >= 0;
  var _badgeCls = p.tool === 'codex' ? 'codex' : p.tool === 'claude' ? 'claude' : 'unknown';
  var _badgeText = p.tool === 'codex' ? 'X' : p.tool === 'claude' ? 'C' : '';
  var _badge = _badgeCls === 'unknown'
    ? '<div class="term-pane-badge unknown" onclick="event.stopPropagation();toggleFocus(\'' + escHtml(_pid) + '\')"></div>'
    : '<div class="term-pane-badge ' + _badgeCls + (_isFocused ? ' glow' : '') + '" onclick="event.stopPropagation();toggleFocus(\'' + escHtml(_pid) + '\')" title="' + (_isFocused ? '取消专注' : '设为专注') + '">' + _badgeText + '</div>';
  return `<div class="term-pane-row${_currentTarget === p.target ? ' active' : ''}${_isFocused ? ' focused' : ''}"
       data-target="${escHtml(p.target)}"
       data-cmd="${escHtml(p.command || '')}"
       data-project-id="${escHtml(_pid)}"
       data-host="${escHtml(p._host || '')}"
       data-tool="${escHtml(p.tool || '')}">
    ${_badge}
    <div class="term-pane-info">
      <div class="term-pane-name">
        <span class="term-pane-name-text">${escHtml((p.label || p.target).replace(/^.*\//, ''))}</span>
        ${subBadge(p)}
        ${p._host ? `<span class="term-host-badge${p._host_online === false ? ' offline' : ''}">${escHtml(p._host)}</span>` : ''}
        <span class="term-pane-kill" title="关闭终端" onclick="event.stopPropagation(); killPane(this);">×</span>
      </div>
    </div>
  </div>`;
}

// ── Pane list ─────────────────────────────────────────────────────────────────
let _firstLoad = true;
var _lastPanesHash = '';
async function loadPanes(forceRebuild) {
  if (!_isAdmin) { openLoginModal(init); return; }
  if (_drag && !forceRebuild) return;   // 拖拽中(含刚按下)不重建列表,避免抓手元素被换掉
  // On mobile detail view: skip entirely to protect iframe focus/IME
  var inDetail = document.getElementById('dev-page').classList.contains('detail-open');
  if (_isMobile && inDetail && !_firstLoad && !forceRebuild) return;
  try {
    const res = await fetch('/api/dev/panes', { headers: _authHeaders() });
    if (res.status === 401) { openLoginModal(init); return; }
    if (!res.ok) return;
    const panes = await res.json();
    // Cache tool type for each pane
    for (const p of panes) { if (p.tool) _paneToolMap[p.target] = p.tool; }
    // 更新远程 pane 映射
    for (const p of panes) {
      if (p._host) _paneHostMap[p.target] = p._host;
    }
    const list = document.getElementById('term-pane-list');
    if (!panes.length) {
      list.innerHTML = `<div class="term-empty-sidebar">暂无活跃终端<br><br><code>mira term &lt;project&gt;</code><br>启动新会话</div>`;
      return;
    }

    var _flatMode = !!localStorage.getItem('mira-dev-flat-list');
    let html = '';

    const groups = new Map();
    if (!_flatMode || _filterProject) {
      for (const p of panes) {
        const pid = p.project_id || '_ungrouped';
        if (!groups.has(pid)) groups.set(pid, { name: p.project_name || p.project_id || '未分组', panes: [] });
        groups.get(pid).panes.push(p);
      }
    }

    if (_flatMode) {
      // Flat list: no grouping
      for (const p of panes) {
        const st = 'idle';
        html += _renderPaneRow(p, st);
      }
    } else {
      // Group panes by project_id
      // On first load with ?project=xxx, collapse all other groups
      if (_firstLoad && _filterProject) {
        for (const [pid] of groups) {
          _groupCollapsed[pid] = (pid !== _filterProject);
        }
      }
      _firstLoad = false;

      // Sort: focused groups first
      var _sortedGroups = Array.from(groups.entries());
      if (_focusProjects.length) {
        _sortedGroups.sort(function(a, b) {
          var af = _focusProjects.indexOf(a[0]) >= 0 ? 0 : 1;
          var bf = _focusProjects.indexOf(b[0]) >= 0 ? 0 : 1;
          return af - bf;
        });
      }

      _lastGroupPids = [];
      // 收集顶层项:文件夹(含≥1活跃成员)+ 未分组项目
      const _topItems = [];
      const _seenFolders = new Set();
      for (const [pid, grp] of _sortedGroups) {
        _lastGroupPids.push({ pid: pid, name: _projName(pid, grp.name) });
        const folder = _pidToFolder[pid];
        if (folder) {
          if (_seenFolders.has(folder.id)) continue;
          _seenFolders.add(folder.id);
          const fhtml = _renderFolder(folder, groups);
          if (fhtml) _topItems.push({ key: 'folder:' + folder.id, type: 'folder', html: fhtml });
        } else {
          // 只有 1 个终端的项目 → 直接显示成一行(不分组、不展开)
          const phtml = grp.panes.length === 1 ? _renderSingleProject(pid, grp, false) : _renderProjectGroup(pid, grp, false);
          _topItems.push({ key: pid, type: 'project', html: phtml });
        }
      }
      // 应用自定义排序(未在 order 里的排末尾,保持稳定)
      if (_devOrder.length) {
        _topItems.sort(function(a, b) {
          var ai = _devOrder.indexOf(a.key); if (ai < 0) ai = 1e9;
          var bi = _devOrder.indexOf(b.key); if (bi < 0) bi = 1e9;
          return ai - bi;
        });
      }
      _topLevelKeys = _topItems.map(function(it) { return it.key; });
      for (const it of _topItems) {
        html += `<div class="term-toplevel" data-key="${escHtml(it.key)}" data-type="${it.type}">${it.html}</div>`;
      }
    }
    // Skip DOM rebuild if user is in detail view (mobile terminal active)
    // to avoid interrupting IME/voice input in the iframe
    var inDetail = document.getElementById('dev-page').classList.contains('detail-open');
    if (inDetail && !forceRebuild) {
      // In detail view, update tool badge in place(pane 行 + 单行项目,避免跳过重建时漏更新)
      for (const p of panes) {
        if (!p.tool) continue;
        var row = document.querySelector('.term-pane-row[data-target="' + CSS.escape(p.target) + '"], .term-single[data-target="' + CSS.escape(p.target) + '"]');
        if (!row) continue;
        row.dataset.tool = p.tool;
        var badge = row.querySelector('.term-pane-badge');
        if (badge && badge.classList.contains('unknown')) {
          var glow = badge.classList.contains('glow') ? ' glow' : '';
          badge.className = 'term-pane-badge ' + p.tool + glow;
          badge.textContent = p.tool === 'codex' ? 'X' : 'C';
        }
      }
    } else {
      // Skip full DOM rebuild if pane list hasn't changed
      var panesHash = JSON.stringify(panes);
      if (panesHash === _lastPanesHash && !forceRebuild) {
        // nothing changed, skip innerHTML
      } else {
        _lastPanesHash = panesHash;
        list.innerHTML = html;
      }
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

function toggleGroup(key) {
  if (_suppressToggle) return;   // 刚拖完那一下 click 不触发折叠
  if (_editMode) {               // 编辑模式:点头部=重命名(展开折叠交给箭头)
    if (key.indexOf('folder:') === 0) _renameFolder(key.slice(7));
    else _renameProject(key);
    return;
  }
  _doToggle(key);
}
function _doToggle(key) {
  _groupCollapsed[key] = !_groupCollapsed[key];
  const collapsed = _groupCollapsed[key];
  if (key.indexOf('folder:') === 0) {
    const fid = key.slice(7);
    const hdr = document.querySelector(`.term-folder-header[data-folder="${CSS.escape(fid)}"]`);
    const body = hdr ? hdr.parentElement.querySelector('.term-folder-body') : null;
    if (hdr) hdr.querySelector('.term-group-arrow').classList.toggle('collapsed', collapsed);
    if (body) body.classList.toggle('collapsed', collapsed);
    return;
  }
  const header = document.querySelector(`.term-group-header[data-group="${CSS.escape(key)}"]`);
  const body = document.querySelector(`.term-group-body[data-group-body="${CSS.escape(key)}"]`);
  if (header) header.querySelector('.term-group-arrow').classList.toggle('collapsed', collapsed);
  if (body) body.classList.toggle('collapsed', collapsed);
}

// ── 项目组 / 文件夹渲染 ────────────────────────────────────────────────────────
function _renderProjectGroup(pid, grp, nested) {
  const collapsed = !!_groupCollapsed[pid];
  const name = _projName(pid, grp.name);
  const focused = _focusProjects.indexOf(pid) >= 0;
  const grip = nested ? '' : `<span class="term-drag-handle" onpointerdown="_gripDown(event,'${escHtml(pid)}','project')" onclick="event.stopPropagation()" title="拖拽:排序 / 拖到其它项目上=合并">⠿</span>`;
  let h = `<div class="term-group-header${focused ? ' focused' : ''}${nested ? ' nested' : ''}"
      data-group="${escHtml(pid)}" data-drop-key="${escHtml(pid)}" data-drop-type="project"
      onclick="toggleGroup('${escHtml(pid)}')">
      ${grip}
      <span class="term-group-arrow${collapsed ? ' collapsed' : ''}" onclick="event.stopPropagation();_doToggle('${escHtml(pid)}')">▾</span>
      <span class="term-group-name" data-group="${escHtml(pid)}">${escHtml(name)}</span>
      <span class="term-group-count">${grp.panes.length}</span>
      <span class="term-group-menu" onclick="event.stopPropagation();_openGroupMenu(event,'${escHtml(pid)}')" title="更多">⋯</span>
    </div>
    <div class="term-group-body${collapsed ? ' collapsed' : ''}" data-group-body="${escHtml(pid)}">`;
  for (const p of grp.panes) h += _renderPaneRow(p, 'idle');
  h += '</div>';
  return h;
}

// 单终端项目:压成一行(项目名 + 工具徽标),点击=打开终端,仍可拖拽/重命名/合并
function _renderSingleProject(pid, grp, nested) {
  const p = grp.panes[0];
  const name = _projName(pid, grp.name);
  const focused = _focusProjects.indexOf(pid) >= 0;
  const isCur = _currentTarget === p.target;
  const badgeCls = p.tool === 'codex' ? 'codex' : p.tool === 'claude' ? 'claude' : 'unknown';
  const badgeText = p.tool === 'codex' ? 'X' : p.tool === 'claude' ? 'C' : '';
  const badge = badgeCls === 'unknown'
    ? `<div class="term-pane-badge unknown" onclick="event.stopPropagation();toggleFocus('${escHtml(pid)}')"></div>`
    : `<div class="term-pane-badge ${badgeCls}${focused ? ' glow' : ''}" onclick="event.stopPropagation();toggleFocus('${escHtml(pid)}')" title="${focused ? '取消专注' : '设为专注'}">${badgeText}</div>`;
  const grip = nested ? '' : `<span class="term-drag-handle" onpointerdown="_gripDown(event,'${escHtml(pid)}','project')" onclick="event.stopPropagation()" title="拖拽:排序 / 拖到其它项目上=合并">⠿</span>`;
  return `<div class="term-group-header term-single${focused ? ' focused' : ''}${nested ? ' nested' : ''}${isCur ? ' active' : ''}"
      data-group="${escHtml(pid)}" data-drop-key="${escHtml(pid)}" data-drop-type="project"
      data-target="${escHtml(p.target)}" data-cmd="${escHtml(p.command || '')}"
      onclick="_singleSelect(this)">
      ${grip}
      ${badge}
      <span class="term-group-name">${escHtml(name)}</span>
      ${subBadge(p)}
      ${p._host ? `<span class="term-host-badge${p._host_online === false ? ' offline' : ''}">${escHtml(p._host)}</span>` : ''}
      <span class="term-pane-kill" title="关闭终端" onclick="event.stopPropagation();_killSingle(this)">×</span>
      <span class="term-group-menu" onclick="event.stopPropagation();_openGroupMenu(event,'${escHtml(pid)}')" title="更多">⋯</span>
    </div>`;
}
function _singleSelect(rowEl) {
  if (_suppressToggle) return;   // 刚拖完那次 click 不当成点击打开
  if (_editMode) { _renameProject(rowEl.dataset.group); return; }  // 编辑模式:点名字=重命名
  selectPane(rowEl.dataset.target, rowEl.dataset.cmd || '');
}
async function _killSingle(killEl) {
  const row = killEl.closest('[data-target]');
  const target = row && row.dataset.target;
  if (!target) return;
  const name = (row.querySelector('.term-group-name') || {}).textContent || target;
  if (!confirm(`确认关闭终端 "${name}" ?\\n\\n该 tmux pane 会被 kill，shell 进程退出，无法恢复。`)) return;
  try {
    const res = await fetch(`/api/dev/panes/${encodeURIComponent(target)}`, { method: 'DELETE', headers: _authHeaders() });
    if (res.ok) loadPanes(true);
  } catch(e) {}
}

function _renderFolder(folder, groups) {
  let inner = '', n = 0;
  for (const mpid of (folder.projects || [])) {
    const g = groups.get(mpid);
    if (!g) continue;            // 该成员当前没有活跃 pane → 不显示
    n++;
    inner += g.panes.length === 1 ? _renderSingleProject(mpid, g, true) : _renderProjectGroup(mpid, g, true);
  }
  if (!n) return '';
  const fkey = 'folder:' + folder.id;
  const collapsed = !!_groupCollapsed[fkey];
  return `<div class="term-folder">
    <div class="term-folder-header" data-folder="${escHtml(folder.id)}" data-drop-key="${escHtml(fkey)}" data-drop-type="folder"
        onclick="toggleGroup('${escHtml(fkey)}')">
      <span class="term-drag-handle" onpointerdown="_gripDown(event,'${escHtml(fkey)}','folder')" onclick="event.stopPropagation()" title="拖拽排序">⠿</span>
      <span class="term-group-arrow${collapsed ? ' collapsed' : ''}" onclick="event.stopPropagation();_doToggle('${escHtml(fkey)}')">▾</span>
      <span class="term-folder-icon">📁</span>
      <span class="term-folder-name">${escHtml(folder.name)}</span>
      <span class="term-group-count">${n}</span>
      <span class="term-group-menu" onclick="event.stopPropagation();_openFolderMenu(event,'${escHtml(folder.id)}')" title="更多">⋯</span>
    </div>
    <div class="term-folder-body${collapsed ? ' collapsed' : ''}">${inner}</div>
  </div>`;
}

// ── 拖拽:桌面只走 mouse 事件,触屏只走 pointer 事件 ──────────────────────────────
// 不混用:Safari 桌面在 pointerdown 后常立刻 pointercancel,会把刚挂的拖拽连 mouse
// 监听一起拆掉。所以桌面(有鼠标)纯 mouse,触屏纯 pointer,各跑各的、互不干扰。
var _drag = null;
var _suppressToggle = false;
var _editMode = false;
function toggleEditMode() {
  _editMode = !_editMode;
  var list = document.getElementById('term-pane-list');
  if (list) list.classList.toggle('edit-mode', _editMode);
  var btn = document.getElementById('dev-edit-btn');
  if (btn) { btn.classList.toggle('active', _editMode); btn.title = _editMode ? '完成编辑' : '编辑:拖拽排序 / 合并 / 重命名 / 删除'; }
}
// 触屏:抓手 onpointerdown 触发(忽略鼠标,鼠标走下面的 mousedown 委托)
function _gripDown(e, key, type) {
  if (!_editMode) return;
  if (e.pointerType === 'mouse') return;
  e.stopPropagation(); e.preventDefault();
  _startDrag(e, key, type, 'pointer');
}
function _startDrag(e, key, type, mode) {
  if (_drag) return;
  _drag = { key: key, type: type, x0: e.clientX, y0: e.clientY, active: false, ghost: null, target: null, capEl: null, pid: e.pointerId, mode: mode };
  if (mode === 'pointer') {
    try { e.currentTarget.setPointerCapture(e.pointerId); _drag.capEl = e.currentTarget; } catch(_) {}
    window.addEventListener('pointermove', _dragMove, { passive: false });
    window.addEventListener('pointerup', _dragUp, { once: true });
    window.addEventListener('pointercancel', _dragUp, { once: true });
  } else {
    window.addEventListener('mousemove', _dragMove);
    window.addEventListener('mouseup', _dragUp, { once: true });
  }
}
function _dragMove(e) {
  if (!_drag) return;
  if (!_drag.active) {
    if (Math.abs(e.clientX - _drag.x0) + Math.abs(e.clientY - _drag.y0) < 6) return;
    _drag.active = true;
    document.body.classList.add('dev-dragging');
    _drag.ghost = document.createElement('div');
    _drag.ghost.className = 'dev-drag-ghost';
    _drag.ghost.textContent = _dragLabel(_drag.key, _drag.type);
    document.body.appendChild(_drag.ghost);
  }
  e.preventDefault();
  _drag.ghost.style.left = (e.clientX + 12) + 'px';
  _drag.ghost.style.top = (e.clientY + 12) + 'px';
  _computeDrop(e.clientX, e.clientY);
}
function _dragLabel(key, type) {
  if (type === 'folder') { const f = _devGroups.find(x => 'folder:' + x.id === key); return '📁 ' + (f ? f.name : ''); }
  const g = _lastGroupPids.find(x => x.pid === key); return g ? g.name : key;
}
function _computeDrop(x, y) {
  const items = [...document.querySelectorAll('#term-pane-list > .term-toplevel')];
  if (!items.length) { _clearDropUI(); _drag.target = null; return; }
  // 读写分离:先只读 rect 算出落点(不碰 DOM),最后统一写 UI —— 避免逐项 读→写→读 触发多次 reflow
  let target = null, overEl = null, lineItem = null, lineBefore = false;
  for (const it of items) {
    const r = it.getBoundingClientRect();
    if (y < r.top || y > r.bottom) continue;
    const hdr = it.querySelector('[data-drop-key]');
    const hr = hdr.getBoundingClientRect();
    // 合并:源是项目、悬在另一项头部中段、不是自己
    if (y >= hr.top && y <= hr.bottom && _drag.type === 'project' && hdr.dataset.dropKey !== _drag.key) {
      const hrel = (y - hr.top) / hr.height;
      if (hrel > 0.28 && hrel < 0.72) {
        target = { mode: 'merge', key: hdr.dataset.dropKey, dropType: hdr.dataset.dropType };
        overEl = hdr; break;
      }
    }
    // 否则:排序,插到该项前/后
    const before = (y - r.top) / r.height < 0.5;
    target = { mode: 'reorder', beforeKey: before ? it.dataset.key : _nextKey(items, it) };
    lineItem = it; lineBefore = before; break;
  }
  if (!target) {
    const last = items[items.length - 1];
    if (y > last.getBoundingClientRect().bottom) { target = { mode: 'reorder', beforeKey: null }; lineItem = last; lineBefore = false; }
  }
  _clearDropUI();
  if (overEl) overEl.classList.add('drag-over');
  else if (lineItem) _showDropLine(lineItem, lineBefore);
  _drag.target = target;
}
function _nextKey(items, it) {
  const i = items.indexOf(it);
  return (i >= 0 && i + 1 < items.length) ? items[i + 1].dataset.key : null;
}
function _showDropLine(item, before) {
  const listEl = document.getElementById('term-pane-list');
  let line = document.getElementById('dev-drop-line');
  if (!line) { line = document.createElement('div'); line.id = 'dev-drop-line'; line.className = 'dev-drop-line'; listEl.appendChild(line); }
  line.style.top = (before ? item.offsetTop : item.offsetTop + item.offsetHeight) + 'px';
  line.style.display = 'block';
}
function _clearDropUI() {
  document.querySelectorAll('.term-group-header.drag-over, .term-folder-header.drag-over').forEach(el => el.classList.remove('drag-over'));
  const line = document.getElementById('dev-drop-line'); if (line) line.style.display = 'none';
}
function _dragUp(e) {
  window.removeEventListener('pointermove', _dragMove);
  window.removeEventListener('pointerup', _dragUp);
  window.removeEventListener('pointercancel', _dragUp);
  window.removeEventListener('mousemove', _dragMove);
  window.removeEventListener('mouseup', _dragUp);
  document.body.classList.remove('dev-dragging');
  const st = _drag; _drag = null;
  if (st && st.capEl) { try { st.capEl.releasePointerCapture(st.pid); } catch(_) {} }
  if (st && st.ghost) st.ghost.remove();
  _clearDropUI();
  if (!st || !st.active) return;
  _suppressToggle = true; setTimeout(() => { _suppressToggle = false; }, 0);  // 抑制拖完那次 click 的折叠
  if (!st.target) return;
  if (st.target.mode === 'merge') {
    if (st.target.dropType === 'folder') {
      const f = _devGroups.find(x => 'folder:' + x.id === st.target.key);
      if (f && f.projects.length) _confirmMerge(st.key, f.projects[0], f.name);
    } else {
      _confirmMerge(st.key, st.target.key, null);
    }
  } else {
    let arr = _topLevelKeys.filter(k => k !== st.key);
    if (st.target.beforeKey == null) arr.push(st.key);
    else { const idx = arr.indexOf(st.target.beforeKey); if (idx < 0) arr.push(st.key); else arr.splice(idx, 0, st.key); }
    _saveOrder(arr);
  }
}
async function _saveOrder(arr) {
  try {
    const res = await fetch('/api/dev/order', { method: 'POST', headers: { 'Content-Type': 'application/json', ..._authHeaders() }, body: JSON.stringify({ order: arr }) });
    if (!res.ok) return;
    await loadDevGroups();
    loadPanes(true);
  } catch(e) {}
}
async function _confirmMerge(src, target, folderName) {
  const sName = _projName(src, src), tName = folderName || _projName(target, target);
  if (!confirm(`把 "${sName}" 合并到 "${tName}"？\n（只是 dev 侧栏分组，不影响项目本身）`)) return;
  await _devMutate('/api/dev/groups/merge', { source: src, target: target, name: folderName || _projName(target, target) });
}
async function _devMutate(url, body) {
  try {
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ..._authHeaders() }, body: JSON.stringify(body) });
    if (!res.ok) { const d = await res.json().catch(() => ({})); alert('操作失败: ' + (d.detail || res.status)); return; }
    await loadDevGroups();
    loadPanes(true);
  } catch(e) { alert('操作失败: ' + e.message); }
}

// ── ⋯ 菜单(重命名 / 合并 / 移出 / 解散)—— 桌面+手机通用 ──────────────────────
function _closeDevMenu() { const m = document.getElementById('dev-ctx-menu'); if (m) m.remove(); }
function _showDevMenu(e, items) {
  _closeDevMenu();
  const m = document.createElement('div');
  m.id = 'dev-ctx-menu';
  m.className = 'dev-ctx-menu';
  m.innerHTML = items.map((it, i) => `<button class="dev-ctx-item${it.danger ? ' danger' : ''}" data-i="${i}">${escHtml(it.label)}</button>`).join('');
  document.body.appendChild(m);
  const r = (e.currentTarget || e.target).getBoundingClientRect();
  m.style.top = (r.bottom + 4) + 'px';
  m.style.left = Math.min(r.left, window.innerWidth - 180) + 'px';
  m.querySelectorAll('.dev-ctx-item').forEach((btn, i) => btn.onclick = (ev) => { ev.stopPropagation(); _closeDevMenu(); items[i].fn(); });
  setTimeout(() => document.addEventListener('click', _closeDevMenu, { once: true }), 0);
}
function _openGroupMenu(e, pid) {
  const inFolder = !!_pidToFolder[pid];
  const items = [
    { label: '重命名', fn: () => _renameProject(pid) },
    { label: '合并到…', fn: () => _mergeIntoPicker(pid) },
  ];
  if (inFolder) items.push({ label: '移出分组', danger: true, fn: () => _devMutate('/api/dev/groups/unmerge', { project: pid }) });
  _showDevMenu(e, items);
}
function _openFolderMenu(e, fid) {
  _showDevMenu(e, [
    { label: '重命名分组', fn: () => _renameFolder(fid) },
    { label: '解散分组', danger: true, fn: () => _dissolveFolder(fid) },
  ]);
}
// 页内输入框(替代原生 prompt——Safari 会抑制重复弹窗,导致 prompt 被静默吞掉)
function _inlinePrompt(title, cur, placeholder, onOk) {
  const ov = document.createElement('div');
  ov.className = 'dev-rename-overlay';
  ov.innerHTML = `<div class="dev-rename-box">
    <div class="dev-rename-title"></div>
    <input class="dev-rename-input" type="text" placeholder="">
    <div class="dev-rename-actions">
      <button class="dev-rename-cancel">取消</button>
      <button class="dev-rename-ok">确定</button>
    </div>
  </div>`;
  ov.querySelector('.dev-rename-title').textContent = title;
  const inp = ov.querySelector('.dev-rename-input');
  inp.value = cur || ''; inp.placeholder = placeholder || '';
  document.body.appendChild(ov);
  setTimeout(() => { inp.focus(); inp.select(); }, 0);
  function close() { ov.remove(); }
  function ok() { const v = inp.value.trim(); close(); onOk(v); }
  ov.querySelector('.dev-rename-cancel').onclick = close;
  ov.querySelector('.dev-rename-ok').onclick = ok;
  ov.addEventListener('mousedown', e => { if (e.target === ov) close(); });
  inp.addEventListener('keydown', e => { if (e.key === 'Enter') ok(); else if (e.key === 'Escape') close(); });
}
function _renameProject(pid) {
  _inlinePrompt('项目显示名', _devNames[pid] || '', '留空恢复默认', function(v) {
    _devMutate('/api/dev/project-name', { project_id: pid, name: v });
  });
}
function _renameFolder(fid) {
  const f = _devGroups.find(x => x.id === fid); if (!f) return;
  _inlinePrompt('分组名', f.name, '', function(v) {
    if (v) _devMutate('/api/dev/groups/rename', { id: fid, name: v });
  });
}
function _mergeIntoPicker(src) {
  const others = _lastGroupPids.filter(g => g.pid !== src);
  if (!others.length) { alert('没有其它项目可合并'); return; }
  const lines = others.map((g, i) => `${i + 1}. ${g.name}`).join('\\n');
  const ans = prompt('合并到哪个项目？输入编号:\\n' + lines);
  if (ans === null) return;
  const idx = parseInt(ans.trim(), 10) - 1;
  if (isNaN(idx) || idx < 0 || idx >= others.length) return;
  _confirmMerge(src, others[idx].pid, null);
}
async function _dissolveFolder(fid) {
  const f = _devGroups.find(x => x.id === fid); if (!f) return;
  if (!confirm(`解散分组 "${f.name}"？`)) return;
  for (const pid of [...f.projects]) {
    try {
      await fetch('/api/dev/groups/unmerge', { method: 'POST', headers: { 'Content-Type': 'application/json', ..._authHeaders() }, body: JSON.stringify({ project: pid }) });
    } catch(e) {}
  }
  await loadDevGroups();
  loadPanes(true);
}

function toggleFocus(pid) {
  var idx = _focusProjects.indexOf(pid);
  if (idx >= 0) _focusProjects.splice(idx, 1);
  else _focusProjects.push(pid);
  localStorage.setItem('mira-focus-projects', JSON.stringify(_focusProjects));
  loadPanes(true);
}

// ── Kill pane ─────────────────────────────────────────────────────────────────
async function killPane(killEl) {
  const row = killEl.closest('.term-pane-row');
  if (!row) return;   // 单终端项目走 _killSingle;这里对齐 _killSingle 的判空,防误绑/结构变动时 TypeError
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
  if (_isMobile) _saveSnapshot();  // save current pane's terminal output before switching
  _currentTarget = target;
  _currentIsRemote = !!_paneHostMap[target];
  const rows = document.querySelectorAll('.term-pane-row, .term-single[data-target]');
  rows.forEach(r => r.classList.toggle('active', r.dataset.target === target));
  document.getElementById('dev-page').classList.add('detail-open');
  // Lock body scroll on mobile to prevent iOS rubber-banding
  if (_isMobile) {
    document.body.classList.add('detail-locked');
    // 详情态:额外显示「返回列表/切换终端」;统计、设置保持可见(手机上也要能进这两个功能)
    document.querySelectorAll('.topbar .topbar-detail-btn').forEach(function(b) { b.style.display = 'inline-flex'; });
  }
  // 历史入口:两端统一放 topbar 右上角(icon)。桌面只放历史(返回/切换是移动端专属,桌面列表常驻)
  var _histBtn = document.getElementById('topbar-hist-btn');
  if (_histBtn) _histBtn.style.display = 'inline-flex';

  // Update title with project name (from group header, not pane label)
  const activeRow = document.querySelector(`.term-pane-row[data-target="${CSS.escape(target)}"], .term-single[data-target="${CSS.escape(target)}"]`);
  const titleEl = document.getElementById('term-detail-title');
  if (activeRow) {
    var pid = activeRow.dataset.projectId || activeRow.dataset.group;   // term-single 用 data-group
    var groupEl = pid ? document.querySelector('.term-group-name[data-group="' + CSS.escape(pid) + '"]') ||
                        document.querySelector('[data-group="' + CSS.escape(pid) + '"] .term-group-name') : null;
    var name = groupEl ? groupEl.textContent
                       : (activeRow.querySelector('.term-pane-name-text')?.textContent
                          || activeRow.querySelector('.term-group-name')?.textContent || target);
    // Strip path prefix: "node/argus" → "argus"
    name = name.replace(/^.*\//, '');
    if (titleEl) titleEl.textContent = name;
    // logo 后显示当前项目名,统一走 topbar-project-name(自带 max-width+ellipsis,不撑破窄 topbar)。
    // 桌面接在「Dev」后带「· 」;移动详情态 Dev(page-title)已被 CSS 藏起省空间,故直接显示项目名、无前缀。
    // (曾经移动端把项目名塞进 page-title,但 body.detail-locked 又把 page-title 藏了 → 移动端不显示)
    var projName = document.getElementById('topbar-project-name');
    if (projName) projName.textContent = _isMobile ? name : ' · ' + name;
  }

  showTerminal();
  var paneRow = document.querySelector('.term-pane-row[data-target="' + CSS.escape(target) + '"]');
  var tool = _paneToolMap[target] || (paneRow ? paneRow.dataset.tool : '') || '';
  // Load tokens and usage in parallel, don't block each other
  _loadPaneTokens(target, tool);
  _updateTopbarUsage(tool);
  _startTokenRefresh(target, tool);
  // 记住当前终端,iOS 后台回收/重载页面后可自动恢复(见 init),避免掉回列表
  if (_isMobile) { try { localStorage.setItem('mira-dev-target', target); } catch(e) {} }
}

var _tokenRefreshTimer = null;
var _usageRefreshTimer = null;
function _startTokenRefresh(target, tool) {
  // per-session token(本地、便宜)每 30s 刷
  if (_tokenRefreshTimer) clearInterval(_tokenRefreshTimer);
  _tokenRefreshTimer = setInterval(async function() {
    if (_currentTarget !== target) { clearInterval(_tokenRefreshTimer); return; }
    var t = _paneToolMap[target] || tool;
    await _loadPaneTokens(target, t);
  }, 30000);

  // 账号级 usage 变化很慢、上游有限流,单独用 5 分钟的节奏刷(切 pane 时已即时刷过一次)
  if (_usageRefreshTimer) clearInterval(_usageRefreshTimer);
  _usageRefreshTimer = setInterval(function() {
    if (_currentTarget !== target) { clearInterval(_usageRefreshTimer); return; }
    _updateTopbarUsage(_paneToolMap[target] || tool);
  }, 300000);
}

function _setMobileTokens(html) {
  var bar = document.getElementById('mobile-token-bar');
  if (!bar) return;
  var dot = bar.querySelector('.ws-dot');
  var usage = bar.querySelector('.mob-usage');  // 保留 usage:它是账号全局的,不该被 token 刷新抹掉
  bar.innerHTML = '';
  if (dot) bar.appendChild(dot);
  if (html) bar.insertAdjacentHTML('beforeend', html);
  if (usage) bar.appendChild(usage);            // usage 放回(排在 tokens 之后)
}

var _tokensRenderedFor = null;  // 上次渲染 token 的 target
var _tokensLastHtml = '';       // 上次写入的桌面 html,内容没变就不重写 DOM
async function _loadPaneTokens(target, tool) {
  var desktop = document.getElementById('toolbar-tokens');
  // 只在切换 pane 时清空;同 pane 的周期刷新等数据回来原地替换,避免数字先消失再出现
  if (_tokensRenderedFor !== target) {
    _tokensRenderedFor = target;
    _tokensLastHtml = '';
    if (desktop) desktop.innerHTML = '';
    _setMobileTokens('');
  }
  if (!tool) return;
  try {
    var res = await fetch('/api/dev/pane-tokens?target=' + encodeURIComponent(target) + '&tool=' + encodeURIComponent(tool), { headers: _authHeaders() });
    if (!res.ok) return;
    var d = await res.json();
    if (_tokensRenderedFor !== target) return;  // 等待期间切了 pane,别覆盖新 pane 的显示
    var hasTool = d && d.tool;
    if (!hasTool && (!d || !d.estimated_cost_usd)) {
      // No token data — just show tool badge
      var badge = tool === 'codex'
        ? '<span class="tok-badge codex">Codex</span>'
        : '<span class="tok-badge claude">Claude</span>';
      if (badge !== _tokensLastHtml) {
        _tokensLastHtml = badge;
        if (desktop) desktop.innerHTML = badge;
        _setMobileTokens(badge);
      }
      return;
    }
    if (!hasTool) d.tool = tool;
    var fT = function(t) { if (!t) return '—'; if (t>=1e9) return (t/1e9).toFixed(1)+'B'; if (t>=1e6) return (t/1e6).toFixed(1)+'M'; if (t>=1e3) return (t/1e3).toFixed(0)+'k'; return String(t); };
    var fB = function(bytes) { if (bytes>=1e9) return (bytes/1e9).toFixed(1)+'GB'; if (bytes>=1e6) return (bytes/1e6).toFixed(0)+'MB'; if (bytes>=1e3) return (bytes/1e3).toFixed(0)+'KB'; return bytes+'B'; };
    var badge = d.tool === 'codex'
      ? '<span class="tok-badge codex">Codex</span>'
      : '<span class="tok-badge claude">Claude</span>';

    // Calculate actual upload/download bytes (tokens * ~5 bytes for JSON encoding)
    var BPT = 5; // bytes per token in HTTP body
    var totalCtx = (d.input_tokens || 0) + (d.cache_read_tokens || d.cached_input_tokens || 0) + (d.cache_creation_tokens || 0);
    var uploadBytes = totalCtx * BPT;
    var downloadBytes = (d.output_tokens || 0) * BPT;

    var html = badge;
    // 当前 context 占用(最后一次请求送入的总 token) / context window
    var ctxTok = d.context_tokens || 0;
    if (ctxTok > 0) {
      var ctxWin = parseInt(localStorage.getItem('mira-ctx-window') || '1000000', 10);
      var ctxPct = Math.min(100, Math.round(ctxTok / ctxWin * 100));
      var ctxCls = ctxPct >= 80 ? 'ctx-hi' : ctxPct >= 60 ? 'ctx-mid' : '';
      html += '<span class="tok-item tok-ctx ' + ctxCls + '" title="当前上下文 ' + fT(ctxTok) + ' / ' + fT(ctxWin) + ' · ' + ctxPct + '%（越满越该开新会话；context window 默认按 1M 算，可在 localStorage mira-ctx-window 改）">ctx ' + ctxPct + '%</span>';
    }
    // 上行/下行 tokens + 流量 只在桌面 topbar 内联显示;手机端太窄放不下,点开展开(dropdown)里看
    var deskExtra = '';
    deskExtra += '<span class="tok-item" title="上行 tokens"><span class="tok-icon tok-up">▲</span><span class="tok-val">' + fT(totalCtx) + '</span></span>';
    deskExtra += '<span class="tok-item" title="下行 tokens"><span class="tok-icon tok-down">▼</span><span class="tok-val">' + fT(d.output_tokens) + '</span></span>';
    deskExtra += '<span class="tok-item" title="上行流量 ' + fB(uploadBytes) + ' / 下行流量 ' + fB(downloadBytes) + '"><span style="color:var(--muted);font-size:10px">' + fB(uploadBytes) + '/' + fB(downloadBytes) + '</span></span>';

    var full = html + deskExtra;
    if (full !== _tokensLastHtml) {
      _tokensLastHtml = full;
      if (desktop) desktop.innerHTML = full;
      _setMobileTokens(html);
    }
  } catch(e) { /* non-fatal */ }
}

// ── Token dropdown: today's per-project breakdown ───────────────────────────
var _tokDropdownData = null;  // cached data
var _tokDropdownOpen = false;

(function() {
  function bind(el) {
    if (!el) return;
    el.addEventListener('click', function(e) {
      e.stopPropagation();
      if (_tokDropdownOpen) { _closeTokDropdown(); return; }
      _openTokDropdown();
    });
  }
  bind(document.getElementById('toolbar-tokens'));
  bind(document.getElementById('mobile-token-bar'));
  document.addEventListener('click', function() { _closeTokDropdown(); });
})();

function _closeTokDropdown() {
  _tokDropdownOpen = false;
  var dd = document.querySelector('.tok-dropdown');
  if (dd) dd.remove();
}

async function _openTokDropdown() {
  // Pick visible parent: desktop toolbar or mobile token bar
  var parent = document.getElementById('toolbar-tokens');
  if (!parent || parent.offsetParent === null) {
    parent = document.getElementById('mobile-token-bar');
  }
  if (!parent) return;
  _closeTokDropdown();
  _tokDropdownOpen = true;

  // Create placeholder
  var dd = document.createElement('div');
  dd.className = 'tok-dropdown';
  // Mobile: position left-aligned, full width
  var isMobile = parent.id === 'mobile-token-bar';
  if (isMobile) { dd.style.left = '0'; dd.style.right = '0'; dd.style.minWidth = 'auto'; }
  dd.innerHTML = '<div style="color:var(--sub);text-align:center;padding:8px">加载中…</div>';
  dd.addEventListener('click', function(e) { e.stopPropagation(); });
  parent.appendChild(dd);

  try {
    var res = await fetch('/api/stats?range=30d', { headers: _authHeaders() });
    if (!res.ok) { dd.innerHTML = '<div style="color:var(--sub)">加载失败</div>'; return; }
    var data = await res.json();
    _renderTokDropdown(dd, data);
  } catch(e) {
    dd.innerHTML = '<div style="color:var(--sub)">加载失败</div>';
  }
}

function _renderTokDropdown(dd, data) {
  if (!_tokDropdownOpen) return;
  var pd = data.project_days || {};
  var nameMap = {};
  (data.projects || []).forEach(function(p) { nameMap[p.project_id] = p.project_name || p.project_id; });

  // Find today's date (local timezone, not UTC)
  var _now = new Date();
  var today = _now.getFullYear() + '-' + String(_now.getMonth()+1).padStart(2,'0') + '-' + String(_now.getDate()).padStart(2,'0');

  var items = [];
  Object.keys(pd).forEach(function(pid) {
    var entry = pd[pid][today];
    if (!entry) return;
    var cost, inp, out, cw, cr;
    if (typeof entry === 'number') { cost = entry; inp = out = cw = cr = 0; }
    else { cost = entry.cost||0; inp = entry.input_tokens||0; out = entry.output_tokens||0; cw = entry.cache_creation_tokens||0; cr = entry.cache_read_tokens||0; }
    if (cost > 0) items.push({ name: nameMap[pid]||pid, cost: cost, inp: inp, out: out, cw: cw, cr: cr });
  });
  items.sort(function(a,b) { return b.cost - a.cost; });

  if (!items.length) {
    dd.innerHTML = '<div class="tok-dropdown-title"><span>今日项目开销</span><span>' + today + '</span></div>' +
      '<div style="color:var(--sub);text-align:center;padding:8px">暂无数据</div>';
    return;
  }

  var fT = function(t) { if (!t) return '—'; if (t>=1e9) return (t/1e9).toFixed(1)+'B'; if (t>=1e6) return (t/1e6).toFixed(1)+'M'; if (t>=1e3) return (t/1e3).toFixed(0)+'k'; return String(t); };
  var fC = function(v) { return v>=100?'$'+v.toFixed(0):v>=10?'$'+v.toFixed(1):'$'+v.toFixed(2); };
  var maxCost = items[0].cost;
  var TC = { inp:'#4e9eff', out:'#f0a050', cw:'#fbbf24', cr:'#5cd08a' };

  var rows = items.map(function(it) {
    var totTok = it.inp + it.out + it.cw + it.cr;
    var segs = [{v:it.inp,c:TC.inp},{v:it.out,c:TC.out},{v:it.cw,c:TC.cw},{v:it.cr,c:TC.cr}]
      .map(function(s){return '<div style="width:'+(s.v/(totTok||1)*100).toFixed(1)+'%;background:'+s.c+'"></div>';}).join('');
    var tip = '输入:'+fT(it.inp)+' 输出:'+fT(it.out)+' 缓存写:'+fT(it.cw)+' 缓存读:'+fT(it.cr);
    return '<div class="tok-dropdown-row">' +
      '<div class="tok-dropdown-name" title="'+escHtml(it.name)+'">'+escHtml(it.name)+'</div>' +
      '<div style="flex:1;min-width:0">' +
        '<div style="height:6px;background:var(--track-bg,rgba(255,255,255,.06));border-radius:3px;overflow:hidden"><div style="height:100%;width:'+(it.cost/maxCost*100).toFixed(1)+'%;background:var(--accent);border-radius:3px;opacity:.7"></div></div>' +
        (totTok ? '<div class="tok-dropdown-bar" style="margin-top:2px" title="'+tip+'">'+segs+'</div>' : '') +
      '</div>' +
      '<div class="tok-dropdown-cost">'+fC(it.cost)+'<div style="font-size:9px;color:var(--muted)">'+fT(totTok)+'</div></div></div>';
  }).join('');

  var total = items.reduce(function(s,it){return s+it.cost;},0);
  var totalTok = items.reduce(function(s,it){return s+it.inp+it.out+it.cw+it.cr;},0);
  // Estimate traffic: upload = (input + cache_read + cache_write) * 5 bytes, download = output * 5 bytes
  var totalUp = items.reduce(function(s,it){return s+it.inp+it.cw+it.cr;},0) * 5;
  var totalDown = items.reduce(function(s,it){return s+it.out;},0) * 5;
  var fB = function(b) { if(b>=1e9) return (b/1e9).toFixed(1)+'GB'; if(b>=1e6) return (b/1e6).toFixed(0)+'MB'; return (b/1e3).toFixed(0)+'KB'; };

  dd.innerHTML =
    '<div class="tok-dropdown-title"><span>今日项目开销</span><span>' + today + '</span></div>' +
    rows +
    '<div class="tok-dropdown-total">合计 ' + fC(total) + ' · ' + fT(totalTok) + ' tokens</div>' +
    '<div class="tok-dropdown-total" style="border-top:none;padding-top:0;margin-top:-4px;font-size:10px;color:var(--sub)">估算流量 <span style="color:#f59e0b">▲' + fB(totalUp) + '</span> <span style="color:#3b82f6">▼' + fB(totalDown) + '</span></div>' +
    '<div class="tok-dropdown-legend">' +
      '<span><span class="tok-dropdown-dot" style="background:#4e9eff"></span>输入</span>' +
      '<span><span class="tok-dropdown-dot" style="background:#f0a050"></span>输出</span>' +
      '<span><span class="tok-dropdown-dot" style="background:#fbbf24"></span>缓存写</span>' +
      '<span><span class="tok-dropdown-dot" style="background:#5cd08a"></span>缓存读</span>' +
    '</div>';
}

// ── Topbar usage: switch between Claude / Codex ──────────────────────────────
window._topbarUsageMode = null;  // null = not yet loaded into toolbar

function _fmtTokens(t) {
  if (!t) return '0';
  if (t >= 1e9) return (t / 1e9).toFixed(1) + 'B';
  if (t >= 1e6) return (t / 1e6).toFixed(1) + 'M';
  if (t >= 1e3) return (t / 1e3).toFixed(0) + 'k';
  return String(t);
}

function _mobileUsageText(d) {
  function _fmtReset(ts) {
    if (!ts) return '';
    var diff = ts * 1000 - Date.now();
    if (diff <= 0) return '';
    var d = Math.floor(diff / 86400000), h = Math.floor((diff % 86400000) / 3600000), m = Math.floor((diff % 3600000) / 60000);
    return d > 0 ? d + 'd' : h > 0 ? h + 'h' : m + 'm';
  }
  function _winHtml(win, label) {
    if (!win) return '';
    var pct = win.utilization != null ? Math.round(win.utilization * 100) : (win.used_percent || 0);
    var cls = pct >= 90 ? 'color:var(--red)' : pct >= 60 ? 'color:var(--orange)' : 'color:var(--green)';
    var reset = _fmtReset(win.resets_at || win.reset_at);
    var h = '<span style="' + cls + ';font-weight:700">' + pct + '%</span>';
    if (reset) h += ' <span style="font-size:9px;color:var(--muted)">' + reset + '</span>';
    return h;
  }
  var s = d.session, w = d.weekly;
  var parts = [];
  if (s) parts.push(_winHtml(s, '会话'));
  if (w) parts.push(_winHtml(w, '周'));
  if (!parts.length) return '';
  return '<span class="tok-item" style="gap:4px">' + parts.join('<span style="color:var(--border)">·</span>') + '</span>';
}

async function _updateTopbarUsage(tool) {
  var el = document.getElementById('toolbar-usage');
  var topbarEl = document.getElementById('topbar-usage');
  if (!el) return;
  window._topbarUsageMode = tool || 'claude';

  // Hide topbar usage, show in toolbar instead
  if (topbarEl) topbarEl.style.display = 'none';

  var apiUrl = window._topbarUsageMode === 'codex' ? '/api/codex-usage' : '/api/claude-usage';

  // Usage 是账号全局的、变化很慢。缓存上次成功值(按 tool 分键),
  // 这样拉取失败时保持显示旧值、不清空,加载时也先垫上旧值,避免"时有时无"。
  var cacheKey = 'mira-usage-' + window._topbarUsageMode;
  // usage 是账号全局的,不该因切项目/切 pane 而空白。
  // 切换工具,或当前显示为空(被 showPlaceholder 等逻辑清过)时,立刻用上次成功值垫上。
  if (el.dataset.tool !== window._topbarUsageMode || !el.innerHTML) {
    var cached = localStorage.getItem(cacheKey);
    if (cached) {
      el.innerHTML = cached;
      el.style.display = 'inline-flex';
    } else if (el.dataset.tool !== window._topbarUsageMode) {
      el.innerHTML = '';
      el.style.display = 'none';
    }
    el.dataset.tool = window._topbarUsageMode;
  }

  try {
    var res = await fetch(apiUrl, { headers: _authHeaders() });
    if (!res.ok) return;        // 保留上次显示的值,不清空
    var d = await res.json();
    if (d.error) return;        // 同上
    var usageHtml = _mobileUsageText(d);
    if (!usageHtml) return;     // 渲染为空(数据缺字段)时保留旧值,绝不用空覆盖
    // 值没变就别重写 innerHTML:重设 innerHTML 会拆建 DOM 导致闪现。原地比对,数字变了才更新。
    if (el.innerHTML !== usageHtml) el.innerHTML = usageHtml;
    el.style.display = 'inline-flex';
    localStorage.setItem(cacheKey, usageHtml);   // 记下上次成功值
    var _mob = document.getElementById('mobile-token-bar');
    if (_mob) {
      var _old = _mob.querySelector('.mob-usage');
      if (!_old) {
        _mob.insertAdjacentHTML('beforeend', '<span class="mob-usage">' + usageHtml + '</span>');
      } else if (_old.innerHTML !== usageHtml) {
        _old.innerHTML = usageHtml;   // 原地更新文本,不删除重建,避免闪现
      }
      _mob.classList.add('visible');
    }
  } catch(e) {}
}

function showTerminal() {
  document.getElementById('term-placeholder').style.display = 'none';
  var toolbar = document.getElementById('term-toolbar');
  if (toolbar) toolbar.classList.add('visible');
  var devPage = document.getElementById('dev-page');
  if (devPage) { devPage.classList.add('stream-mode'); devPage.classList.remove('sub-hybrid'); }
  document.getElementById('xterm-wrap').classList.add('visible');
  document.getElementById('mobile-token-bar').classList.add('visible');
  document.getElementById('mobile-input-bar').style.display = 'flex';
  if (_currentTarget) _connectPtyWs(_currentTarget);
  if (!_isMobile) _focusInputBox();
}

function showPlaceholder() {
  document.getElementById('dev-page').classList.remove('stream-mode');
  document.getElementById('dev-page').classList.remove('sub-hybrid');
  document.getElementById('mobile-term-output').classList.remove('visible');
  document.getElementById('xterm-wrap').classList.remove('visible');
  document.getElementById('mobile-token-bar').classList.remove('visible');
  document.getElementById('mobile-input-bar').style.display = '';
  var toolbar = document.getElementById('term-toolbar');
  if (toolbar) toolbar.classList.remove('visible');
  var switcher = document.getElementById('pane-switcher');
  if (switcher) switcher.classList.remove('open');
  _disconnectPtyWs();
  try { localStorage.removeItem('mira-dev-target'); } catch(e) {}  // 主动回列表 → 清掉恢复记录
  _currentIsRemote = false;
  if (_tokenRefreshTimer) { clearInterval(_tokenRefreshTimer); _tokenRefreshTimer = null; }
  if (_usageRefreshTimer) { clearInterval(_usageRefreshTimer); _usageRefreshTimer = null; }
  window._topbarUsageMode = 'claude';
  var _tbu = document.getElementById('topbar-usage');
  if (_tbu) _tbu.style.display = '';
  // 不清空 toolbar-usage:usage 是账号全局的,保留上次值(占位态下整条 toolbar 本就隐藏),
  // 切回有终端的项目时即时显示,不再"消失"。
  document.getElementById('term-placeholder').style.display = '';
  document.getElementById('dev-page').classList.remove('detail-open');
  document.body.classList.remove('detail-locked');
  // Restore topbar buttons and title
  document.querySelectorAll('.topbar .topbar-btn').forEach(function(b) { b.style.display = ''; });
  document.querySelectorAll('.topbar .topbar-detail-btn').forEach(function(b) { b.style.display = ''; });
  var pt = document.querySelector('.topbar-page-title');
  if (pt) pt.textContent = 'Dev';
  var pn = document.getElementById('topbar-project-name');
  if (pn) pn.textContent = '';   // 回列表 → 清掉 logo 后的项目名
}

// ── New window ────────────────────────────────────────────────────────────────
async function newWindow(cwd) {
  try {
    // Snapshot existing targets before creating
    var oldTargets = new Set(
      Array.from(document.querySelectorAll('.term-pane-row[data-target], .term-single[data-target]')).map(r => r.dataset.target)
    );
    await fetch('/api/terminal/new-window', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify({ cwd: cwd || null })
    });
    // Server triggers monitor poll before responding, so new pane should be
    // available immediately. Retry a few times with short delay as fallback.
    for (var _attempt = 0; _attempt < 4; _attempt++) {
      if (_attempt > 0) await new Promise(r => setTimeout(r, 300));
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
    await loadPanes(true);
  } catch(e) { console.warn('new-window:', e); }
}

// ── New terminal dialog ───────────────────────────────────────────────────────
var _newTermProjects = null;
var _newTermProjectsPromise = null;
var _newTermProjectsRetry = null;

function _fetchNewTermProjects() {
  // 不做长期缓存：每次都重新拉取，新建的项目才能及时出现在列表里
  if (_newTermProjectsPromise) return _newTermProjectsPromise;
  _newTermProjectsPromise = fetch('/api/dev/project-options', { headers: _authHeaders() })
    .then(function(res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    })
    .then(function(projects) {
      if (projects.length) {
        _newTermProjects = projects;
        clearTimeout(_newTermProjectsRetry);
        _newTermProjectsRetry = null;
        var overlay = document.getElementById('new-term-overlay');
        if (overlay && overlay.style.display !== 'none') {
          _renderNewTermProjects(projects, false);
        }
      } else if (!_newTermProjectsRetry) {
        // The server is rebuilding its project cache. Keep the dialog
        // responsive and retry without ever blocking the click handler.
        _newTermProjectsRetry = setTimeout(function() {
          _newTermProjectsRetry = null;
          _fetchNewTermProjects().catch(function() {});
        }, 1500);
      }
      return projects;
    })
    .finally(function() { _newTermProjectsPromise = null; });
  return _newTermProjectsPromise;
}

function _renderNewTermProjects(projects, loading) {
  const list = document.getElementById('new-term-list');
  let html = `<div class="new-term-item" data-cwd="">
    <div class="new-term-item-name">~ 主目录</div>
    <div class="new-term-item-path">在用户 home 目录打开</div>
  </div>`;
  if (loading) html += '<div class="new-term-loading">正在加载项目…</div>';
  for (const p of projects || []) {
    html += `<div class="new-term-item-sep"></div>`;
    html += `<div class="new-term-item" data-cwd="${escHtml(p.path)}">
      <div class="new-term-item-name">${escHtml(p.name || p.id)}</div>
      <div class="new-term-item-path">${escHtml(p.path)}</div>
    </div>`;
  }
  list.innerHTML = html;
  list.querySelectorAll('.new-term-item').forEach(el => {
    el.addEventListener('click', () => pickNewTerm(el.dataset.cwd || null));
  });
}

function openNewTermDialog() {
  const overlay = document.getElementById('new-term-overlay');
  // 先渲染已有列表（或加载态），后台刷新拿到新列表后会自动重绘
  _renderNewTermProjects(_newTermProjects || [], !_newTermProjects);
  overlay.style.display = '';
  _fetchNewTermProjects().catch(function(e) {
    console.warn('fetch projects:', e);
    var loading = document.querySelector('#new-term-list .new-term-loading');
    if (loading) loading.textContent = '项目加载失败，请重试';
  });
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
  'Enter':  '\n',
  'Tab':    '\t',
  'Ctrl+C': '\x03',
  'Ctrl+D': '\x04',
  'Ctrl+Z': '\x1a',
  'Ctrl+L': '\x0c',
  'Ctrl+A': '\x01',
  'Ctrl+E': '\x05',
  'Ctrl+U': '\x15',
  'Ctrl+O': '\x0f',
  'Esc':    '\x1b',
  'Up':     '\x1b[A',
  'Down':   '\x1b[B',
};

function _hasPaneTarget(target) {
  // 同时认分组里的 .term-pane-row 和单终端项目的 .term-single(顶层项);
  // 只认前者会让单终端项目在 WS 一断时被误判为"已消失"→ 踢回列表。
  return !!document.querySelector('.term-pane-row[data-target="' + CSS.escape(target) + '"], .term-single[data-target="' + CSS.escape(target) + '"]');
}

// ── xterm.js PTY 真终端(100% 复刻;快照拼接链路的替代) ─────────────────────
var _ptyWs = null, _ptyTerm = null, _ptyFit = null, _snapTimer = null;
var _fitCorrectTimer = null;   // _ptyFitResize 的 80ms 溢出补正 timer;连续 resize 时 clear 掉旧的
var _ptyRetryDelay = 2000;
var _termSwitchSeq = 0;   // 每次连接自增;淡入回调只认最新序号,防快速连切时旧回调误淡入

function _xtermTheme() {
  var cs = getComputedStyle(document.body);
  function v(name, fb) { var x = cs.getPropertyValue(name).trim(); return x || fb; }
  var theme = { background: v('--bg', '#0d1117'), foreground: v('--text', '#e6edf3'),
                cursor: v('--accent', '#58a6ff') };
  // 各主题在 CSS 里定义了 --ansi-0..15,但之前从没喂给 xterm → 终端一直用 xterm 内置默认
  // 调色板;浅色主题(珊瑚橙)上 ANSI 白(#e5e5e5)/亮白(#fff)贴着米白背景基本看不清。这里把
  // 主题调色板接进来。坑:--ansi-N 的值可能是 var(--red) 这类嵌套引用,getPropertyValue 读
  // 自定义属性只拿到未解析字面量,故用探针元素把 var() 落到真实 color 上再读回解析后的 rgb。
  var keys = ['black','red','green','yellow','blue','magenta','cyan','white',
              'brightBlack','brightRed','brightGreen','brightYellow','brightBlue','brightMagenta','brightCyan','brightWhite'];
  var probe = document.createElement('span');
  probe.style.cssText = 'position:absolute;visibility:hidden;pointer-events:none';
  document.body.appendChild(probe);
  for (var i = 0; i < 16; i++) {
    if (!cs.getPropertyValue('--ansi-' + i).trim()) continue;   // 该主题没定义这一格 → 留给 xterm 默认
    probe.style.color = 'var(--ansi-' + i + ')';
    var rgb = getComputedStyle(probe).color;
    if (rgb) theme[keys[i]] = rgb;
  }
  document.body.removeChild(probe);
  return theme;
}

function _xtermMinContrast() {
  // claude 等 TUI 假设深底,用写死的 truecolor/高位256 亮色前景;浅底主题(珊瑚橙)上这些字
  // 贴着米白背景看不清,而 truecolor 绕过 ANSI 调色板改不动(改 --ansi-* 无效)。
  // minimumContrastRatio 让 xterm 对全色域自动把"对比不足"的前景压到可读,够对比的色不动。
  // 仅浅底开启(按 --bg 亮度判断),深底返回 1(=不干预原配色)。
  var bg = getComputedStyle(document.body).getPropertyValue('--bg').trim();
  var probe = document.createElement('span');
  probe.style.cssText = 'position:absolute;visibility:hidden';
  probe.style.color = bg || '#000';
  document.body.appendChild(probe);
  var m = getComputedStyle(probe).color.match(/\d+/g);
  document.body.removeChild(probe);
  if (!m) return 1;
  var lum = (0.299 * +m[0] + 0.587 * +m[1] + 0.114 * +m[2]) / 255;
  return lum > 0.5 ? 7 : 1;
}

function _refreshXtermTheme() {
  // 换肤实时生效:xterm v5 的 options 是响应式 setter
  if (_ptyTerm) {
    _ptyTerm.options.theme = _xtermTheme();
    _ptyTerm.options.minimumContrastRatio = _xtermMinContrast();
    _ptyTerm.refresh(0, _ptyTerm.rows - 1);   // canvas 渲染器需手动重绘才刷新对比度缓存
  }
}

function _connectPtyWs(target) {
  _disconnectPtyWs();
  var wrap = document.getElementById('xterm-container');
  if (!wrap) return;
  // 切换项目/pane 时把终端淡出:随后的 reset + 多次 fit + 溢出补正会反复 resize/重绘,
  // 全藏在 opacity:0 后,稳定(init 后)再淡入 —— 用户看不到闪烁和瞬时滚动条。
  var switchSeq = ++_termSwitchSeq;
  var _revealTerm = function() { if (switchSeq === _termSwitchSeq) wrap.classList.remove('term-switching'); };
  wrap.classList.add('term-switching');
  setTimeout(_revealTerm, 1500);   // 兜底:init 迟迟不来也别把终端卡在空白
  // 幕后连续 fit 到尺寸收敛再淡入:切换初期容器高度还在变(token 栏/输入栏布局未稳),
  // 固定延时 fit 若落在淡入后会造成可见的校准跳动("闪两下")。改为在 opacity:0 下用 rAF
  // 反复 fit+溢出补正,直到 cols×rows 连续两帧不变(布局稳)才淡入 —— 布局几帧就稳,比死等快,
  // 且淡入时尺寸已定死,之后无 fit 跳动。守卫 switchSeq:被新切换取代就停。
  function _fitThenReveal() {
    var prev = '', stable = 0, tries = 0;
    (function step() {
      if (switchSeq !== _termSwitchSeq || !_ptyFit || !_ptyTerm) return;
      try { _ptyFit.fit(); } catch (_) {}
      var over = wrap.scrollWidth - wrap.clientWidth;   // fit 按含 padding 的宽算,会多 1-2 列
      if (over > 0) {
        var drop = Math.min(4, Math.ceil(over / (wrap.scrollWidth / _ptyTerm.cols)));
        if (_ptyTerm.cols - drop > 10) _ptyTerm.resize(_ptyTerm.cols - drop, _ptyTerm.rows);
      }
      var overY = wrap.scrollHeight - wrap.clientHeight;   // padding-top 同样骗高 fit,会多算行 → 末行溢出被输入栏盖
      if (overY > 0 && _ptyTerm.rows > 4) {
        var dropR = Math.min(3, Math.ceil(overY / (wrap.scrollHeight / _ptyTerm.rows)));
        _ptyTerm.resize(_ptyTerm.cols, _ptyTerm.rows - dropR);
      }
      var dim = _ptyTerm.cols + 'x' + _ptyTerm.rows;
      if (dim === prev) stable++; else { stable = 0; prev = dim; }
      if (stable >= 2 || ++tries >= 15) { _ptySendSize(); _revealTerm(); return; }  // 15 帧兜底
      requestAnimationFrame(step);
    })();
  }
  if (!_ptyTerm) {
    _ptyTerm = new Terminal({
      fontFamily: "ui-monospace, 'SF Mono', Menlo, monospace",
      fontSize: _isMobile ? 12 : 13,   // 手机小一号(用户点名),列数也随之多几列
      // tmux 客户端本身跑在备用屏,xterm 的 scrollback 永远积累不到内容(实测):
      // 滚动 = 滚轮/触摸事件翻译成转义序列透传给 tmux/claude,由它们原地重绘
      scrollback: 0,
      theme: _xtermTheme(),
      minimumContrastRatio: _xtermMinContrast()
    });
    _ptyTerm.open(wrap);
    // canvas 渲染器:字形直接画进单元格。iOS Safari 上 DOM 渲染器有亚像素字距缝
    // (测量宽 vs 实际字形宽偏差累积),canvas 无此问题且滚动渲染更快;失败回退 DOM
    try { _ptyTerm.loadAddon(new CanvasAddon.CanvasAddon()); } catch (_) {}
    // 输出通道(桌面敲键 + 手机合成滚轮的转义序列都走这里)
    _ptyTerm.onData(function(d) {
      if (_ptyWs && _ptyWs.readyState === WebSocket.OPEN)
        _ptyWs.send(new TextEncoder().encode(d));
    });
    // 两端统一 fit+resize:手机也把窗口重排成自己的宽度(约 50 列,claude TUI 原生
    // 自适应窄屏,右侧不再缺内容)。tmux 共享窗口尺寸跟随最后操作端 —— 手机打开时
    // 桌面同看同一窗口会变窄,桌面一操作又变回,内容归属不受影响(用户拍板的取舍)
    _ptyFit = new FitAddon.FitAddon();
    _ptyTerm.loadAddon(_ptyFit);
    window.addEventListener('resize', _ptyFitResize);
    // 桌面:输入框多行长高等布局变化会压矮终端容器,但只有 window.resize 会触发 fit →
    // 画布保持旧行数,末行溢出被裁在快捷键栏上方(用户报"快捷键上面有块高度挡住内容")。
    // 用 ResizeObserver 盯容器高度,变了就防抖补 fit。手机不挂:软键盘引发的容器抖动
    // 会触发全量重绘吞打字内容(d05f63d 踩过),手机侧靠 visibilitychange/focus 自愈已够。
    // 盯的是 flex 父 #xterm-wrap,不是 #xterm-container 自身:后者 overflow-x:auto,fit 每次
    // 多算 1-2 列会瞬时溢出→横滚动条出现,又缩其 contentRect 高→再触发 fit→80ms 补正去溢出
    // →滚动条消失→高又变→…形成 fit⇄滚动条自激振荡,底部一直闪(用户报的 bug)。父 inset:0
    // 绝对定位的子滚动条压不到父,父高只随 flex 重排(输入框长高)变,既断环又保留本意。
    if (!_isMobile && typeof ResizeObserver !== 'undefined') {
      var _wrapParent = wrap.parentNode;
      var _wrapFitTimer = 0, _wrapLastH = 0;
      new ResizeObserver(function(entries) {
        var h = entries[0].contentRect.height;
        if (h === _wrapLastH) return;   // 纯宽度变化走 window.resize,不重复 fit
        _wrapLastH = h;
        clearTimeout(_wrapFitTimer);
        _wrapFitTimer = setTimeout(_ptyFitResize, 100);
      }).observe(_wrapParent);
    }
    // A(自愈):多端共享一个 tmux 窗口(window-size=latest)时,手机切到后台期间另一
    // 宽端可能把窗口撑宽,推来的宽帧被本端窄 xterm 折成散帧,claude 空闲又不重绘。
    // 一回到前台就重发本端尺寸抢回 latest 并触发重绘 —— 覆盖"没手动滑一下也自己好"。
    // 仅手机、且 PTY 活着时做。桌面不需要(它是常态的 latest)。
    if (_isMobile) {
      var _ptyReassert = function() {
        if (_ptyTerm && _ptyWs && _ptyWs.readyState === WebSocket.OPEN) _ptyFitResize();
      };
      document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') _ptyReassert();
      });
      window.addEventListener('pageshow', function(e) { if (e.persisted) _ptyReassert(); });  // iOS bfcache 恢复
      window.addEventListener('focus', _ptyReassert);
    }
    if (_isMobile) {
      // 手机:不用 disableStdin(它会连滚轮转义都拦掉),改用 inputmode=none 抑制软键盘;
      // 竖向滑动合成 WheelEvent 交给 xterm 按已协商的模式(鼠标上报/备用屏滚动)翻译,
      // 与桌面滚轮完全同一条链路;松手后带动量衰减(终端按行滚,惯性补手感)
      var ta = wrap.querySelector('.xterm-helper-textarea');
      if (ta) { ta.setAttribute('inputmode', 'none'); ta.setAttribute('aria-hidden', 'true'); }
      var _tY = null, _tX = null, _tVel = 0, _tPrevT = 0, _tRAF = 0, _tAcc = 0;
      function _wheel(dy) {
        var el = wrap.querySelector('.xterm-screen') || wrap;
        el.dispatchEvent(new WheelEvent('wheel', { deltaY: dy, deltaMode: 0, bubbles: true, cancelable: true }));
      }
      // 关键性能点:每次 touchmove 直接派发会产生 60Hz 的滚动转义流,每个都触发
      // tmux 整屏重绘回传 → 洪水拥塞=延时感。改为累积增量、每帧合并派发一次。
      function _tFlush() {
        _tRAF = 0;
        if (_tAcc) { _wheel(_tAcc); _tAcc = 0; }
        if (_tY === null && Math.abs(_tVel) >= 1.5) {   // 手指已离开:惯性接力
          _tAcc = _tVel;
          _tVel *= 0.93;   // 每帧衰减 7%,≈0.5s 滑止
          _tRAF = requestAnimationFrame(_tFlush);
        }
      }
      wrap.addEventListener('touchstart', function(e) {
        if (_tRAF) { cancelAnimationFrame(_tRAF); _tRAF = 0; }   // 手指按下即停惯性
        _tVel = 0; _tAcc = 0; _tPrevT = e.timeStamp;
        _tY = e.touches[0].clientY; _tX = e.touches[0].clientX;
      }, { passive: true });
      wrap.addEventListener('touchmove', function(e) {
        if (_tY === null) return;
        var dy = _tY - e.touches[0].clientY;
        var dx = _tX - e.touches[0].clientX;
        _tY = e.touches[0].clientY; _tX = e.touches[0].clientX;
        if (Math.abs(dx) > Math.abs(dy)) { _tVel = 0; return; }   // 横向手势不惯性
        var dt = Math.max(1, e.timeStamp - _tPrevT);
        _tPrevT = e.timeStamp;
        _tVel = (dy / dt) * 16;   // 换算成每帧(16ms)速度,touchend 后接力
        _tAcc += dy * 1.5;
        if (!_tRAF) _tRAF = requestAnimationFrame(_tFlush);
      }, { passive: true });
      wrap.addEventListener('touchend', function() {
        _tY = null; _tX = null;
        if (Math.abs(_tVel) >= 1.5 && !_tRAF) _tRAF = requestAnimationFrame(_tFlush);
      }, { passive: true });
    }
  } else {
    _ptyTerm.reset();   // 换 pane 先清屏:上一个 pane 的残影一个字都不能留(防串)
  }
  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var ws = new WebSocket(proto + '//' + location.host + '/ws/terminal/'
           + encodeURIComponent(target) + '/pty?token=' + encodeURIComponent(_adminToken || _subToken));
  ws.binaryType = 'arraybuffer';
  _ptyWs = ws;
  ws.onopen = function() { _ptyRetryDelay = 2000; _setWsDot(true); };
  ws.onmessage = function(e) {
    if (_ptyWs !== ws || !_ptyTerm) return;
    if (typeof e.data === 'string') {
      var c = {};
      try { c = JSON.parse(e.data); } catch (_) { return; }
      if (c.type === 'init') {
        _ptyTerm.resize(c.cols, c.rows);
        _fitThenReveal();   // 幕后 fit 到尺寸收敛(布局稳)再淡入:既不空等,淡入后也无 fit 跳动
      }
      return;
    }
    _ptyTerm.write(new Uint8Array(e.data));
    if (!_snapTimer) _snapTimer = setTimeout(function() {
      _snapTimer = null;
      // 校验归属:2s 内可能已切 pane(单例终端已 reset 载入新内容),只在仍是本 target 时写快照,防串台
      if (_currentTarget === target) _paneSnapshots[target] = _xtermSnapshot();
    }, 2000);
  };
  ws.onclose = function() {
    if (_ptyWs !== ws) return;
    _setWsDot(false);
    if (_currentTarget !== target) return;
    // 子账号行是 loadSubProjects 渲染的 data-pid,不是 .term-pane-row/.term-single(data-target);
    // _hasPaneTarget 在子账号下恒为 false → 误判"pane 已消失"→ loadPanes 里的
    // "非 admin 弹 openLoginModal" 会把子账号踢到 owner 登录框。子账号一律走重连,不查 pane 存活。
    if (_isSub || _hasPaneTarget(target)) {
      setTimeout(function() { if (_ptyWs === ws) _connectPtyWs(target); }, _ptyRetryDelay);
      _ptyRetryDelay = Math.min(_ptyRetryDelay * 2, 30000);
    } else {
      showPlaceholder();   // pane 已不存在(窗口被关):回列表,不留冻结残影
      loadPanes();
    }
  };
}

function _ptySendSize() {
  if (_ptyWs && _ptyWs.readyState === WebSocket.OPEN && _ptyTerm)
    _ptyWs.send(JSON.stringify({ type: 'resize', cols: _ptyTerm.cols, rows: _ptyTerm.rows }));
}

function _ptyFitResize() {
  if (!_ptyFit || !_ptyTerm) return;
  try { _ptyFit.fit(); } catch (_) { return; }
  _ptySendSize();
  // fit 按 clientWidth/Height(含 padding)算行列,会多出 1-2 列 / 半~一行 → 右缘、底部溢出。
  // 画布尺寸下一帧才落地,同帧量不到 —— 延后量实际溢出像素,横竖各折算该减几列/行。
  clearTimeout(_fitCorrectTimer);   // 连续 resize(拖窗/键盘抖动)时,旧补正作废,只保留最后一次
  _fitCorrectTimer = setTimeout(function() {
    var wrap = document.getElementById('xterm-container');
    if (!wrap || !_ptyTerm) return;
    var cols = _ptyTerm.cols, rows = _ptyTerm.rows;
    var overX = wrap.scrollWidth - wrap.clientWidth;
    if (overX > 0) cols = Math.max(11, cols - Math.min(4, Math.ceil(overX / (wrap.scrollWidth / _ptyTerm.cols))));
    var overY = wrap.scrollHeight - wrap.clientHeight;   // padding-top 骗高 fit → 末行溢出被输入栏盖
    if (overY > 0) rows = Math.max(4, rows - Math.min(3, Math.ceil(overY / (wrap.scrollHeight / _ptyTerm.rows))));
    if (cols !== _ptyTerm.cols || rows !== _ptyTerm.rows) {
      _ptyTerm.resize(cols, rows);
      _ptySendSize();
    }
  }, 80);
}

function _xtermSnapshot() {
  // 供 pane 切换器预览:取 xterm 缓冲最后 20 个非空行
  if (!_ptyTerm) return '';
  var buf = _ptyTerm.buffer.active, out = [];
  for (var i = 0; i < buf.length; i++) {
    var line = buf.getLine(i);
    if (line) { var s = line.translateToString(true); if (s.trim()) out.push(s); }
  }
  return out.slice(-20).join('\n');
}

function _disconnectPtyWs() {
  if (_snapTimer) { clearTimeout(_snapTimer); _snapTimer = null; }   // 排队的快照定时器随断连一并取消
  if (_ptyWs) {
    var w = _ptyWs; _ptyWs = null;
    try { w.onclose = null; w.close(); } catch (_) {}
  }
}

function _setWsDot(connected) {
  var dot = document.getElementById('ws-dot');
  if (dot) {
    dot.className = 'ws-dot ' + (connected ? 'ok' : 'err');
    dot.title = connected ? '已连接' : '已断开 · 点击重连';
  }
  _setDesktopWsDot(connected);
}

function _setDesktopWsDot(connected) {
  var dot = document.getElementById('desktop-ws-dot');
  if (!dot) return;
  dot.className = 'desktop-ws-dot ' + (connected ? 'ok' : 'err');
  dot.title = connected ? '终端已连接' : '终端连接中';
}
function _sendOk() {
  _sendToTerminal('y\n');
  _showToast('已确认', 1500);
}

// 智能 ↵:画面输入行上有幽灵建议(暗色文字)时,自动 Tab 采纳再回车发出;
// 否则发裸回车(选菜单)。实测规则:裸回车对幽灵建议无效,必须 Tab 先采纳。
function _smartEnter() {
  // 曾想检测灰色幽灵补全、有则自动 Tab 采纳再发送,但依赖的旧快照链路已退役、长期失效。
  // 简化为普通回车 —— 要采纳 claude 的灰色建议,请按快捷键栏里的 Tab。
  _sendToTerminal('\n');
}
function _clearInput() {
  _sendToTerminal('\x15');  // Ctrl+U: clear terminal input line
}
function _sendNum(sel) {
  var v = sel.value;
  if (!v) return;
  _sendToTerminal(v);  // type digit into terminal without Enter
  sel.value = '';
}
function _onWsDotClick() {
  if (_ptyWs && _ptyWs.readyState === WebSocket.OPEN) return;
  if (_currentTarget) {
    _setWsDot(true);
    _connectPtyWs(_currentTarget);
  }
}

async function _sendToTerminal(keys, promptText) {
  // 失败必须可见:静默吞掉会让用户以为"按键坏了"(iOS 假死页/断网时按半天没反应)
  if (!_currentTarget) { _showToast('⚠ 未连接终端,刷新页面重试', 2500); return false; }
  try {
    var _body = { keys: keys };
    if (promptText) _body.prompt = promptText;   // 子账号:供后端精确归属这条 prompt(不靠时间)
    var res = await fetch('/api/terminals/' + encodeURIComponent(_currentTarget) + '/send', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify(_body)
    });
    if (!res.ok) _showToast('⚠ 按键发送失败 (' + res.status + ')', 2500);
    return res.ok;
  } catch(e) {
    console.warn('send error:', e);
    _showToast('⚠ 按键发送失败(网络),刷新页面重试', 2500);
    return false;
  }
}

var _mobileInputInited = false;
function _initMobileInput() {
  // 桌面也要绑定:owner 的"输入框模式"和子账号在桌面都用这套输入框,回车发送/发送按钮/
  // 特殊键都在下面绑,之前 `if(!_isMobile)return` 把桌面挡在门外 → 桌面回车发不出去。
  if (_mobileInputInited) return;   // 幂等:init/initSub 都会调,累加 addEventListener 会导致回车重复发送
  var input = document.getElementById('mobile-cmd-input');
  var sendBtn = document.getElementById('mobile-send-btn');
  if (!input || !sendBtn) return;
  _mobileInputInited = true;

  // Auto-resize textarea height
  function autoResize() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  }
  input.addEventListener('input', autoResize);

  // Mobile keyboard: scroll output to bottom and ensure input stays visible
  if (_isMobile) {
    input.addEventListener('focus', function() {
      setTimeout(function() {
        var output = document.getElementById('mobile-term-output');
        if (output) output.scrollTop = output.scrollHeight;
        // Force input into view on iOS
        input.scrollIntoView({ block: 'end', behavior: 'smooth' });
      }, 300);
    });
  }

  // Send on Enter (without Shift); Shift+Enter = newline
  input.addEventListener('keydown', function(e) {
    // !e.isComposing:中文输入法组词时按回车是"确认候选词",不能当发送(否则会误发/发重复)
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) {
      e.preventDefault();
      _sendMobileCmd();
    }
    // 空输入框时 ↑/↓ 直通终端(导航 claude 的菜单/选项);历史回溯改用 Alt+↑/↓。
    // 输入框有内容时不拦截,让方向键正常移动光标。
    if (e.key === 'ArrowUp' && !input.value.trim()) {
      e.preventDefault();
      if (e.altKey) _navigateHistory(-1); else _sendToTerminal('\x1b[A');
    }
    if (e.key === 'ArrowDown' && !input.value.trim()) {
      e.preventDefault();
      if (e.altKey) _navigateHistory(1); else _sendToTerminal('\x1b[B');
    }
  });

  // Send button
  sendBtn.addEventListener('click', function() {
    _sendMobileCmd();
  });

  // Special key buttons
  var _lastCtrlC = 0;   // ⌃C 两段式退出的时间窗
  document.getElementById('mobile-keys-row').addEventListener('click', async function(e) {
    var btn = e.target.closest('.mobile-key-btn');
    if (!btn) return;
    var keyName = btn.dataset.key;
    var seq = _SPECIAL_KEYS[keyName];
    if (!seq && keyName && keyName.length === 1) {
      // Single char keys (digits etc): send char + Enter
      _sendToTerminal(keyName + '\n');
      return;
    }
    if (seq) {
      if (keyName === 'Ctrl+C') {
        // ⌃C = 退出会话,两段式:
        // 第一击发原子对 \x03\x03(空闲 claude 优雅退出;忙碌=打断);
        // 5 秒内第二击走 respawn 强杀 —— ^C 退出受 claude 状态摆布(忙碌只打断,
        // 大上下文时连"再按一次退出"都不可靠),强杀才保证必退,shell 原地重生
        var now = Date.now();
        if (now - _lastCtrlC < 5000) {
          _lastCtrlC = 0;
          _showToast('强制退出会话中…', 1500);
          fetch('/api/terminals/' + encodeURIComponent(_currentTarget) + '/respawn', {
            method: 'POST', headers: _authHeaders()
          }).then(function(r) {
            _showToast(r.ok ? '✓ 会话已退出' : '⚠ 强制退出失败 (' + r.status + ')', 2000);
          }).catch(function() { _showToast('⚠ 强制退出失败(网络)', 2000); });
          return;
        }
        _lastCtrlC = now;
        seq = '\x03\x03';
      }
      _sendToTerminal(seq);
    }
  });
}

var _sendingCmd = false;   // 在途锁:网络卡时连按回车,同一条消息会重复发出

async function _sendMobileCmd() {
  if (_sendingCmd) return;   // 上一条还在路上,这次按键直接吞掉(防重复发送)
  var input = document.getElementById('mobile-cmd-input');
  var text = input.value;
  _sendingCmd = true;
  // 立即清空输入框(不等网络返回):既是即时反馈,也保证极端时序下不会重发同一段文字
  input.value = '';
  input.style.height = 'auto';
  try {
    if (text) {
      // Add to history (dedup, max 100)
      _cmdHistory = _cmdHistory.filter(function(c) { return c !== text; });
      _cmdHistory.push(text);
      if (_cmdHistory.length > 100) _cmdHistory = _cmdHistory.slice(-100);
      localStorage.setItem('mira-cmd-history', JSON.stringify(_cmdHistory));
      _historyIdx = -1;
    }
    // Send text + Enter (empty text = bare Enter for confirmations/selections)
    var ok = await _sendToTerminal(text + '\n', text || null);   // 非空文本作为 prompt 原文精确归属
    if (!ok && text && !input.value) {
      input.value = text;   // 发送失败:把文字还回输入框,别让长 prompt 丢掉
      _showToast('发送失败,请重试', 2000);
    }
  } finally {
    _sendingCmd = false;
    input.focus();
  }
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

// ── Mobile pane switcher ──────────────────────────────────────────────────────
// ── Safari-style tab switcher (mobile) ─────────────────────────────────────
var _paneSnapshots = {};

function _saveSnapshot() {
  // 切走瞬间抓一帧预览:PTY 路径从 xterm 缓冲取,不再依赖已退役的 DOM 输出区
  if (!_currentTarget || !_ptyTerm) return;
  var snap = _xtermSnapshot();
  if (snap) _paneSnapshots[_currentTarget] = snap;
}

function _openTabSwitcher() {
  _saveSnapshot();
  var overlay = document.getElementById('tab-switcher');
  if (!overlay) return;
  if (overlay.classList.contains('open')) { _closeTabSwitcher(); return; }
  // Build from cached sidebar data (no API call)
  // 同时认分组里的 .term-pane-row 和单终端项目的 .term-single(只认前者会让全是
  // 单终端项目的情况下切换器整个空掉)。两者的 name/projectId 取法不同,下面做兼容。
  var rows = document.querySelectorAll('.term-pane-row[data-target], .term-single[data-target]');
  if (!rows.length) return;
  var cards = [];
  rows.forEach(function(row) {
    var target = row.dataset.target;
    var cmd = row.dataset.cmd || '';
    var isCurrent = (_currentTarget === target);
    var _tool = _paneToolMap[target] || row.dataset.tool || '';
    var _pid = row.dataset.projectId || row.dataset.group || '';   // term-single 用 data-group
    var _isFoc = _focusProjects.indexOf(_pid) >= 0;
    var _dotColor = _tool === 'codex' ? '#22c55e' : _tool === 'claude' ? '#818cf8' : 'var(--border)';
    var nameEl = row.querySelector('.term-pane-name-text') || row.querySelector('.term-group-name');
    var name = (nameEl ? nameEl.textContent : target).replace(/^.*\//, '');
    var snap = _paneSnapshots[target];
    var previewHtml = snap
      ? '<div class="tab-card-preview">' + escHtml(snap) + '</div>'
      : '<div class="tab-card-empty">暂无预览</div>';
    var cardCls = 'tab-card show' + (isCurrent ? ' active' : '') + (_isFoc ? ' focused' : '');
    var cardHtml = '<div class="' + cardCls + '"'
      + ' data-target="' + escHtml(target) + '"'
      + ' data-cmd="' + escHtml(cmd) + '">'
      + '<div class="tab-card-header">'
      + '<span class="tab-card-dot" style="background:' + _dotColor + '"></span>'
      + '<span class="tab-card-name">' + escHtml(name) + '</span>'
      + (_isFoc ? '<span style="font-size:8px;color:' + _dotColor + ';margin-right:4px">★</span>' : '')
      + '<button class="tab-card-close" onclick="event.stopPropagation();_killTabCard(this)" title="关闭">&times;</button>'
      + '</div>'
      + previewHtml
      + '</div>';
    cards.push({html: cardHtml, focused: _isFoc});
  });
  // Sort: focused cards first
  cards.sort(function(a, b) { return (a.focused ? 0 : 1) - (b.focused ? 0 : 1); });
  overlay.innerHTML = '<div class="tab-grid">' + cards.map(function(c) { return c.html; }).join('') + '</div>';
  overlay.classList.add('open');
  requestAnimationFrame(function() { overlay.classList.add('visible'); });
  // 3D scroll
  overlay.addEventListener('scroll', _tabScrollRAF);
  // Click backdrop to close（命名函数:重复 open 时浏览器按引用去重,不会累加监听器）
  overlay.addEventListener('click', _tabBackdropClick);
  // Click card to select
  overlay.querySelectorAll('.tab-card').forEach(function(card) {
    card.addEventListener('click', function() {
      var t = card.dataset.target, cmd = card.dataset.cmd;
      _closeTabSwitcher();
      selectPane(t, cmd);
    });
  });
  _updateTabPerspective();
  var activeCard = overlay.querySelector('.tab-card.active');
  if (activeCard) activeCard.scrollIntoView({ block: 'center', behavior: 'instant' });
}

function _tabBackdropClick(e) {
  var ov = document.getElementById('tab-switcher');
  if (e.target === ov || e.target.classList.contains('tab-grid')) _closeTabSwitcher();
}
var _tabRAF = null;
function _tabScrollRAF() {
  if (_tabRAF) return;
  _tabRAF = requestAnimationFrame(function() {
    _updateTabPerspective();
    _tabRAF = null;
  });
}
function _updateTabPerspective() {
  var overlay = document.getElementById('tab-switcher');
  if (!overlay) return;
  var viewH = (window.visualViewport && window.visualViewport.height) || window.innerHeight;  // 软键盘弹起时用可视视口
  var cards = overlay.querySelectorAll('.tab-card');
  // 读写分离:先一次性读完所有 rect,再统一写 transform,避免逐卡 读→写→读 的 layout thrashing
  var angles = [];
  for (var i = 0; i < cards.length; i++) {
    var rect = cards[i].getBoundingClientRect();
    angles[i] = Math.max(-4, Math.min(4, 4 - (rect.top + rect.height / 2) / viewH * 8));
  }
  for (var j = 0; j < cards.length; j++) {
    cards[j].style.transform = 'perspective(800px) rotateX(' + angles[j].toFixed(1) + 'deg)';
  }
}

function _closeTabSwitcher() {
  var overlay = document.getElementById('tab-switcher');
  if (!overlay) return;
  overlay.classList.remove('visible');
  overlay.removeEventListener('scroll', _tabScrollRAF);
  overlay.removeEventListener('click', _tabBackdropClick);
  setTimeout(function() {
    overlay.classList.remove('open');
    overlay.innerHTML = '';
  }, 250);
}

function _killTabCard(btn) {
  var card = btn.closest('.tab-card');
  if (!card) return;
  var target = card.dataset.target;
  card.style.transition = 'transform .3s, opacity .3s';
  card.style.transform = 'translateX(-100%) rotateZ(-5deg)';
  card.style.opacity = '0';
  setTimeout(function() {
    card.remove();
    delete _paneSnapshots[target];
    // Kill the pane via API
    fetch('/api/terminals/' + encodeURIComponent(target), {
      method: 'DELETE', headers: _authHeaders()
    }).then(function() { loadPanes(true); });
    // If no cards left, close
    var overlay = document.getElementById('tab-switcher');
    if (overlay && !overlay.querySelector('.tab-card')) _closeTabSwitcher();
  }, 300);
}

async function _togglePaneSwitcher() {
  var panel = document.getElementById('pane-switcher');
  if (!panel) return;
  if (panel.classList.contains('open')) {
    panel.classList.remove('open');
    return;
  }
  // Build list from current pane data
  try {
    var res = await fetch('/api/dev/panes', { headers: _authHeaders() });
    if (!res.ok) return;
    var panes = await res.json();
    var html = '';
    for (var i = 0; i < panes.length; i++) {
      var p = panes[i];
      var isCurrent = (_currentTarget === p.target);
      var _dc = p.tool === 'codex' ? '#22c55e' : p.tool === 'claude' ? '#818cf8' : 'var(--border)';
      html += '<div class="pane-switcher-item' + (isCurrent ? ' current' : '') + '"'
        + ' data-target="' + escHtml(p.target) + '"'
        + ' data-cmd="' + escHtml(p.command || '') + '">'
        + '<div class="pane-switcher-name">'
        + '<span class="pane-switcher-dot" style="background:' + _dc + '"></span>'
        + escHtml(p.label || p.target) + '</div>'
        + '<div class="pane-switcher-sub">' + escHtml(p.project_name || p.command || '') + '</div>'
        + '</div>';
    }
    panel.innerHTML = html;
    panel.querySelectorAll('.pane-switcher-item').forEach(function(el) {
      el.addEventListener('click', function() {
        panel.classList.remove('open');
        selectPane(el.dataset.target, el.dataset.cmd);
      });
    });
    panel.classList.add('open');
  } catch(e) { console.warn('pane switcher:', e); }
}

// ── Toast notification ────────────────────────────────────────────────────────
var _toastTimer = null;
function _showToast(msg, duration) {
  var el = document.getElementById('dev-toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(function() { el.classList.remove('show'); }, duration || 3000);
}

// ── Image compression ────────────────────────────────────────────────────────
function _compressImage(file, maxDim, quality) {
  maxDim = maxDim || 1568;
  quality = quality || 0.8;
  return new Promise(function(resolve) {
    // SVG / GIF: skip compression
    if (file.type === 'image/svg+xml' || file.type === 'image/gif') {
      return resolve(file);
    }
    var img = new Image();
    var url = URL.createObjectURL(file);
    img.onload = function() {
      URL.revokeObjectURL(url);
      var w = img.width, h = img.height;
      var needsResize = (w > maxDim || h > maxDim);
      // Already small enough → skip entirely
      if (!needsResize && file.size < 512 * 1024) {
        return resolve(file);
      }
      // Scale down to fit maxDim
      if (needsResize) {
        var ratio = Math.min(maxDim / w, maxDim / h);
        w = Math.round(w * ratio);
        h = Math.round(h * ratio);
      }
      var canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      canvas.getContext('2d').drawImage(img, 0, 0, w, h);
      // Try WebP, JPEG, PNG — pick smallest
      var formats = [
        ['image/webp', quality],
        ['image/jpeg', quality],
        ['image/png', undefined]
      ];
      var pending = formats.length, results = [];
      function _pickBest() {
        if (--pending > 0) return;
        results.sort(function(a, b) { return a.size - b.size; });
        var best = results[0];
        if (!needsResize && best.size >= file.size) {
          console.log('[mira] compression skipped (original smaller): ' + (file.size/1024).toFixed(0) + 'KB');
          return resolve(file);
        }
        var ext = best.type === 'image/webp' ? 'webp' : (best.type === 'image/png' ? 'png' : 'jpg');
        var compressed = new File([best], file.name.replace(/\.[^.]+$/, '.' + ext), {type: best.type});
        console.log('[mira] image compressed: ' + (file.size/1024).toFixed(0) + 'KB → ' + (compressed.size/1024).toFixed(0) + 'KB (' + w + 'x' + h + ' ' + ext + ')');
        resolve(compressed);
      }
      formats.forEach(function(fmt) {
        canvas.toBlob(function(b) { if (b) results.push(b); _pickBest(); }, fmt[0], fmt[1]);
      });
    };
    img.onerror = function() { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

// ── File upload ──────────────────────────────────────────────────────────────
async function _uploadImage(file) {
  if (!file) return;
  _showToast('压缩中…', 10000);
  file = await _compressImage(file);
  _showToast('上传中…', 10000);
  var fd = new FormData();
  fd.append('file', file);
  try {
    // 远程 pane → 带 host 参数转发到远程主机
    var uploadUrl = '/api/upload/image';
    var activeRow = document.querySelector('.term-pane-row.active, .term-single.active');
    if (activeRow) {
      var target = activeRow.getAttribute('data-target') || '';
      var hostMatch = _paneHostMap && _paneHostMap[target];
      if (hostMatch) uploadUrl += '?host=' + encodeURIComponent(hostMatch);
    }
    var res = await fetch(uploadUrl, {
      method: 'POST',
      headers: _authHeaders(),
      body: fd
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    var data = await res.json();
    var path = data.path || data.url || '';
    _showToast('文件已上传: ' + path, 4000);
    if (_isMobile) {
      // Mobile: insert path into textarea
      var input = document.getElementById('mobile-cmd-input');
      if (input) {
        input.value = (input.value ? input.value + ' ' : '') + path;
        input.focus();
      }
    } else {
      // Desktop: show confirm popup to send path to terminal
      _showUploadConfirm(path);
    }
  } catch(e) {
    _showToast('上传失败: ' + e.message, 4000);
  }
}

function _showUploadConfirm(path) {
  // Remove existing
  var old = document.getElementById('upload-confirm-overlay');
  if (old) old.remove();
  old = document.getElementById('upload-confirm-popup');
  if (old) old.remove();

  var overlay = document.createElement('div');
  overlay.id = 'upload-confirm-overlay';
  overlay.className = 'upload-confirm-overlay';
  overlay.onclick = function() { overlay.remove(); popup.remove(); };

  var popup = document.createElement('div');
  popup.id = 'upload-confirm-popup';
  popup.className = 'upload-confirm';
  popup.innerHTML = '<div class="upload-confirm-title">文件已上传</div>'
    + '<div class="upload-confirm-path">' + escHtml(path) + '</div>'
    + '<div class="upload-confirm-btns">'
    + '<button onclick="document.getElementById(\'upload-confirm-overlay\').click()">关闭</button>'
    + '<button class="primary" id="upload-send-btn">发送到终端</button>'
    + '</div>';

  document.body.appendChild(overlay);
  document.body.appendChild(popup);

  document.getElementById('upload-send-btn').onclick = function() {
    _sendToTerminal(path);
    overlay.remove();
    popup.remove();
    _showToast('路径已发送到终端', 2000);
  };
}

// Clipboard paste: try Clipboard API first (HTTPS), fallback to paste-trap (HTTP)
var _pasteTrap = null;
function _pasteFromClipboard() {
  // Try Clipboard API (only works on HTTPS / secure context)
  if (navigator.clipboard && navigator.clipboard.read && window.isSecureContext) {
    navigator.clipboard.read().then(function(items) {
      for (var i = 0; i < items.length; i++) {
        var types = items[i].types;
        for (var j = 0; j < types.length; j++) {
          if (types[j].startsWith('image/')) {
            items[i].getType(types[j]).then(function(blob) {
              var file = new File([blob], 'clipboard.' + blob.type.split('/')[1], {type: blob.type});
              _uploadImage(file);
            });
            return;
          }
        }
      }
      _showToast('剪贴板中没有图片', 2000);
    }).catch(function() { _openPasteTrap(); });
    return;
  }
  _openPasteTrap();
}

function _openPasteTrap() {
  // HTTP fallback: focus a hidden contenteditable, user presses Cmd+V
  if (!_pasteTrap) {
    _pasteTrap = document.createElement('div');
    _pasteTrap.contentEditable = 'true';
    _pasteTrap.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:280px;padding:24px;background:var(--panel);border:1px solid var(--accent);border-radius:var(--radius);z-index:600;text-align:center;font-family:var(--mono);font-size:13px;color:var(--text);outline:none;';
    _pasteTrap.innerHTML = '<div style="margin-bottom:8px;font-size:14px;font-weight:700">📋 粘贴图片</div><div style="color:var(--sub);font-size:12px">按 <kbd style="background:var(--bg);padding:2px 6px;border-radius:4px;border:1px solid var(--border)">⌘V</kbd> 粘贴剪贴板内容</div><div style="margin-top:12px;font-size:11px;color:var(--muted)">点击外部关闭</div>';
    _pasteTrap.addEventListener('paste', function(e) {
      e.preventDefault();
      var items = e.clipboardData && e.clipboardData.items;
      var found = false;
      for (var i = 0; items && i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          _uploadImage(items[i].getAsFile());
          found = true;
          break;
        }
      }
      if (!found) _showToast('剪贴板中没有图片', 2000);
      _closePasteTrap();
    });
  }
  // Show overlay + trap
  var ov = document.createElement('div');
  ov.id = 'paste-trap-overlay';
  ov.style.cssText = 'position:fixed;inset:0;z-index:599;background:rgba(0,0,0,.5);';
  ov.onclick = function() { _closePasteTrap(); };
  document.body.appendChild(ov);
  document.body.appendChild(_pasteTrap);
  _pasteTrap.focus();
}

function _closePasteTrap() {
  var ov = document.getElementById('paste-trap-overlay');
  if (ov) ov.remove();
  if (_pasteTrap && _pasteTrap.parentNode) _pasteTrap.remove();
}

// File input handlers
function _initUpload() {
  var mobileInput = document.getElementById('mobile-file-input');
  if (mobileInput) {
    mobileInput.addEventListener('change', function() {
      if (this.files && this.files[0]) _uploadImage(this.files[0]);
      this.value = '';
    });
  }
  var desktopInput = document.getElementById('desktop-file-input');
  if (desktopInput) {
    desktopInput.addEventListener('change', function() {
      if (this.files && this.files[0]) _uploadImage(this.files[0]);
      this.value = '';
    });
  }

  // Global paste interception
  document.addEventListener('paste', function(e) {
    var items = e.clipboardData && e.clipboardData.items;
    // Image paste → upload
    for (var i = 0; items && i < items.length; i++) {
      if (items[i].type.startsWith('image/')) {
        e.preventDefault();
        _uploadImage(items[i].getAsFile());
        return;
      }
    }
    // Multi-line text paste → send via API to avoid ttyd truncation
    var text = e.clipboardData && e.clipboardData.getData('text');
    if (text && text.includes('\n') && _currentTarget &&
        document.getElementById('dev-page').classList.contains('detail-open')) {
      e.preventDefault();
      _sendToTerminal(text);
      _showToast('已粘贴 ' + text.split('\n').length + ' 行', 2000);
    }
  });
}

// ── claude 完整会话历史(读 ~/.claude jsonl,不受终端擦屏影响)──────────────────
var _histBefore = 0, _histTarget = null, _histLoading = false;

function openPaneHistory() {
  if (!_currentTarget) { _showToast('先选择一个终端', 1500); return; }
  _histTarget = _currentTarget; _histBefore = 0;
  var title = document.getElementById('term-detail-title');
  document.getElementById('hist-title').textContent = '会话历史 · ' + ((title && title.textContent.trim()) || _histTarget);
  document.getElementById('hist-meta').textContent = '';
  document.getElementById('hist-inner').innerHTML = '<div class="hist-empty">加载中…</div>';
  document.getElementById('hist-overlay').classList.add('open');
  _loadPaneHistory(true);
}

function closePaneHistory() {
  document.getElementById('hist-overlay').classList.remove('open');
}

function _histTs(iso) {
  var d = new Date(iso);
  if (isNaN(d)) return '';
  var p = function(x) { return String(x).padStart(2, '0'); };
  return (d.getMonth() + 1) + '/' + d.getDate() + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
}

function _histRenderTurn(t) {
  var tools = '';
  if (t.tools) {
    var parts = Object.keys(t.tools).map(function(k) {
      var nm = k.replace(/^mcp__.*__/, '');   // MCP 全限定名太长,只留末段
      return nm + (t.tools[k] > 1 ? '×' + t.tools[k] : '');
    });
    if (parts.length) tools = '<div class="hist-tools">⚙ ' + escHtml(parts.join(' · ')) + '</div>';
  }
  var body = (t.text || '').trim();
  if (t.agent) {
    // 子代理轮次:缩进降级显示,带任务标签;派发任务书(user)与过程文本同样式
    var tag = '<span class="hist-agent-tag">↳ ' + escHtml(t.agent) + '</span>';
    return '<div class="hist-turn hist-agent">' + tag
      + (body ? '<div class="hist-asst">' + escHtml(body) + '</div>' : '') + tools + '</div>';
  }
  if (t.role === 'user') {
    var ts = t.ts ? '<div class="hist-ts">' + _histTs(t.ts) + '</div>' : '';
    return '<div class="hist-turn">' + ts + '<div class="hist-user">' + escHtml(t.text) + '</div></div>';
  }
  return '<div class="hist-turn">' + (body ? '<div class="hist-asst">' + escHtml(body) + '</div>' : '') + tools + '</div>';
}

async function _loadPaneHistory(initial) {
  if (_histLoading) return;
  _histLoading = true;
  var body = document.getElementById('hist-body');
  var inner = document.getElementById('hist-inner');
  try {
    // limit 按「用户回合」计:一页 = 最近 10 次对话回合及其间全部过程
    var res = await fetch('/api/dev/pane-history?target=' + encodeURIComponent(_histTarget)
      + '&before=' + _histBefore + '&limit=10', { headers: _authHeaders() });
    if (!res.ok) {
      if (initial) inner.innerHTML = '<div class="hist-empty">'
        + (res.status === 404 ? '没有找到该项目的 claude 会话记录' : '加载失败(' + res.status + ')') + '</div>';
      return;
    }
    var d = await res.json();
    var html = (d.turns || []).map(_histRenderTurn).join('');
    var more = d.has_more
      ? '<button class="hist-more" id="hist-more" onclick="_loadPaneHistory(false)">加载更早的对话</button>' : '';
    if (initial) {
      inner.innerHTML = more + (html || '<div class="hist-empty">这个会话还没有对话</div>');
      body.scrollTop = body.scrollHeight;   // 打开时定位到最新
      document.getElementById('hist-meta').textContent = '共 ' + d.total + ' 轮 · ' + d.session;
    } else {
      var old = document.getElementById('hist-more');
      if (old) old.remove();
      var prevH = body.scrollHeight;
      inner.insertAdjacentHTML('afterbegin', more + html);
      body.scrollTop = body.scrollTop + (body.scrollHeight - prevH);   // 保持阅读位置
    }
    _histBefore += (d.turns || []).length;
  } catch (e) {
    if (initial) inner.innerHTML = '<div class="hist-empty">加载失败</div>';
  } finally {
    _histLoading = false;
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
// ── 子账号视图:复用 dev 页全套(皮肤/终端/快捷键/上传/topbar 用量),只换数据源与权限 ──
// 终端统一走 xterm PTY 直连(同 showTerminal),不再用子账号 ttyd(/subterm/<port>/)。
async function initSub() {
  document.getElementById('dev-page').classList.add('sub-mode');
  document.body.classList.add('sub-mode');
  new MutationObserver(function() { _refreshXtermTheme(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  document.getElementById('term-pane-list').addEventListener('click', function(e) {
    var row = e.target.closest('.term-pane-row');
    if (row) selectSubProject(row.dataset.pid);
  });
  _initMobileInput();
  _initUpload();
  await loadSubProjects();
  var _subInterval = setInterval(loadSubProjects, 15000);
  // 子账号视图也接 visibilitychange:后台暂停轮询/断 WS,省电、防请求风暴
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      clearInterval(_subInterval); _subInterval = null;
      if (_tokenRefreshTimer) { clearInterval(_tokenRefreshTimer); _tokenRefreshTimer = null; }
      if (_usageRefreshTimer) { clearInterval(_usageRefreshTimer); _usageRefreshTimer = null; }
      _disconnectPtyWs();
    } else {
      loadSubProjects();
      _subInterval = setInterval(loadSubProjects, 15000);
      if (_currentTarget && document.getElementById('dev-page').classList.contains('detail-open')) {
        _connectPtyWs(_currentTarget);
        _startTokenRefresh(_currentTarget, 'claude');
      }
    }
  });
}

async function loadSubProjects() {
  var projs = (_sub && _sub.projects) ? _sub.projects.map(function(id){ return {id:id, name:id}; }) : [];
  var res = await fetch('/api/sub/projects', { headers: _authHeaders() }).catch(function(){ return null; });
  if (res && res.ok) projs = await res.json();
  var list = document.getElementById('term-pane-list');
  if (!list) return;
  if (!projs.length) {
    list.innerHTML = '<div class="term-empty-sidebar">还没有被授权的项目<br><br>等管理员在后台勾选授权</div>';
    return;
  }
  var cur = _currentSubPid || '';
  list.innerHTML = projs.map(function(p) {
    var pid = escHtml(p.id), name = escHtml(p.name || p.id);
    return '<div class="term-pane-row term-single' + (pid === cur ? ' active' : '') + '" data-pid="' + pid + '">'
      + '<div class="term-pane-badge claude">C</div>'
      + '<span class="term-pane-name"><span class="term-pane-name-text">' + name + '</span></span>'
      + '</div>';
  }).join('');
}

var _currentSubPid = '';
async function selectSubProject(pid) {
  if (!pid) return;
  _currentSubPid = pid;
  _currentTarget = null;
  document.querySelectorAll('.term-pane-row').forEach(function(r){ r.classList.toggle('active', r.dataset.pid === pid); });
  document.getElementById('dev-page').classList.add('detail-open');
  if (_isMobile) {
    document.body.classList.add('detail-locked');
    document.querySelectorAll('.topbar .topbar-btn').forEach(function(b){ b.style.display = 'none'; });
    document.querySelectorAll('.topbar .topbar-detail-btn').forEach(function(b){ b.style.display = 'inline-flex'; });
  }
  var _histBtn = document.getElementById('topbar-hist-btn');   // 桌面 sub 项目同样在右上角显示历史 icon
  if (_histBtn) _histBtn.style.display = 'inline-flex';
  var row = document.querySelector('.term-pane-row[data-pid="' + CSS.escape(pid) + '"]');
  var name = row ? ((row.querySelector('.term-pane-name-text') || {}).textContent || pid) : pid;
  var titleEl = document.getElementById('term-detail-title'); if (titleEl) titleEl.textContent = name;
  var pn = document.getElementById('topbar-project-name'); if (pn) pn.textContent = _isMobile ? name : ' · ' + name;
  document.getElementById('term-placeholder').style.display = 'none';
  var res = await fetch('/api/sub/project/' + encodeURIComponent(pid) + '/session', { method: 'POST', headers: _authHeaders() }).catch(function(){ return null; });
  if (!res || !res.ok) { _subTermError(res && res.status === 403 ? '无权访问该项目' : '会话启动失败,稍后重试'); return; }
  var d = await res.json();
  _currentTarget = d.target;
  showSubTerminal();
  if (d.target) { _loadPaneTokens(d.target, 'claude'); _updateTopbarUsage('claude'); _startTokenRefresh(d.target, 'claude'); }
}

function _subTermError(msg) {
  var ph = document.getElementById('term-placeholder');
  if (!ph) return;
  ph.style.display = '';
  if (ph.firstElementChild) ph.firstElementChild.textContent = msg;
}

function showSubTerminal() {
  document.getElementById('term-placeholder').style.display = 'none';
  var toolbar = document.getElementById('term-toolbar'); if (toolbar) toolbar.classList.add('visible');
  var devPage = document.getElementById('dev-page');
  devPage.classList.add('stream-mode');
  devPage.classList.remove('sub-hybrid');
  document.getElementById('xterm-wrap').classList.add('visible');
  document.getElementById('mobile-token-bar').classList.add('visible');
  document.getElementById('mobile-input-bar').style.display = 'flex';
  if (_currentTarget) _connectPtyWs(_currentTarget);
  if (!_isMobile) _focusInputBox();
}

function _focusInputBox() {
  if (_isMobile) return;   // 移动端不自动弹软键盘,用户点了才聚焦
  setTimeout(function() {
    var i = document.getElementById('mobile-cmd-input');
    var dp = document.getElementById('dev-page');
    if (i && dp && dp.classList.contains('stream-mode')) i.focus();
  }, 80);
}

function _subWaystation(msg, showLogin) {
  document.body.innerHTML = '<div style="position:fixed;inset:0;display:flex;flex-direction:column;'
    + 'align-items:center;justify-content:center;gap:18px;text-align:center;padding:24px;'
    + 'background:var(--bg);color:var(--text);font-family:var(--mono)">'
    + '<div style="font-size:20px;font-weight:700"><span style="color:var(--accent)">M</span>ira 协作</div>'
    + '<div style="font-size:13px;color:var(--sub);line-height:1.7;max-width:360px">' + msg + '</div>'
    + (showLogin ? '<a href="/auth/feishu/login" style="font-size:15px;font-weight:600;background:var(--accent);'
        + 'color:#fff;border-radius:10px;padding:12px 26px;text-decoration:none">飞书登录</a>' : '')
    + '</div>';
}

async function init() {
  // 飞书回调的中转态(用 dev 页本身承载,不另起页面)
  var _sp = new URLSearchParams(location.search);
  if (_sp.get('sub_status') && _sp.get('sub_status') !== 'active') {
    return _subWaystation('登录成功,正在等待管理员批准并分配项目。<br>批准后刷新本页即可开始。', false);
  }
  if (_sp.get('sub_error')) {
    return _subWaystation('登录失败,请重试。', true);
  }
  await _initAuth();
  if (_isSub) { return initSub(); }
  if (!_isAdmin) { openLoginModal(init); return; }
  // Event delegation: bind click once on the container, survives innerHTML rebuilds
  // Prevent sidebar clicks from stealing focus away from the terminal iframe
  document.getElementById('term-pane-list').addEventListener('mousedown', function(e) {
    if (e.target.closest('.term-pane-row') && !e.target.closest('.term-pane-kill')) {
      e.preventDefault();
    }
    // 桌面拖拽:只从抓手 ⠿ 发起(整行可拖会把"点名字改名"的微动当成拖拽吞掉)。
    if (!_editMode) return;       // 只有"编辑"模式才能拖
    if (e.button !== 0) return;
    var top = e.target.closest('#term-pane-list > .term-toplevel');
    if (!top) return;
    if (e.target.closest('.term-drag-handle')) {   // 抓手只在顶层项,所以拖的就是 top
      e.preventDefault(); e.stopPropagation();
      _startDrag(e, top.dataset.key, top.dataset.type, 'mouse');
    }
  });
  document.getElementById('term-pane-list').addEventListener('click', function(e) {
    var row = e.target.closest('.term-pane-row');
    if (!row) return;
    if (e.target.closest('.term-pane-kill')) return;
    selectPane(row.dataset.target, row.dataset.cmd);
  });
  // 换肤实时同步 xterm 主题
  new MutationObserver(function() { _refreshXtermTheme(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  // Init mobile input bar + upload handlers
  _initMobileInput();
  _initUpload();
  await loadDevGroups();
  await loadPanes();
  // 移动端:iOS 可能在后台回收/重载页面 → 用上次停留的终端视图自动恢复,不再掉回项目列表。
  // (该 target 已不存在则清掉记录。)
  if (_isMobile) {
    var _saved = null;
    try { _saved = localStorage.getItem('mira-dev-target'); } catch(e) {}
    if (_saved && _hasPaneTarget(_saved)) selectPane(_saved);
    else if (_saved) { try { localStorage.removeItem('mira-dev-target'); } catch(e) {} }
  }
  var _panesInterval = setInterval(loadPanes, 8000);
  // Warm the lightweight project list while the page is idle so the first
  // click on + normally opens with a complete list and no network wait.
  var _preloadProjects = function() { _fetchNewTermProjects().catch(function() {}); };
  if (window.requestIdleCallback) requestIdleCallback(_preloadProjects, { timeout: 1500 });
  else setTimeout(_preloadProjects, 300);

  // Pause all polling when tab is hidden, resume when visible
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      clearInterval(_panesInterval); _panesInterval = null;
      if (_tokenRefreshTimer) { clearInterval(_tokenRefreshTimer); _tokenRefreshTimer = null; }
      if (_usageRefreshTimer) { clearInterval(_usageRefreshTimer); _usageRefreshTimer = null; }
      // 后台主动断开终端 WS:避免 iOS 掐断时触发 onclose 的重连/回列表逻辑
      _disconnectPtyWs();
    } else {
      loadPanes();
      _panesInterval = setInterval(loadPanes, 8000);
      if (_currentTarget) {
        var t = _paneToolMap[_currentTarget] || '';
        if (t) _startTokenRefresh(_currentTarget, t);
        // 回前台:仍在终端详情视图则重连 WS 恢复输出
        if (document.getElementById('dev-page').classList.contains('detail-open')) {
          _connectPtyWs(_currentTarget);
        }
      }
    }
  });
}
init();
