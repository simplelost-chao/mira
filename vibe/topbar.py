"""Shared topbar component for all Mira pages.

Usage in a raw-string page (dev_page.py):
    from vibe.topbar import topbar_css, topbar_html, settings_overlay_html, topbar_js
    ...

Usage in an f-string page (detail_page.py):
    from vibe.topbar import topbar_css, topbar_html, settings_overlay_html, topbar_js
    _tb_css = topbar_css()
    _tb_html = topbar_html(title="项目名")
    _overlays = settings_overlay_html()
    _tb_js = topbar_js()
    return f'''...{_tb_css}...{_tb_html}...{_overlays}...{_tb_js}...'''
"""


def theme_vars_css(extra_vars: str = "") -> str:
    """CSS variable definitions for all themes + pixel-cyber grid + body base."""
    return (
        "  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n"
        "  :root {\n"
        "    --bg: #080c14; --panel: rgba(14,20,36,.95); --border: rgba(255,255,255,.07);\n"
        "    --text: #eef1f7; --sub: #7a8499; --muted: #4a5060;\n"
        "    --accent: #4f46e5; --accent-rgb: 79,70,229;\n"
        "    --green: #3fb950; --orange: #e5a650; --red: #e06c75; --yellow: #d29922;\n"
        "    --purple: #818cf8; --gold: #d29922;\n"
        "    --mono: 'JetBrains Mono', monospace;\n"
        "    --sans: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;\n"
        "    --radius: 8px; --radius-sm: 4px;\n"
        "    --ansi-0:#3a3f4b; --ansi-1:var(--red); --ansi-2:var(--green); --ansi-3:var(--yellow);\n"
        "    --ansi-4:#4e9eff; --ansi-5:#c792ea; --ansi-6:#56b6c2; --ansi-7:var(--text);\n"
        "    --ansi-8:var(--muted); --ansi-9:var(--red); --ansi-10:var(--green); --ansi-11:var(--orange);\n"
        "    --ansi-12:#82aaff; --ansi-13:#d9a0f5; --ansi-14:#89ddff; --ansi-15:#ffffff;\n"
        + (f"    {extra_vars}\n" if extra_vars else "")
        + "  }\n"
        "  [data-theme=\"neon-pixel\"] {\n"
        "    --bg: #0a0a0a; --panel: rgba(20,20,20,.95); --border: #00ff00;\n"
        "    --text: #e0e0ff; --sub: #a0a0cc; --muted: #505070;\n"
        "    --accent: #ff00ff; --accent-rgb: 255,0,255;\n"
        "    --green: #00ff00; --orange: #ff8800; --red: #ff0040; --yellow: #ffff00;\n"
        "    --purple: #ff00ff; --gold: #ffff00;\n"
        "    --radius: 0px; --radius-sm: 0px;\n"
        "    --ansi-0:#282840; --ansi-4:#00ccff; --ansi-5:#ff00ff; --ansi-6:#00ffff;\n"
        "    --ansi-7:#e0e0ff; --ansi-8:#505070; --ansi-12:#00ccff; --ansi-13:#ff00ff; --ansi-14:#00ffff; --ansi-15:#ffffff;\n"
        "  }\n"
        "  [data-theme=\"pixel-cyber\"] {\n"
        "    --bg: #020c1a; --panel: rgba(10,31,56,.95); --border: #00d4ff;\n"
        "    --text: #eef8ff; --sub: #a8daf0; --muted: #6bbad8;\n"
        "    --accent: #ff0055; --accent-rgb: 255,0,85;\n"
        "    --green: #00ff88; --orange: #ffaa00; --red: #ff3355; --yellow: #ffaa00;\n"
        "    --purple: #a855f7; --gold: #ffaa00;\n"
        "    --radius: 0px; --radius-sm: 0px;\n"
        "    --ansi-0:#2a5570; --ansi-4:#00d4ff; --ansi-5:#a855f7; --ansi-6:#00d4ff;\n"
        "    --ansi-7:#eef8ff; --ansi-8:#6bbad8; --ansi-12:#00d4ff; --ansi-13:#a855f7; --ansi-14:#00d4ff; --ansi-15:#ffffff;\n"
        "  }\n"
        "  [data-theme=\"pixel-cyber\"] body {\n"
        "    background-image: linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px),\n"
        "                      linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px);\n"
        "    background-size: 8px 8px;\n"
        "  }\n"
        "  [data-theme=\"claude-light\"] {\n"
        "    --bg: #f5f3ef; --panel: rgba(255,255,255,.97); --border: rgba(0,0,0,.08);\n"
        "    --text: #1a1a1a; --sub: #6b6b6b; --muted: #b0b0b0;\n"
        "    --accent: #da7756; --accent-rgb: 218,119,86;\n"
        "    --green: #16a34a; --orange: #d97706; --red: #dc2626; --yellow: #ca8a04;\n"
        "    --purple: #7c3aed; --gold: #b45309;\n"
        "    --radius: 12px; --radius-sm: 8px;\n"
        "    --ansi-0:#383a42; --ansi-4:#4078f2; --ansi-5:#a626a4; --ansi-6:#0184bc;\n"
        "    --ansi-7:#1a1a1a; --ansi-15:#383a42;\n"
        "  }\n"
        "  [data-theme=\"claude-dark\"] {\n"
        "    --bg: #131313; --panel: rgba(33,33,33,.95); --border: #303030;\n"
        "    --text: #ededed; --sub: #8f8f8f; --muted: #5d5d5d;\n"
        "    --accent: #09B83E; --accent-rgb: 9,184,62;\n"
        "    --green: #4caf50; --orange: #e5a84b; --red: #ef4444; --yellow: #d4a84b;\n"
        "    --purple: #a78bfa; --gold: #d4a84b;\n"
        "    --radius: 12px; --radius-sm: 8px;\n"
        "    --ansi-0:#3a3f4b; --ansi-4:#4e9eff; --ansi-5:#c792ea; --ansi-6:#56b6c2;\n"
        "    --ansi-7:#ededed; --ansi-8:#5d5d5d; --ansi-12:#82aaff; --ansi-13:#d9a0f5; --ansi-14:#89ddff; --ansi-15:#ffffff;\n"
        "  }\n"
        "  body { background: var(--bg); color: var(--text); font-family: var(--mono); min-height: 100vh; overflow-x: hidden; }\n"
    )


