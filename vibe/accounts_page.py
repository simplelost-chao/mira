"""子账号管理页(owner-only):审批账号 + 勾选授权项目 + 禁用。

数据:GET /api/accounts(账号)+ GET /api/dev/project-options(项目列表)。
操作:POST /api/accounts/{id}/approve|disable、PUT /api/accounts/{id}/projects。
"""


def render_accounts_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css = theme_vars_css()
    _tb_css = topbar_css()
    _tb_html = topbar_html(title="账号")
    _overlays = settings_overlay_html()
    _tb_js = topbar_js()
    return f'''<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>账号 · Mira</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/fonts/fonts.css">
<style>
  *,*::before,*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
{_theme_css}
  html, body {{ height: 100vh; overflow: hidden; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--mono); padding-top: 52px; }}
  .content {{ overflow-y: auto; height: calc(100vh - 52px); padding: 24px 20px 80px; max-width: 860px; margin: 0 auto; }}
{_tb_css}
  .sec-title {{ font-size: 11px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
    color: var(--muted); margin: 22px 0 10px; }}
  .acc-card {{ background: rgba(255,255,255,.025); border: 1px solid var(--border); border-radius: 10px;
    padding: 14px 16px; margin-bottom: 10px; box-shadow: var(--card-shadow); }}
  .acc-head {{ display: flex; align-items: center; gap: 10px; }}
  .acc-avatar {{ width: 32px; height: 32px; border-radius: 50%; background: var(--panel);
    object-fit: cover; flex-shrink: 0; border: 1px solid var(--border); }}
  .acc-name {{ font-size: 14px; font-weight: 600; color: var(--text); }}
  .acc-oid {{ font-size: 11px; color: var(--muted); word-break: break-all; }}
  .acc-spacer {{ flex: 1; }}
  .badge {{ font-size: 10px; padding: 2px 8px; border-radius: 8px; border: 1px solid; white-space: nowrap; }}
  .badge.pending {{ color: var(--orange); border-color: color-mix(in srgb, var(--orange) 40%, transparent); }}
  .badge.active {{ color: var(--green); border-color: color-mix(in srgb, var(--green) 40%, transparent); }}
  .badge.disabled {{ color: var(--muted); border-color: var(--border); }}
  .btn {{ font-size: 12px; font-family: var(--mono); padding: 5px 12px; border-radius: 6px; cursor: pointer;
    border: 1px solid var(--border); background: none; color: var(--text); transition: all .12s; }}
  .btn:hover {{ border-color: var(--accent); color: var(--accent); }}
  .btn.primary {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .btn.danger {{ color: var(--red); border-color: color-mix(in srgb, var(--red) 40%, transparent); }}
  .btn.danger:hover {{ background: color-mix(in srgb, var(--red) 12%, transparent); border-color: var(--red); }}
  .acc-actions {{ display: flex; gap: 8px; }}
  .proj-grant {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }}
  .proj-grant-title {{ font-size: 11px; color: var(--muted); margin-bottom: 8px; }}
  .proj-grid {{ display: flex; flex-wrap: wrap; gap: 6px 14px; }}
  .proj-chk {{ display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--sub); cursor: pointer; }}
  .proj-chk input {{ accent-color: var(--accent); cursor: pointer; }}
  .grant-save {{ margin-top: 10px; }}
  .empty {{ color: var(--muted); font-size: 12px; padding: 10px 0; }}
  .hint {{ font-size: 11px; color: var(--muted); margin-bottom: 6px; line-height: 1.6; }}
</style>
</head>
<body>
{_tb_html}
<div class="content">
  <div class="hint">子账号通过飞书登录后进入"待批准";你在这里批准并勾选授权项目后,他才能登录、只看/操作被授权项目里的 Claude 会话(无裸 shell)。</div>
  <div id="root"><div class="empty">加载中…</div></div>
</div>
{_overlays}
<script>
{_tb_js}
let _projects = [];
function esc(s) {{ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}

async function load() {{
  try {{
    const [accs, projs] = await Promise.all([
      fetch('/api/accounts', {{headers:_authHeaders()}}).then(r=>r.ok?r.json():Promise.reject(r.status)),
      fetch('/api/dev/project-options', {{headers:_authHeaders()}}).then(r=>r.ok?r.json():[]),
    ]);
    _projects = projs || [];
    render(accs || []);
  }} catch(e) {{
    if (e === 401 && typeof openLoginModal === 'function') {{ openLoginModal(load); return; }}
    document.getElementById('root').innerHTML = '<div class="empty">加载失败</div>';
  }}
}}

function _accHead(a) {{
  const av = a.avatar ? `<img class="acc-avatar" src="${{esc(a.avatar)}}" alt="">` : `<div class="acc-avatar"></div>`;
  return `${{av}}<div><div class="acc-name">${{esc(a.name||'(未命名)')}}</div>
    <div class="acc-oid">${{esc(a.feishu_open_id)}}</div></div>
    <div class="acc-spacer"></div><span class="badge ${{a.status}}">${{a.status}}</span>`;
}}

function _projGrant(a) {{
  const granted = new Set(a.projects||[]);
  const boxes = _projects.map(p =>
    `<label class="proj-chk"><input type="checkbox" data-pid="${{esc(p.id)}}" ${{granted.has(p.id)?'checked':''}}>${{esc(p.name)}}</label>`
  ).join('') || '<span class="empty">暂无项目</span>';
  return `<div class="proj-grant">
    <div class="proj-grant-title">授权项目(勾选后保存)</div>
    <div class="proj-grid" data-oid="${{esc(a.feishu_open_id)}}">${{boxes}}</div>
    <button class="btn primary grant-save" onclick="saveGrant('${{esc(a.feishu_open_id)}}', this)">保存授权</button>
  </div>`;
}}

function render(accs) {{
  const pending = accs.filter(a=>a.status==='pending');
  const active = accs.filter(a=>a.status==='active');
  const disabled = accs.filter(a=>a.status==='disabled');
  let h = '';
  h += `<div class="sec-title">待批准 (${{pending.length}})</div>`;
  h += pending.length ? pending.map(a => `<div class="acc-card"><div class="acc-head">${{_accHead(a)}}
      <div class="acc-actions"><button class="btn primary" onclick="act('${{esc(a.feishu_open_id)}}','approve')">批准</button>
      <button class="btn danger" onclick="act('${{esc(a.feishu_open_id)}}','disable')">拒绝</button></div></div></div>`).join('')
    : '<div class="empty">没有待批准的账号</div>';

  h += `<div class="sec-title">已启用 (${{active.length}})</div>`;
  h += active.length ? active.map(a => `<div class="acc-card"><div class="acc-head">${{_accHead(a)}}
      <div class="acc-actions"><button class="btn danger" onclick="act('${{esc(a.feishu_open_id)}}','disable')">禁用</button></div></div>
      ${{_projGrant(a)}}</div>`).join('')
    : '<div class="empty">还没有启用的子账号</div>';

  if (disabled.length) {{
    h += `<div class="sec-title">已禁用 (${{disabled.length}})</div>`;
    h += disabled.map(a => `<div class="acc-card"><div class="acc-head">${{_accHead(a)}}
      <div class="acc-actions"><button class="btn" onclick="act('${{esc(a.feishu_open_id)}}','approve')">重新启用</button></div></div></div>`).join('');
  }}
  document.getElementById('root').innerHTML = h;
}}

async function act(oid, action) {{
  if (action==='disable' && !confirm('确认禁用/拒绝该账号?')) return;
  const res = await fetch(`/api/accounts/${{encodeURIComponent(oid)}}/${{action}}`, {{method:'POST', headers:_authHeaders()}});
  if (res.ok) load(); else alert('操作失败');
}}

async function saveGrant(oid, btn) {{
  const grid = document.querySelector(`.proj-grid[data-oid="${{CSS.escape(oid)}}"]`);
  const projects = [...grid.querySelectorAll('input:checked')].map(i=>i.dataset.pid);
  const res = await fetch(`/api/accounts/${{encodeURIComponent(oid)}}/projects`, {{
    method:'PUT', headers:{{'Content-Type':'application/json', ..._authHeaders()}}, body: JSON.stringify({{projects}})
  }});
  if (res.ok) {{ const o=btn.textContent; btn.textContent='已保存'; setTimeout(()=>btn.textContent=o,1200); }}
  else alert('保存失败');
}}

load();
</script>
</body></html>'''
