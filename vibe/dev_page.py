"""Dev mode page — sidebar pane list + ttyd iframe."""

_BUILD_ID = None


def _build_id() -> str:
    """运行中代码的 git 短提交号 + 启动分钟标记,用来在页面上核对'是否刷到最新版'。
    模块加载时算一次;每次重启(无热重载)会重新导入、重算。"""
    global _BUILD_ID
    if _BUILD_ID is not None:
        return _BUILD_ID
    import subprocess
    from pathlib import Path
    try:
        root = Path(__file__).resolve().parent.parent
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=2)
        h = r.stdout.strip() or "unknown"
        d = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "-uno"],
                           capture_output=True, text=True, timeout=2)
        _BUILD_ID = h + ("+dirty" if d.stdout.strip() else "")
    except Exception:
        _BUILD_ID = "unknown"
    return _BUILD_ID


def render_dev_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js

    page_css = r"""
  /* ── Page reset (lock body to viewport, terminal handles its own scroll) ── */
  :root { --app-h: 100vh; }
  html, body { margin: 0; padding: 0; height: 100vh; overflow: hidden; overscroll-behavior: none; width: 100%; max-width: 100vw; }
  /* Lock scroll when mobile terminal detail is open */
  body.detail-locked { position: fixed; width: 100%; touch-action: none; }
  /* 部署版本号(右下角)—— 用来核对页面是否刷到最新代码 */
  /* ── Main layout ── */
  .dev-page {
    margin-top: 52px;
    height: calc(var(--app-h) - 52px);
    display: flex;
    overflow: hidden;
    background: var(--bg);
  }

  /* ── Sidebar ── */
  .term-sidebar {
    width: 200px; border-right: 1px solid var(--border);
    display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden;
    background: var(--panel); position: relative;
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
  .term-edit-btn {
    background: none; border: 1px solid var(--border); color: var(--muted);
    width: 20px; height: 20px; border-radius: var(--radius-sm);
    cursor: pointer; transition: all .12s; display: flex; align-items: center; justify-content: center; padding: 0;
  }
  .term-edit-btn:hover { color: var(--accent); border-color: var(--accent); }
  .term-edit-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
  #term-pane-list { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; position: relative; }
  /* 抓手 / ⋯菜单 / 删除 默认隐藏,只在"编辑"模式显示 */
  #term-pane-list:not(.edit-mode) .term-drag-handle,
  #term-pane-list:not(.edit-mode) .term-group-menu,
  #term-pane-list:not(.edit-mode) .term-pane-kill { display: none; }
  #term-pane-list.edit-mode .term-drag-handle { opacity: .9; }
  #term-pane-list.edit-mode .term-group-menu { opacity: 1; }
  #term-pane-list.edit-mode .term-pane-kill { opacity: .8; }
  #term-pane-list.edit-mode .term-single { cursor: text; }
  .term-pane-row {
    padding: 10px 14px; display: flex; align-items: flex-start; gap: 8px;
    cursor: pointer; border-left: 2px solid transparent; transition: background .12s, border-color .12s;
  }
  .term-pane-row:hover { background: rgba(255,255,255,.03); }
  .term-pane-row.active { background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }
  .term-pane-row.focused { background: rgba(var(--accent-rgb),.04); }
  .term-pane-row.focused .term-pane-name-text { color: var(--accent); }
  .term-pane-kill {
    opacity: 0.5; flex-shrink: 0; cursor: pointer;
    width: 18px; height: 18px; border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    color: var(--muted); font-size: 12px; line-height: 1;
    transition: opacity .12s, color .12s, background .12s;
    margin-left: 4px;
  }
  .term-pane-kill:hover {
    opacity: 1 !important;
    color: var(--red, #ef4444);
    background: rgba(239, 68, 68, 0.12);
  }
  .term-pane-badge {
    width: 16px; height: 16px; border-radius: 4px; flex-shrink: 0; margin-top: 1px;
    display: flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 800; font-family: var(--mono);
    letter-spacing: -0.5px; line-height: 1;
  }
  .term-pane-badge.claude { background: rgba(129,140,248,.18); color: #818cf8; cursor: pointer; transition: all .15s; }
  .term-pane-badge.codex  { background: rgba(34,197,94,.18); color: #22c55e; cursor: pointer; transition: all .15s; }
  .term-pane-badge.claude.glow { background: rgba(129,140,248,.4); box-shadow: 0 0 8px rgba(129,140,248,.5); }
  .term-pane-badge.codex.glow  { background: rgba(34,197,94,.4); box-shadow: 0 0 8px rgba(34,197,94,.5); }
  .term-pane-badge.unknown {
    width: 8px; height: 8px; border-radius: 50%; margin: 4px 4px 0 4px;
    background: none; border: 1.5px solid var(--border);
  }
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
  /* 单终端项目压成的一行 */
  .term-single { gap: 7px; }
  .term-single .term-group-name { color: var(--text); font-weight: 500; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .term-single.active { background: rgba(var(--accent-rgb),.1); border-left: 2px solid var(--accent); padding-left: 12px; }
  .term-single.active .term-group-name { color: var(--accent); }
  .term-group-header.focused { background: rgba(var(--accent-rgb),.06); border-left: 2px solid var(--accent); }
  .term-group-header.focused .term-group-name { color: var(--accent); }
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
  /* ⋯ 菜单触发 + 拖拽合并 + 文件夹(主题变量驱动,切主题一致) */
  .term-group-menu {
    font-size: 13px; color: var(--muted); padding: 0 4px; border-radius: 3px;
    line-height: 1; cursor: pointer; opacity: 0; transition: opacity .12s, color .12s; flex-shrink: 0;
  }
  .term-group-header:hover .term-group-menu, .term-folder-header:hover .term-group-menu { opacity: 1; }
  .term-group-menu:hover { color: var(--text); background: rgba(255,255,255,.08); }
  .term-group-header.drag-over, .term-folder-header.drag-over {
    background: color-mix(in srgb, var(--accent) 16%, transparent);
    box-shadow: inset 0 0 0 1px var(--accent);
  }
  /* 拖拽抓手 + 排序辅助(主题变量驱动) */
  .term-drag-handle {
    font-size: 15px; color: var(--sub); cursor: grab; flex-shrink: 0; line-height: 1;
    padding: 2px 4px; margin-left: -2px; touch-action: none; user-select: none;
    opacity: .65; transition: opacity .12s, color .12s;
  }
  .term-group-header:hover .term-drag-handle, .term-folder-header:hover .term-drag-handle { opacity: 1; }
  .term-drag-handle:hover { color: var(--accent); }
  .term-drag-handle:active { cursor: grabbing; }
  body.dev-dragging, body.dev-dragging * { cursor: grabbing !important; }
  /* 拖拽时让终端 iframe 不吃鼠标事件,否则光标划过它时 mousemove 会被 iframe 截走 */
  body.dev-dragging #ttyd-frame { pointer-events: none !important; }
  .dev-drag-ghost {
    position: fixed; z-index: 5000; pointer-events: none; white-space: nowrap;
    background: var(--panel); border: 1px solid var(--accent); border-radius: 6px;
    padding: 4px 10px; font-size: 11px; color: var(--text); box-shadow: 0 6px 20px rgba(0,0,0,.45);
    max-width: 220px; overflow: hidden; text-overflow: ellipsis;
  }
  .dev-drop-line {
    position: absolute; left: 6px; right: 6px; height: 2px; display: none; z-index: 10;
    pointer-events: none; background: var(--accent); border-radius: 2px;
    box-shadow: 0 0 6px var(--accent);
  }
  .term-folder { border-bottom: 1px solid rgba(255,255,255,.04); }
  .term-folder-header {
    padding: 8px 14px; display: flex; align-items: center; gap: 6px;
    cursor: pointer; user-select: none; transition: background .12s;
  }
  .term-folder-header:hover { background: rgba(255,255,255,.03); }
  .term-folder-icon { font-size: 12px; flex-shrink: 0; }
  .term-folder-name {
    font-size: 11px; font-weight: 700; color: var(--text);
    flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .term-folder-body { overflow: hidden; padding-left: 10px;
    border-left: 2px solid color-mix(in srgb, var(--accent) 30%, transparent); margin-left: 14px; }
  .term-folder-body.collapsed { display: none; }
  .term-group-header.nested { padding-left: 8px; }
  /* 上下文菜单 */
  .dev-ctx-menu {
    position: fixed; z-index: 4000; min-width: 140px;
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
    box-shadow: 0 8px 28px rgba(0,0,0,.4); padding: 4px; display: flex; flex-direction: column;
  }
  .dev-ctx-item {
    text-align: left; font-family: var(--mono); font-size: 12px; color: var(--text);
    background: none; border: none; border-radius: 5px; padding: 7px 10px; cursor: pointer;
  }
  .dev-ctx-item:hover { background: rgba(255,255,255,.07); }
  .dev-ctx-item.danger { color: var(--red); }
  .dev-ctx-item.danger:hover { background: color-mix(in srgb, var(--red) 12%, transparent); }
  /* 页内重命名输入框(替代原生 prompt) */
  .dev-rename-overlay { position: fixed; inset: 0; z-index: 8000; background: rgba(0,0,0,.5);
    display: flex; align-items: center; justify-content: center; }
  .dev-rename-box { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    padding: 18px 20px; width: 300px; max-width: 88vw; box-shadow: 0 12px 40px rgba(0,0,0,.45); }
  .dev-rename-title { font-size: 13px; color: var(--text); font-weight: 600; margin-bottom: 12px; }
  .dev-rename-input { width: 100%; box-sizing: border-box; background: var(--bg);
    border: 1px solid var(--border); border-radius: 6px; color: var(--text);
    font-family: var(--mono); font-size: 14px; padding: 8px 10px; outline: none; }
  .dev-rename-input:focus { border-color: var(--accent); }
  .dev-rename-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
  .dev-rename-actions button { font-size: 12px; font-family: var(--mono); padding: 6px 16px;
    border-radius: 6px; cursor: pointer; border: 1px solid var(--border); background: var(--bg); color: var(--text); }
  .dev-rename-ok { background: var(--accent) !important; color: #fff !important; border-color: var(--accent) !important; }
  .term-group-body .term-pane-row { padding-left: 26px; }

  /* ── Remote host badge ── */
  .term-host-badge {
    font-size: 9px; padding: 1px 5px; border-radius: 6px;
    background: rgba(var(--accent-rgb),.15); color: var(--accent);
    white-space: nowrap; flex-shrink: 0; line-height: 14px;
  }
  /* 子账号开的进程标识 */
  .term-sub-badge {
    width: 18px; height: 18px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 9px; font-weight: 700; line-height: 1; text-transform: uppercase;
    background: rgba(229,166,80,.18); color: var(--orange, #e5a650);
    border: 1px solid rgba(229,166,80,.4);
    flex-shrink: 0; overflow: hidden; vertical-align: middle;
  }
  .term-sub-badge.term-sub-av {
    padding: 0; object-fit: cover; background: var(--panel); border-color: var(--border);
  }
  .term-host-badge.offline {
    background: rgba(255,255,255,.06); color: var(--muted);
  }

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
    border: none; display: block; visibility: hidden; pointer-events: none; background: var(--bg);
    position: absolute; inset: 0; width: 100%; height: 100%;
    overflow: hidden;
  }
  #ttyd-frame.visible { visibility: visible; pointer-events: auto; }
  /* Touch overlay + scroll badge: mobile-only (hidden on desktop) */
  .term-touch-overlay { display: none; }
  .term-scroll-badge { display: none; }
  /* Mobile-only elements hidden on desktop */
  .mobile-term-output { display: none; }
  /* head/scrollback/live 三区:display:contents 让 div 的文本按父级 pre-wrap 连续排版 */
  .mobile-term-output .term-head, .mobile-term-output .term-sb, .mobile-term-output .term-live { display: contents; }
  .mobile-input-bar { display: none; }

  /* ── claude 完整会话历史(读 ~/.claude jsonl)── */
  .hist-overlay { position: fixed; inset: 0; z-index: 400; background: var(--bg); display: none; flex-direction: column; }
  .hist-overlay.open { display: flex; }
  .hist-head { display: flex; align-items: center; gap: 10px; padding: 10px 14px;
    padding-top: max(10px, env(safe-area-inset-top)); border-bottom: 1px solid var(--border); background: var(--panel); }
  .hist-title { font-size: 13px; font-weight: 700; color: var(--text); flex: 1;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .hist-meta { font-size: 10px; color: var(--muted); white-space: nowrap; }
  .hist-close { background: none; border: 1px solid var(--border); color: var(--sub); border-radius: 6px;
    padding: 4px 14px; font-family: inherit; font-size: 12px; cursor: pointer; flex-shrink: 0; }
  .hist-body { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; overscroll-behavior: contain;
    padding: 14px 14px calc(30px + env(safe-area-inset-bottom)); }
  .hist-inner { max-width: 860px; margin: 0 auto; }
  .hist-more { display: block; margin: 0 auto 16px; background: none; border: 1px solid var(--border);
    color: var(--accent); border-radius: 14px; padding: 5px 18px; font-family: inherit; font-size: 12px; cursor: pointer; }
  .hist-more:disabled { opacity: .4; }
  .hist-empty { text-align: center; color: var(--muted); font-size: 12px; padding: 40px 0; }
  .hist-turn { margin-bottom: 14px; }
  .hist-ts { font-size: 10px; color: var(--muted); margin-bottom: 3px; }
  .hist-user { background: rgba(var(--accent-rgb), .08); border-left: 3px solid var(--accent); border-radius: 6px;
    padding: 8px 11px; font-size: 13px; color: var(--text); white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; }
  .hist-asst { padding: 6px 2px 0; font-size: 12.5px; color: var(--sub); line-height: 1.55;
    white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; }
  .hist-tools { font-size: 10px; color: var(--muted); margin-top: 5px; }

  .dev-page.stream-mode .term-iframe-wrap {
    display: none;
  }
  /* 子账号桌面 hybrid:真终端(iframe)做显示(claude 自己管历史,滚动原生),
     底部输入框沿用 stream 模式全套样式(输入走后端、prompt 带账号) */
  .dev-page.stream-mode.sub-hybrid .term-iframe-wrap { display: block; }
  .dev-page.stream-mode.sub-hybrid .mobile-term-output,
  .dev-page.stream-mode.sub-hybrid .mobile-term-output.visible { display: none !important; }
  .dev-page.stream-mode .mobile-term-output.visible {
    display: block; flex: 1; min-height: 0;
    background: var(--bg); color: var(--text);
    font-family: var(--mono); font-size: 12px; line-height: 1.4;
    padding: 8px 10px 16px; margin: 0;
    overflow-x: hidden; overflow-y: auto;
    white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere;
  }
  .dev-page.stream-mode .mobile-input-bar {
    display: flex; flex-direction: column; flex-shrink: 0;
    padding: 0;
    border-top: 1px solid var(--border);
    background: var(--panel);
  }
  .dev-page.stream-mode .mobile-keys-row {
    display: flex; gap: 6px; align-items: center;
    padding: 8px 12px;
    overflow-x: auto;
    border-bottom: 1px solid rgba(255,255,255,.04);
  }
  .dev-page.stream-mode .mobile-input-row {
    display: flex; align-items: flex-end; gap: 8px;
    padding: 10px 12px 12px;
  }
  .dev-page.stream-mode .mobile-cmd-input {
    display: block; width: 100%; flex: 1;
    min-height: 64px; max-height: 220px;
    background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
    color: var(--text); font-family: var(--mono); font-size: 16px;
    padding: 9px 12px; outline: none; resize: none; line-height: 1.45;
    overflow-y: auto;
  }
  .dev-page.stream-mode .mobile-key-btn,
  .dev-page.stream-mode .mobile-num-sel,
  .dev-page.stream-mode .mobile-attach-btn,
  .dev-page.stream-mode .mobile-send-btn {
    flex-shrink: 0;
  }
  .dev-page.stream-mode .mobile-key-btn {
    background: rgba(255,255,255,.06); border: 1px solid var(--border);
    color: var(--sub); font-family: var(--mono); font-size: 12px;
    padding: 4px 10px; border-radius: 4px; cursor: pointer;
    white-space: nowrap; line-height: 1.2;
  }
  .dev-page.stream-mode .mobile-num-sel {
    background: rgba(255,255,255,.06); border: 1px solid var(--border);
    color: var(--sub); font-family: var(--mono); font-size: 12px;
    padding: 4px 6px; border-radius: 4px; appearance: none;
  }
  .dev-page.stream-mode .keys-sep {
    width: 1px; height: 16px; background: var(--border); flex-shrink: 0;
  }
  .dev-page.stream-mode .mobile-send-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 52px; align-self: stretch; border-radius: 8px; cursor: pointer;
    background: var(--accent); border: none; color: #fff; font-size: 20px;
  }

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
    background: rgba(0,0,0,.65);
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
  .new-term-loading {
    padding: 18px 20px; font-size: 11px; color: var(--muted);
  }
  .new-term-item-sep {
    height: 1px; background: var(--border); margin: 0 20px;
  }

  /* ── Mobile detail header (replaces topbar when a pane is open) ── */
  .term-detail-header { display: none; }
  .pane-switcher { display: none; }
  .term-switch-btn { display: none; }

  /* ── Mobile input bar (hidden on desktop) ── */
  .mobile-input-bar { display: none; }

  /* ── Mobile ── */
  /* ── 子账号模式:复用 dev 全套 UI,藏掉 owner 专属入口 ── */
  .sub-mode .term-new-btn,
  .sub-mode .term-edit-btn,
  .sub-mode .term-placeholder-btn,
  .sub-mode .topbar a.topbar-btn[href="/accounts"],
  .sub-mode .topbar a.topbar-btn[href="/deploy"] { display: none !important; }

  @media (max-width: 900px) {
    .term-detail-header { display: none !important; }
    .dev-page.detail-open { height: calc(var(--app-h, 100dvh) - 52px); }
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
    .term-pane-badge { margin-top: 4px; }
    .term-pane-name { font-size: 14px; }
    .term-pane-proj { font-size: 12px; margin-top: 3px; }
    .term-group-header { padding: 12px 16px; }
    .term-group-body .term-pane-row { padding-left: 28px; }
    .term-main { display: none; flex-direction: column; }
    .dev-page.detail-open .term-sidebar { display: none; }
    /* 手机进终端详情时,版本号 badge 跟着隐藏(badge 是 body 直接子元素、
       是 #dev-page 的兄弟,所以用 ~ 兄弟选择器,不能用后代选择器)。 */
    .dev-page.detail-open ~ .version-badge { display: none; }
    .dev-page.detail-open .term-main {
      display: flex; position: fixed; left: 0; right: 0; bottom: 0; top: 52px;
      height: calc(var(--app-h, 100dvh) - 52px); z-index: 90;
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
      background: var(--bg); color: var(--text);
      font-family: var(--mono); font-size: 11px; line-height: 1.35;
      padding: 4px 6px 40px; margin: 0;
      overflow-x: hidden; overflow-y: auto; -webkit-overflow-scrolling: touch;
      white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere;
      overscroll-behavior: contain;
      -webkit-text-size-adjust: none;
    }

    .term-sep {
      border: none; border-top: 1px solid rgba(255,255,255,.1);
      margin: 2px 0;
    }
    .term-link {
      color: var(--accent); text-decoration: underline;
      word-break: break-all;
    }
    .ws-dot {
      width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; cursor: pointer;
      transition: background .3s;
    }
    .ws-dot.ok { background: var(--green); }
    .ws-dot.err { background: var(--red); animation: ws-blink 1.5s ease-in-out infinite; }
    @keyframes ws-blink { 0%,100%{opacity:1} 50%{opacity:.4} }

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
    .mobile-key-btn.ok-btn { background: rgba(34,197,94,.15); border-color: rgba(34,197,94,.3); color: #22c55e; font-weight: 700; padding: 4px 14px; }
    .mobile-key-btn.ok-btn:active { background: rgba(34,197,94,.3); }
    .mobile-num-sel {
      background: rgba(255,255,255,.06); border: 1px solid var(--border);
      color: var(--sub); font-family: var(--mono); font-size: 11px;
      padding: 3px 4px; border-radius: 4px; flex-shrink: 0;
      -webkit-appearance: none; appearance: none; text-align: center; width: 42px;
    }
    .keys-sep { width: 1px; height: 16px; background: var(--border); flex-shrink: 0; margin: 0 2px; align-self: center; }
    /* Input row */
    .mobile-input-row {
      display: flex; align-items: flex-end; gap: 8px;
      padding: 8px 10px; padding-bottom: max(8px, env(safe-area-inset-bottom));
    }
    .mobile-cmd-input {
      flex: 1; min-height: 40px; max-height: 180px;
      background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
      color: var(--text); font-family: var(--mono); font-size: 16px;
      padding: 8px 12px; outline: none; resize: none;
      line-height: 1.4; overflow-y: auto;
    }
    .mobile-cmd-input:focus { border-color: var(--accent); }
    .mobile-cmd-input::placeholder { color: var(--muted); }
    /* 手机上输入框压到单行高;全局 stream-mode 规则的 64px 只留给桌面 */
    .dev-page.stream-mode .mobile-cmd-input { min-height: 40px; }
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
    /* ── Pane switcher (mobile detail header) ── */
    .term-switch-btn {
      background: none; border: 1px solid var(--border);
      border-radius: 6px; color: var(--sub); font-size: 16px;
      width: 32px; height: 32px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; -webkit-tap-highlight-color: transparent;
      transition: color .12s, border-color .12s;
    }
    .term-switch-btn:active { color: var(--accent); border-color: var(--accent); }
    .pane-switcher {
      display: none; flex-direction: column;
      background: var(--panel); border-bottom: 1px solid var(--border);
      max-height: 50vh; overflow-y: auto; -webkit-overflow-scrolling: touch;
      z-index: 210;
    }
    .pane-switcher.open { display: flex; }
    .pane-switcher-item {
      padding: 12px 16px; cursor: pointer;
      border-bottom: 1px solid rgba(255,255,255,.04);
      transition: background .1s;
      -webkit-tap-highlight-color: transparent;
    }
    .pane-switcher-item:active { background: rgba(var(--accent-rgb),.1); }
    .pane-switcher-item.current { background: rgba(var(--accent-rgb),.08); }
    .pane-switcher-name { font-size: 14px; font-weight: 600; color: var(--text); }
    .pane-switcher-sub { font-size: 11px; color: var(--sub); margin-top: 2px; }
    .pane-switcher-dot {
      display: inline-block; width: 6px; height: 6px; border-radius: 50%;
      margin-right: 6px; vertical-align: middle;
    }
    .mobile-attach-btn {
      display: flex; align-items: center; justify-content: center;
      width: 36px; height: 36px; flex-shrink: 0;
      background: none; border: 1px solid var(--border); border-radius: 8px;
      color: var(--sub); font-size: 18px; cursor: pointer;
      -webkit-tap-highlight-color: transparent;
      transition: color .12s, border-color .12s;
    }
    .mobile-attach-btn:active { color: var(--accent); border-color: var(--accent); }
  }

  /* ── Desktop term toolbar (above iframe) ── */
  .term-toolbar {
    display: none; align-items: center; gap: 8px;
    padding: 4px 12px; background: var(--bg);
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .term-toolbar.visible { display: flex; }
  .term-toolbar-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; background: none; border: 1px solid var(--border);
    border-radius: var(--radius-sm); color: var(--sub); cursor: pointer;
    transition: color .12s, border-color .12s;
  }
  .term-toolbar-btn svg { display: block; }
  .term-toolbar-btn:hover { color: var(--accent); border-color: var(--accent); }
  .desktop-ws-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
    background: var(--red); transition: background .2s;
  }
  .desktop-ws-dot.ok { background: var(--green); }
  .desktop-ws-dot.err { background: var(--red); animation: desktop-ws-blink 1.5s ease-in-out infinite; }
  @keyframes desktop-ws-blink { 0%,100%{opacity:1} 50%{opacity:.4} }
  .toolbar-spacer { flex: 1; }
  .toolbar-tokens {
    font-size: 11px; color: var(--sub); display: flex; align-items: center; gap: 12px;
    font-variant-numeric: tabular-nums; cursor: pointer; position: relative;
  }
  .toolbar-tokens:hover { color: var(--text); }
  .toolbar-tokens .tok-item { display: flex; align-items: center; gap: 2px; }
  .toolbar-tokens .tok-icon { font-size: 10px; color: var(--muted); }
  .toolbar-tokens .tok-up { color: #f59e0b; }
  .toolbar-tokens .tok-down { color: #3b82f6; }
  .toolbar-tokens .tok-val { font-weight: 600; }
  .toolbar-tokens .tok-cost { color: var(--purple); font-weight: 700; }
  .tok-badge { font-size: 9px; font-weight: 700; letter-spacing: .5px; padding: 1px 6px; border-radius: 3px; text-transform: uppercase; }
  .tok-badge.claude { background: rgba(129,140,248,.15); color: #818cf8; }
  .tok-badge.codex { background: rgba(34,197,94,.15); color: #22c55e; }
  .tok-warn { color: #f59e0b; font-size: 14px; cursor: help; animation: tok-pulse 2s ease-in-out infinite; margin-left: 2px; }
  .tok-ctx { font-weight: 700; color: var(--sub); cursor: help; }
  .tok-ctx.ctx-mid { color: var(--orange, #f59e0b); }
  .tok-ctx.ctx-hi { color: var(--red, #ef4444); }
  @keyframes tok-pulse { 0%,100%{opacity:1} 50%{opacity:.4} }

  .tok-dropdown { position: absolute; top: calc(100% + 8px); right: 0; z-index: 300;
    background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 12px 14px; min-width: 300px; max-width: 380px;
    box-shadow: 0 8px 24px rgba(0,0,0,.4); font-size: 12px; cursor: default; }
  .tok-dropdown-title { font-size: 11px; color: var(--sub); margin-bottom: 10px;
    display: flex; justify-content: space-between; align-items: center; }
  .tok-dropdown-row { display: grid; grid-template-columns: 90px 1fr 52px; align-items: center;
    gap: 8px; margin-bottom: 6px; }
  .tok-dropdown-name { font-size: 11px; color: var(--text); overflow: hidden;
    text-overflow: ellipsis; white-space: nowrap; }
  .tok-dropdown-bar { height: 6px; background: rgba(255,255,255,.06); border-radius: 3px; overflow: hidden; display: flex; }
  .tok-dropdown-bar > div { height: 100%; }
  .tok-dropdown-cost { font-size: 11px; color: var(--sub); text-align: right;
    font-family: var(--mono); white-space: nowrap; }
  .tok-dropdown-total { font-size: 11px; color: var(--sub); text-align: right; margin-top: 8px;
    padding-top: 6px; border-top: 1px solid var(--border); }
  .tok-dropdown-legend { display: flex; gap: 10px; margin-top: 6px; font-size: 10px; color: var(--sub); }
  .tok-dropdown-legend span { display: flex; align-items: center; gap: 3px; }
  .tok-dropdown-dot { width: 6px; height: 6px; border-radius: 50%; }
  .toolbar-usage {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: 11px; font-variant-numeric: tabular-nums;
  }
  .mobile-token-bar { display: none; }
  @media (max-width: 900px) {
    .term-toolbar { display: none !important; }
    .mobile-token-bar {
      display: none; padding: 6px 12px;
      font-size: 11px; color: var(--sub); background: var(--panel);
      border-bottom: 1px solid var(--border);
      font-variant-numeric: tabular-nums;
      flex-shrink: 0;
    }
    .mobile-token-bar.visible { display: flex; gap: 12px; align-items: center; cursor: pointer; position: relative; }
    .mobile-token-bar .tok-item { display: flex; align-items: center; gap: 2px; }
    .mobile-token-bar .tok-icon { font-size: 10px; color: var(--muted); }
    .mobile-token-bar .tok-val { font-weight: 600; }
    .mobile-token-bar .tok-cost { color: var(--purple); font-weight: 700; }
    .mobile-token-bar .tok-badge { font-size: 9px; font-weight: 700; letter-spacing: .5px; padding: 1px 6px; border-radius: 3px; text-transform: uppercase; }
    .mobile-token-bar .tok-badge.claude { background: rgba(129,140,248,.15); color: #818cf8; }
    .mobile-token-bar .tok-badge.codex { background: rgba(34,197,94,.15); color: #22c55e; }
  }

  /* ── Toast notification ── */
  #dev-toast {
    position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%);
    background: var(--panel); border: 1px solid var(--border);
    color: var(--text); font-family: var(--mono); font-size: 12px;
    padding: 8px 16px; border-radius: 8px; z-index: 600;
    opacity: 0; pointer-events: none; transition: opacity .25s;
    white-space: nowrap; max-width: 90vw; overflow: hidden; text-overflow: ellipsis;
    box-shadow: 0 4px 16px rgba(0,0,0,.3);
  }
  #dev-toast.show { opacity: 1; pointer-events: auto; }

  /* ── Safari-style tab switcher (mobile only) ── */
  .tab-switcher {
    position: fixed; inset: 0; z-index: 300;
    background: rgba(0,0,0,.88);
    /* backdrop-filter removed for perf */
    overflow-y: auto; -webkit-overflow-scrolling: touch;
    padding: 60px 12px 40px;
    display: none; opacity: 0;
    transition: opacity .25s;
  }
  .tab-switcher.open { display: block; }
  .tab-switcher.visible { opacity: 1; }
  .tab-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
  }
  .tab-card {
    position: relative;
    border-radius: 10px;
    background: var(--bg);
    border: 1px solid rgba(255,255,255,.1);
    overflow: hidden;
    transform-origin: center bottom;
    transform: perspective(800px) rotateX(1.5deg);
    transition: transform .35s ease, opacity .3s;
    box-shadow: 0 4px 16px rgba(0,0,0,.5);
    opacity: 0;
  }
  .tab-card.active { border-color: var(--accent); box-shadow: 0 4px 16px rgba(0,0,0,.5), 0 0 0 1px var(--accent); }
  .tab-card.focused { border-color: rgba(129,140,248,.4); background: rgba(var(--accent-rgb),.06); }
  .tab-card.focused .tab-card-header { background: rgba(var(--accent-rgb),.08); }
  .tab-card.focused .tab-card-name { color: var(--accent); font-weight: 700; }
  .tab-card.show { opacity: 1; }
  .tab-card-header {
    display: flex; align-items: center; gap: 5px;
    padding: 6px 8px;
    background: var(--panel);
    border-bottom: 1px solid rgba(255,255,255,.06);
    font-size: 10px; font-weight: 600; color: var(--text);
  }
  .tab-card-dot {
    width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  }
  .tab-card-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tab-card-close {
    width: 18px; height: 18px; flex-shrink: 0;
    background: none; border: none; color: var(--muted);
    cursor: pointer; font-size: 14px; line-height: 1;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%; transition: background .15s, color .15s;
  }
  .tab-card-close:active { background: rgba(255,255,255,.1); color: var(--red); }
  .tab-card-preview {
    height: 120px; overflow: hidden; position: relative;
    font-family: var(--mono); font-size: 10px; line-height: 1.35;
    color: var(--text); padding: 6px 8px;
    pointer-events: none; user-select: none;
    white-space: pre-wrap; word-break: break-word;
  }
  .tab-card-preview::after {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 40px;
    background: linear-gradient(transparent, var(--bg));
    pointer-events: none;
  }
  .tab-card-empty {
    height: 120px; display: flex; align-items: center; justify-content: center;
    color: var(--muted); font-size: 10px;
  }
  /* pixel-cyber skin */
  [data-theme="pixel-cyber"] .tab-card { border-color: rgba(0,212,255,.2); box-shadow: 0 4px 20px rgba(0,8,20,.6), 0 0 12px rgba(0,212,255,.08); }
  [data-theme="pixel-cyber"] .tab-card.active { border-color: #00d4ff; box-shadow: 0 4px 20px rgba(0,8,20,.6), 0 0 16px rgba(0,212,255,.25); }
  [data-theme="pixel-cyber"] .tab-switcher { background: rgba(0,8,20,.92); }
  /* neon-pixel skin */
  [data-theme="neon-pixel"] .tab-card { border-color: rgba(0,255,0,.15); }
  [data-theme="neon-pixel"] .tab-card.active { border-color: #ff00ff; box-shadow: 0 0 16px rgba(255,0,255,.2); }

  /* ── Upload confirm popup (desktop) ── */
  .upload-confirm {
    position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%);
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px 24px; z-index: 500;
    box-shadow: 0 8px 32px rgba(0,0,0,.4); min-width: 300px;
    font-family: var(--mono);
  }
  .upload-confirm-title { font-size: 14px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
  .upload-confirm-path {
    font-size: 12px; color: var(--green); background: rgba(255,255,255,.04);
    padding: 6px 10px; border-radius: 6px; word-break: break-all; margin-bottom: 14px;
  }
  .upload-confirm-btns { display: flex; gap: 8px; justify-content: flex-end; }
  .upload-confirm-btns button {
    background: none; border: 1px solid var(--border); color: var(--sub);
    padding: 6px 14px; border-radius: 6px; cursor: pointer;
    font-size: 12px; font-family: var(--mono); transition: all .12s;
  }
  .upload-confirm-btns button:hover { border-color: var(--accent); color: var(--accent); }
  .upload-confirm-btns button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .upload-confirm-overlay {
    position: fixed; inset: 0; z-index: 499;
    background: rgba(0,0,0,.5);
  }

  /* ── Prompt line highlight (Phase 3) ── */
  .term-line-prompt { background: rgba(var(--accent-rgb), 0.04); display: block; }

  /* ── Skin-specific overrides ── */

  /* claude-light: rgba(255,255,255,x) overlays are invisible on light bg */
  [data-theme="claude-light"] .term-pane-row:hover { background: rgba(0,0,0,.04); }
  [data-theme="claude-light"] .term-group-header:hover { background: rgba(0,0,0,.03); }
  [data-theme="claude-light"] .term-group-header { border-bottom-color: rgba(0,0,0,.06); }
  [data-theme="claude-light"] .term-group-count { background: rgba(0,0,0,.07); }
  [data-theme="claude-light"] .mobile-key-btn { background: rgba(0,0,0,.06); }
  [data-theme="claude-light"] .new-term-overlay { background: rgba(0,0,0,.45); }
  [data-theme="claude-light"] .new-term-dialog { box-shadow: 0 8px 32px rgba(0,0,0,.15); }
  [data-theme="claude-light"] .new-term-dialog-close:hover { background: rgba(0,0,0,.06); }
  [data-theme="claude-light"] .term-pane-kill:hover { background: rgba(220,38,38,.1); }
  [data-theme="claude-light"] .term-sidebar-header { color: var(--accent); border-bottom: 1px solid rgba(0,0,0,.08); }
  [data-theme="claude-light"] .term-group-name { color: var(--accent); }

  /* ── neon-pixel: 霓虹发光 + CRT 扫描线 ── */
  [data-theme="neon-pixel"] .term-sidebar {
    border-right: 1px solid #00ff00;
    box-shadow: 2px 0 16px rgba(0,255,0,.15), inset -1px 0 0 rgba(0,255,0,.3);
  }
  [data-theme="neon-pixel"] .term-sidebar-header {
    border-bottom: 1px solid rgba(0,255,0,.4);
    box-shadow: 0 1px 10px rgba(0,255,0,.15);
    color: #00ff00;
    letter-spacing: 2px;
    text-shadow: 0 0 8px rgba(0,255,0,.8);
  }
  [data-theme="neon-pixel"] .term-group-header {
    border-bottom: 1px solid rgba(0,255,0,.12);
  }
  [data-theme="neon-pixel"] .term-group-name {
    color: rgba(0,255,0,.8);
    letter-spacing: .5px;
  }
  [data-theme="neon-pixel"] .term-group-arrow { color: rgba(0,255,0,.5); }
  [data-theme="neon-pixel"] .term-pane-badge.claude { box-shadow: 0 0 5px rgba(129,140,248,.4); }
  [data-theme="neon-pixel"] .term-pane-badge.codex  { box-shadow: 0 0 5px rgba(34,197,94,.4); }
  [data-theme="neon-pixel"] .term-pane-row.active {
    background: rgba(255,0,255,.1);
    border-left-color: #ff00ff;
    box-shadow: inset 3px 0 12px rgba(255,0,255,.3);
  }
  [data-theme="neon-pixel"] .term-pane-row.active .term-pane-name-text {
    color: #ff00ff;
    text-shadow: 0 0 8px rgba(255,0,255,.8);
  }
  [data-theme="neon-pixel"] .term-pane-row:hover { background: rgba(255,0,255,.05); }
  [data-theme="neon-pixel"] .term-toolbar {
    border-bottom: 1px solid rgba(0,255,0,.2);
    box-shadow: 0 2px 8px rgba(0,255,0,.08);
    background: rgba(10,10,10,.98);
  }
  /* CRT 扫描线 */
  [data-theme="neon-pixel"] .term-iframe-wrap::after {
    content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 2;
    background: repeating-linear-gradient(
      0deg, transparent, transparent 3px,
      rgba(0,255,0,.025) 3px, rgba(0,255,0,.025) 4px
    );
  }
  [data-theme="neon-pixel"] #ttyd-frame { background: #0a0a0a; }
  [data-theme="neon-pixel"] .term-group-count { background: rgba(255,0,255,.15); color: #ff00ff; border: 1px solid rgba(255,0,255,.3); }
  [data-theme="neon-pixel"] .term-host-badge { border: 1px solid var(--accent); }

  /* ── pixel-cyber: 赛博朋克青色 + 红色激活 ── */
  [data-theme="pixel-cyber"] .term-sidebar {
    border-right: 1px solid rgba(0,212,255,.5);
    box-shadow: 2px 0 24px rgba(0,212,255,.2), inset -1px 0 0 rgba(0,212,255,.35);
    /* 侧边栏内部微弱网格 */
    background-image: linear-gradient(rgba(0,212,255,.025) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(0,212,255,.025) 1px, transparent 1px);
    background-size: 12px 12px;
  }
  [data-theme="pixel-cyber"] .term-sidebar-header {
    border-bottom: 1px solid rgba(0,212,255,.4);
    box-shadow: 0 1px 12px rgba(0,212,255,.2);
    color: #00d4ff;
    letter-spacing: 2px;
    text-shadow: 0 0 10px rgba(0,212,255,.7);
  }
  [data-theme="pixel-cyber"] .term-group-header {
    border-bottom: 1px solid rgba(0,212,255,.1);
  }
  [data-theme="pixel-cyber"] .term-group-name {
    color: rgba(0,212,255,.75);
    letter-spacing: .5px;
  }
  [data-theme="pixel-cyber"] .term-group-arrow { color: rgba(0,212,255,.45); }
  [data-theme="pixel-cyber"] .term-pane-badge.claude { box-shadow: 0 0 5px rgba(129,140,248,.4); }
  [data-theme="pixel-cyber"] .term-pane-badge.codex  { box-shadow: 0 0 5px rgba(34,197,94,.4); }
  /* 激活 pane：红色边框 + 青色内阴影 */
  [data-theme="pixel-cyber"] .term-pane-row.active {
    background: rgba(255,0,85,.09);
    border-left: 2px solid #ff0055;
    box-shadow: inset 4px 0 16px rgba(0,212,255,.15), inset 0 0 30px rgba(255,0,85,.04);
  }
  [data-theme="pixel-cyber"] .term-pane-row.active .term-pane-name-text {
    color: #ff0055;
    text-shadow: 0 0 8px rgba(255,0,85,.8);
  }
  [data-theme="pixel-cyber"] .term-pane-row:hover { background: rgba(0,212,255,.05); }
  [data-theme="pixel-cyber"] .term-toolbar {
    border-bottom: 1px solid rgba(0,212,255,.25);
    border-top: 1px solid rgba(0,212,255,.5);
    box-shadow: 0 2px 10px rgba(0,212,255,.12), 0 -1px 12px rgba(0,212,255,.2);
    background: rgba(2,12,26,.98);
  }
  /* 全局方格底纹 */
  [data-theme="pixel-cyber"] body {
    background-image:
      linear-gradient(rgba(0,212,255,.12) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,255,.12) 1px, transparent 1px);
    background-size: 24px 24px;
  }
  /* CRT 扫描线叠在格子上 */
  [data-theme="pixel-cyber"] .term-iframe-wrap::after {
    content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 2;
    background:
      repeating-linear-gradient(
        0deg, transparent, transparent 3px,
        rgba(0,212,255,.028) 3px, rgba(0,212,255,.028) 4px
      );
  }
  [data-theme="pixel-cyber"] #ttyd-frame { background: #020c1a; }
  [data-theme="pixel-cyber"] .term-group-count {
    background: rgba(0,212,255,.12); color: #00d4ff;
    border: 1px solid rgba(0,212,255,.3);
  }
  [data-theme="pixel-cyber"] .term-host-badge { border: 1px solid rgba(0,212,255,.5); color: #00d4ff; }
  /* placeholder 区域赛博风格 */
  [data-theme="pixel-cyber"] .term-placeholder {
    background: radial-gradient(ellipse at center, rgba(0,212,255,.06) 0%, transparent 65%);
  }
  [data-theme="pixel-cyber"] .term-placeholder-btn {
    border-color: rgba(0,212,255,.4);
    color: #00d4ff;
    text-shadow: 0 0 8px rgba(0,212,255,.5);
    box-shadow: 0 0 12px rgba(0,212,255,.15), inset 0 0 8px rgba(0,212,255,.05);
  }
  [data-theme="pixel-cyber"] .term-placeholder-btn:hover {
    border-color: #00d4ff;
    box-shadow: 0 0 20px rgba(0,212,255,.35), inset 0 0 12px rgba(0,212,255,.1);
  }
  /* 激活 pane 名称：打字机光标闪烁 */
  [data-theme="pixel-cyber"] .term-pane-row.active .term-pane-name-text::after {
    content: '_';
    animation: cyber-blink .8s step-end infinite;
    color: #ff0055;
    margin-left: 1px;
  }
  @keyframes cyber-blink { 0%,100%{opacity:1} 50%{opacity:0} }
  /* 侧边栏顶部发光条 */
  [data-theme="pixel-cyber"] .term-sidebar::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, #00d4ff, #ff0055, #00d4ff, transparent);
    box-shadow: 0 0 8px rgba(0,212,255,.6);
    z-index: 1;
  }
  [data-theme="pixel-cyber"] .term-placeholder-btn:hover {
    border-color: #ff0055;
    color: #ff0055;
    text-shadow: 0 0 8px rgba(255,0,85,.6);
    box-shadow: 0 0 16px rgba(255,0,85,.2);
  }
  /* ── pixel-cyber 移动版样式 ── */
  [data-theme="pixel-cyber"] .term-detail-header {
    background: rgba(2,12,26,.98);
    border-bottom: 1px solid rgba(0,212,255,.3);
    box-shadow: 0 1px 12px rgba(0,212,255,.15);
  }
  [data-theme="pixel-cyber"] .term-detail-back,
  [data-theme="pixel-cyber"] .term-switch-btn {
    border-color: rgba(0,212,255,.35);
    color: #00d4ff;
  }
  [data-theme="pixel-cyber"] .term-detail-title { color: #00d4ff; text-shadow: 0 0 8px rgba(0,212,255,.5); }
  [data-theme="pixel-cyber"] .pane-switcher {
    background: rgba(2,12,26,.98);
    border-bottom: 1px solid rgba(0,212,255,.25);
  }
  [data-theme="pixel-cyber"] .pane-switcher-item { border-bottom-color: rgba(0,212,255,.1); }
  [data-theme="pixel-cyber"] .pane-switcher-item.current { background: rgba(0,212,255,.08); }
  [data-theme="pixel-cyber"] .pane-switcher-name { color: #00d4ff; }
  [data-theme="pixel-cyber"] .mobile-term-output.visible {
    background: #020c1a;
    color: #eef8ff;
  }
  [data-theme="pixel-cyber"] .mobile-input-bar {
    background: rgba(2,12,26,.98);
    border-top: 1px solid rgba(0,212,255,.3);
    box-shadow: 0 -1px 12px rgba(0,212,255,.12);
  }
  [data-theme="pixel-cyber"] .mobile-keys-row { border-bottom-color: rgba(0,212,255,.12); }
  [data-theme="pixel-cyber"] .mobile-key-btn {
    background: rgba(0,212,255,.06);
    border-color: rgba(0,212,255,.25);
    color: #00d4ff;
  }
  [data-theme="pixel-cyber"] .mobile-key-btn:active {
    background: rgba(0,212,255,.2);
    border-color: #00d4ff;
  }
  [data-theme="pixel-cyber"] .mobile-cmd-input {
    background: rgba(0,212,255,.04);
    border-color: rgba(0,212,255,.3);
    color: #e0f7ff;
  }
  [data-theme="pixel-cyber"] .mobile-cmd-input:focus { border-color: #00d4ff; box-shadow: 0 0 8px rgba(0,212,255,.2); }
  [data-theme="pixel-cyber"] .mobile-send-btn { background: #00d4ff; color: #020c1a; }
  [data-theme="pixel-cyber"] .mobile-attach-btn { border-color: rgba(0,212,255,.3); color: #00d4ff; }

  /* ── dyson: 深空 HUD + 青色发光 + 琥珀能量 + 扫描线 ── */
  [data-theme="dyson"] .term-sidebar {
    border-right: 1px solid rgba(56,230,255,.22);
    box-shadow: 2px 0 24px rgba(56,230,255,.12), inset -1px 0 0 rgba(56,230,255,.25);
  }
  [data-theme="dyson"] .term-sidebar::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, #38e6ff, #ffb627, #38e6ff, transparent);
    box-shadow: 0 0 8px rgba(56,230,255,.6); z-index: 1;
  }
  [data-theme="dyson"] .term-sidebar-header {
    border-bottom: 1px solid rgba(56,230,255,.25);
    color: #7df9ff; letter-spacing: 2px; text-transform: uppercase;
    text-shadow: 0 0 10px rgba(56,230,255,.5);
    font-family: 'Chakra Petch', var(--mono);
  }
  [data-theme="dyson"] .term-group-name { color: rgba(174,188,212,.95); letter-spacing: .5px; font-size: 12.5px; }
  [data-theme="dyson"] .term-group-arrow { color: rgba(56,230,255,.5); }
  [data-theme="dyson"] .term-pane-badge.claude { box-shadow: 0 0 8px rgba(56,230,255,.45); }
  [data-theme="dyson"] .term-pane-badge.codex  { box-shadow: 0 0 8px rgba(45,224,166,.4); }
  [data-theme="dyson"] .term-pane-row.active {
    background: rgba(56,230,255,.08);
    border-left-color: #38e6ff;
    box-shadow: inset 3px 0 14px rgba(56,230,255,.22);
  }
  [data-theme="dyson"] .term-pane-row.active .term-pane-name-text {
    color: #7df9ff; text-shadow: 0 0 8px rgba(56,230,255,.6);
  }
  [data-theme="dyson"] .term-pane-row:hover { background: rgba(56,230,255,.045); }
  [data-theme="dyson"] .term-toolbar {
    border-bottom: 1px solid rgba(56,230,255,.18);
    box-shadow: 0 2px 12px rgba(56,230,255,.07);
    background: rgba(10,15,28,.96);
  }
  [data-theme="dyson"] .term-iframe-wrap::after {
    content: ''; position: absolute; inset: 0; pointer-events: none; z-index: 2;
    background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(56,230,255,.02) 2px, rgba(56,230,255,.02) 3px);
  }
  [data-theme="dyson"] #ttyd-frame { background: #070b15; }
  [data-theme="dyson"] .term-group-count { background: rgba(56,230,255,.12); color: #7df9ff; border: 1px solid rgba(56,230,255,.3); }
  [data-theme="dyson"] .term-host-badge { border: 1px solid rgba(56,230,255,.5); color: #7df9ff; }
  [data-theme="dyson"] .term-placeholder {
    background: radial-gradient(ellipse at center, rgba(56,230,255,.06) 0%, transparent 65%);
  }
  [data-theme="dyson"] .term-placeholder-btn {
    border-color: rgba(56,230,255,.4); color: #7df9ff;
    text-shadow: 0 0 8px rgba(56,230,255,.5);
    box-shadow: 0 0 12px rgba(56,230,255,.15), inset 0 0 8px rgba(56,230,255,.05);
  }
  [data-theme="dyson"] .term-placeholder-btn:hover {
    border-color: #38e6ff;
    box-shadow: 0 0 20px rgba(56,230,255,.35), inset 0 0 12px rgba(56,230,255,.1);
  }
  [data-theme="dyson"] .term-detail-header {
    background: rgba(10,15,28,.98); border-bottom: 1px solid rgba(56,230,255,.25);
    box-shadow: 0 1px 12px rgba(56,230,255,.12);
  }
  [data-theme="dyson"] .term-detail-back,
  [data-theme="dyson"] .term-switch-btn { border-color: rgba(56,230,255,.35); color: #7df9ff; }
  [data-theme="dyson"] .term-detail-title { color: #7df9ff; text-shadow: 0 0 8px rgba(56,230,255,.5); }
  [data-theme="dyson"] .mobile-term-output.visible { background: #070b15; color: #eaf2ff; }
  [data-theme="dyson"] .mobile-input-bar {
    background: rgba(10,15,28,.98); border-top: 1px solid rgba(56,230,255,.25);
    box-shadow: 0 -1px 12px rgba(56,230,255,.1);
  }
  [data-theme="dyson"] .mobile-key-btn {
    background: rgba(56,230,255,.06); border-color: rgba(56,230,255,.25); color: #7df9ff;
  }
  [data-theme="dyson"] .mobile-key-btn:active { background: rgba(56,230,255,.2); border-color: #38e6ff; }
  [data-theme="dyson"] .mobile-cmd-input {
    background: rgba(56,230,255,.04); border-color: rgba(56,230,255,.3); color: #eaf2ff;
  }
  [data-theme="dyson"] .mobile-cmd-input:focus { border-color: #38e6ff; box-shadow: 0 0 8px rgba(56,230,255,.25); }
  [data-theme="dyson"] .mobile-send-btn { background: #38e6ff; color: #070b15; }
  [data-theme="dyson"] .mobile-attach-btn { border-color: rgba(56,230,255,.3); color: #7df9ff; }
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
        // Keep terminal output scrolled to bottom when keyboard changes
        var output = document.getElementById('mobile-term-output');
        if (output) output.scrollTop = output.scrollHeight;
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
  _clearDropUI();
  const items = [...document.querySelectorAll('#term-pane-list > .term-toplevel')];
  if (!items.length) { _drag.target = null; return; }
  let target = null;
  for (const it of items) {
    const r = it.getBoundingClientRect();
    if (y < r.top || y > r.bottom) continue;
    const hdr = it.querySelector('[data-drop-key]');
    const hr = hdr.getBoundingClientRect();
    const overHeader = y >= hr.top && y <= hr.bottom;
    // 合并:源是项目、悬在另一项头部中段、不是自己
    if (overHeader && _drag.type === 'project' && hdr.dataset.dropKey !== _drag.key) {
      const hrel = (y - hr.top) / hr.height;
      if (hrel > 0.28 && hrel < 0.72) {
        target = { mode: 'merge', key: hdr.dataset.dropKey, dropType: hdr.dataset.dropType };
        hdr.classList.add('drag-over');
        break;
      }
    }
    // 否则:排序,插到该项前/后
    const before = (y - r.top) / r.height < 0.5;
    target = { mode: 'reorder', beforeKey: before ? it.dataset.key : _nextKey(items, it) };
    _showDropLine(it, before);
    break;
  }
  if (!target) {
    const last = items[items.length - 1];
    if (y > last.getBoundingClientRect().bottom) { target = { mode: 'reorder', beforeKey: null }; _showDropLine(last, false); }
  }
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

  // Update title with project name (from group header, not pane label)
  const activeRow = document.querySelector(`.term-pane-row[data-target="${CSS.escape(target)}"], .term-single[data-target="${CSS.escape(target)}"]`);
  const titleEl = document.getElementById('term-detail-title');
  const pageTitle = document.querySelector('.topbar-page-title');
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
    if (pageTitle && _isMobile) pageTitle.textContent = name;
    // 桌面:在 logo「DEV」后显示当前项目名(移动端 page-title 本身已替换为项目名,不重复)
    var projName = document.getElementById('topbar-project-name');
    if (projName) projName.textContent = _isMobile ? '' : ' · ' + name;
  }

  if (!_isMobile && !_currentIsRemote) {
    // Fire-and-forget: don't block UI on tmux focus switch
    fetch('/api/terminal/focus', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify({ target })
    }).catch(function() {});
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

function _resizeTtydFrame() {
  var frame = document.getElementById('ttyd-frame');
  if (!frame || !frame.contentWindow) return;
  try { frame.contentWindow.postMessage({ type: 'mira-resize' }, '*'); } catch(_) {}
  try { frame.contentWindow.dispatchEvent(new Event('resize')); } catch(_) {}
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
        '<div style="height:6px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden"><div style="height:100%;width:'+(it.cost/maxCost*100).toFixed(1)+'%;background:var(--accent);border-radius:3px;opacity:.7"></div></div>' +
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

async function _copyTmuxBuffer() {
  try {
    const res = await fetch('/api/terminal/buffer', { headers: _authHeaders() });
    if (!res.ok) return;
    const { text } = await res.json();
    if (!text) return;
    // Try modern clipboard API first, fall back to execCommand
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try { await navigator.clipboard.writeText(text); _showToast('已复制 ' + text.length + ' 字符', 1500); return; } catch(e) {}
    }
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    _showToast('已复制 ' + text.length + ' 字符', 1500);
  } catch(e) { console.warn('copy buffer:', e); }
}

function showTerminal() {
  document.getElementById('term-placeholder').style.display = 'none';
  // Show desktop toolbar
  var toolbar = document.getElementById('term-toolbar');
  if (toolbar) toolbar.classList.add('visible');
  var devPage = document.getElementById('dev-page');

  // owner 桌面若开了"输入框模式"配置,也走 stream(流式输出 + 本地输入框,一次输入很多不卡)
  if (_isMobile || _currentIsRemote || localStorage.getItem('mira-input-box-mode')) {
    if (devPage) devPage.classList.add('stream-mode');
    document.getElementById('ttyd-frame').classList.remove('visible');
    document.getElementById('mobile-term-output').classList.add('visible');
    document.getElementById('mobile-token-bar').classList.add('visible');
    document.getElementById('mobile-input-bar').style.display = 'flex';
    _startBufferPoll();
    if (_currentTarget) _connectTermWs(_currentTarget);
    _focusInputBox();   // 桌面:切进来直接能敲字,不用先点输入框
    return;
  }

  if (devPage) { devPage.classList.remove('stream-mode'); devPage.classList.remove('sub-hybrid'); }
  _disconnectTermWs();
  document.getElementById('mobile-term-output').classList.remove('visible');
  document.getElementById('mobile-token-bar').classList.remove('visible');
  document.getElementById('mobile-input-bar').style.display = '';
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
      _applyTtydTheme();
    });
  }
  frame.classList.add('visible');
  requestAnimationFrame(function() {
    _resizeTtydFrame();
    setTimeout(_resizeTtydFrame, 80);
    setTimeout(_resizeTtydFrame, 250);
  });
  _startBufferPoll();
}

function showPlaceholder() {
  _stopBufferPoll();
  document.getElementById('dev-page').classList.remove('stream-mode');
  document.getElementById('dev-page').classList.remove('sub-hybrid');
  document.getElementById('ttyd-frame').classList.remove('visible');
  document.getElementById('mobile-term-output').classList.remove('visible');
  document.getElementById('mobile-token-bar').classList.remove('visible');
  document.getElementById('mobile-input-bar').style.display = '';
  var toolbar = document.getElementById('term-toolbar');
  if (toolbar) toolbar.classList.remove('visible');
  var switcher = document.getElementById('pane-switcher');
  if (switcher) switcher.classList.remove('open');
  _disconnectTermWs();
  try { localStorage.removeItem('mira-dev-target'); } catch(e) {}  // 主动回列表 → 清掉恢复记录
  _currentIsRemote = false;
  if (_tokenRefreshTimer) { clearInterval(_tokenRefreshTimer); _tokenRefreshTimer = null; }
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
  'Esc':    '\x1b',
  'Up':     '\x1b[A',
  'Down':   '\x1b[B',
};

// ── ANSI-to-HTML converter (supports 16/256/truecolor + bold) ────────────────
var _ANSI16 = [
  'var(--ansi-0)','var(--ansi-1)','var(--ansi-2)','var(--ansi-3)',
  'var(--ansi-4)','var(--ansi-5)','var(--ansi-6)','var(--ansi-7)',
  'var(--ansi-8)','var(--ansi-9)','var(--ansi-10)','var(--ansi-11)',
  'var(--ansi-12)','var(--ansi-13)','var(--ansi-14)','var(--ansi-15)'
];
var _isLightTheme = function() { return document.documentElement.dataset.theme === 'claude-light'; };
function _adaptRgb(r, g, b, hasBg) {
  // Don't adjust foreground when there's an explicit background — the bg provides contrast
  if (hasBg) return 'rgb('+r+','+g+','+b+')';
  var lum = (0.299*r + 0.587*g + 0.114*b) / 255;
  if (_isLightTheme()) {
    if (lum > 0.82) { var f = 0.25; return 'rgb('+Math.round(r*f)+','+Math.round(g*f)+','+Math.round(b*f)+')'; }
  } else {
    if (lum < 0.12) { return 'rgb('+Math.round(r+(255-r)*0.7)+','+Math.round(g+(255-g)*0.7)+','+Math.round(b+(255-b)*0.7)+')'; }
  }
  return 'rgb('+r+','+g+','+b+')';
}
function _ansi256(n, hasBg) {
  if (n < 16) return _ANSI16[n];
  if (n >= 232) { var g = (n - 232) * 10 + 8; return _adaptRgb(g, g, g, hasBg); }
  n -= 16;
  return _adaptRgb(Math.floor(n/36)*51, Math.floor((n%36)/6)*51, (n%6)*51, hasBg);
}
function _stripAnsi(text) { return text.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, ''); }
function _ansiToHtml(raw, noChrome) {
  // noChrome=true:用于 scrollback 片段 —— 只是滚出屏幕的 transcript,没有底部
  // 输入框/状态栏,跳过 2.8 的 chrome 剥离(否则片段里出现 ❯ 行会被误剥周边内容)。
  // 1. Strip non-SGR escape sequences FIRST (so they don't interfere with blank-line detection)
  var text = raw.replace(/\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g, ''); // OSC
  text = text.replace(/\x1b\[[\?]?[0-9;]*[A-LN-Za-ln-z]/g, '');    // CSI non-SGR
  // 2. Strip trailing whitespace per line (tmux pads to full terminal width)
  //    Also drop lines that are purely box-drawing chars (tmux borders / status separators)
  text = text.split('\n').map(function(l) {
    l = l.replace(/[\s\x1b]+$/, '');
    var plain = l.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '').trim();
    if (plain.length > 4 && /^[\u2500-\u257F]+$/.test(plain)) return '\x00HR\x00';
    return l;
  }).join('\n');
  // 2.5. Extract and rejoin URLs split across lines by terminal wrapping.
  //      Scan raw text char by char: when we hit "https://", collect all URL-safe
  //      chars while skipping newlines, spaces, and SGR escape codes.
  var _out = '', _i = 0;
  while (_i < text.length) {
    var _hi = text.indexOf('https://', _i);
    if (_hi === -1) { _out += text.slice(_i); break; }
    _out += text.slice(_i, _hi);
    // Scan forward collecting URL chars, skipping \n, \r, spaces, SGR codes
    var _url = '', _j = _hi, _blanks = 0;
    while (_j < text.length) {
      var _ch = text[_j];
      if (_ch === '\x1b' && text[_j+1] === '[') {
        // skip SGR sequence
        var _m = text.indexOf('m', _j + 2);
        if (_m !== -1) { _j = _m + 1; continue; }
      }
      if (_ch === '\n' || _ch === '\r') { _blanks++; _j++; if (_blanks > 3) break; continue; }
      if (_ch === ' ' || _ch === '\t') { _j++; continue; }
      // URL-safe characters
      if (/[A-Za-z0-9%&=?_\-+.\/;:@~#!$'()*,]/.test(_ch)) {
        _url += _ch; _blanks = 0; _j++;
      } else { break; }
    }
    _out += _url;
    _i = _j;
  }
  text = _out;
  // 2.8. Strip Claude Code status bar and ASCII pet.
  //      Layout from bottom: empty, ⏵⏵ status, ───border, ❯ prompt, ───border, pet art, n____n
  //      Strategy: find ❯ prompt, remove junk below AND above it, keep ❯.
  if (!noChrome) {
  var _lines = text.split('\n');
  function _isJunk(line) {
    var r = line.replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');
    var p = r.trim();
    if (!p) return true;
    if ((r.match(/\u2500/g) || []).length > 10) return true;
    if (/bypass permissions|shift\+tab|esc to interrupt|to manage/i.test(p)) return true;
    if (/^[⏵⏴►▶]/.test(p)) return true;
    if (p.length < 40 && /^[\s|_n\/\\(){}\[\]×·├┤┬┴┼\u2800-\u28FF\-.]+$/.test(p)) return true;
    if (p.length < 30 && /^[A-Z][a-z]+(-[A-Z][a-z]+)?$/.test(p)) return true;
    return false;
  }
  // Find last ❯ prompt in bottom 30 lines
  var _promptIdx = -1;
  for (var _k = _lines.length - 1; _k >= 0 && _k >= _lines.length - 30; _k--) {
    var _pl = _lines[_k].replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '').trim();
    if (/^❯/.test(_pl)) { _promptIdx = _k; break; }
  }
  if (_promptIdx >= 0) {
    // Trim pet art from ❯ line: strip ANSI, find ❯ + user input, discard trailing junk
    var _rawPrompt = _lines[_promptIdx].replace(/\x1b\[[0-9;]*[a-zA-Z]/g, '');
    var _pm = _rawPrompt.match(/^(❯[^|_\n]*?)\s{5,}/);
    var _promptLine = _pm ? _pm[1].trimEnd() : _rawPrompt.replace(/\s{10,}.*$/, '').trimEnd();
    // Remove junk below ❯
    var _below = _promptIdx + 1;
    while (_below < _lines.length && _isJunk(_lines[_below])) _below++;
    // Remove junk above ❯ (pet art, borders)
    var _above = _promptIdx - 1;
    while (_above >= 0 && _above >= _promptIdx - 15 && _isJunk(_lines[_above])) _above--;
    _lines = _lines.slice(0, _above + 1).concat(['\x00HR\x00', _promptLine]).concat(_lines.slice(_below));
  }
  text = _lines.join('\n');
  }
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
        else if (c === 38 && codes[j+1] === 5) { fg = _ansi256(codes[j+2]||0, !!bg); j += 2; }
        else if (c === 48 && codes[j+1] === 5) { bg = _ansi256(codes[j+2]||0, false); j += 2; }
        else if (c === 38 && codes[j+1] === 2) { fg = _adaptRgb(codes[j+2]||0, codes[j+3]||0, codes[j+4]||0, !!bg); j += 4; }
        else if (c === 48 && codes[j+1] === 2) { bg = 'rgb('+(codes[j+2]||0)+','+(codes[j+3]||0)+','+(codes[j+4]||0)+')'; j += 4; }
      }
    }
  }
  // Phase 3: highlight prompt lines (lines ending with $, %, >, ❯)
  html = html.split('\n').map(function(line) {
    if (line === '\x00HR\x00') return '<hr class="term-sep">';
    var stripped = line.replace(/<[^>]*>/g, '').trim();
    if (/[$%>❯]\s*$/.test(stripped) && stripped.length > 0) {
      return '<span class="term-line-prompt">' + line + '</span>';
    }
    return line;
  }).join('\n');
  // Phase 4: make URLs clickable (https://... outside of existing <a> tags)
  html = html.replace(/(https?:\/\/[^\s<>"']+)/g, '<a href="$1" target="_blank" rel="noopener" class="term-link">$1</a>');
  return html;
}

// ── Mobile WebSocket terminal stream ────────────────────────────────────────
var _termWs = null;

// ── Stream 模式 scrollback 积累(快照拼接)────────────────────────────────────
// claude 的 TUI 自己管理视口:旧内容被原地擦除,不经过 tmux 滚动,pane 历史是 0
// (子账号 pane 尤其如此,从出生就是 claude)。WS 快照因此只有可见一屏,没法往上翻。
// 解法:每帧快照和上一帧做行对齐,识别「滚出屏幕顶部的行」,在客户端积累成 scrollback。
var _sbTarget = null;     // scrollback 归属的 pane target
var _sbChunks = [];       // [{html, lines}] 已积累的片段(整段追加/整段丢弃,不切内部)
var _sbLines = 0;         // 总行数(封顶用)
var _sbFlushedIdx = 0;    // 已写入 DOM 的 chunk 数(增量 append)
var _sbRebuild = false;   // 封顶裁剪后需要全量重建 DOM
var _sbPrevPlain = null;  // 上一帧纯文本行(对齐比较用)
var _sbPrevRaw = null;    // 上一帧原始行(含 ANSI,取滚出内容用)
var _sbLastData = null;   // 上一帧原文(去重)
var _sbAnchor = 0;        // 冻结区边界:快照前 _sbAnchor 行是不再变的旧历史(owner pane
                          // 进 claude 前的 tmux 历史);丢行发生在这条边界上,渲染时
                          // scrollback 要插在冻结区和实时屏之间才能保持时间顺序
var _sbHeadRaw = null;    // 冻结区上次渲染的原文(不变就不重写 DOM)
var _SB_MAX_LINES = 2000;

function _sbReset(target) {
  _sbTarget = target;
  _sbChunks = []; _sbLines = 0; _sbFlushedIdx = 0; _sbRebuild = false;
  _sbPrevPlain = null; _sbPrevRaw = null; _sbLastData = null; _sbAnchor = 0;
  _sbHeadRaw = null;
}

function _sbStripLine(l) {
  return l.replace(/\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g, '')
          .replace(/\x1b\[[?]?[0-9;]*[a-zA-Z]/g, '')
          .replace(/\s+$/, '');
}

// 每条 WS 消息都要经过这里(而不是只在渲染帧),否则用户上滑暂停渲染期间的滚动会丢。
function _sbIngest(data) {
  if (data === _sbLastData) return;
  _sbLastData = data;
  var raw = data.split('\n');
  var plain = raw.map(_sbStripLine);
  var prevP = _sbPrevPlain, prevR = _sbPrevRaw;
  _sbPrevPlain = plain; _sbPrevRaw = raw;
  if (!prevP) return;
  // 1. 两帧公共前缀 p = 冻结区边界。丢行不一定发生在快照顶部:owner pane 的快照是
  //    「几百行冻结的 tmux 旧历史 + claude 当前屏」,claude 的行从中间边界消失,
  //    顶部永远不动 —— 所以必须从第一个变化点开始对齐,而不是从第 0 行。
  var n = Math.min(plain.length, prevP.length);
  var p = 0;
  while (p < n && plain[p] === prevP[p]) p++;
  if (p >= prevP.length) return;   // prev 是 cur 的前缀:只是底部追加,没有丢行
  if (p >= plain.length) return;   // cur 是 prev 的前缀:内容收缩(折叠),不追加
  // 2. 在变化点之后找上移量 s:cur[p+k] == prev[p+s+k](即 prev 的 p..p+s 行丢了)
  var s = -1;
  var maxS = Math.min(prevP.length - p, 400);
  for (var cand = 1; cand <= maxS; cand++) {
    var checked = 0, hit = 0, anchored = false;
    for (var k = 0; k < 14 && p + k < plain.length - 6 && p + cand + k < prevP.length; k++) {
      var a = plain[p + k], b = prevP[p + cand + k];
      if (!a && !b) continue;          // 双空行不计分
      checked++;
      if (a === b) { hit++; if (a) anchored = true; }
    }
    if (checked >= 3 && anchored && hit / checked >= 0.7) { s = cand; break; }
  }
  if (s <= 0) return;   // 原地改写(流式更新)/折叠/清屏跳变 → 保守不追加
  var chunkRaw = prevR.slice(p, p + s);
  var hasContent = false;
  for (var c = p; c < p + s; c++) if (prevP[c]) { hasContent = true; break; }
  if (!hasContent) { _sbAnchor = p; return; }   // 全空行:边界照记,内容不积累
  var html = _ansiToHtml(chunkRaw.join('\n') + '\n', true);
  if (!html) return;
  _sbChunks.push({ html: html, lines: s });
  _sbLines += s;
  _sbAnchor = p;
  while (_sbLines > _SB_MAX_LINES && _sbChunks.length > 1) {
    _sbLines -= _sbChunks.shift().lines;
    if (_sbFlushedIdx > 0) _sbFlushedIdx--;
    _sbRebuild = true;
  }
}

// 渲染帧里调用:把积累的 scrollback 增量刷进 DOM(只在跟随模式下被调,不打断上滑手势)
function _sbFlush(sbEl) {
  if (_sbRebuild) {
    sbEl.innerHTML = _sbChunks.map(function(c) { return c.html; }).join('');
    _sbFlushedIdx = _sbChunks.length;
    _sbRebuild = false;
    return;
  }
  while (_sbFlushedIdx < _sbChunks.length) {
    sbEl.insertAdjacentHTML('beforeend', _sbChunks[_sbFlushedIdx++].html);
  }
}

function _hasPaneTarget(target) {
  // 同时认分组里的 .term-pane-row 和单终端项目的 .term-single(顶层项);
  // 只认前者会让单终端项目在 WS 一断时被误判为"已消失"→ 踢回列表。
  return !!document.querySelector('.term-pane-row[data-target="' + CSS.escape(target) + '"], .term-single[data-target="' + CSS.escape(target) + '"]');
}

var _wsRetryDelay = 2000;   // WS 重连退避(成功连上后在 onopen 重置)
function _connectTermWs(target) {
  _disconnectTermWs();
  // 换 pane 才清 scrollback;同 pane 重连(后台回前台/断线)保留已积累的历史
  if (_sbTarget !== target) _sbReset(target);
  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var url = proto + '//' + location.host + '/ws/terminal/' + encodeURIComponent(target)
            + '/stream?token=' + encodeURIComponent(_adminToken || _subToken);
  var termWs = new WebSocket(url);
  _termWs = termWs;
  var output = document.getElementById('mobile-term-output');

  var _lastWsData = '';
  var _pendingWsData = null;
  var _renderWsFrame = 0;
  var _termFollow = true;   // true=跟随最新输出到底;false=用户上滑看历史,暂停整屏重建

  function _termAtBottom() {
    return (output.scrollHeight - output.scrollTop - output.clientHeight) < 60;
  }

  function _renderTerminalFrame() {
    _renderWsFrame = 0;
    var data = _pendingWsData;
    if (_termWs !== termWs || !output || data === null) return;
    // 用户在看历史(_termFollow=false)时不重建 DOM:iOS Safari 上整屏 innerHTML 替换会
    // 清除正在进行的触摸滚动,程序在跑时后端高频推全量快照 → 高频重建 → 手势每次都被打断,
    // 表现为"完全滑不动"。故上滑期间只把最新数据留在 _pendingWsData,滑回底部再恢复跟随。
    if (!_termFollow) return;
    _pendingWsData = null;
    if (data === _lastWsData) return;
    _lastWsData = data;
    // 三区结构:head(快照里 anchor 之前的冻结旧历史)+ scrollback(只增量追加)+
    // live(anchor 之后的实时屏,每帧重建)。scrollback 必须插在冻结区和实时屏之间,
    // 时间顺序才对;head 内容不变时跳过重写,live 高频重建也不碰几千行的 scrollback。
    var headEl = output.firstElementChild;
    // DOM 归属校验:三区 DOM 是跨帧复用的,切 pane 后旧 pane 的 scrollback DOM 还留着,
    // 必须整体重建,否则别的项目的历史会串到当前 pane 上面(咬过:argus 里看到其他项目)。
    if (!headEl || !headEl.classList.contains('term-head') || output.dataset.sbTarget !== target) {
      output.innerHTML = '<div class="term-head"></div><div class="term-sb"></div><div class="term-live"></div>';
      output.dataset.sbTarget = target;
      headEl = output.firstElementChild;
      _sbFlushedIdx = 0;   // DOM 是新的,已积累的 scrollback 需要重新灌入
      _sbRebuild = _sbChunks.length > 0;
      _sbHeadRaw = null;
    }
    var sbEl = headEl.nextElementSibling;
    var allLines = data.split('\n');
    var anchor = Math.min(_sbAnchor, allLines.length);
    var headRaw = anchor > 0 ? allLines.slice(0, anchor).join('\n') + '\n' : '';
    if (_sbHeadRaw !== headRaw) {
      _sbHeadRaw = headRaw;
      headEl.innerHTML = headRaw ? _ansiToHtml(headRaw, true) : '';
    }
    _sbFlush(sbEl);
    sbEl.nextElementSibling.innerHTML = _ansiToHtml(allLines.slice(anchor).join('\n'));
    output.scrollTop = output.scrollHeight;
    // Cache snapshot for tab switcher (last 20 lines of plain text)
    if (_currentTarget) {
      var _lines = output.textContent.split('\n').filter(function(l) { return l.trim(); });
      _paneSnapshots[_currentTarget] = _lines.slice(-20).join('\n');
    }
  }

  // 触摸/滚动驱动"跟随最新 ↔ 看历史"切换。覆盖式绑定(on*),避免每次重连累加监听器。
  function _resumeIfPending() {
    if (_pendingWsData !== null && !_renderWsFrame)
      _renderWsFrame = requestAnimationFrame(_renderTerminalFrame);
  }
  output.ontouchstart = function() { _termFollow = false; };  // 手指一碰即暂停重建,手势才不被打断
  output.ontouchend = function() { if (_termAtBottom()) { _termFollow = true; _resumeIfPending(); } };
  output.onscroll = function() {
    if (_termAtBottom()) { if (!_termFollow) { _termFollow = true; _resumeIfPending(); } }
    else { _termFollow = false; }
  };

  termWs._cancelPendingRender = function() {
    if (_renderWsFrame) cancelAnimationFrame(_renderWsFrame);
    _renderWsFrame = 0;
    _pendingWsData = null;
  };

  termWs.onmessage = function(e) {
    if (_termWs !== termWs) return;
    if (!output) return;
    // scrollback 拼接必须每条消息都做(渲染可以丢帧,滚出的历史行不能丢)
    if (_sbTarget === target) _sbIngest(e.data);
    // Keep only the newest terminal snapshot and render at most once per
    // animation frame. This prevents ANSI conversion and full DOM replacement
    // from queueing up while output is arriving quickly.
    _pendingWsData = e.data;
    if (!_renderWsFrame) _renderWsFrame = requestAnimationFrame(_renderTerminalFrame);
  };

  termWs.onclose = function() {
    termWs._cancelPendingRender();
    if (_termWs === termWs) _termWs = null;
    _setWsDot(false);
    // Auto-reconnect if still viewing this pane in stream mode.
    // 后台(document.hidden)不重连:iOS 掐断连接时不该触发下面的"回列表"逻辑,
    // 回前台由 visibilitychange 统一重连。
    if (_currentTarget !== target ||
        !document.getElementById('dev-page').classList.contains('detail-open') ||
        document.hidden) return;
    var _retry = _wsRetryDelay;
    _wsRetryDelay = Math.min(_wsRetryDelay * 1.5, 20000);   // 指数退避,防重连风暴
    setTimeout(async function() {
      if (_currentTarget !== target || document.hidden) return;
      try { await loadPanes(true); } catch(e) {}
      if (!_hasPaneTarget(target)) {
        _currentTarget = null;
        showPlaceholder();
        return;
      }
      _connectTermWs(target);
    }, _retry);
  };
  termWs.onopen = function() { _setWsDot(true); _wsRetryDelay = 2000; };
  termWs.onerror = function() {};
}

function _disconnectTermWs() {
  if (_termWs) {
    if (_termWs._cancelPendingRender) _termWs._cancelPendingRender();
    _termWs.onclose = null;  // prevent auto-reconnect
    _termWs.onmessage = null;  // 断开后残留消息不得再进拼接/渲染(防串台)
    try { _termWs.close(); } catch(e) {}
    _termWs = null;
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
  if (_termWs && _termWs.readyState === WebSocket.OPEN) return;
  if (_currentTarget) {
    _setWsDot(true);
    _connectTermWs(_currentTarget);
  }
}

async function _sendToTerminal(keys, promptText) {
  if (!_currentTarget) return;
  try {
    var _body = { keys: keys };
    if (promptText) _body.prompt = promptText;   // 子账号:供后端精确归属这条 prompt(不靠时间)
    await fetch('/api/terminals/' + encodeURIComponent(_currentTarget) + '/send', {
      method: 'POST',
      headers: _authHeaders({'Content-Type': 'application/json'}),
      body: JSON.stringify(_body)
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

var _mobileInputInited = false;
function _initMobileInput() {
  // 桌面也要绑定:owner 的"输入框模式"和子账号在桌面都用这套输入框,回车发送/发送按钮/
  // 特殊键都在下面绑,之前 `if(!_isMobile)return` 把桌面挡在门外 → 桌面回车发不出去。
  if (_mobileInputInited) return;   // 幂等:init/initSub 都会调,累加 addEventListener 会导致回车重复发送
  var input = document.getElementById('mobile-cmd-input');
  var sendBtn = document.getElementById('mobile-send-btn');
  if (!input || !sendBtn) return;
  _mobileInputInited = true;

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
    if (!seq && keyName && keyName.length === 1) {
      // Single char keys (digits etc): send char + Enter
      if (!_isMobile && _inScrollMode) _scrollTerminal('exit');
      _sendToTerminal(keyName + '\n');
      return;
    }
    if (seq) {
      if (!_isMobile && _inScrollMode) _scrollTerminal('exit');
      _sendToTerminal(seq);
    }
  });
}

async function _sendMobileCmd() {
  var input = document.getElementById('mobile-cmd-input');
  var text = input.value;
  // Exit scroll mode first
  if (_inScrollMode) await _scrollTerminal('exit');
  if (text) {
    // Add to history (dedup, max 100)
    _cmdHistory = _cmdHistory.filter(function(c) { return c !== text; });
    _cmdHistory.push(text);
    if (_cmdHistory.length > 100) _cmdHistory = _cmdHistory.slice(-100);
    localStorage.setItem('mira-cmd-history', JSON.stringify(_cmdHistory));
    _historyIdx = -1;
  }
  // Send text + Enter (empty text = bare Enter for confirmations/selections)
  await _sendToTerminal(text + '\n', text || null);   // 非空文本作为 prompt 原文精确归属
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

// ── Mobile pane switcher ──────────────────────────────────────────────────────
// ── Safari-style tab switcher (mobile) ─────────────────────────────────────
var _paneSnapshots = {};

function _saveSnapshot() {
  if (!_currentTarget) return;
  var output = document.getElementById('mobile-term-output');
  if (output && output.textContent) {
    // Save last ~20 lines of plain text for preview
    var lines = output.textContent.split('\n').filter(function(l) { return l.trim(); });
    _paneSnapshots[_currentTarget] = lines.slice(-20).join('\n');
  }
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
  var viewH = window.innerHeight;
  overlay.querySelectorAll('.tab-card').forEach(function(card) {
    var rect = card.getBoundingClientRect();
    var center = rect.top + rect.height / 2;
    var ratio = center / viewH;
    var angle = 4 - ratio * 8;
    angle = Math.max(-4, Math.min(4, angle));
    card.style.transform = 'perspective(800px) rotateX(' + angle.toFixed(1) + 'deg)';
  });
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

// ── Auto-copy: poll tmux buffer for changes ──────────────────────────────────
// tmux mouse mode captures text selection into paste buffer.
// We poll the buffer and auto-copy to system clipboard when it changes.
var _bufferPollTimer = null;
var _lastTmuxBuffer = '';

function _startBufferPoll() {
  if (_bufferPollTimer) return;
  // Snapshot current buffer so we don't immediately copy old content
  fetch('/api/terminal/buffer', { headers: _authHeaders() })
    .then(function(r) { return r.ok ? r.json() : {}; })
    .then(function(d) { _lastTmuxBuffer = (d.text || '').trim(); })
    .catch(function() {});
  _bufferPollTimer = setInterval(_checkBufferChange, 4000);
}

function _stopBufferPoll() {
  if (_bufferPollTimer) { clearInterval(_bufferPollTimer); _bufferPollTimer = null; }
}

var _pendingCopyText = null;

function _doCopy(text) {
  var ok = false;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(function() {
      _showToast('已复制 ' + text.length + ' 字符', 1500);
    }).catch(function() {
      // clipboard API failed, try execCommand in next click
      _execCopy(text);
    });
    return;
  }
  _execCopy(text);
}

function _execCopy(text) {
  var ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;left:-9999px;top:0';
  document.body.appendChild(ta);
  ta.select();
  var ok = false;
  try { ok = document.execCommand('copy'); } catch(_) {}
  document.body.removeChild(ta);
  _showToast(ok ? '已复制 ' + text.length + ' 字符' : '复制失败', 1500);
}

function _showCopyToast(text) {
  _pendingCopyText = text;
  var preview = text.length > 50 ? text.substring(0, 47) + '…' : text;
  preview = preview.replace(/\n/g, ' ↵ ');
  // Remove existing copy-toast
  var old = document.getElementById('copy-toast');
  if (old) old.remove();
  var toast = document.createElement('div');
  toast.id = 'copy-toast';
  toast.style.cssText = 'position:fixed;bottom:60px;left:50%;transform:translateX(-50%);z-index:999;background:var(--panel,#1e293b);color:var(--text,#e2e8f0);border:1px solid var(--accent,#818cf8);border-radius:8px;padding:10px 16px;font-family:var(--mono);font-size:12px;cursor:pointer;max-width:80vw;box-shadow:0 4px 20px rgba(0,0,0,.4);display:flex;align-items:center;gap:10px;';
  toast.innerHTML = '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + preview.replace(/</g,'&lt;') + '</span><span style="background:var(--accent,#818cf8);color:#fff;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap">点击复制</span>';
  toast.addEventListener('click', function() {
    if (_pendingCopyText) _doCopy(_pendingCopyText);
    toast.remove();
  });
  document.body.appendChild(toast);
  setTimeout(function() { if (toast.parentNode) toast.remove(); }, 8000);
}

async function _checkBufferChange() {
  try {
    var res = await fetch('/api/terminal/buffer', { headers: _authHeaders() });
    if (!res.ok) return;
    var data = await res.json();
    var text = (data.text || '').trim();
    if (!text || text.length < 2) return;
    if (text === _lastTmuxBuffer) return;
    _lastTmuxBuffer = text;
    var ok = false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      try { await navigator.clipboard.writeText(text); ok = true; } catch(e) {}
    }
    if (ok) {
      var preview = text.length > 50 ? text.substring(0, 47) + '…' : text;
      _showToast('已复制: ' + preview.replace(/\n/g, ' ↵ '), 2000);
    } else {
      _showCopyToast(text);
    }
  } catch(e) { console.warn('[mira-copy] ERROR:', e); }
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

// ── ttyd theme sync ───────────────────────────────────────────────────────────
function _applyTtydTheme() {
  var frame = document.getElementById('ttyd-frame');
  if (!frame || !frame.contentWindow) return;
  // The injected mira-ttyd-theme script inside the iframe handles everything;
  // we just tell it the skin changed via postMessage.
  try { frame.contentWindow.postMessage({ type: 'mira-theme' }, '*'); } catch(_) {}
}

// ── Listen for status/mouseup from ttyd iframe (via postMessage) ─────────────
window.addEventListener('message', function(e) {
  var frame = document.getElementById('ttyd-frame');
  if (frame && e.source === frame.contentWindow && e.data && e.data.type === 'mira-ttyd-connection') {
    _setDesktopWsDot(e.data.connected === true);
    return;
  }
  if (e.data && e.data.type === 'mira-mouseup') {
    setTimeout(_checkBufferChange, 200);
  }
});

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
  if (t.role === 'user') {
    var ts = t.ts ? '<div class="hist-ts">' + _histTs(t.ts) + '</div>' : '';
    return '<div class="hist-turn">' + ts + '<div class="hist-user">' + escHtml(t.text) + '</div></div>';
  }
  var tools = '';
  if (t.tools) {
    var parts = Object.keys(t.tools).map(function(k) { return k + (t.tools[k] > 1 ? '×' + t.tools[k] : ''); });
    if (parts.length) tools = '<div class="hist-tools">⚙ ' + escHtml(parts.join(' · ')) + '</div>';
  }
  var body = (t.text || '').trim();
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
// 终端用子账号自己的【可写】ttyd(/subterm/<port>/),会话已加固到拿不到裸 shell。
let _subTermBase = '';

async function initSub() {
  document.getElementById('dev-page').classList.add('sub-mode');
  document.body.classList.add('sub-mode');
  new MutationObserver(function() { _applyTtydTheme(); })
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
      _disconnectTermWs();
    } else {
      loadSubProjects();
      _subInterval = setInterval(loadSubProjects, 15000);
      if (_currentTarget && document.getElementById('dev-page').classList.contains('detail-open')) {
        if (_isMobile) _connectTermWs(_currentTarget);
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
  var row = document.querySelector('.term-pane-row[data-pid="' + CSS.escape(pid) + '"]');
  var name = row ? ((row.querySelector('.term-pane-name-text') || {}).textContent || pid) : pid;
  var titleEl = document.getElementById('term-detail-title'); if (titleEl) titleEl.textContent = name;
  var pageTitle = document.querySelector('.topbar-page-title'); if (pageTitle && _isMobile) pageTitle.textContent = name;
  document.getElementById('term-placeholder').style.display = 'none';
  var res = await fetch('/api/sub/project/' + encodeURIComponent(pid) + '/session', { method: 'POST', headers: _authHeaders() }).catch(function(){ return null; });
  if (!res || !res.ok) { _subTermError(res && res.status === 403 ? '无权访问该项目' : '会话启动失败,稍后重试'); return; }
  var d = await res.json();
  _currentTarget = d.target;
  _subTermBase = d.term_base || '';
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
  if (_isMobile) {
    // 手机:stream 模式(iframe 在手机上输入有问题)—— 输出流+输入栏,输入走后端带账号
    devPage.classList.remove('sub-hybrid');
    document.getElementById('ttyd-frame').classList.remove('visible');
    document.getElementById('mobile-term-output').classList.add('visible');
    document.getElementById('mobile-token-bar').classList.add('visible');
    document.getElementById('mobile-input-bar').style.display = 'flex';
    if (_currentTarget) _connectTermWs(_currentTarget);
    return;
  }
  // 桌面:真终端 + 输入框并存 —— 显示用可写 ttyd(claude 自己管完整历史,滚动/字号原生);
  // 输入推荐走底部输入框(经后端、prompt 100% 带账号),直接在终端敲的归属走时间推断。
  if (!_subTermBase) { _subTermError('终端暂不可用,请重试'); return; }
  devPage.classList.add('sub-hybrid');
  var frame = document.getElementById('ttyd-frame');
  if (!frame.src || !frame.src.endsWith(_subTermBase)) {
    frame.src = _subTermBase;
    frame.addEventListener('load', function() { _applyTtydTheme(); });
  }
  frame.classList.add('visible');
  document.getElementById('mobile-term-output').classList.remove('visible');
  document.getElementById('mobile-input-bar').style.display = 'flex';
  _disconnectTermWs();   // 桌面 hybrid 由 iframe 渲染,不需要快照流
  requestAnimationFrame(function() { _resizeTtydFrame(); setTimeout(_resizeTtydFrame, 250); });
  _focusInputBox();   // 切进来直接能在输入框敲字
}

function _focusInputBox() {
  if (_isMobile) return;   // 移动端不自动弹软键盘,用户点了才聚焦
  setTimeout(function() {
    var i = document.getElementById('mobile-cmd-input');
    var dp = document.getElementById('dev-page');
    if (i && dp && dp.classList.contains('stream-mode')) i.focus();
  }, 80);
}

// 输入框模式下,预加载/隐藏的 ttyd iframe(加载完 xterm 会自动 focus)会偷走焦点 →
// 敲字进了终端 iframe。焦点一旦落到 iframe 就抢回输入框。绑定一次。
document.addEventListener('focusin', function(e) {
  if (_isMobile) return;
  var dp = document.getElementById('dev-page');
  if (!dp || !dp.classList.contains('stream-mode')) return;
  var t = e.target;
  if (t && (t.id === 'ttyd-frame' || t.tagName === 'IFRAME')) {
    var i = document.getElementById('mobile-cmd-input');
    if (i) i.focus();
  }
});

function _focusTerm() {
  // 把键盘焦点交给终端 iframe,进去就能直接打字(不用先点一下)
  var frame = document.getElementById('ttyd-frame');
  try { frame.contentWindow.focus(); } catch (e) {}
  try { frame.focus(); } catch (e) {}
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
  // Watch for skin changes and sync to ttyd iframe
  new MutationObserver(function() { _applyTtydTheme(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  // Init mobile input bar + upload handlers
  _initMobileInput();
  _initUpload();
  // Preload ttyd iframe on desktop so it's ready when user clicks a pane
  if (!_isMobile && !localStorage.getItem('mira-input-box-mode')) {
    // 输入框模式不预加载 ttyd(否则它加载完会抢焦点、把敲的字吃进隐藏的终端)
    var _preFrame = document.getElementById('ttyd-frame');
    if (_preFrame && !_preFrame.src) _preFrame.src = '/terminal/';
  }
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
  _startBufferPoll();
  // Warm the lightweight project list while the page is idle so the first
  // click on + normally opens with a complete list and no network wait.
  var _preloadProjects = function() { _fetchNewTermProjects().catch(function() {}); };
  if (window.requestIdleCallback) requestIdleCallback(_preloadProjects, { timeout: 1500 });
  else setTimeout(_preloadProjects, 300);

  // Pause all polling when tab is hidden, resume when visible
  document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
      clearInterval(_panesInterval); _panesInterval = null;
      _stopBufferPoll();
      if (_tokenRefreshTimer) { clearInterval(_tokenRefreshTimer); _tokenRefreshTimer = null; }
      // 后台主动断开终端 WS:避免 iOS 掐断时触发 onclose 的重连/回列表逻辑
      _disconnectTermWs();
    } else {
      loadPanes();
      _panesInterval = setInterval(loadPanes, 8000);
      _startBufferPoll();
      if (_currentTarget) {
        var t = _paneToolMap[_currentTarget] || '';
        if (t) _startTokenRefresh(_currentTarget, t);
        // 回前台:仍在流式终端视图则重连 WS 恢复输出
        if (_isMobile && document.getElementById('dev-page').classList.contains('detail-open')) {
          _connectTermWs(_currentTarget);
        }
      }
    }
  });
}
init();
"""

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, interactive-widget=resizes-visual">\n'
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
<!-- Tab switcher overlay (mobile) -->
<div class="tab-switcher" id="tab-switcher"></div>

