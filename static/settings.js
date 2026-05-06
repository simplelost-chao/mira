/**
 * Shared settings overlay — single source of truth for all Mira pages.
 *
 * Usage: include <script src="/static/settings.js"></script> then call initSettings().
 * Requires: _isAdmin, _adminToken, _authHeaders(), openLoginModal() from the host page.
 */

/* ── CSS (injected once) ───────────────────────────────────────────────────── */
(function injectSettingsCSS() {
  if (document.getElementById('mira-settings-css')) return;
  const style = document.createElement('style');
  style.id = 'mira-settings-css';
  style.textContent = `
.settings-overlay {
  display: none; position: fixed; inset: 0; z-index: 400;
  background: rgba(0,0,0,.6);
  align-items: center; justify-content: center;
}
.settings-overlay.open { display: flex; }
.settings-modal {
  background: var(--card, var(--panel)); border: 1px solid var(--border);
  border-radius: 12px; width: 100%; max-width: 420px; padding: 24px;
  max-height: 90vh; overflow-y: auto;
}
.settings-title { font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 16px; }
.settings-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 18px; }
.settings-tab {
  padding: 8px 16px; font-size: 12px; color: var(--text-muted, var(--muted)); cursor: pointer;
  border: none; border-bottom: 2px solid transparent; background: none;
  font-family: var(--font-mono, var(--mono)); letter-spacing: .5px; transition: all .15s;
}
.settings-tab:hover { color: var(--text); }
.settings-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.settings-tab-panel { display: none; }
.settings-tab-panel.active { display: block; }
.settings-group { margin-bottom: 16px; }
.settings-label { font-size: 11px; color: var(--text-muted, var(--muted)); margin-bottom: 6px; letter-spacing: .5px; }
.settings-input {
  width: 100%; box-sizing: border-box;
  background: var(--card-deep, var(--bg)); border: 1px solid var(--border);
  border-radius: 6px; padding: 8px 10px;
  color: var(--text); font-size: 13px; font-family: var(--font-mono, var(--mono));
  outline: none; transition: border-color .15s;
}
.settings-input:focus { border-color: var(--accent); }
.settings-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 24px; }
.settings-btn-cancel {
  padding: 7px 16px; background: var(--card-deep, var(--bg)); border: 1px solid var(--border);
  border-radius: 6px; color: var(--text-sec, var(--sub)); cursor: pointer; font-size: 13px;
  font-family: var(--font-mono, var(--mono));
}
.settings-btn-save {
  padding: 7px 16px; background: var(--accent); border: none;
  border-radius: 6px; color: #fff; cursor: pointer; font-size: 13px;
  font-family: var(--font-mono, var(--mono));
}
.settings-clear-btn {
  background: none; border: 1px solid var(--border); border-radius: 6px;
  color: var(--text-muted, var(--muted)); cursor: pointer;
  padding: 0 8px; font-size: 14px; line-height: 1;
}
.settings-clear-btn:hover { border-color: var(--accent); color: var(--accent); }
.skin-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.skin-card {
  border: 1px solid var(--border); border-radius: 7px;
  padding: 8px; cursor: pointer; transition: border-color .15s;
}
.skin-card:hover { border-color: var(--accent); }
.skin-card.active { border-color: var(--accent); background: rgba(var(--accent-rgb), .1); }
.skin-preview {
  height: 28px; border-radius: 4px; overflow: hidden;
  display: grid; grid-template-columns: 1fr 1fr; margin-bottom: 6px;
}
.skin-preview div { height: 100%; }
.skin-name { font-size: 11px; color: var(--text-sec, var(--sub)); text-align: center; }

/* Remote hosts */
.rhost-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.rhost-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; background: var(--card-deep, var(--bg));
  border: 1px solid var(--border); border-radius: 8px;
}
.rhost-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.rhost-dot.online { background: var(--green, #22c55e); box-shadow: 0 0 5px var(--green, #22c55e); }
.rhost-dot.offline { background: var(--text-muted, #64748b); }
.rhost-dot.unknown { background: var(--border); }
.rhost-info { flex: 1; min-width: 0; }
.rhost-alias { font-size: 12px; font-weight: 600; color: var(--text); }
.rhost-url { font-size: 10px; color: var(--text-muted, var(--muted)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rhost-actions { display: flex; gap: 4px; flex-shrink: 0; }
.rhost-btn {
  background: none; border: 1px solid var(--border); border-radius: 5px;
  color: var(--text-muted, var(--muted)); cursor: pointer; padding: 2px 8px;
  font-size: 11px; transition: all .12s;
}
.rhost-btn:hover { border-color: var(--accent); color: var(--accent); }
.rhost-btn.danger:hover { border-color: var(--red, #ef4444); color: var(--red, #ef4444); }
.rhost-add-form { display: flex; flex-direction: column; gap: 8px; }
.rhost-add-row { display: flex; gap: 6px; }
.rhost-add-row .settings-input { flex: 1; font-size: 12px; padding: 6px 8px; }
.rhost-guide {
  margin-top: 12px; padding: 12px; background: var(--card-deep, var(--bg));
  border: 1px solid var(--border); border-radius: 8px;
  font-size: 11px; color: var(--text-sec, var(--sub)); line-height: 1.6;
}
.rhost-guide summary {
  font-weight: 600; color: var(--text); cursor: pointer; font-size: 12px;
  margin-bottom: 6px;
}
.rhost-guide code {
  background: rgba(255,255,255,.06); padding: 1px 5px; border-radius: 3px;
  font-family: var(--font-mono, var(--mono)); font-size: 11px;
}
.rhost-guide h4 { color: var(--accent); font-size: 11px; margin: 8px 0 4px; font-weight: 600; }
`;
  document.head.appendChild(style);
})();

