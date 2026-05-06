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
        "    --ansi-0:#0e1420; --ansi-1:var(--red); --ansi-2:var(--green); --ansi-3:var(--yellow);\n"
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
        "    --ansi-0:#0e0e1a; --ansi-4:#00ccff; --ansi-5:#ff00ff; --ansi-6:#00ffff;\n"
        "    --ansi-7:#e0e0ff; --ansi-8:#2a2a40; --ansi-12:#00ccff; --ansi-13:#ff00ff; --ansi-14:#00ffff; --ansi-15:#ffffff;\n"
        "  }\n"
        "  [data-theme=\"pixel-cyber\"] {\n"
        "    --bg: #020c1a; --panel: rgba(10,31,56,.95); --border: #00d4ff;\n"
        "    --text: #eef8ff; --sub: #a8daf0; --muted: #6bbad8;\n"
        "    --accent: #ff0055; --accent-rgb: 255,0,85;\n"
        "    --green: #00ff88; --orange: #ffaa00; --red: #ff3355; --yellow: #ffaa00;\n"
        "    --purple: #a855f7; --gold: #ffaa00;\n"
        "    --radius: 0px; --radius-sm: 0px;\n"
        "    --ansi-0:#04111f; --ansi-4:#00d4ff; --ansi-5:#a855f7; --ansi-6:#00d4ff;\n"
        "    --ansi-7:#eef8ff; --ansi-8:#1a3a50; --ansi-12:#00d4ff; --ansi-13:#a855f7; --ansi-14:#00d4ff; --ansi-15:#ffffff;\n"
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
        "    --ansi-0:#1a1a1a; --ansi-4:#4e9eff; --ansi-5:#c792ea; --ansi-6:#56b6c2;\n"
        "    --ansi-7:#ededed; --ansi-8:#3a3a3a; --ansi-12:#82aaff; --ansi-13:#d9a0f5; --ansi-14:#89ddff; --ansi-15:#ffffff;\n"
        "  }\n"
        "  body { background: var(--bg); color: var(--text); font-family: var(--mono); min-height: 100vh; overflow-x: hidden; padding-top: 52px; }\n"
    )