<div class="dev-page" id="dev-page">
  <!-- Sidebar: pane list -->
  <div class="term-sidebar">
    <div class="term-sidebar-header">
      <span>所有终端</span>
      <div style="display:flex;gap:6px;align-items:center">
        <button class="term-edit-btn" id="dev-edit-btn" onclick="toggleEditMode()" title="编辑:拖拽排序 / 合并 / 重命名 / 删除"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg></button>
        <button class="term-new-btn" onclick="openNewTermDialog()" title="新建终端窗口">+</button>
      </div>
    </div>
    <div id="term-pane-list">
      <div class="term-empty-sidebar">正在加载…</div>
    </div>
  </div>

  <!-- Main: ttyd iframe -->
  <div class="term-main">
    <!-- Mobile-only header (back to list + project name) -->
    <div class="term-detail-header" id="term-detail-header">
      <a class="term-switch-btn" href="/" title="主页" style="text-decoration:none">⌂</a>
      <button class="term-detail-back" onclick="showPlaceholder()" title="返回列表">← 列表</button>
      <span class="term-detail-title" id="term-detail-title">终端</span>
      <button class="term-switch-btn" onclick="_togglePaneSwitcher()" title="切换终端">⇅</button>
      <button class="term-switch-btn" onclick="openSettings()" title="设置">⚙</button>
    </div>
    <!-- Mobile pane switcher dropdown -->
    <div class="pane-switcher" id="pane-switcher"></div>
    <div id="term-placeholder" class="term-placeholder">
      <div>从左侧选择一个项目，或者：</div>
      <button class="term-placeholder-btn" onclick="openNewTermDialog()">+ 新建终端窗口</button>
    </div>
    <!-- Desktop toolbar (above iframe, visible when pane selected) -->
    <div class="term-toolbar" id="term-toolbar">
      <!-- 上传/粘贴已统一到输入框左侧(桌面开"输入框模式"即有);顶部工具栏只保留状态显示 -->
      <button class="stats-btn" onclick="openPaneHistory()" title="完整会话历史(不受终端擦屏影响)" style="background:none;border:1px solid var(--border);color:var(--sub);border-radius:6px;padding:3px 12px;font-family:inherit;font-size:11px;cursor:pointer">历史</button>
      <span class="toolbar-spacer"></span>
      <span class="desktop-ws-dot err" id="desktop-ws-dot" title="终端连接中"></span>
      <span class="toolbar-tokens" id="toolbar-tokens"></span>
      <span class="toolbar-usage" id="toolbar-usage"></span>
    </div>
    <div class="term-iframe-wrap" id="term-iframe-wrap">
      <div class="term-touch-overlay" id="term-touch-overlay"></div>
      <div class="term-scroll-badge" id="term-scroll-badge">滚动模式</div>
      <iframe id="ttyd-frame" allow="clipboard-read; clipboard-write"></iframe>
    </div>
    <!-- Mobile token bar -->
    <div class="mobile-token-bar" id="mobile-token-bar"><span class="ws-dot ok" id="ws-dot" onclick="_onWsDotClick()" title="连接状态"></span></div>
    <!-- Mobile: independent terminal output via WebSocket (ANSI-rendered) -->
    <div class="mobile-term-output" id="mobile-term-output"></div>
    <!-- Mobile input bar: bypasses iframe input issues via tmux send-keys -->
    <div class="mobile-input-bar" id="mobile-input-bar">
      <div class="mobile-keys-row" id="mobile-keys-row">
        <button class="mobile-key-btn ok-btn" onclick="_sendOk()" title="确认">OK</button>
        <span class="keys-sep"></span>
        <button class="mobile-key-btn" data-key="Ctrl+C">⌃C</button>
        <button class="mobile-key-btn" data-key="Esc">Esc</button>
        <button class="mobile-key-btn" data-key="Tab">Tab</button>
        <button class="mobile-key-btn" onclick="_clearInput()" title="清空输入框">Cls</button>
        <span class="keys-sep"></span>
        <button class="mobile-key-btn" data-key="Up">↑</button>
        <button class="mobile-key-btn" data-key="Down">↓</button>
        <span class="keys-sep"></span>
        <button class="mobile-key-btn" onclick="openPaneHistory()" title="完整会话历史">历史</button>
        <span class="keys-sep"></span>
        <select class="mobile-num-sel" id="mobile-num-sel" onchange="_sendNum(this)">
          <option value="">1-9</option>
          <option value="1">1</option><option value="2">2</option><option value="3">3</option>
          <option value="4">4</option><option value="5">5</option><option value="6">6</option>
          <option value="7">7</option><option value="8">8</option><option value="9">9</option>
        </select>
        <span class="keys-sep"></span>
        <label class="mobile-key-btn" for="mobile-file-input" title="上传文件" style="display:inline-flex;align-items:center;justify-content:center">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
          </svg>
        </label>
      </div>
      <div class="mobile-input-row">
        <input type="file" id="mobile-file-input" style="display:none">
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

<!-- claude 完整会话历史(读 ~/.claude jsonl) -->
<div class="hist-overlay" id="hist-overlay">
  <div class="hist-head">
    <span class="hist-title" id="hist-title">会话历史</span>
    <span class="hist-meta" id="hist-meta"></span>
    <button class="hist-close" onclick="closePaneHistory()">关闭</button>
  </div>
  <div class="hist-body" id="hist-body"><div class="hist-inner" id="hist-inner"></div></div>
</div>

<!-- Toast notification -->
<div id="dev-toast"></div>

"""
        + settings_overlay_html() + "\n\n"
        + "<script>\n"
        + "window._topbarUsageMode = null; // dev page manages usage in toolbar\n"
        + topbar_js() + "\n"
        + page_js
        + "</script>\n"
        + "</body>\n</html>\n"
    )