def topbar_css() -> str:
    """CSS for the topbar and shared skin/settings components."""
    return (
        "  /* ── Topbar ── */\n"
        "  .topbar {\n"
        "    position: sticky; top: 0; z-index: 100;\n"
        "    background: var(--panel); border-bottom: 1px solid var(--border);\n"
        "    backdrop-filter: blur(12px);\n"
        "    display: flex; align-items: center; gap: 12px; padding: 0 20px; height: 52px;\n"
        "  }\n"
        "  .topbar-logo {\n"
        "    display: inline-flex; align-items: baseline; gap: 0;\n"
        "    font-family: 'Silkscreen', monospace;\n"
        "    letter-spacing: 2px; line-height: 1; text-transform: uppercase; flex-shrink: 0;\n"
        "  }\n"
        "  .topbar-logo .logo-m { font-size: 22px; font-weight: 400; color: var(--accent); text-shadow: 0 0 4px rgba(var(--accent-rgb, 79,70,229), 0.4); }\n"
        "  .topbar-logo .logo-ira { font-size: 16px; font-weight: 400; color: var(--text); opacity: .75; }\n"
        "  .topbar-logo .logo-cursor { font-size: 16px; font-weight: 400; color: var(--accent); opacity: .9; animation: topbar-blink 1.1s step-end infinite; }\n"
        "  @keyframes topbar-blink { 0%,100%{opacity:.9}50%{opacity:0} }\n"
        "  .topbar-sep { width: 1px; height: 18px; background: var(--border); flex-shrink: 0; }\n"
        "  .topbar-page-title { font-size: 12px; color: var(--sub); letter-spacing: 1px; text-transform: uppercase; font-weight: 700; }\n"
        "  .topbar-spacer { flex: 1; }\n"
        "  /* Claude usage indicator in topbar */\n"
        "  .topbar-usage {\n"
        "    display: grid; grid-template-columns: auto auto 1fr; gap: 2px 6px;\n"
        "    font-size: 10px; color: var(--sub); cursor: default; white-space: nowrap;\n"
        "    align-items: center; font-variant-numeric: tabular-nums;\n"
        "  }\n"
        "  .topbar-usage-name { text-align: right; color: var(--muted); }\n"
        "  .topbar-usage-pct { text-align: right; min-width: 26px; font-weight: 600; }\n"
        "  .topbar-usage-bar {\n"
        "    width: 52px; height: 5px; border-radius: 3px; background: rgba(255,255,255,.08); overflow: hidden;\n"
        "  }\n"
        "  .topbar-usage-fill { height: 100%; border-radius: 3px; transition: width .3s; }\n"
        "  .topbar-usage-fill.low { background: var(--green); }\n"
        "  .topbar-usage-fill.mid { background: var(--orange); }\n"
        "  .topbar-usage-fill.high { background: var(--red); }\n"
        "  .topbar-usage-pct.high { color: var(--red); }\n"
        "  .topbar-usage-pct.mid { color: var(--orange); }\n"
        "  @media (max-width: 900px) {\n"
        "    .topbar-usage-bar { width: 40px; } .topbar-usage-name { display: none; }\n"
        "  }\n"
        "  .topbar-back {\n"
        "    display: inline-flex; align-items: center; gap: 5px;\n"
        "    color: var(--sub); font-size: 12px; text-decoration: none;\n"
        "    border: 1px solid var(--border); border-radius: var(--radius-sm);\n"
        "    padding: 3px 10px; transition: all .15s; white-space: nowrap;\n"
        "  }\n"
        "  .topbar-back:hover { color: var(--text); border-color: var(--accent); }\n"
        "  .topbar-btn {\n"
        "    background: none; border: 1px solid var(--border); border-radius: var(--radius-sm);\n"
        "    color: var(--sub); font-size: 13px; padding: 4px 10px; cursor: pointer;\n"
        "    font-family: var(--mono); transition: all .15s; display: inline-flex; align-items: center;\n"
        "  }\n"
        "  .topbar-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
        "  .topbar-detail-btns .topbar-btn { display: inline-flex !important; }\n"
        "  /* ── Skin cards (used inside settings overlay) ── */\n"
        "  .skin-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 18px; }\n"
        "  .skin-card { border: 1px solid var(--border); border-radius: 7px; padding: 8px; cursor: pointer; transition: border-color .15s; }\n"
        "  .skin-card:hover, .skin-card.active { border-color: var(--accent); }\n"
        "  .skin-preview { height: 28px; border-radius: 4px; overflow: hidden; display: grid; grid-template-columns: 1fr 1fr; margin-bottom: 6px; }\n"
        "  .skin-preview div { height: 100%; }\n"
        "  .skin-name { font-size: 11px; color: var(--sub); text-align: center; }\n"
        "  /* ── Version badge ── */\n"
        "  .version-badge {\n"
        "    position: fixed; bottom: 6px; right: 10px; z-index: 50;\n"
        "    font-size: 10px; color: var(--text); opacity: 0.15;\n"
        "    font-family: var(--mono); pointer-events: none; user-select: none;\n"
        "  }\n"
    )


