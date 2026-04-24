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
        "    --mono: 'JetBrains Mono', monospace;\n"
        "    --sans: 'Noto Sans SC', sans-serif;\n"
        "    --radius: 8px; --radius-sm: 4px;\n"
        + (f"    {extra_vars}\n" if extra_vars else "")
        + "  }\n"
        "  [data-theme=\"neon-pixel\"] {\n"
        "    --bg: #0a0a0a; --panel: rgba(20,20,20,.95); --border: #00ff00;\n"
        "    --text: #e0e0ff; --sub: #a0a0cc; --muted: #505070;\n"
        "    --accent: #ff00ff; --accent-rgb: 255,0,255;\n"
        "    --green: #00ff00; --orange: #ff8800; --red: #ff0040; --yellow: #ffff00;\n"
        "    --radius: 0px; --radius-sm: 0px;\n"
        "  }\n"
        "  [data-theme=\"pixel-cyber\"] {\n"
        "    --bg: #020c1a; --panel: rgba(10,31,56,.95); --border: #00d4ff;\n"
        "    --text: #eef8ff; --sub: #a8daf0; --muted: #6bbad8;\n"
        "    --accent: #ff0055; --accent-rgb: 255,0,85;\n"
        "    --green: #00ff88; --orange: #ffaa00; --red: #ff3355; --yellow: #ffaa00;\n"
        "    --radius: 0px; --radius-sm: 0px;\n"
        "  }\n"
        "  [data-theme=\"pixel-cyber\"] body {\n"
        "    background-image: linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px),\n"
        "                      linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px);\n"
        "    background-size: 8px 8px;\n"
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
        "    letter-spacing: 3px; line-height: 1; text-transform: uppercase; flex-shrink: 0;\n"
        "  }\n"
        "  .topbar-logo .logo-m { font-size: 22px; font-weight: 900; color: var(--accent); text-shadow: 0 0 10px var(--accent); }\n"
        "  .topbar-logo .logo-ira { font-size: 16px; font-weight: 700; color: var(--text); opacity: .75; }\n"
        "  .topbar-logo .logo-cursor { font-size: 18px; font-weight: 400; color: var(--accent); opacity: .9; animation: topbar-blink 1.1s step-end infinite; }\n"
        "  @keyframes topbar-blink { 0%,100%{opacity:.9}50%{opacity:0} }\n"
        "  .topbar-sep { width: 1px; height: 18px; background: var(--border); flex-shrink: 0; }\n"
        "  .topbar-page-title { font-size: 12px; color: var(--sub); letter-spacing: 1px; text-transform: uppercase; font-weight: 700; }\n"
        "  .topbar-spacer { flex: 1; }\n"
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
        "  /* ── Skin cards (used inside settings overlay) ── */\n"
        "  .skin-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 18px; }\n"
        "  .skin-card { border: 1px solid var(--border); border-radius: 7px; padding: 8px; cursor: pointer; transition: border-color .15s; }\n"
        "  .skin-card:hover, .skin-card.active { border-color: var(--accent); }\n"
        "  .skin-preview { height: 28px; border-radius: 4px; overflow: hidden; display: grid; grid-template-columns: 1fr 1fr; margin-bottom: 6px; }\n"
        "  .skin-preview div { height: 100%; }\n"
        "  .skin-name { font-size: 11px; color: var(--sub); text-align: center; }\n"
    )


def topbar_html(title: str = "", back_url: str = "") -> str:
    """The <div class="topbar"> element.

    Args:
        title:    Page subtitle shown after the separator (e.g. "Dev", "Stats").
        back_url: If given, shows a ← 返回 link pointing here.
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
    if back_url:
        parts.append(f'  <a class="topbar-back" href="{back_url}">← 返回</a>')
    parts += [
        '  <button class="topbar-btn" onclick="openSettings()" title="设置">',
        '    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block">',
        '      <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>',
        '    </svg>',
        '  </button>',
        '</div>',
    ]
    return "\n".join(parts)


def settings_overlay_html() -> str:
    """Settings overlay (with inline skin picker) + login overlay."""
    return """\
