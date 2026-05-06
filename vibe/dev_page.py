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
  #term-pane-list { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }
  .term-pane-row {
    padding: 10px 14px; display: flex; align-items: flex-start; gap: 8px;
    cursor: pointer; border-left: 2px solid transparent; transition: background .12s, border-color .12s;
  }
  .term-pane-row:hover { background: rgba(255,255,255,.03); }
  .term-pane-row.active { background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }
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

  /* ── Remote host badge ── */
  .term-host-badge {
    font-size: 9px; padding: 1px 5px; border-radius: 6px;
    background: rgba(var(--accent-rgb),.15); color: var(--accent);
    white-space: nowrap; flex-shrink: 0; line-height: 14px;
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
    border: none; display: none; background: var(--bg);
    position: absolute; inset: 0; width: 100%; height: 100%;
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
  .pane-switcher { display: none; }
  .term-switch-btn { display: none; }

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
      background: var(--bg); color: var(--text);
      font-family: var(--mono); font-size: 12px; line-height: 1.4;
      padding: 6px 8px; margin: 0;
      overflow-x: hidden; overflow-y: auto; -webkit-overflow-scrolling: touch;
      white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere;
      overscroll-behavior: contain;
    }

    .term-sep {
      border: none; border-top: 1px solid rgba(255,255,255,.1);
      margin: 2px 0;
    }
    .term-link {
      color: var(--accent); text-decoration: underline;
      word-break: break-all;
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
    padding: 4px 12px; background: var(--panel);
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .term-toolbar.visible { display: flex; }
  .term-toolbar-btn {
    background: none; border: 1px solid var(--border); border-radius: var(--radius-sm);
    color: var(--sub); font-family: var(--mono); font-size: 12px;
    padding: 3px 10px; cursor: pointer; transition: color .12s, border-color .12s;
  }
  .term-toolbar-btn:hover { color: var(--accent); border-color: var(--accent); }
  @media (max-width: 900px) {
    .term-toolbar { display: none !important; }
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
    background: rgba(0,0,0,.4); backdrop-filter: blur(2px);
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
  [data-theme="neon-pixel"] .term-pane-dot.idle    { box-shadow: 0 0 5px var(--green); }
  [data-theme="neon-pixel"] .term-pane-dot.running { box-shadow: 0 0 8px var(--green), 0 0 18px rgba(0,255,0,.5); }
  [data-theme="neon-pixel"] .term-pane-dot.confirm { box-shadow: 0 0 8px var(--orange), 0 0 18px rgba(255,136,0,.5); }
  [data-theme="neon-pixel"] .term-pane-dot.error   { box-shadow: 0 0 8px var(--red), 0 0 14px rgba(255,0,64,.5); }
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
  [data-theme="pixel-cyber"] .term-pane-dot.idle    { box-shadow: 0 0 5px var(--green); }
  [data-theme="pixel-cyber"] .term-pane-dot.running { box-shadow: 0 0 8px var(--green), 0 0 18px rgba(0,255,136,.4); }
  [data-theme="pixel-cyber"] .term-pane-dot.confirm { box-shadow: 0 0 8px var(--orange), 0 0 18px rgba(255,170,0,.4); }
  [data-theme="pixel-cyber"] .term-pane-dot.error   { box-shadow: 0 0 8px var(--red), 0 0 14px rgba(255,51,85,.4); }
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
    color: rgba(0,212,255,.9);
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
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// ── State ──────────────────────────────────────────────────────────────────────
let _currentTarget = null;
const _paneState = {};
const _groupCollapsed = {};  // project_id -> bool
const _paneHostMap = {};     // target -> host alias (远程 pane 映射)
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
}

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
    // 更新远程 pane 映射
    for (const p of panes) {
      if (p._host) _paneHostMap[p.target] = p._host;
    }
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
              ${p._host ? `<span class="term-host-badge${p._host_online === false ? ' offline' : ''}">${escHtml(p._host)}</span>` : ''}
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
  // Show desktop toolbar
  var toolbar = document.getElementById('term-toolbar');
  if (toolbar) toolbar.classList.add('visible');

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
      _applyTtydTheme();
    });
  }
  frame.classList.add('visible');
}

