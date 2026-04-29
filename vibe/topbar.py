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
        "    --sans: -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;\n"
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
        "  [data-theme=\"claude-light\"] {\n"
        "    --bg: #f5f3ef; --panel: rgba(255,255,255,.97); --border: rgba(0,0,0,.08);\n"
        "    --text: #1a1a1a; --sub: #6b6b6b; --muted: #b0b0b0;\n"
        "    --accent: #da7756; --accent-rgb: 218,119,86;\n"
        "    --green: #16a34a; --orange: #d97706; --red: #dc2626; --yellow: #ca8a04;\n"
        "    --radius: 12px; --radius-sm: 8px;\n"
        "  }\n"
        "  [data-theme=\"claude-dark\"] {\n"
        "    --bg: #131313; --panel: rgba(33,33,33,.95); --border: #303030;\n"
        "    --text: #ededed; --sub: #8f8f8f; --muted: #5d5d5d;\n"
        "    --accent: #cdcdcd; --accent-rgb: 205,205,205;\n"
        "    --green: #4caf50; --orange: #e5a84b; --red: #ef4444; --yellow: #d4a84b;\n"
        "    --radius: 12px; --radius-sm: 8px;\n"
        "  }\n"
        "  body { background: var(--bg); color: var(--text); font-family: var(--mono); min-height: 100vh; overflow-x: hidden; }\n"
    )


