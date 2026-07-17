"""Dev mode page — sidebar pane list + xterm.js PTY terminal.
页面自身的 CSS/JS 在 static/dev.css、static/dev.js(曾内嵌在这里,拆出去换语法高亮和 lint)。"""

_BUILD_ID = None


def _asset_v(name: str) -> str:
    """static 资源的内容指纹(md5 前 8 位),拼在 ?v= 上:内容一变即破缓存,
    不靠手动 bump(手机 Safari 缓存有前科)。模块导入时算一次,与 _build_id 同假设(无热重载)。"""
    import hashlib
    from pathlib import Path
    try:
        p = Path(__file__).resolve().parent.parent / "static" / name
        return hashlib.md5(p.read_bytes()).hexdigest()[:8]
    except OSError:
        return "0"


_DEV_CSS_V = _asset_v("dev.css")
_DEV_JS_V = _asset_v("dev.js")


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


    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, interactive-widget=resizes-visual">\n'
        '<link rel="stylesheet" href="/static/xterm/xterm.css">\n'
        '<script src="/static/xterm/xterm.js"></script>\n'
        '<script src="/static/xterm/addon-fit.js"></script>\n'
        '<script src="/static/xterm/addon-canvas.js"></script>\n'
        "<title>Dev · Mira</title>\n"
        "<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>\n"
        '<link rel="stylesheet" href="/static/fonts/fonts.css">\n'
        "<style>\n"
        + theme_vars_css()
        + topbar_css()
        + "</style>\n"
        + f'<link rel="stylesheet" href="/static/dev.css?v={_DEV_CSS_V}">\n'
        + "</head>\n<body>\n\n"
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

  <!-- Main: xterm.js PTY 终端 -->
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
      <!-- 上传/粘贴已统一到输入框左侧(桌面开"输入框模式"即有);历史入口已移到 topbar 右上角 icon;工具栏只保留状态显示 -->
      <span class="toolbar-spacer"></span>
      <span class="desktop-ws-dot err" id="desktop-ws-dot" title="终端连接中"></span>
      <span class="toolbar-tokens" id="toolbar-tokens"></span>
      <span class="toolbar-usage" id="toolbar-usage"></span>
    </div>
    <!-- Mobile token bar -->
    <div class="mobile-token-bar" id="mobile-token-bar"><span class="ws-dot ok" id="ws-dot" onclick="_onWsDotClick()" title="连接状态"></span></div>
    <!-- xterm.js PTY 真终端(替代下面的快照拼接 mobile-term-output) -->
    <div class="xterm-wrap" id="xterm-wrap"><div id="xterm-container"></div></div>
    <!-- Mobile: independent terminal output via WebSocket (ANSI-rendered) -->
    <div class="mobile-term-output" id="mobile-term-output"></div>
    <!-- Mobile input bar: bypasses iframe input issues via tmux send-keys -->
    <div class="mobile-input-bar" id="mobile-input-bar">
      <div class="mobile-keys-row" id="mobile-keys-row">
        <label class="mobile-key-btn" for="mobile-file-input" title="上传文件" style="display:inline-flex;align-items:center;justify-content:center">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
          </svg>
        </label>
        <span class="keys-sep"></span>
        <button class="mobile-key-btn ok-btn" onclick="_sendOk()" title="确认">OK</button>
        <button class="mobile-key-btn" onclick="_smartEnter()" title="回车(确认/选菜单);采纳灰色建议请按 Tab">↵</button>
        <span class="keys-sep"></span>
        <button class="mobile-key-btn" data-key="Ctrl+C" title="退出会话:点一下=打断/优雅退出;5秒内再点一下=强制退出(必退)">⌃C</button>
        <button class="mobile-key-btn" data-key="Ctrl+O" title="展开/收起后台代理与详细输出">⌃O</button>
        <button class="mobile-key-btn" data-key="Esc">Esc</button>
        <button class="mobile-key-btn" data-key="Tab">Tab</button>
        <button class="mobile-key-btn" onclick="_clearInput()" title="清空输入框">Cls</button>
        <span class="keys-sep"></span>
        <button class="mobile-key-btn" data-key="Up">↑</button>
        <button class="mobile-key-btn" data-key="Down">↓</button>
        <span class="keys-sep"></span>
        <select class="mobile-num-sel" id="mobile-num-sel" onchange="_sendNum(this)">
          <option value="">1-9</option>
          <option value="1">1</option><option value="2">2</option><option value="3">3</option>
          <option value="4">4</option><option value="5">5</option><option value="6">6</option>
          <option value="7">7</option><option value="8">8</option><option value="9">9</option>
        </select>
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
        + "</script>\n"
        + f'<script src="/static/dev.js?v={_DEV_JS_V}"></script>\n'
        + "</body>\n</html>\n"
    )
