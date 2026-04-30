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
`;
  document.head.appendChild(style);
})();

/* ── Escape helper ─────────────────────────────────────────────────────────── */
function _escSettings(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
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
  const keyMap = { 'set-openrouter': 'openrouter_api_key', 'set-deepseek': 'deepseek_api_key', 'set-kimi': 'kimi_api_key' };
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
      <button class="settings-tab" onclick="switchSettingsTab('security',this)">安全</button>
    </div>

    <!-- 外观 tab -->
    <div class="settings-tab-panel active" id="settings-panel-appearance">
      <div class="settings-group">
        <div class="settings-label" style="text-transform:uppercase;letter-spacing:1px">皮肤</div>
        <div class="skin-grid" id="settings-skin-grid"></div>
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
  ['set-openrouter', 'set-deepseek', 'set-kimi', 'set-admin-password'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  document.getElementById('set-openrouter').placeholder = data.openrouter_api_key || 'sk-or-...';
  document.getElementById('set-deepseek').placeholder   = data.deepseek_api_key   || 'sk-...';
  document.getElementById('set-kimi').placeholder       = data.kimi_api_key       || 'sk-...';
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
      (soundData.sounds || []).map(s => `<option value="${s}"${s === current ? ' selected' : ''}>${_escSettings(s)}</option>`).join('');
  }
  // Logout button
  const logoutBtn = document.getElementById('settings-logout-btn');
  if (logoutBtn) logoutBtn.style.display = (_isAdmin && _adminToken) ? '' : 'none';

  _renderSettingsSkins();
  // Reset to first tab
  switchSettingsTab('appearance', document.querySelector('.settings-tab'));
  document.getElementById('settings-overlay').classList.add('open');
}

function closeSettings() {
  document.getElementById('settings-overlay').classList.remove('open');
}

async function saveSettings() {
  const body = {};
  const keys = { openrouter_api_key: 'set-openrouter', deepseek_api_key: 'set-deepseek', kimi_api_key: 'set-kimi' };
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