/* ── Escape helpers ────────────────────────────────────────────────────────── */
function _escSettings(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
function _escAttr(s) {
  return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* ── Skin system ───────────────────────────────────────────────────────────── */
const SKINS = [
  { id: 'default',      name: '深空默认', preview: ['#0f1117', '#4f46e5'] },
  { id: 'claude-light',  name: '珊瑚橙',  preview: ['#f5f3ef', '#da7756'] },
  { id: 'claude-dark',   name: '黑曜',    preview: ['#131313', '#09B83E'] },
  { id: 'neon-pixel',   name: '霓虹像素', preview: ['#0a0a0a', '#ff00ff'] },
  { id: 'pixel-cyber',  name: '像素赛博', preview: ['#000d1a', '#ff0066'] },
];

function applySkin(id) {
  const skin = SKINS.find(s => s.id === id) ? id : 'default';
  document.documentElement.dataset.theme = skin;
  localStorage.setItem('mira-skin', skin);
}
// Apply saved skin immediately
applySkin(localStorage.getItem('mira-skin') || 'default');

/* ── Dev flat list toggle ──────────────────────────────────────────────────── */
function toggleDevFlatList(on) {
  localStorage.setItem('mira-dev-flat-list', on ? '1' : '');
}

/* ── Notification sound ────────────────────────────────────────────────────── */
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

/* ── Settings state ────────────────────────────────────────────────────────── */
const _clearedKeys = new Set();

function clearKeyInput(inputId) {
  const el = document.getElementById(inputId);
  if (el) { el.value = ''; el.placeholder = '已清除，保存后生效'; }
  const keyMap = { 'set-openrouter': 'openrouter_api_key', 'set-deepseek': 'deepseek_api_key', 'set-kimi': 'kimi_api_key', 'set-gemini': 'gemini_api_key', 'set-doubao': 'doubao_api_key', 'set-doubao-ak': 'doubao_access_key', 'set-doubao-sk': 'doubao_secret_key' };
  if (keyMap[inputId]) _clearedKeys.add(keyMap[inputId]);
}

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
      <div class="skin-name">${_escSettings(s.name)}</div>
    </div>`
  ).join('');
}

/* ── Inject overlay HTML ───────────────────────────────────────────────────── */
function initSettings() {
  if (document.getElementById('settings-overlay')) return;
  const html = `
<div class="settings-overlay" id="settings-overlay" onclick="if(event.target===this)closeSettings()">
  <div class="settings-modal">
    <div class="settings-title">设置</div>
    <div class="settings-tabs">
      <button class="settings-tab active" onclick="switchSettingsTab('appearance',this)">外观</button>
      <button class="settings-tab" onclick="switchSettingsTab('api',this)">API</button>
      <button class="settings-tab" onclick="switchSettingsTab('hosts',this)">远程主机</button>
      <button class="settings-tab" onclick="switchSettingsTab('security',this)">安全</button>
    </div>

    <!-- 外观 tab -->
    <div class="settings-tab-panel active" id="settings-panel-appearance">
      <div class="settings-group">
        <div class="settings-label" style="text-transform:uppercase;letter-spacing:1px">皮肤</div>
        <div class="skin-grid" id="settings-skin-grid"></div>
      </div>
      <div class="settings-group">
        <div class="settings-label" style="text-transform:uppercase;letter-spacing:1px">终端列表</div>
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:12px;color:var(--sub)">
          <input type="checkbox" id="set-dev-flat-list" onchange="toggleDevFlatList(this.checked)" style="accent-color:var(--accent)">
          平铺模式（不按项目分组）
        </label>
      </div>
      <div class="settings-group">
        <div class="settings-label" style="text-transform:uppercase;letter-spacing:1px">提示音效</div>
        <div style="display:flex;gap:6px;align-items:center">
          <select class="settings-input" id="set-notification-sound" style="flex:1;appearance:auto"></select>
          <button onclick="previewSound()" style="background:none;border:1px solid var(--border);border-radius:6px;color:var(--text-muted,var(--muted));cursor:pointer;padding:4px 10px;font-size:12px" title="试听">&#9654;</button>
        </div>
      </div>
    </div>

    <!-- API tab -->
    <div class="settings-tab-panel" id="settings-panel-api">
      <div class="settings-group">
        <div class="settings-label" style="text-transform:uppercase;letter-spacing:1px">项目使用的 API</div>
        <div id="settings-providers" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:6px;min-height:24px"></div>
        <div style="font-size:10px;color:var(--text-muted,var(--muted))">检测自你的所有项目</div>
      </div>
      <div style="height:1px;background:var(--border);margin-bottom:16px"></div>
      <div style="font-size:11px;color:var(--text-muted,var(--muted));margin-bottom:4px;text-transform:uppercase;letter-spacing:1px">余额监控（选填）</div>
      <div style="font-size:10px;color:var(--text-sec,var(--sub));margin-bottom:12px">填入 API Key 后，首页将显示余额信息</div>
      <div class="settings-group">
        <div class="settings-label">OpenRouter API Key</div>
        <div style="display:flex;gap:6px">
          <input class="settings-input" id="set-openrouter" type="password" placeholder="sk-or-..." autocomplete="off" style="flex:1">
          <button class="settings-clear-btn" onclick="clearKeyInput('set-openrouter')" title="清除">✕</button>
        </div>
      </div>
      <div class="settings-group">
        <div class="settings-label">DeepSeek API Key</div>
        <div style="display:flex;gap:6px">
          <input class="settings-input" id="set-deepseek" type="password" placeholder="sk-..." autocomplete="off" style="flex:1">
          <button class="settings-clear-btn" onclick="clearKeyInput('set-deepseek')" title="清除">✕</button>
        </div>
      </div>
      <div class="settings-group">
        <div class="settings-label">Kimi (Moonshot) API Key</div>
        <div style="display:flex;gap:6px">
          <input class="settings-input" id="set-kimi" type="password" placeholder="sk-..." autocomplete="off" style="flex:1">
          <button class="settings-clear-btn" onclick="clearKeyInput('set-kimi')" title="清除">✕</button>
        </div>
      </div>
      <div class="settings-group">
        <div class="settings-label">Gemini API Key</div>
        <div style="display:flex;gap:6px">
          <input class="settings-input" id="set-gemini" type="password" placeholder="AIza..." autocomplete="off" style="flex:1">
          <button class="settings-clear-btn" onclick="clearKeyInput('set-gemini')" title="清除">✕</button>
        </div>
      </div>
      <div class="settings-group">
        <div class="settings-label">豆包 ARK API Key <span style="font-weight:400;color:var(--text-muted,var(--muted));font-size:10px">（LLM 推理用，不含余额）</span></div>
        <div style="display:flex;gap:6px">
          <input class="settings-input" id="set-doubao" type="password" placeholder="..." autocomplete="off" style="flex:1">
          <button class="settings-clear-btn" onclick="clearKeyInput('set-doubao')" title="清除">✕</button>
        </div>
      </div>
      <div class="settings-group">
        <div class="settings-label">豆包 Access Key <span style="font-weight:400;color:var(--text-muted,var(--muted));font-size:10px">（余额查询，火山引擎 AK）</span></div>
        <div style="display:flex;gap:6px">
          <input class="settings-input" id="set-doubao-ak" type="password" placeholder="AKxx..." autocomplete="off" style="flex:1">
          <button class="settings-clear-btn" onclick="clearKeyInput('set-doubao-ak')" title="清除">✕</button>
        </div>
      </div>
      <div class="settings-group">
        <div class="settings-label">豆包 Secret Key <span style="font-weight:400;color:var(--text-muted,var(--muted));font-size:10px">（余额查询，火山引擎 SK）</span></div>
        <div style="display:flex;gap:6px">
          <input class="settings-input" id="set-doubao-sk" type="password" placeholder="..." autocomplete="off" style="flex:1">
          <button class="settings-clear-btn" onclick="clearKeyInput('set-doubao-sk')" title="清除">✕</button>
        </div>
      </div>
    </div>

    <!-- 远程主机 tab -->
    <div class="settings-tab-panel" id="settings-panel-hosts">
      <div class="settings-group">
        <div class="settings-label" style="text-transform:uppercase;letter-spacing:1px">已连接主机</div>
        <div class="rhost-list" id="rhost-list">
          <div style="font-size:11px;color:var(--text-muted)">加载中...</div>
        </div>
      </div>
      <div class="settings-group">
        <div class="settings-label" style="text-transform:uppercase;letter-spacing:1px">添加主机</div>
        <div class="rhost-add-form">
          <div class="rhost-add-row">
            <input class="settings-input" id="rhost-add-alias" placeholder="别名（如 macbook-pro）" autocomplete="off">
          </div>
          <div class="rhost-add-row">
            <input class="settings-input" id="rhost-add-url" placeholder="地址（如 http://100.64.0.2:8888）" autocomplete="off">
          </div>
          <div class="rhost-add-row">
            <input class="settings-input" id="rhost-add-password" type="password" placeholder="管理员密码（选填）" autocomplete="off">
            <button class="rhost-btn" onclick="_addRemoteHost()" style="white-space:nowrap">+ 添加</button>
          </div>
        </div>
      </div>
      <details class="rhost-guide">
        <summary>如何添加一台新主机？</summary>
        <h4>macOS</h4>
        1. 在目标 Mac 上安装 Mira（<code>pip install -e .</code> 或 clone 代码）<br>
        2. 启动服务，监听所有接口：<br>
        <code>cd ~/GitHub/mira && vibe serve --host 0.0.0.0</code><br>
        3. 获取 Tailscale IP：<code>tailscale ip -4</code><br>
        4. 在上方填入别名、地址（http://IP:8888）和密码<br>
        <h4>Windows</h4>
        1. 安装 Python 3.10+ 和 Git<br>
        2. 克隆 Mira：<code>git clone https://github.com/user/mira.git</code><br>
        3. 安装依赖：<code>pip install -e .</code><br>
        4. 启动服务：<code>vibe serve --host 0.0.0.0</code><br>
        5. 获取 Tailscale IP：<code>tailscale ip -4</code><br>
        6. Windows 防火墙需放行端口 8888<br>
        <h4>Linux</h4>
        步骤同 macOS。如有防火墙：<code>sudo ufw allow 8888/tcp</code><br>
        <h4>网络要求</h4>
        所有主机需在同一 Tailscale 网络（或局域网）中。<br>
        确保目标主机的 Mira 使用 <code>--host 0.0.0.0</code> 启动，否则仅监听 localhost。
      </details>
    </div>

    <!-- 安全 tab -->
    <div class="settings-tab-panel" id="settings-panel-security">
      <div class="settings-group">
        <div class="settings-label">修改管理员密码</div>
        <input class="settings-input" id="set-admin-password" type="password" placeholder="留空则不修改" autocomplete="new-password">
      </div>
    </div>

    <div class="settings-footer">
      <button id="settings-logout-btn" onclick="if(typeof logout==='function')logout();closeSettings()" style="display:none;margin-right:auto;background:none;border:1px solid var(--border);color:var(--text-muted,var(--muted));padding:7px 14px;border-radius:6px;cursor:pointer;font-size:13px" title="退出登录">退出登录</button>
      <button class="settings-btn-cancel" onclick="closeSettings()">取消</button>
      <button class="settings-btn-save" onclick="saveSettings()">保存</button>
    </div>
  </div>
</div>`;
  document.body.insertAdjacentHTML('beforeend', html);
}

/* ── Open / close / save ───────────────────────────────────────────────────── */
async function openSettings() {
  if (!_isAdmin) { openLoginModal(openSettings); return; }
  _clearedKeys.clear();
  const [data, provData, soundData] = await Promise.all([
    fetch('/api/settings', { headers: _authHeaders() }).then(r => r.json()),
    fetch('/api/llm-providers').then(r => r.json()).catch(() => ({ providers: [] })),
    fetch('/api/sounds').then(r => r.json()).catch(() => ({ sounds: [] })),
  ]);
  // Clear previous values
  ['set-openrouter', 'set-deepseek', 'set-kimi', 'set-gemini', 'set-doubao', 'set-doubao-ak', 'set-doubao-sk', 'set-admin-password'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('set-openrouter').placeholder = data.openrouter_api_key || 'sk-or-...';
  document.getElementById('set-deepseek').placeholder   = data.deepseek_api_key   || 'sk-...';
  document.getElementById('set-kimi').placeholder       = data.kimi_api_key       || 'sk-...';
  document.getElementById('set-gemini').placeholder       = data.gemini_api_key     || 'AIza...';
  document.getElementById('set-doubao').placeholder       = data.doubao_api_key     || '...';
  document.getElementById('set-doubao-ak').placeholder   = data.doubao_access_key  || 'AKxx...';
  document.getElementById('set-doubao-sk').placeholder   = data.doubao_secret_key  || '...';
  document.getElementById('set-admin-password').placeholder = data.admin_password ? '留空则不修改' : '未设置';
  // Provider tags
  const box = document.getElementById('settings-providers');
  if (box) {
    const providers = provData.providers || [];
    box.innerHTML = providers.length
      ? providers.map(p => `<span style="display:inline-block;padding:3px 10px;background:rgba(var(--accent-rgb),.12);color:var(--accent);border-radius:12px;font-size:11px;font-weight:600">${_escSettings(p)}</span>`).join('')
      : '<span style="font-size:11px;color:var(--text-sec,var(--sub))">未检测到 API 使用</span>';
  }
  // Sound selector
  const sel = document.getElementById('set-notification-sound');
  if (sel) {
    const current = data.notification_sound || 'Pop';
    sel.innerHTML = '<option value="off">关闭</option>' +
      (soundData.sounds || []).map(s => `<option value="${_escAttr(s)}"${s === current ? ' selected' : ''}>${_escSettings(s)}</option>`).join('');
  }
  // Logout button
  const logoutBtn = document.getElementById('settings-logout-btn');
  if (logoutBtn) logoutBtn.style.display = (_isAdmin && _adminToken) ? '' : 'none';

  _renderSettingsSkins();
  // Init dev flat list checkbox
  var _flatCb = document.getElementById('set-dev-flat-list');
  if (_flatCb) _flatCb.checked = !!localStorage.getItem('mira-dev-flat-list');
  _loadRemoteHosts();
  // Reset to first tab
  switchSettingsTab('appearance', document.querySelector('.settings-tab'));
  document.getElementById('settings-overlay').classList.add('open');
}

function closeSettings() {
  document.getElementById('settings-overlay').classList.remove('open');
}

async function saveSettings() {
  const body = {};
  const keys = { openrouter_api_key: 'set-openrouter', deepseek_api_key: 'set-deepseek', kimi_api_key: 'set-kimi', gemini_api_key: 'set-gemini', doubao_api_key: 'set-doubao', doubao_access_key: 'set-doubao-ak', doubao_secret_key: 'set-doubao-sk' };
  for (const [k, id] of Object.entries(keys)) {
    const v = document.getElementById(id).value.trim();
    if (v) body[k] = v;
    else if (_clearedKeys.has(k)) body[k] = '';
  }
  body.admin_password = document.getElementById('set-admin-password').value.trim();
  const soundSel = document.getElementById('set-notification-sound');
  if (soundSel) {
    body.notification_sound = soundSel.value;
    _notificationSound = soundSel.value;
    localStorage.setItem('mira-notification-sound', soundSel.value);
  }
  await fetch('/api/settings', { method: 'POST', headers: _authHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify(body) });
  if (body.admin_password) { _adminToken = ''; _isAdmin = false; localStorage.removeItem('mira-admin-token'); }
  closeSettings();
  // Reload balance if available (homepage)
  if (typeof loadBalance === 'function') loadBalance(true);
}

/* ── Remote Hosts Management ──────────────────────────────────────────────── */

async function _loadRemoteHosts() {
  const list = document.getElementById('rhost-list');
  if (!list) return;
  try {
    const res = await fetch('/api/settings/remote-hosts', { headers: _authHeaders() });
    if (!res.ok) { list.innerHTML = '<div style="font-size:11px;color:var(--text-muted)">加载失败</div>'; return; }
    const data = await res.json();
    const hosts = data.hosts || [];
    if (!hosts.length) {
      list.innerHTML = '<div style="font-size:11px;color:var(--text-muted)">尚未添加远程主机</div>';
      return;
    }
    list.innerHTML = hosts.map(h => {
      const dotCls = h.online === true ? 'online' : h.online === false ? 'offline' : 'unknown';
      const statusText = h.online === true ? '在线' : h.online === false ? '离线' : '未知';
      return `<div class="rhost-item">
        <span class="rhost-dot ${dotCls}" title="${statusText}"></span>
        <div class="rhost-info">
          <div class="rhost-alias">${_escSettings(h.alias)}</div>
          <div class="rhost-url">${_escSettings(h.url)} ${h.has_password ? '🔒' : ''}</div>
        </div>
        <div class="rhost-actions">
          <button class="rhost-btn" data-alias="${_escAttr(h.alias)}" onclick="_testRemoteHost(this.dataset.alias, this)">测试</button>
          <button class="rhost-btn danger" data-alias="${_escAttr(h.alias)}" onclick="_removeRemoteHost(this.dataset.alias)">删除</button>
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    list.innerHTML = '<div style="font-size:11px;color:var(--red)">加载失败: ' + _escSettings(e.message) + '</div>';
  }
}

