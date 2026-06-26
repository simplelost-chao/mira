"""子账号页 /sub —— 飞书登录 + 跟 Claude 协作(响应式,手机/电脑都适配)。

无 owner 导航、无裸终端。所有接口用 X-Sub-Token。
桌面:侧栏(项目)+ 主区(对话);手机:项目列表 → 点进去全屏对话 + 返回。
移动键盘用 visualViewport 动态 --app-h,输入栏始终贴在可视区底部;输入处理 IME。
"""


def render_sub_page() -> str:
    from vibe.topbar import theme_vars_css
    _theme = theme_vars_css()
    return f'''<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover">
<title>协作 · Mira</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/fonts/fonts.css">
<style>
  *,*::before,*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{ --app-h: 100vh; }}
{_theme}
  html, body {{ height: 100%; overflow: hidden; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--mono); -webkit-tap-highlight-color: transparent; }}
  #app {{ position: fixed; top: 0; left: 0; right: 0; height: var(--app-h); display: flex; flex-direction: column; }}

  /* ── 登录 / 等待态 ── */
  .center {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; padding: 24px; text-align: center; }}
  .logo {{ font-size: 22px; font-weight: 700; }}
  .logo .a {{ color: var(--accent); }}
  .msg {{ font-size: 13px; color: var(--sub); line-height: 1.7; max-width: 360px; }}
  .feishu-btn {{ display: inline-flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600;
    background: var(--accent); color: #fff; border: none; border-radius: 10px; padding: 12px 26px; cursor: pointer; text-decoration: none; }}
  .feishu-btn:active {{ opacity: .85; }}
  .ghost {{ font-size: 12px; color: var(--muted); background: none; border: 1px solid var(--border); border-radius: 6px; padding: 6px 12px; cursor: pointer; }}

  /* ── 头部 ── */
  .hdr {{ display: flex; align-items: center; gap: 10px; height: 50px; padding: 0 14px; border-bottom: 1px solid var(--border); background: var(--panel); flex-shrink: 0; }}
  .hdr-back {{ display: none; background: none; border: none; color: var(--text); font-size: 20px; cursor: pointer; padding: 4px 6px 4px 0; line-height: 1; }}
  .hdr-av {{ width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border); object-fit: cover; background: var(--bg); flex-shrink: 0; }}
  .hdr-title {{ font-size: 14px; font-weight: 600; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

  /* ── 布局 ── */
  .body {{ flex: 1; display: flex; min-height: 0; }}
  .side {{ width: 250px; border-right: 1px solid var(--border); overflow-y: auto; flex-shrink: 0; -webkit-overflow-scrolling: touch; }}
  .side-title {{ font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted); padding: 14px 16px 8px; }}
  .proj {{ display: flex; align-items: center; gap: 9px; padding: 12px 16px; cursor: pointer; border-left: 2px solid transparent; font-size: 13px; }}
  .proj:active {{ background: rgba(255,255,255,.05); }}
  .proj.active {{ background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }}
  .proj-badge {{ width: 20px; height: 20px; border-radius: 5px; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; background: rgba(var(--accent-rgb),.18); color: var(--accent); }}
  .proj-name {{ flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); }}
  .proj.active .proj-name {{ color: var(--accent); }}

  .main {{ flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0; }}
  .termwrap {{ flex: 1; min-height: 0; position: relative; background: var(--bg); }}
  .term {{ position: absolute; inset: 0; width: 100%; height: 100%; border: 0; display: block; }}
  .placeholder {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 13px; text-align: center; padding: 24px; }}
  .inputbar {{ display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--border); background: var(--panel); flex-shrink: 0; align-items: flex-end; }}
  .inputbar textarea {{ flex: 1; resize: none; min-height: 40px; max-height: 140px; background: var(--bg); border: 1px solid var(--border); border-radius: 10px; color: var(--text); font-family: var(--mono); font-size: 15px; line-height: 1.45; padding: 9px 12px; outline: none; }}
  .inputbar textarea:focus {{ border-color: var(--accent); }}
  .send {{ background: var(--accent); color: #fff; border: none; border-radius: 10px; padding: 0 18px; height: 40px; font-weight: 600; font-size: 14px; cursor: pointer; flex-shrink: 0; }}
  .send:disabled {{ opacity: .45; }}

  /* ── 手机:列表 / 对话 单视图切换 ── */
  @media (max-width: 760px) {{
    #app.chat-open .side {{ display: none; }}
    #app:not(.chat-open) .main {{ display: none; }}
    #app:not(.chat-open) .hdr-back {{ display: none; }}
    #app.chat-open .hdr-back {{ display: block; }}
    #app:not(.chat-open) .hdr-av {{ display: block; }}
    #app.chat-open .hdr-av {{ display: none; }}
    .side {{ width: 100%; border-right: none; }}
  }}
</style>
</head>
<body>
<div id="app"></div>
<script>
const TOKEN_KEY = 'mira-sub-token';
const app = document.getElementById('app');
let _cur = null, _curPid = null, _projects = [], _me = null, _composing = false;
function tok() {{ return localStorage.getItem(TOKEN_KEY) || ''; }}
function H() {{ const t = tok(); return t ? {{'X-Sub-Token': t}} : {{}}; }}
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}

// ── 移动键盘:动态 --app-h,输入栏始终贴可视区底 ──
(function() {{
  function u() {{
    var h = window.visualViewport ? Math.round(window.visualViewport.height) : window.innerHeight;
    document.documentElement.style.setProperty('--app-h', h + 'px');
    window.scrollTo(0, 0);
  }}
  u();
  if (window.visualViewport) {{ window.visualViewport.addEventListener('resize', u); window.visualViewport.addEventListener('scroll', u); }}
  window.addEventListener('resize', u);
}})();

function renderLogin(msg) {{
  app.className = '';
  app.innerHTML = `<div class="center"><div class="logo"><span class="a">M</span>ira 协作</div>
    ${{msg ? `<div class="msg">${{esc(msg)}}</div>` : '<div class="msg">用飞书登录,在被授权的项目里跟 Claude 一起干活。</div>'}}
    <a class="feishu-btn" href="/auth/feishu/login">飞书登录</a></div>`;
}}
function renderPending() {{
  app.className = '';
  app.innerHTML = `<div class="center"><div class="logo"><span class="a">M</span>ira 协作</div>
    <div class="msg">登录成功,正在等待管理员批准并分配项目。<br>批准后刷新本页即可开始。</div>
    <button class="ghost" onclick="logout()">退出</button></div>`;
}}
function logout() {{ localStorage.removeItem(TOKEN_KEY); location.href = '/sub'; }}

async function boot() {{
  const q = new URLSearchParams(location.search);
  if (q.get('token')) {{ localStorage.setItem(TOKEN_KEY, q.get('token')); history.replaceState({{}},'','/sub'); }}
  if (q.get('status') === 'pending') return renderPending();
  if (q.get('error')) return renderLogin('登录失败,请重试。');
  if (!tok()) return renderLogin();
  const res = await fetch('/api/sub/me', {{headers: H()}}).catch(()=>null);
  if (!res || res.status === 401) {{ localStorage.removeItem(TOKEN_KEY); return renderLogin('登录已失效,请重新登录。'); }}
  _me = await res.json();
  renderApp();
}}

function renderApp() {{
  const av = _me.avatar ? `<img class="hdr-av" src="${{esc(_me.avatar)}}">` : '<div class="hdr-av"></div>';
  app.className = '';
  app.innerHTML = `
    <div class="hdr">
      <button class="hdr-back" onclick="backToList()">‹</button>
      ${{av}}
      <div class="hdr-title" id="hdrTitle">${{esc(_me.name || '我')}}</div>
      <button class="ghost" onclick="logout()">退出</button>
    </div>
    <div class="body">
      <div class="side"><div class="side-title">项目</div><div id="projlist"><div class="side-title" style="text-transform:none;letter-spacing:0;color:var(--muted)">加载中…</div></div></div>
      <div class="main">
        <div class="termwrap">
          <div class="placeholder" id="termph">选一个项目,开始跟 Claude 协作</div>
          <iframe class="term" id="term" hidden></iframe>
        </div>
        <div class="inputbar">
          <textarea id="inp" rows="1" enterkeyhint="send" placeholder="给 Claude 发一句话,回车发送(Shift+回车换行)" disabled></textarea>
          <button class="send" id="sendbtn" disabled onclick="send()">发送</button>
        </div>
      </div>
    </div>`;
  const inp = document.getElementById('inp');
  inp.addEventListener('compositionstart', () => {{ _composing = true; }});
  inp.addEventListener('compositionend', () => {{ _composing = false; }});
  inp.addEventListener('keydown', e => {{
    if (e.key === 'Enter' && !e.shiftKey && !_composing && !e.isComposing) {{ e.preventDefault(); send(); }}
  }});
  inp.addEventListener('input', () => {{ inp.style.height = 'auto'; inp.style.height = Math.min(inp.scrollHeight, 140) + 'px'; }});
  document.addEventListener('keydown', e => {{ if (e.key === 'Escape') backToList(); }});
  loadProjects();
  setInterval(loadProjects, 10000);
}}

async function loadProjects() {{
  const res = await fetch('/api/sub/projects', {{headers: H()}}).catch(()=>null);
  if (!res || !res.ok) return;
  _projects = await res.json();
  const list = document.getElementById('projlist');
  if (!list) return;
  if (!_projects.length) {{ list.innerHTML = '<div class="side-title" style="text-transform:none;letter-spacing:0;color:var(--muted)">还没有被授权的项目</div>'; return; }}
  list.innerHTML = _projects.map(p =>
    `<div class="proj${{_curPid===p.id?' active':''}}" onclick="pickProject('${{esc(p.id)}}')">
      <span class="proj-badge">C</span><span class="proj-name">${{esc(p.name||p.id)}}</span></div>`
  ).join('');
}}

function backToList() {{
  app.classList.remove('chat-open');
}}

function showPlaceholder(text) {{
  const ph = document.getElementById('termph'), fr = document.getElementById('term');
  if (ph) {{ ph.textContent = text; ph.hidden = false; }}
  if (fr) {{ fr.hidden = true; fr.removeAttribute('src'); }}
}}

async function pickProject(pid) {{
  _curPid = pid; _cur = null;
  app.classList.add('chat-open');
  const p = _projects.find(x => x.id === pid);
  const ht = document.getElementById('hdrTitle'); if (ht) ht.textContent = (p && p.name) || pid;
  loadProjects();
  showPlaceholder('正在启动该项目的 Claude 会话…');
  const inp = document.getElementById('inp'), btn = document.getElementById('sendbtn');
  inp.disabled = true; btn.disabled = true;
  const res = await fetch(`/api/sub/project/${{encodeURIComponent(pid)}}/session`, {{method:'POST', headers: H()}}).catch(()=>null);
  if (pid !== _curPid) return;
  if (!res || !res.ok) {{ showPlaceholder(res && res.status===403 ? '无权访问该项目' : '会话启动失败,稍后重试'); return; }}
  const d = await res.json();
  _cur = d.target;
  // 只读终端:嵌入该项目的 ttyd(实时渲染,跟 dev 页一样;子账号无法在里面输入)
  const fr = document.getElementById('term'), ph = document.getElementById('termph');
  if (d.term_base) {{ fr.src = d.term_base; fr.hidden = false; if (ph) ph.hidden = true; }}
  else if (ph) {{ ph.textContent = '终端暂不可用,可继续在下方发送消息'; ph.hidden = false; }}
  inp.disabled = false; btn.disabled = false;
  if (window.innerWidth > 760) inp.focus();
}}

async function send() {{
  const inp = document.getElementById('inp'), btn = document.getElementById('sendbtn');
  const text = inp.value.trim();
  if (!text || !_cur) return;
  btn.disabled = true;
  const res = await fetch(`/api/sub/pane/${{encodeURIComponent(_cur)}}/send`, {{
    method:'POST', headers: {{'Content-Type':'application/json', ...H()}}, body: JSON.stringify({{text}})
  }}).catch(()=>null);
  btn.disabled = false;
  if (res && res.ok) {{ inp.value = ''; inp.style.height = 'auto'; }}
  else alert(res && res.status===403 ? '无权操作该会话' : '发送失败');
  inp.focus();
}}

boot();
</script>
</body></html>'''
