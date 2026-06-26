"""子账号页 /sub —— 飞书登录 + 聊天式"跟 Claude 对话"。

无 owner 导航。所有接口用 X-Sub-Token(飞书会话 token,存 localStorage)。
飞书回调会带 ?token= / ?status=pending / ?error= 跳到这里。
"""


def render_sub_page() -> str:
    from vibe.topbar import theme_vars_css
    _theme = theme_vars_css()
    return f'''<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>协作 · Mira</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/fonts/fonts.css">
<style>
  *,*::before,*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
{_theme}
  html, body {{ height: 100vh; overflow: hidden; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--mono); display: flex; flex-direction: column; }}
  #app {{ flex: 1; display: flex; flex-direction: column; min-height: 0; }}
  .center {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; padding: 24px; text-align: center; }}
  .logo {{ font-size: 22px; font-weight: 700; }}
  .logo .a {{ color: var(--accent); }}
  .msg {{ font-size: 13px; color: var(--sub); line-height: 1.7; max-width: 360px; }}
  .feishu-btn {{ display: inline-flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600;
    background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 11px 22px; cursor: pointer; text-decoration: none; }}
  .feishu-btn:hover {{ opacity: .9; }}
  .ghost {{ font-size: 12px; color: var(--muted); background: none; border: 1px solid var(--border);
    border-radius: 6px; padding: 6px 12px; cursor: pointer; }}
  /* app */
  .hdr {{ display: flex; align-items: center; gap: 10px; padding: 10px 16px; border-bottom: 1px solid var(--border);
    background: var(--panel); flex-shrink: 0; }}
  .hdr-av {{ width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border); object-fit: cover; }}
  .hdr-name {{ font-size: 13px; font-weight: 600; }}
  .hdr-sp {{ flex: 1; }}
  .layout {{ flex: 1; display: flex; min-height: 0; }}
  .side {{ width: 240px; border-right: 1px solid var(--border); overflow-y: auto; flex-shrink: 0; }}
  .side-title {{ font-size: 10px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted); padding: 12px 14px 6px; }}
  .sess {{ display: flex; align-items: center; gap: 8px; padding: 9px 14px; cursor: pointer; border-left: 2px solid transparent; font-size: 12px; }}
  .sess:hover {{ background: rgba(255,255,255,.03); }}
  .sess.active {{ background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }}
  .sess-badge {{ width: 18px; height: 18px; border-radius: 4px; font-size: 10px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
  .sess-badge.claude {{ background: rgba(var(--accent-rgb),.18); color: var(--accent); }}
  .sess-badge.codex {{ background: rgba(92,208,138,.18); color: var(--green); }}
  .sess-name {{ flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--sub); }}
  .sess.waiting .sess-name::after {{ content: ' ●'; color: var(--orange); }}
  .main {{ flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0; }}
  .out {{ flex: 1; overflow-y: auto; padding: 14px 16px; font-size: 12px; line-height: 1.5;
    white-space: pre-wrap; word-break: break-word; color: var(--sub); }}
  .inputbar {{ display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid var(--border); background: var(--panel); }}
  .inputbar textarea {{ flex: 1; resize: none; height: 38px; max-height: 120px; background: var(--bg);
    border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-family: var(--mono); font-size: 13px; padding: 9px 11px; outline: none; }}
  .inputbar textarea:focus {{ border-color: var(--accent); }}
  .send {{ background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 0 18px; font-weight: 600; cursor: pointer; flex-shrink: 0; }}
  .send:disabled {{ opacity: .5; cursor: default; }}
  .placeholder {{ flex: 1; display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 13px; }}
  @media (max-width: 700px) {{
    .side {{ width: 140px; }}
  }}
</style>
</head>
<body>
<div id="app"></div>
<script>
const TOKEN_KEY = 'mira-sub-token';
const app = document.getElementById('app');
let _cur = null, _pollTimer = null, _panes = [];
function tok() {{ return localStorage.getItem(TOKEN_KEY) || ''; }}
function H() {{ const t = tok(); return t ? {{'X-Sub-Token': t}} : {{}}; }}
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}
function stripAnsi(s) {{ return String(s||'').replace(/\\x1b\\[[0-9;?]*[ -/]*[@-~]/g, '').replace(/\\x1b[\\]P^_].*?(\\x07|\\x1b\\\\)/g, '').replace(/[\\x00-\\x08\\x0b-\\x1f\\x7f]/g, ''); }}

function renderLogin(msg) {{
  app.innerHTML = `<div class="center">
    <div class="logo"><span class="a">M</span>ira 协作</div>
    ${{msg ? `<div class="msg">${{esc(msg)}}</div>` : '<div class="msg">用飞书登录,即可在被授权的项目里跟 Claude 一起干活。</div>'}}
    <a class="feishu-btn" href="/auth/feishu/login">飞书登录</a>
  </div>`;
}}
function renderPending() {{
  app.innerHTML = `<div class="center">
    <div class="logo"><span class="a">M</span>ira 协作</div>
    <div class="msg">登录成功,正在等待管理员批准并分配项目。<br>批准后刷新本页即可开始。</div>
    <button class="ghost" onclick="logout()">退出</button>
  </div>`;
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
  const me = await res.json();
  renderApp(me);
}}

function renderApp(me) {{
  const av = me.avatar ? `<img class="hdr-av" src="${{esc(me.avatar)}}">` : '<div class="hdr-av"></div>';
  app.innerHTML = `<div class="hdr">${{av}}<div class="hdr-name">${{esc(me.name||'我')}}</div><div class="hdr-sp"></div>
      <button class="ghost" onclick="logout()">退出</button></div>
    <div class="layout">
      <div class="side"><div class="side-title">项目</div><div id="sesslist"></div></div>
      <div class="main"><div class="out placeholder" id="out">从左侧选一个项目,开始跟 Claude 协作</div>
        <div class="inputbar"><textarea id="inp" placeholder="给 Claude 发一句话,回车发送…" disabled></textarea>
          <button class="send" id="sendbtn" disabled onclick="send()">发送</button></div>
      </div>
    </div>`;
  const inp = document.getElementById('inp');
  inp.addEventListener('keydown', e => {{ if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }} }});
  loadProjects();
  setInterval(loadProjects, 8000);
}}

let _curPid = null;
async function loadProjects() {{
  const res = await fetch('/api/sub/projects', {{headers: H()}}).catch(()=>null);
  if (!res || !res.ok) return;
  _panes = await res.json();
  const list = document.getElementById('sesslist');
  if (!list) return;
  if (!_panes.length) {{ list.innerHTML = '<div class="side-title" style="color:var(--muted);text-transform:none;letter-spacing:0">还没有被授权的项目</div>'; return; }}
  list.innerHTML = _panes.map(p =>
    `<div class="sess${{_curPid===p.id?' active':''}}" onclick="pickProject('${{esc(p.id)}}')">
      <span class="sess-badge claude">C</span><span class="sess-name">${{esc(p.name||p.id)}}</span></div>`
  ).join('');
}}

async function pickProject(pid) {{
  _curPid = pid;
  loadProjects();
  const out = document.getElementById('out'); out.classList.remove('placeholder'); out.textContent = '正在启动该项目的 Claude 会话…';
  const inp = document.getElementById('inp'), btn = document.getElementById('sendbtn');
  inp.disabled = true; btn.disabled = true;
  // 起/复用加固会话
  const res = await fetch(`/api/sub/project/${{encodeURIComponent(pid)}}/session`, {{method:'POST', headers: H()}}).catch(()=>null);
  if (!res || !res.ok) {{ out.textContent = res && res.status===403 ? '无权访问该项目' : '会话启动失败'; return; }}
  const d = await res.json();
  if (pid !== _curPid) return;   // 期间又切了项目
  _cur = d.target;
  inp.disabled = false; btn.disabled = false; inp.focus();
  if (_pollTimer) clearInterval(_pollTimer);
  pollOutput();
  _pollTimer = setInterval(pollOutput, 2000);
}}

async function pollOutput() {{
  if (!_cur) return;
  const res = await fetch(`/api/sub/pane/${{encodeURIComponent(_cur)}}/output?lines=200`, {{headers: H()}}).catch(()=>null);
  const out = document.getElementById('out');
  if (!out || _cur == null) return;
  if (!res || !res.ok) {{ out.textContent = res && res.status===403 ? '无权访问该会话' : '读取失败'; return; }}
  const d = await res.json();
  const atBottom = out.scrollHeight - out.scrollTop - out.clientHeight < 40;
  out.textContent = stripAnsi(d.output || '');
  if (atBottom) out.scrollTop = out.scrollHeight;
}}

async function send() {{
  const inp = document.getElementById('inp'), btn = document.getElementById('sendbtn');
  const text = inp.value.trim();
  if (!text || !_cur) return;
  btn.disabled = true;
  const res = await fetch(`/api/sub/pane/${{encodeURIComponent(_cur)}}/send`, {{
    method: 'POST', headers: {{'Content-Type':'application/json', ...H()}}, body: JSON.stringify({{text}})
  }}).catch(()=>null);
  btn.disabled = false;
  if (res && res.ok) {{ inp.value = ''; setTimeout(pollOutput, 300); }}
  else alert(res && res.status===403 ? '无权操作该会话' : '发送失败');
  inp.focus();
}}

boot();
</script>
</body></html>'''