async function _addRemoteHost() {
  const alias = document.getElementById('rhost-add-alias').value.trim();
  const url = document.getElementById('rhost-add-url').value.trim();
  const password = document.getElementById('rhost-add-password').value.trim();
  if (!alias || !url) { alert('请填写别名和地址'); return; }
  if (alias.includes(':')) { alert('别名不能包含冒号'); return; }
  try {
    const res = await fetch('/api/settings/remote-hosts', {
      method: 'POST',
      headers: _authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ alias, url, admin_password: password }),
    });
    if (!res.ok) { const e = await res.json(); alert(e.detail || '添加失败'); return; }
    document.getElementById('rhost-add-alias').value = '';
    document.getElementById('rhost-add-url').value = '';
    document.getElementById('rhost-add-password').value = '';
    _loadRemoteHosts();
  } catch (e) {
    alert('添加失败: ' + e.message);
  }
}

async function _removeRemoteHost(alias) {
  if (!confirm('确认删除远程主机 "' + alias + '"？')) return;
  try {
    await fetch('/api/settings/remote-hosts/' + encodeURIComponent(alias), {
      method: 'DELETE', headers: _authHeaders(),
    });
    _loadRemoteHosts();
  } catch (e) {
    alert('删除失败: ' + e.message);
  }
}

async function _testRemoteHost(alias, btn) {
  const origText = btn.textContent;
  btn.textContent = '...';
  btn.disabled = true;
  try {
    const res = await fetch('/api/settings/remote-hosts/' + encodeURIComponent(alias) + '/test', {
      method: 'POST', headers: _authHeaders(),
    });
    const data = await res.json();
    if (data.ok) {
      btn.textContent = '✓ ' + data.project_count + ' 项目';
      btn.style.color = 'var(--green, #22c55e)';
      btn.style.borderColor = 'var(--green, #22c55e)';
    } else {
      btn.textContent = '✗ 离线';
      btn.style.color = 'var(--red, #ef4444)';
      btn.style.borderColor = 'var(--red, #ef4444)';
    }
    setTimeout(() => { btn.textContent = origText; btn.style.color = ''; btn.style.borderColor = ''; btn.disabled = false; }, 3000);
    _loadRemoteHosts();
  } catch (e) {
    btn.textContent = '✗ 错误';
    btn.style.color = 'var(--red, #ef4444)';
    setTimeout(() => { btn.textContent = origText; btn.style.color = ''; btn.style.borderColor = ''; btn.disabled = false; }, 3000);
  }
}