def topbar_css() -> str:
    """CSS for the topbar and shared skin/settings components."""
    return (
        "  /* ── Settings tabs ── */\n"
        "  .settings-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 18px; }\n"
        "  .settings-tab {\n"
        "    padding: 8px 16px; font-size: 12px; color: var(--sub); cursor: pointer;\n"
        "    border: none; border-bottom: 2px solid transparent; background: none;\n"
        "    font-family: var(--mono); letter-spacing: .5px; transition: all .15s;\n"
        "  }\n"
        "  .settings-tab:hover { color: var(--text); }\n"
        "  .settings-tab.active { color: var(--accent); border-bottom-color: var(--accent); }\n"
        "  .settings-tab-panel { display: none; }\n"
        "  .settings-tab-panel.active { display: block; }\n"
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
    if back_url:
        parts.append(f'  <a class="topbar-back" href="{back_url}">← 返回</a>')
    if not hide_dev:
        parts.append('  <a class="topbar-btn" href="/dev" title="进入开发模式" style="text-decoration:none">Dev</a>')
    parts += [
        '  <button class="topbar-btn" onclick="window.location.href=\'/\'" title="MIRA 对话">⌘</button>',
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
    <div style="font-size:15px;font-weight:700;margin-bottom:16px">设置</div>
    <div class="settings-tabs">
      <button class="settings-tab active" onclick="switchSettingsTab('appearance',this)">外观</button>
      <button class="settings-tab" onclick="switchSettingsTab('api',this)">API</button>
      <button class="settings-tab" onclick="switchSettingsTab('security',this)">安全</button>
    </div>

    <!-- 外观 tab -->
    <div class="settings-tab-panel active" id="settings-panel-appearance">
      <div style="font-size:11px;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:1px">皮肤</div>
      <div class="skin-grid" id="settings-skin-grid" style="margin-bottom:18px"></div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:1px">提示音效</div>
      <div style="display:flex;gap:6px;align-items:center">
        <select id="set-notification-sound" style="flex:1;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;font-family:var(--mono);appearance:auto"></select>
        <button onclick="previewSound()" style="background:none;border:1px solid var(--border);border-radius:6px;color:var(--sub);cursor:pointer;padding:4px 10px;font-size:12px;font-family:var(--mono)" title="试听">&#9654;</button>
      </div>
    </div>

    <!-- API tab -->
    <div class="settings-tab-panel" id="settings-panel-api">
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px;text-transform:uppercase;letter-spacing:1px">项目使用的 API</div>
      <div id="settings-providers" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px;min-height:24px"></div>
      <div style="font-size:10px;color:var(--muted);margin-bottom:16px">检测自你的所有项目</div>
      <div style="height:1px;background:var(--border);margin-bottom:16px"></div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px;text-transform:uppercase;letter-spacing:1px">余额监控（选填）</div>
      <div style="font-size:10px;color:var(--sub);margin-bottom:12px">填入 API Key 后，首页将显示余额信息</div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">OpenRouter API Key</div>
      <div style="display:flex;gap:6px;margin-bottom:12px">
        <input id="set-openrouter" type="password" style="flex:1;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;box-sizing:border-box;font-family:var(--mono)">
        <button onclick="clearKeyInput('set-openrouter')" style="background:none;border:1px solid var(--border);border-radius:6px;color:var(--sub);cursor:pointer;padding:0 8px;font-size:14px;line-height:1" title="清除">✕</button>
      </div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">DeepSeek API Key</div>
      <div style="display:flex;gap:6px;margin-bottom:12px">
        <input id="set-deepseek" type="password" style="flex:1;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;box-sizing:border-box;font-family:var(--mono)">
        <button onclick="clearKeyInput('set-deepseek')" style="background:none;border:1px solid var(--border);border-radius:6px;color:var(--sub);cursor:pointer;padding:0 8px;font-size:14px;line-height:1" title="清除">✕</button>
      </div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">Kimi API Key <span style="color:var(--sub);font-size:10px">(moonshot.cn)</span></div>
      <div style="display:flex;gap:6px;margin-bottom:12px">
        <input id="set-kimi" type="password" style="flex:1;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;box-sizing:border-box;font-family:var(--mono)">
        <button onclick="clearKeyInput('set-kimi')" style="background:none;border:1px solid var(--border);border-radius:6px;color:var(--sub);cursor:pointer;padding:0 8px;font-size:14px;line-height:1" title="清除">✕</button>
      </div>
    </div>

    <!-- 安全 tab -->
    <div class="settings-tab-panel" id="settings-panel-security">
      <div style="font-size:11px;color:var(--muted);margin-bottom:6px">修改管理员密码</div>
      <input id="set-admin-password" type="password" style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 10px;color:var(--text);font-size:12px;outline:none;box-sizing:border-box;font-family:var(--mono)">
    </div>

    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px">
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
  { id: 'claude-light', name: '珊瑚橙', preview: ['#f5f3ef', '#da7756'] },
  { id: 'claude-dark',  name: '黑曜', preview: ['#131313', '#cdcdcd'] },
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
function switchSettingsTab(name, btn) {
  document.querySelectorAll('.settings-tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
  const panel = document.getElementById('settings-panel-' + name);
  if (panel) panel.classList.add('active');
  if (btn) btn.classList.add('active');
}
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
// Track which keys user explicitly cleared (to send empty string for deletion)
const _clearedKeys = new Set();
function clearKeyInput(inputId) {
  const el = document.getElementById(inputId);
  if (el) { el.value = ''; el.placeholder = '已清除，保存后生效'; }
  // Map input id → settings key
  const keyMap = {'set-openrouter':'openrouter_api_key','set-deepseek':'deepseek_api_key','set-kimi':'kimi_api_key'};
  if (keyMap[inputId]) _clearedKeys.add(keyMap[inputId]);
}
// ── Notification sound ────────────────────────────────────────────────────────
let _notificationSound = localStorage.getItem('mira-notification-sound') || 'Pop';
function previewSound() {
  const sel = document.getElementById('set-notification-sound');
  if (sel) _playSound(sel.value);
}
function _playSound(name) {
  if (!name || name === 'off') return;
  const a = new Audio('/api/sounds/' + encodeURIComponent(name));
  a.play().catch(() => {});
}
function playNotificationSound() { _playSound(_notificationSound); }

async function openSettings() {
  if (!_isAdmin) { openLoginModal(openSettings); return; }
  _clearedKeys.clear();
  const [data, provData, soundData] = await Promise.all([
    fetch('/api/settings', {headers: _authHeaders()}).then(r => r.json()),
    fetch('/api/llm-providers').then(r => r.json()).catch(() => ({providers:[]})),
    fetch('/api/sounds').then(r => r.json()).catch(() => ({sounds:[]})),
  ]);
  document.getElementById('set-openrouter').placeholder = data.openrouter_api_key || 'sk-or-...';
  document.getElementById('set-deepseek').placeholder   = data.deepseek_api_key   || 'sk-...';
  document.getElementById('set-kimi').placeholder       = data.kimi_api_key        || 'sk-...';
  document.getElementById('set-admin-password').placeholder = data.admin_password ? '留空则不修改' : '未设置';
  // Render detected provider tags
  const box = document.getElementById('settings-providers');
  if (box) {
    const providers = provData.providers || [];
    box.innerHTML = providers.length
      ? providers.map(p => `<span style="display:inline-block;padding:3px 10px;background:rgba(var(--accent-rgb),.12);color:var(--accent);border-radius:12px;font-size:11px;font-weight:600">${p}</span>`).join('')
      : '<span style="font-size:11px;color:var(--sub)">未检测到 API 使用</span>';
  }
  // Populate sound selector
  const sel = document.getElementById('set-notification-sound');
  if (sel) {
    const current = data.notification_sound || 'Pop';
    sel.innerHTML = '<option value="off">关闭</option>' +
      (soundData.sounds || []).map(s => `<option value="${s}"${s === current ? ' selected' : ''}>${s}</option>`).join('');
  }
  _renderSettingsSkins();
  document.getElementById('settings-overlay').style.display = 'flex';
}
function closeSettings() { document.getElementById('settings-overlay').style.display = 'none'; }
async function saveSettings() {
  const body = {};
  const keys = {openrouter_api_key:'set-openrouter', deepseek_api_key:'set-deepseek', kimi_api_key:'set-kimi'};
  for (const [k, id] of Object.entries(keys)) {
    const v = document.getElementById(id).value.trim();
    if (v) body[k] = v;                          // user typed a new key
    else if (_clearedKeys.has(k)) body[k] = '';   // user explicitly cleared → delete
    // else: untouched → omit (backend keeps existing)
  }
  body.admin_password = document.getElementById('set-admin-password').value.trim();
  const soundSel = document.getElementById('set-notification-sound');
  if (soundSel) {
    body.notification_sound = soundSel.value;
    _notificationSound = soundSel.value;
    localStorage.setItem('mira-notification-sound', soundSel.value);
  }
  await fetch('/api/settings', {method:'POST', headers: _authHeaders({'Content-Type':'application/json'}), body: JSON.stringify(body)});
  if (body.admin_password) { _adminToken = ''; _isAdmin = false; localStorage.removeItem('mira-admin-token'); }
  closeSettings();
}"""
