"""部署 / Deployments 页面:端口总览、共享服务反向影响、各项目部署条目。

只读展示为主,数据由前端 fetch /api/deployments 填充;
编辑通过 /api/deployments 的 POST/PUT/DELETE 完成。
"""


def render_deploy_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css = theme_vars_css()
    _tb_css    = topbar_css()
    _tb_html   = topbar_html(title="部署")
    _overlays  = settings_overlay_html()
    _tb_js     = topbar_js()
    return f'''<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>部署 · Mira</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/fonts/fonts.css">
<style>
{_theme_css}
{_tb_css}
  body {{ background: var(--bg); color: var(--text); font-family: var(--sans); }}
  .wrap {{ max-width: 1100px; margin: 0 auto; padding: 16px; }}
  h2 {{ font-size: 16px; margin: 22px 0 10px; color: var(--text); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--sub); font-weight: 600; }}
  .conflict {{ color: var(--red); font-weight: 600; }}
  .card {{ background: var(--panel); border: 1px solid var(--border);
           border-radius: var(--radius); padding: 14px; margin-bottom: 12px; }}
  .card h3 {{ font-size: 14px; margin-bottom: 6px; }}
  code {{ font-family: var(--mono); font-size: 12px; }}
  .muted {{ color: var(--muted); }}
  .scroll-x {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
</style>
</head><body>
{_tb_html}
<div class="wrap">
  <h2>端口总览（冲突标红）</h2>
  <div class="scroll-x"><table id="port-table"><tbody></tbody></table></div>

  <h2>共享服务 · 反向影响（动它会影响谁）</h2>
  <div class="scroll-x"><table id="impact-table"><tbody></tbody></table></div>

  <h2>各项目部署</h2>
  <div id="deploy-cards"></div>
</div>
{_overlays}
<script>
{_tb_js}
</script>
<script>
function esc(s) {{ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }}
async function load() {{
  const r = await fetch('/api/deployments', {{headers: _authHeaders()}});
  if (!r.ok) {{ document.getElementById('deploy-cards').innerHTML = '<p class="muted">需要管理员登录后查看。</p>'; return; }}
  const data = await r.json();
  const conflictPorts = new Set((data.port_conflicts || []).map(c => c.port));

  const portRows = {{}};
  (data.deployments || []).forEach(d => (d.ports || []).forEach(p => {{ (portRows[p] = portRows[p] || []).push(d.project); }}));
  (data.base_services || []).forEach(s => {{ if (s.port != null) (portRows[s.port] = portRows[s.port] || []).push(s.name); }});
  let pt = '<tr><th>端口</th><th>使用者</th></tr>';
  Object.keys(portRows).sort((a,b)=>a-b).forEach(p => {{
    const cls = conflictPorts.has(Number(p)) ? ' class="conflict"' : '';
    pt += `<tr${{cls}}><td>${{esc(p)}}</td><td>${{portRows[p].map(esc).join(', ')}}</td></tr>`;
  }});
  document.getElementById('port-table').innerHTML = pt;

  let it = '<tr><th>共享服务</th><th>被这些项目依赖</th></tr>';
  Object.entries(data.reverse_impact || {{}}).forEach(([svc, projs]) => {{
    it += `<tr><td>${{esc(svc)}}</td><td>${{(projs.length ? projs.map(esc).join(', ') : '<span class="muted">无</span>')}}</td></tr>`;
  }});
  document.getElementById('impact-table').innerHTML = it;

  const missingByProj = {{}};
  (data.missing_deps || []).forEach(m => {{ missingByProj[m.project] = m.missing; }});
  let cards = '';
  (data.deployments || []).forEach(d => {{
    const miss = missingByProj[d.project];
    cards += `<div class="card"><h3>${{esc(d.project)}}</h3>`;
    cards += `<div class="muted">端口 ${{(d.ports||[]).map(esc).join(', ') || '—'}} · 依赖 ${{(d.depends_on||[]).map(esc).join(', ') || '—'}}</div>`;
    if (miss) cards += `<div class="conflict">⚠️ 依赖缺失: ${{miss.map(esc).join(', ')}}</div>`;
    if (d.domain) cards += `<div><code>${{esc(d.domain)}}</code></div>`;
    if (d.notes) cards += `<pre style="white-space:pre-wrap;margin-top:6px">${{esc(d.notes)}}</pre>`;
    cards += `</div>`;
  }});
  document.getElementById('deploy-cards').innerHTML = cards || '<p class="muted">还没有部署条目。</p>';
}}
load();
</script>
</body></html>'''