def topbar_html(title: str = "", back_url: str = "", hide_dev: bool = False) -> str:
    """The <div class="topbar"> element.

    Args:
        title:    Page subtitle shown after the separator (e.g. "Stats").
        back_url: If given, shows a ← 返回 link on the left side.
        hide_dev: If True, hides the Dev button (use on the dev page itself).
    """
    parts = [
        '<div class="topbar">',
        '  <a class="topbar-logo" href="/" style="text-decoration:none">',
        '    <span class="logo-m">M</span><span class="logo-ira">IRA</span><span class="logo-cursor">_</span>',
        '  </a>',
    ]
    if title:
        parts += [
            '  <div class="topbar-sep"></div>',
            f'  <span class="topbar-page-title">{title}</span>',
        ]
    parts.append('  <div class="topbar-spacer"></div>')
    parts.append('  <div class="topbar-usage" id="topbar-usage" style="display:none" title="Claude Code 用量"></div>')
    if back_url:
        parts.append(f'  <a class="topbar-back" href="{back_url}">← 返回</a>')
    if not hide_dev:
        parts.append('  <a class="topbar-btn" href="/dev" title="进入开发模式" style="text-decoration:none">Dev</a>')
    parts += [
        '  <a class="topbar-btn" href="/" title="MIRA 对话" style="text-decoration:none">⌘</a>',
        '  <button class="topbar-btn" onclick="openSettings()" title="设置">',
        '    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block">',
        '      <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>',
        '    </svg>',
        '  </button>',
        '  <div class="topbar-detail-btns" style="display:none;gap:6px;align-items:center">',
        '    <button class="topbar-btn" onclick="showPlaceholder()" title="返回列表">← 列表</button>',
        '    <button class="topbar-btn" onclick="_togglePaneSwitcher()" title="切换终端">⇅</button>',
        '  </div>',
        '</div>',
    ]
    return "\n".join(parts)