def topbar_css() -> str:
    """CSS for the topbar and shared skin/settings components."""
    return (
        "  /* ── Topbar ── */\n"
        "  .topbar {\n"
        "    position: fixed; top: 0; left: 0; right: 0; z-index: 100;\n"
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
        "    display: inline-flex; align-items: center; gap: 6px;\n"
        "    cursor: default;\n"
        "  }\n"
        "  .topbar-ring {\n"
        "    position: relative; width: 28px; height: 28px;\n"
        "  }\n"
        "  .topbar-ring svg { transform: rotate(-90deg); }\n"
        "  .topbar-ring-bg { fill: none; stroke: rgba(255,255,255,.08); stroke-width: 3; }\n"
        "  .topbar-ring-fg { fill: none; stroke-width: 3; stroke-linecap: round; transition: stroke-dashoffset .5s; }\n"
        "  .topbar-ring-fg.low { stroke: var(--green); }\n"
        "  .topbar-ring-fg.mid { stroke: var(--orange); }\n"
        "  .topbar-ring-fg.high { stroke: var(--red); }\n"
        "  .topbar-ring-text {\n"
        "    position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;\n"
        "    font-size: 8px; font-weight: 700; font-family: var(--mono);\n"
        "    font-variant-numeric: tabular-nums; color: var(--sub);\n"
        "  }\n"
        "  .topbar-ring-text.high { color: var(--red); }\n"
        "  .topbar-ring-text.mid { color: var(--orange); }\n"
        "  .topbar-usage-tip {\n"
        "    display: none; position: absolute; top: 40px; right: 0; z-index: 200;\n"
        "    background: var(--panel); border: 1px solid var(--border); border-radius: 8px;\n"
        "    padding: 8px 12px; font-size: 11px; color: var(--text); white-space: nowrap;\n"
        "    box-shadow: 0 4px 16px rgba(0,0,0,.4); font-family: var(--mono);\n"
        "  }\n"
        "  .topbar-usage-tip.show { display: block; }\n"
        "  .topbar-usage-tip div { margin-bottom: 3px; }\n"
        "  .topbar-usage-tip div:last-child { margin-bottom: 0; }\n"
        "  .topbar-back {\n"
        "    display: inline-flex; align-items: center; gap: 5px;\n"
        "    color: var(--sub); font-size: 12px; text-decoration: none;\n"
        "    border: 1px solid var(--border); border-radius: var(--radius-sm);\n"
        "    padding: 3px 10px; transition: all .15s; white-space: nowrap;\n"
        "  }\n"
        "  .topbar-back:hover { color: var(--text); border-color: var(--accent); }\n"
        "  .topbar-btn {\n"
        "    display: inline-flex; align-items: center; justify-content: center;\n"
        "    width: 32px; height: 32px; background: none; border: 1px solid var(--border);\n"
        "    border-radius: var(--radius-sm); color: var(--sub); cursor: pointer;\n"
        "    transition: all .15s; text-decoration: none; position: relative;\n"
        "  }\n"
        "  .topbar-btn svg { display: block; }\n"
        "  .topbar-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
        "  .topbar-detail-btn {\n"
        "    display: none; align-items: center; justify-content: center;\n"
        "    width: 32px; height: 32px; background: none; border: 1px solid var(--border);\n"
        "    border-radius: var(--radius-sm); color: var(--sub); cursor: pointer;\n"
        "    transition: all .15s;\n"
        "  }\n"
        "  .topbar-detail-btn svg { display: block; }\n"
        "  .topbar-detail-btn:hover { border-color: var(--accent); color: var(--accent); }\n"
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
        '<div class="topbar" style="position:fixed;top:0;left:0;right:0">',
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
        parts.append('  <a class="topbar-btn" href="/dev" title="终端" style="text-decoration:none">'
                      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                      '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>'
                      '</svg></a>')
    parts += [
        '  <button class="topbar-btn" onclick="openSettings()" title="设置">',
        '    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:block">',
        '      <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1.08 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1.08 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.604.852.997 1.51 1.08H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1.08z"/>',
        '    </svg>',
        '  </button>',
    ]
    if hide_dev:
        parts += [
            '  <button class="topbar-detail-btn" onclick="showPlaceholder()" title="返回列表">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>'
            '<line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>'
            '</svg></button>',
            '  <button class="topbar-detail-btn" onclick="_openTabSwitcher()" title="切换终端">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>'
            '<line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>'
            '</svg></button>',
        ]
    parts.append('</div>')
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
    function _ring(data) {
      if (!data || data.utilization == null) return '';
      var pct = Math.round(data.utilization * 100);
      var cls = pct >= 90 ? 'high' : pct >= 60 ? 'mid' : 'low';
      var r = 11, c = 2 * Math.PI * r, off = c * (1 - data.utilization);
      return '<div class="topbar-ring">'
        + '<svg width="28" height="28" viewBox="0 0 28 28">'
        + '<circle class="topbar-ring-bg" cx="14" cy="14" r="' + r + '"/>'
        + '<circle class="topbar-ring-fg ' + cls + '" cx="14" cy="14" r="' + r + '" stroke-dasharray="' + c.toFixed(1) + '" stroke-dashoffset="' + off.toFixed(1) + '"/>'
        + '</svg><div class="topbar-ring-text ' + cls + '">' + pct + '</div></div>';
    }
    function _tipLine(label, data) {
      if (!data || data.utilization == null) return '';
      var pct = Math.round(data.utilization * 100);
      var t = label + ' ' + pct + '%';
      if (data.resets_at) {
        var diff = data.resets_at * 1000 - Date.now();
        if (diff > 0) {
          var h = Math.floor(diff / 3600000), m = Math.floor((diff % 3600000) / 60000);
          t += ' · ' + (h > 0 ? h + 'h ' + m + 'm' : m + 'm') + '后重置';
        }
      }
      return '<div>' + t + '</div>';
    }
    var html = _ring(d.session) + _ring(d.weekly)
      + '<div class="topbar-usage-tip" id="topbar-usage-tip">'
      + _tipLine('会话', d.session) + _tipLine('周', d.weekly) + '</div>';
    el.innerHTML = html;
    el.style.display = 'inline-flex';
    el.style.position = 'relative';
    el.onclick = function(e) {
      e.stopPropagation();
      var tip = document.getElementById('topbar-usage-tip');
      if (tip) tip.classList.toggle('show');
    };
    document.addEventListener('click', function() {
      var tip = document.getElementById('topbar-usage-tip');
      if (tip) tip.classList.remove('show');
    }, { once: false });
  } catch(e) {}
  setTimeout(_loadTopbarUsage, 120000);
}
if (_adminToken) _loadTopbarUsage();

// Settings functions loaded from /static/settings.js (shared with homepage)
"""