<!-- Settings overlay -->
<div id="settings-overlay" style="display:none;position:fixed;inset:0;z-index:400;background:rgba(0,0,0,.6);align-items:center;justify-content:center;"
     onclick="if(event.target===this)closeSettings()">
  <div style="background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:28px;width:380px;max-width:94vw;max-height:90vh;overflow-y:auto">
    <div style="font-size:15px;font-weight:700;margin-bottom:18px">设置</div>
    <div style="font-size:11px;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:1px">外观</div>
    <div class="skin-grid" id="settings-skin-grid"></div>
    <div style="font-size:11px;color:var(--muted);margin-bottom:6px">OpenRouter API Key</div>
    <input id="set-openrouter" type="password" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;margin-bottom:12px;box-sizing:border-box;font-family:var(--mono)">
    <div style="font-size:11px;color:var(--muted);margin-bottom:6px">DeepSeek API Key</div>
    <input id="set-deepseek" type="password" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;margin-bottom:12px;box-sizing:border-box;font-family:var(--mono)">
    <div style="font-size:11px;color:var(--muted);margin-bottom:6px">Kimi API Key</div>
    <input id="set-kimi" type="password" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;margin-bottom:12px;box-sizing:border-box;font-family:var(--mono)">
    <div style="font-size:11px;color:var(--muted);margin-bottom:6px">管理员密码</div>
    <input id="set-admin-password" type="password" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;margin-bottom:18px;box-sizing:border-box;font-family:var(--mono)">
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button onclick="closeSettings()" style="background:none;border:1px solid var(--border);color:var(--sub);padding:7px 16px;border-radius:6px;cursor:pointer;font-size:13px;font-family:var(--mono)">取消</button>
      <button onclick="saveSettings()" style="background:var(--accent);border:none;color:#fff;padding:7px 16px;border-radius:6px;cursor:pointer;font-size:13px;font-family:var(--mono)">保存</button>
    </div>
  </div>
</div>

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
</div>"""


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
  } catch(_) { _isAdmin = true; }
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

// ── Skin ──────────────────────────────────────────────────────────────────────
const SKINS = [
  { id: 'default',     name: '深空默认', preview: ['#0f1117', '#4f46e5'] },
  { id: 'neon-pixel',  name: '霓虹像素', preview: ['#0a0a0a', '#ff00ff'] },
  { id: 'pixel-cyber', name: '像素赛博', preview: ['#000d1a', '#ff0066'] },
];
function applySkin(id) {
  const skin = SKINS.find(s => s.id === id) ? id : 'default';
  document.documentElement.dataset.theme = skin;
  localStorage.setItem('mira-skin', skin);
}
applySkin(localStorage.getItem('mira-skin') || 'default');

// ── Settings ──────────────────────────────────────────────────────────────────
function _renderSettingsSkins() {
  const current = document.documentElement.dataset.theme || 'default';
  const grid = document.getElementById('settings-skin-grid');
  if (!grid) return;
  grid.innerHTML = SKINS.map(s =>
    `<div class="skin-card ${s.id === current ? 'active' : ''}" onclick="applySkin('${s.id}');_renderSettingsSkins();">
      <div class="skin-preview"><div style="background:${s.preview[0]}"></div><div style="background:${s.preview[1]}"></div></div>
      <div class="skin-name">${s.name}</div>
    </div>`
  ).join('');
}
async function openSettings() {
  if (!_isAdmin) { openLoginModal(openSettings); return; }
  const data = await fetch('/api/settings', {headers: _authHeaders()}).then(r => r.json());
  document.getElementById('set-openrouter').placeholder = data.openrouter_api_key || 'sk-or-...';
  document.getElementById('set-deepseek').placeholder   = data.deepseek_api_key   || 'sk-...';
  document.getElementById('set-kimi').placeholder       = data.kimi_api_key        || 'sk-...';
  document.getElementById('set-admin-password').placeholder = data.admin_password ? '留空则不修改' : '未设置';
  _renderSettingsSkins();
  document.getElementById('settings-overlay').style.display = 'flex';
}
function closeSettings() { document.getElementById('settings-overlay').style.display = 'none'; }
async function saveSettings() {
  const body = {
    openrouter_api_key: document.getElementById('set-openrouter').value.trim(),
    deepseek_api_key:   document.getElementById('set-deepseek').value.trim(),
    kimi_api_key:       document.getElementById('set-kimi').value.trim(),
    admin_password:     document.getElementById('set-admin-password').value.trim(),
  };
  await fetch('/api/settings', {method:'POST', headers: _authHeaders({'Content-Type':'application/json'}), body: JSON.stringify(body)});
  if (body.admin_password) { _adminToken = ''; _isAdmin = false; localStorage.removeItem('mira-admin-token'); }
  closeSettings();
}"""