def settings_overlay_html() -> str:
    """Shared settings JS + login overlay."""
    return """\
<script src="/static/settings.js?v=2"></script>
<script>initSettings();</script>

<!-- Login overlay -->
<div id="login-overlay" style="display:none;position:fixed;inset:0;z-index:500;background:rgba(0,0,0,.7);align-items:center;justify-content:center;" onclick="if(event.target===this)closeLoginModal()">
  <div style="background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:32px 28px;width:320px;text-align:center">
    <div style="font-size:20px;font-weight:700;color:var(--text);margin-bottom:6px">🔒 管理员登录</div>
    <div style="font-size:13px;color:var(--sub);margin-bottom:20px">此操作需要管理员权限</div>
    <input id="login-password" type="password" placeholder="输入密码" autocomplete="current-password"
      style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 14px;color:var(--text);font-size:14px;outline:none;margin-bottom:10px;box-sizing:border-box"
      onkeydown="if(event.key==='Enter')doLogin()">
    <div id="login-error" style="color:var(--red);font-size:12px;margin-bottom:10px;display:none">密码错误，请重试</div>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button onclick="closeLoginModal()" style="background:none;border:1px solid var(--border);color:var(--sub);padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;font-family:var(--mono)">取消</button>
      <button onclick="doLogin()" style="background:var(--accent);border:none;color:#fff;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;font-family:var(--mono)">登录</button>
    </div>
  </div>
</div>

<!-- Version badge -->
<div class="version-badge" id="version-badge"></div>
<script>
fetch('/api/version').then(r=>r.json()).then(d=>{
  document.getElementById('version-badge').textContent='v'+d.version;
}).catch(()=>{});
</script>"""


def topbar_js() -> str:
    """Shared JS: auth, settings (with skin picker), skin functions."""
    return """\
// ── Auth ─────────────────────────────────────────────────────────────────────
let _adminToken = localStorage.getItem('mira-admin-token') || '';
let _isAdmin = false;

function _authHeaders(extra) {
  extra = extra || {};
  return _adminToken ? {'X-Admin-Token': _adminToken, ...extra} : extra;
}

async function _initAuth() {
  try {
    const { admin } = await fetch('/api/auth/check', {headers: _authHeaders()}).then(r => r.json());
    _isAdmin = admin;
    if (!admin) { _adminToken = ''; localStorage.removeItem('mira-admin-token'); }
  } catch(_) { _isAdmin = false; }
}

let _loginCallback = null;
function openLoginModal(cb) {
  _loginCallback = cb || null;
  const ov = document.getElementById('login-overlay');
  ov.style.display = 'flex';
  document.getElementById('login-password').value = '';
  document.getElementById('login-error').style.display = 'none';
  setTimeout(() => document.getElementById('login-password').focus(), 50);
}
function closeLoginModal() {
  document.getElementById('login-overlay').style.display = 'none';
  _loginCallback = null;
}
async function doLogin() {
  const pw = document.getElementById('login-password').value;
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({password: pw}),
    });
    if (!res.ok) throw new Error('wrong');
    const { token } = await res.json();
    _adminToken = token; _isAdmin = true;
    localStorage.setItem('mira-admin-token', token);
    closeLoginModal();
    if (_loginCallback) { const fn = _loginCallback; _loginCallback = null; fn(); }
  } catch(e) {
    document.getElementById('login-error').style.display = '';
  }
}

// ── Topbar Claude usage indicator ──
async function _loadTopbarUsage() {
  try {
    const res = await fetch('/api/claude-usage', {headers: _adminToken ? {'X-Admin-Token': _adminToken} : {}});
    if (!res.ok) return;
    const d = await res.json();
    if (d.error) return;
    const el = document.getElementById('topbar-usage');
    if (!el) return;
    function _tb(label, data) {
      if (!data || data.utilization == null) return '';
      const pct = Math.round(data.utilization * 100);
      const cls = pct >= 90 ? 'high' : pct >= 60 ? 'mid' : 'low';
      return `<span class="topbar-usage-name">${label}</span>`
        + `<span class="topbar-usage-pct ${cls}">${pct}%</span>`
        + `<div class="topbar-usage-bar"><div class="topbar-usage-fill ${cls}" style="width:${pct}%"></div></div>`;
    }
    const html = _tb('会话', d.session) + _tb('周', d.weekly);
    if (html) { el.innerHTML = html; el.style.display = 'flex'; }
  } catch(e) {}
  setTimeout(_loadTopbarUsage, 120000);
}
if (_adminToken) _loadTopbarUsage();

// Settings functions loaded from /static/settings.js (shared with homepage)
"""
