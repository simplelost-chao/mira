"""Dev mode page — all active tmux sessions across all projects."""


def render_dev_page() -> str:
    return r'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dev · Mira</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Noto+Sans+SC:wght@400;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #080c14; --panel: rgba(14,20,36,.95); --border: rgba(255,255,255,.07);
    --text: #eef1f7; --sub: #7a8499; --muted: #4a5060;
    --accent: #4f46e5; --accent-rgb: 79,70,229;
    --green: #3fb950; --orange: #e5a650; --red: #e06c75; --yellow: #d29922;
    --mono: 'JetBrains Mono', monospace;
    --sans: 'Noto Sans SC', sans-serif;
    --radius: 8px; --radius-sm: 4px;
  }
  [data-theme="neon-pixel"] {
    --bg: #0a0a0a; --panel: rgba(20,20,20,.95); --border: #00ff00;
    --text: #e0e0ff; --sub: #a0a0cc; --muted: #505070;
    --accent: #ff00ff; --accent-rgb: 255,0,255;
    --green: #00ff00; --orange: #ff8800; --red: #ff0040; --yellow: #ffff00;
    --radius: 0px; --radius-sm: 0px;
  }
  [data-theme="pixel-cyber"] {
    --bg: #020c1a; --panel: rgba(10,31,56,.95); --border: #00d4ff;
    --text: #eef8ff; --sub: #a8daf0; --muted: #6bbad8;
    --accent: #ff0055; --accent-rgb: 255,0,85;
    --green: #00ff88; --orange: #ffaa00; --red: #ff3355; --yellow: #ffaa00;
    --radius: 0px; --radius-sm: 0px;
  }
  [data-theme="pixel-cyber"] body {
    background-image: linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px);
    background-size: 8px 8px;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--mono); min-height: 100vh; overflow-x: hidden; }

  /* ── Topbar ── */
  .topbar {
    position: sticky; top: 0; z-index: 100;
    background: var(--panel); border-bottom: 1px solid var(--border);
    backdrop-filter: blur(12px);
    display: flex; align-items: center; gap: 12px; padding: 0 20px; height: 52px;
  }
  .topbar-logo {
    display: inline-flex; align-items: baseline; gap: 0;
    letter-spacing: 3px; line-height: 1; text-transform: uppercase; flex-shrink: 0;
  }
  .topbar-logo .logo-m { font-size: 22px; font-weight: 900; color: var(--accent); text-shadow: 0 0 10px var(--accent); }
  .topbar-logo .logo-ira { font-size: 16px; font-weight: 700; color: var(--text); opacity: .75; }
  .topbar-logo .logo-cursor { font-size: 18px; font-weight: 400; color: var(--accent); opacity: .9; animation: logo-blink 1.1s step-end infinite; }
  @keyframes logo-blink { 0%,100%{opacity:.9}50%{opacity:0} }
  .topbar-sep { width: 1px; height: 18px; background: var(--border); flex-shrink: 0; }
  .topbar-page-title { font-size: 12px; color: var(--sub); letter-spacing: 1px; text-transform: uppercase; font-weight: 700; }
  .topbar-spacer { flex: 1; }
  .topbar-back {
    display: inline-flex; align-items: center; gap: 5px;
    color: var(--sub); font-size: 12px; text-decoration: none;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 3px 10px; transition: all .15s; white-space: nowrap;
  }
  .topbar-back:hover { color: var(--text); border-color: var(--accent); }
  .topbar-btn {
    background: none; border: 1px solid var(--border); border-radius: var(--radius-sm);
    color: var(--sub); font-size: 13px; padding: 3px 10px; cursor: pointer;
    font-family: var(--mono); transition: all .15s;
  }
  .topbar-btn:hover { border-color: var(--accent); color: var(--accent); }
  .skin-wrap { position: relative; }
  .skin-picker {
    display: none; position: fixed;
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 10px; padding: 10px; z-index: 9999;
    box-shadow: 0 8px 32px rgba(0,0,0,.5); min-width: 180px;
  }
  .skin-picker.open { display: block; }
  .skin-picker-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
  .skin-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .skin-card { border: 1px solid var(--border); border-radius: 7px; padding: 8px; cursor: pointer; transition: border-color .15s; }
  .skin-card:hover, .skin-card.active { border-color: var(--accent); }
  .skin-preview { height: 28px; border-radius: 4px; overflow: hidden; display: grid; grid-template-columns: 1fr 1fr; margin-bottom: 6px; }
  .skin-preview div { height: 100%; }
  .skin-name { font-size: 11px; color: var(--sub); text-align: center; }

  /* ── Main layout ── */
  .dev-page {
    height: calc(100vh - 52px);
    display: flex;
    overflow: hidden;
  }

  /* ── Sidebar (pane list) ── */
  .term-sidebar {
    width: 200px; border-right: 1px solid var(--border);
    display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden;
  }
  .term-sidebar-header {
    padding: 10px 14px; font-size: 10px; color: var(--muted);
    font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  #term-pane-list { flex: 1; overflow-y: auto; }
  .term-pane-row {
    padding: 10px 14px; display: flex; align-items: flex-start; gap: 8px;
    cursor: pointer; border-left: 2px solid transparent; transition: background .12s, border-color .12s;
  }
  .term-pane-row:hover { background: rgba(255,255,255,.03); }
  .term-pane-row.active { background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }
  .term-pane-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
  .term-pane-dot.running { background: var(--green); box-shadow: 0 0 5px rgba(63,185,80,.5); }
  .term-pane-dot.waiting { background: var(--yellow); }
  .term-pane-info { min-width: 0; flex: 1; }
  .term-pane-name { font-size: 12px; color: var(--text); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-pane-proj { font-size: 10px; color: var(--sub); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-pane-cmd  { font-size: 9px; color: var(--muted); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-sidebar-footer {
    padding: 8px 14px; font-size: 10px; color: var(--muted);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
  .term-empty-sidebar { padding: 32px 16px; font-size: 12px; color: var(--muted); line-height: 1.8; }
  .term-empty-sidebar code { color: var(--sub); }

  /* ── Terminal main ── */
  .term-main { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
  .term-titlebar {
    padding: 7px 14px; display: flex; align-items: center;
    justify-content: space-between; border-bottom: 1px solid var(--border);
    flex-shrink: 0; gap: 8px;
  }
  .term-title-left { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
  .term-back-btn {
    display: none;
    background: none; border: none; color: var(--accent);
    font-size: 16px; padding: 0 6px 0 0; cursor: pointer; flex-shrink: 0;
    line-height: 1;
  }
  #term-title { font-size: 11px; color: var(--sub); font-family: var(--mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-quickbtns { display: flex; gap: 6px; flex-shrink: 0; }
  .term-qbtn {
    background: var(--panel); border: 1px solid var(--border);
    color: var(--muted); font-size: 10px; padding: 2px 8px;
    border-radius: var(--radius-sm); cursor: pointer; font-family: var(--mono); transition: all .12s;
  }
  .term-qbtn:hover { border-color: var(--accent); color: var(--accent); }
  .term-output {
    flex: 1; padding: 12px 16px; font-family: var(--mono);
    font-size: 12px; line-height: 1.6; overflow-y: auto;
    white-space: pre-wrap; word-break: break-all; color: var(--text);
  }
  .term-empty {
    height: 100%; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: var(--muted); font-size: 13px; text-align: center; gap: 10px; line-height: 1.7;
  }
  .term-empty code { color: var(--sub); font-size: 11px; }
  .term-inputbar {
    padding: 8px 12px; border-top: 1px solid var(--border);
    display: flex; gap: 8px; flex-shrink: 0; background: var(--panel);
  }
  .term-input {
    flex: 1; background: rgba(255,255,255,.04); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 7px 10px; color: var(--text);
    font-family: var(--mono); font-size: 12px; outline: none; transition: border-color .15s;
  }
  .term-input:focus { border-color: var(--accent); }
  .term-input:disabled { opacity: .4; cursor: not-allowed; }
  .term-send-btn {
    background: var(--accent); border: none; color: #fff;
    padding: 7px 16px; border-radius: var(--radius-sm); font-size: 12px;
    cursor: pointer; font-family: var(--mono); transition: opacity .12s; flex-shrink: 0;
  }
  .term-send-btn:hover { opacity: .85; }
  .term-send-btn:disabled { opacity: .4; cursor: not-allowed; }

  /* ── Mobile: master-detail (≤ 900px) ── */
  @media (max-width: 900px) {
    .topbar { padding: 0 14px; gap: 8px; height: 48px; }
    .topbar-logo { letter-spacing: 1px; }
    .topbar-logo .logo-m { font-size: 20px; }
    .topbar-logo .logo-ira { font-size: 14px; }
    .topbar-logo .logo-cursor { font-size: 16px; }
    .topbar-page-title { display: none; }
    .topbar-sep { display: none; }
    .dev-page { height: calc(100vh - 48px); }

    /* List view (default): sidebar fills full screen */
    .term-sidebar { width: 100%; flex: 1; border-right: none; }
    .term-sidebar-header { padding: 14px 16px 10px; font-size: 11px; letter-spacing: .5px; text-transform: none; font-weight: 700; }
    .term-sidebar-footer { display: none; }
    #term-pane-list { padding: 0; }
    .term-pane-row {
      position: relative;
      padding: 14px 48px 14px 16px;
      border-left: none;
      border-bottom: 1px solid var(--border);
      border-radius: 0;
      gap: 10px;
    }
    .term-pane-row::after {
      content: '›';
      position: absolute; right: 16px; top: 50%;
      transform: translateY(-50%);
      color: var(--muted); font-size: 22px; line-height: 1;
    }
    .term-pane-row:hover { border-left-color: transparent; }
    .term-pane-row.active { border-left-color: transparent; background: rgba(var(--accent-rgb),.08); }
    .term-pane-dot { margin-top: 6px; }
    .term-pane-name { font-size: 14px; }
    .term-pane-proj { font-size: 12px; margin-top: 3px; }
    .term-pane-cmd  { font-size: 10px; }

    /* Detail view: hidden until .detail-open */
    .term-main { display: none; }
    .dev-page.detail-open .term-sidebar { display: none; }
    .dev-page.detail-open .term-main { display: flex; flex: 1; }

    /* Back button */
    .term-back-btn { display: inline-flex; align-items: center; }

    /* Terminal adjustments */
    .term-output { font-size: 11px; padding: 8px 12px; }
    .term-input { font-size: 14px; padding: 8px 10px; }
    .term-send-btn { padding: 8px 16px; font-size: 13px; }
    .term-inputbar { padding: 8px 10px; }
    .term-qbtn { padding: 4px 10px; }
  }
</style>
</head>
<body>

<div class="topbar">
  <span class="topbar-logo">
    <span class="logo-m">M</span><span class="logo-ira">IRA</span><span class="logo-cursor">_</span>
  </span>
  <div class="topbar-sep"></div>
  <span class="topbar-page-title">Dev</span>
  <div class="topbar-spacer"></div>
  <a class="topbar-back" href="/">← 返回</a>
  <button class="topbar-btn" onclick="openSettings()">⚙</button>
  <div class="skin-wrap">
    <button class="topbar-btn" id="skin-btn" onclick="toggleSkinPicker()">◈</button>
    <div class="skin-picker" id="skin-picker"></div>
  </div>
</div>

<div class="dev-page" id="dev-page">
  <!-- Sidebar: pane list -->
  <div class="term-sidebar">
    <div class="term-sidebar-header">所有终端</div>
    <div id="term-pane-list">
      <div class="term-empty-sidebar">正在加载…</div>
    </div>
    <div class="term-sidebar-footer">每 5 秒刷新列表</div>
  </div>

  <!-- Main: terminal output -->
  <div class="term-main">
    <div class="term-titlebar">
      <div class="term-title-left">
        <button class="term-back-btn" onclick="goBackToList()">‹</button>
        <span id="term-title"></span>
      </div>
      <div class="term-quickbtns">
        <button class="term-qbtn" id="btn-ctrlc">Ctrl+C</button>
        <button class="term-qbtn" id="btn-enter">↵ Enter</button>
      </div>
    </div>
    <div class="term-output" id="term-output">
      <div class="term-empty">
        <div style="font-size:28px;opacity:.3">⬛</div>
        <div>从左侧选择一个终端</div>
        <div><code>mira term &lt;project&gt;</code> 启动新会话</div>
      </div>
    </div>
    <div class="term-inputbar">
      <input class="term-input" id="term-input" placeholder="发送按键…" disabled
             onkeydown="if(event.key==='Enter')sendKeys()">
      <button class="term-send-btn" id="term-send-btn" onclick="sendKeys()" disabled>发送</button>
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
</div>

<!-- Settings overlay -->
<div id="settings-overlay" style="display:none;position:fixed;inset:0;z-index:400;background:rgba(0,0,0,.6);align-items:center;justify-content:center;"
     onclick="if(event.target===this)closeSettings()" class="settings-ov-open">
  <div style="background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:28px;width:360px;max-width:94vw">
    <div style="font-size:15px;font-weight:700;margin-bottom:18px">⚙ 设置</div>
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

<script>
// ── Helpers ──────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Auth ─────────────────────────────────────────────────────────────────────
let _adminToken = localStorage.getItem('mira-admin-token') || '';
let _isAdmin = false;

function _authHeaders(extra = {}) {
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

// ── Settings ──────────────────────────────────────────────────────────────────
async function openSettings() {
  if (!_isAdmin) { openLoginModal(openSettings); return; }
  const data = await fetch('/api/settings', {headers: _authHeaders()}).then(r => r.json());
  document.getElementById('set-openrouter').placeholder = data.openrouter_api_key || 'sk-or-...';
  document.getElementById('set-deepseek').placeholder   = data.deepseek_api_key   || 'sk-...';
  document.getElementById('set-kimi').placeholder       = data.kimi_api_key        || 'sk-...';
  document.getElementById('set-admin-password').placeholder = data.admin_password ? '留空则不修改' : '未设置';
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
function renderSkinPicker() {
  const picker = document.getElementById('skin-picker');
  const current = document.documentElement.dataset.theme || 'default';
  picker.innerHTML =
    `<div class="skin-picker-label">选择皮肤</div><div class="skin-grid">` +
    SKINS.map(s =>
      `<div class="skin-card ${s.id === current ? 'active' : ''}" data-skin-id="${s.id}"
            onclick="applySkin(this.dataset.skinId);toggleSkinPicker();">
        <div class="skin-preview"><div style="background:${s.preview[0]}"></div><div style="background:${s.preview[1]}"></div></div>
        <div class="skin-name">${s.name}</div>
      </div>`
    ).join('') + `</div>`;
}
function toggleSkinPicker() {
  const picker = document.getElementById('skin-picker');
  const open = picker.classList.toggle('open');
  if (open) {
    renderSkinPicker();
    const btn = document.getElementById('skin-btn');
    const rect = btn.getBoundingClientRect();
    picker.style.top = (rect.bottom + 8) + 'px';
    picker.style.right = (window.innerWidth - rect.right) + 'px';
  }
}
document.addEventListener('click', e => {
  if (!e.target.closest('.skin-wrap')) document.getElementById('skin-picker')?.classList.remove('open');
});
applySkin(localStorage.getItem('mira-skin') || 'default');

// ── State ─────────────────────────────────────────────────────────────────────
let _currentTarget = null;
let _pollTimer = null;
let _pollGen = 0;
let _autoScroll = true;

// ── Pane list ─────────────────────────────────────────────────────────────────
async function loadPanes() {
  if (!_isAdmin) { openLoginModal(init); return; }
  try {
    const res = await fetch('/api/dev/panes', {headers: _authHeaders()});
    if (res.status === 401) { openLoginModal(init); return; }
    if (!res.ok) return;
    const panes = await res.json();
    const list = document.getElementById('term-pane-list');
    if (!panes.length) {
      list.innerHTML = `<div class="term-empty-sidebar">暂无活跃终端<br><br><code>mira term &lt;project&gt;</code><br>启动新会话</div>`;
      return;
    }
    list.innerHTML = panes.map(p => `
      <div class="term-pane-row${_currentTarget === p.target ? ' active' : ''}"
           data-target="${escHtml(p.target)}"
           data-cmd="${escHtml(p.command || '')}">
        <div class="term-pane-dot ${p.waiting ? 'waiting' : 'running'}"></div>
        <div class="term-pane-info">
          <div class="term-pane-name">${escHtml(p.label)}</div>
          <div class="term-pane-proj">${escHtml(p.project_id || p.target)}</div>
          ${p.command ? `<div class="term-pane-cmd">${escHtml(p.command)}</div>` : ''}
        </div>
      </div>`).join('');
    list.querySelectorAll('.term-pane-row').forEach(row => {
      row.addEventListener('click', () => selectPane(row.dataset.target, row.dataset.cmd));
    });
    const targets = new Set(panes.map(p => p.target));
    if (_currentTarget && !targets.has(_currentTarget)) {
      _currentTarget = null; stopPoll();
    }
  } catch(e) { console.warn('dev panes:', e); }
}

// ── Pane selection ────────────────────────────────────────────────────────────
function selectPane(target, cmd) {
  _pollGen++;
  _currentTarget = target;
  _autoScroll = true;

  document.querySelectorAll('.term-pane-row').forEach(r =>
    r.classList.toggle('active', r.dataset.target === target));

  document.getElementById('term-title').textContent = target + (cmd ? '  ·  ' + cmd : '');
  document.getElementById('term-input').disabled = false;
  document.getElementById('term-send-btn').disabled = false;
  document.getElementById('term-output').textContent = '';

  // Mobile: show detail view
  document.getElementById('dev-page').classList.add('detail-open');

  stopPoll();
  startPoll();
}

function goBackToList() {
  stopPoll();
  _currentTarget = null;
  document.getElementById('dev-page').classList.remove('detail-open');
  document.getElementById('term-input').disabled = true;
  document.getElementById('term-send-btn').disabled = true;
  document.getElementById('term-title').textContent = '';
  document.getElementById('term-output').innerHTML =
    `<div class="term-empty"><div style="font-size:28px;opacity:.3">⬛</div><div>从左侧选择一个终端</div><div><code>mira term &lt;project&gt;</code> 启动新会话</div></div>`;
}

// ── Output polling ────────────────────────────────────────────────────────────
function startPoll() {
  if (_pollTimer) return;
  _pollTimer = setTimeout(runPoll, 0);
}
function stopPoll() {
  if (_pollTimer) { clearTimeout(_pollTimer); _pollTimer = null; }
  _pollGen++;
}
async function runPoll() {
  if (!_pollTimer) return;
  await fetchOutput();
  if (_pollTimer) _pollTimer = setTimeout(runPoll, 500);
}
async function fetchOutput() {
  if (!_currentTarget) return;
  const gen = _pollGen;
  try {
    const res = await fetch(
      `/api/terminals/${encodeURIComponent(_currentTarget)}/output?lines=200`,
      {headers: _authHeaders()});
    if (_pollGen !== gen) return;
    if (!res.ok) return;
    const data = await res.json();
    const el = document.getElementById('term-output');
    if (!el) return;
    el.textContent = data.output || '';
    if (_autoScroll) el.scrollTop = el.scrollHeight;
  } catch(e) {}
}

document.getElementById('term-output').addEventListener('scroll', function() {
  _autoScroll = Math.abs(this.scrollHeight - this.scrollTop - this.clientHeight) < 60;
});

// ── Send ──────────────────────────────────────────────────────────────────────
function sendKeys() {
  const inp = document.getElementById('term-input');
  const keys = inp.value.trim();
  if (!keys || !_currentTarget) return;
  inp.value = '';
  fetch(`/api/terminals/${encodeURIComponent(_currentTarget)}/send`, {
    method: 'POST',
    headers: _authHeaders({'Content-Type': 'application/json'}),
    body: JSON.stringify({keys: keys + '\n'})
  }).catch(() => {});
}

function sendRaw(keys) {
  if (!_currentTarget) return;
  fetch(`/api/terminals/${encodeURIComponent(_currentTarget)}/send`, {
    method: 'POST',
    headers: _authHeaders({'Content-Type': 'application/json'}),
    body: JSON.stringify({keys})
  }).catch(() => {});
}

document.getElementById('btn-ctrlc').addEventListener('click', () => sendRaw('C-c'));
document.getElementById('btn-enter').addEventListener('click', () => sendRaw('\n'));

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await _initAuth();
  if (!_isAdmin) { openLoginModal(init); return; }
  await loadPanes();
  setInterval(loadPanes, 5000);
}
init();
</script>
</body>
</html>'''