function showPlaceholder() {
  document.getElementById('ttyd-frame').classList.remove('visible');
  document.getElementById('mobile-term-output').classList.remove('visible');
  var toolbar = document.getElementById('term-toolbar');
  if (toolbar) toolbar.classList.remove('visible');
  var switcher = document.getElementById('pane-switcher');
  if (switcher) switcher.classList.remove('open');
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
        const ta = Math.max(
          new Date((a.claude_activity && a.claude_activity.last_session) || 0).getTime(),
          new Date((a.codex_activity && a.codex_activity.last_session) || 0).getTime()
        );
        const tb = Math.max(
          new Date((b.claude_activity && b.claude_activity.last_session) || 0).getTime(),
          new Date((b.codex_activity && b.codex_activity.last_session) || 0).getTime()
        );
        return tb - ta;
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
function _ansiToHtml(raw) {
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

// ── Mobile pane switcher ──────────────────────────────────────────────────────
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
      var st = _paneState[p.target] || 'inactive';
      var dotColor = { idle:'var(--green)', running:'var(--green)', confirm:'var(--orange)', error:'var(--red)', done:'var(--green)' }[st] || 'var(--border)';
      html += '<div class="pane-switcher-item' + (isCurrent ? ' current' : '') + '"'
        + ' data-target="' + escHtml(p.target) + '"'
        + ' data-cmd="' + escHtml(p.command || '') + '">'
        + '<div class="pane-switcher-name">'
        + '<span class="pane-switcher-dot" style="background:' + dotColor + '"></span>'
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

// ── File upload ──────────────────────────────────────────────────────────────
async function _uploadImage(file) {
  if (!file) return;
  _showToast('上传中…', 10000);
  var fd = new FormData();
  fd.append('file', file);
  try {
    // 远程 pane → 带 host 参数转发到远程主机
    var uploadUrl = '/api/upload/image';
    var activeRow = document.querySelector('.term-pane-row.active');
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

  // Global paste interception (capture image paste before iframe gets it)
  document.addEventListener('paste', function(e) {
    var items = e.clipboardData && e.clipboardData.items;
    for (var i = 0; items && i < items.length; i++) {
      if (items[i].type.startsWith('image/')) {
        e.preventDefault();
        _uploadImage(items[i].getAsFile());
        return;
      }
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
  // Watch for skin changes and sync to ttyd iframe
  new MutationObserver(function() { _applyTtydTheme(); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  // Init mobile input bar + upload handlers
  _initMobileInput();
  _initUpload();
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
      <button class="term-switch-btn" onclick="_togglePaneSwitcher()" title="切换终端">⇅</button>
    </div>
    <!-- Mobile pane switcher dropdown -->
    <div class="pane-switcher" id="pane-switcher"></div>
    <div id="term-placeholder" class="term-placeholder">
      <div>从左侧选择一个项目，或者：</div>
      <button class="term-placeholder-btn" onclick="openNewTermDialog()">+ 新建终端窗口</button>
    </div>
    <!-- Desktop toolbar (above iframe, visible when pane selected) -->
    <div class="term-toolbar" id="term-toolbar">
      <label class="term-toolbar-btn" for="desktop-file-input">📎 上传文件</label>
      <input type="file" id="desktop-file-input" style="display:none">
      <button class="term-toolbar-btn" onclick="_pasteFromClipboard()" title="从剪贴板粘贴图片">📋 粘贴</button>
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
        <button class="mobile-key-btn" data-key="Ctrl+C">⌃C</button>
        <button class="mobile-key-btn" data-key="Up">↑</button>
        <button class="mobile-key-btn" data-key="Down">↓</button>
        <button class="mobile-key-btn" data-key="1">1</button>
        <button class="mobile-key-btn" data-key="2">2</button>
        <button class="mobile-key-btn" data-key="3">3</button>
        <button class="mobile-key-btn" data-key="4">4</button>
        <button class="mobile-key-btn" data-key="5">5</button>
        <button class="mobile-key-btn" onclick="openLoginModal()" style="margin-left:auto">🔑</button>
      </div>
      <div class="mobile-input-row">
        <label class="mobile-attach-btn" for="mobile-file-input" title="上传文件">📎</label>
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

<!-- Toast notification -->
<div id="dev-toast"></div>

"""
        + settings_overlay_html() + "\n\n"
        + "<script>\n"
        + topbar_js() + "\n"
        + page_js
        + "</script>\n</body>\n</html>\n"
    )
