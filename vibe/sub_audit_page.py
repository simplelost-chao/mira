"""子账号审计页(owner-only):每个子账号的 prompts + token/开销。

数据:GET /api/sub-audit(时间推断归属,见 history_db.get_sub_account_audit)。
"""


def render_sub_audit_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css = theme_vars_css()
    _tb_css = topbar_css()
    _tb_html = topbar_html(title="子账号审计")
    _overlays = settings_overlay_html()
    _tb_js = topbar_js()
    return f'''<!DOCTYPE html>
<html lang="zh"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>子账号审计 · Mira</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/fonts/fonts.css">
<style>
  *,*::before,*::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
{_theme_css}
  html, body {{ height: 100vh; overflow: hidden; }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--mono); padding-top: 52px; }}
  .content {{ overflow-y: auto; height: calc(100vh - 52px); padding: 20px 16px 80px; max-width: 900px; margin: 0 auto; }}
{_tb_css}
  .hint {{ font-size: 11px; color: var(--muted); line-height: 1.6; margin-bottom: 16px; }}
  .empty {{ color: var(--muted); font-size: 12px; padding: 10px 0; }}
  .badge {{ font-size: 10px; padding: 2px 8px; border-radius: 8px; border: 1px solid; white-space: nowrap; }}
  .badge.pending {{ color: var(--orange, #f59e0b); border-color: color-mix(in srgb, var(--orange, #f59e0b) 40%, transparent); }}
  .badge.active {{ color: var(--green, #22c55e); border-color: color-mix(in srgb, var(--green, #22c55e) 40%, transparent); }}
  .badge.disabled {{ color: var(--muted); border-color: var(--border); }}

  .sa-card {{ background: rgba(255,255,255,.025); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; margin-bottom: 16px; box-shadow: var(--card-shadow); }}
  .sa-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }}
  .sa-av {{ width: 32px; height: 32px; border-radius: 50%; object-fit: cover; border: 1px solid var(--border); background: var(--panel); flex-shrink: 0; }}
  .sa-dot {{ width: 32px; height: 32px; border-radius: 50%; background: var(--panel); border: 1px solid var(--border); flex-shrink: 0; }}
  .sa-name {{ font-size: 15px; font-weight: 700; color: var(--text); }}
  .sa-spacer {{ flex: 1; }}

  .sa-totals {{ display: flex; gap: 10px; margin-bottom: 16px; }}
  .sa-metric {{ flex: 1; background: var(--card-deep, var(--bg)); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; text-align: center; }}
  .sa-metric-v {{ font-size: 18px; font-weight: 700; color: var(--accent); font-family: var(--mono); }}
  .sa-metric-l {{ font-size: 10px; color: var(--muted); letter-spacing: .5px; text-transform: uppercase; margin-top: 3px; }}

  .sa-section-title {{ font-size: 11px; font-weight: 700; letter-spacing: 1px; color: var(--muted); margin: 14px 0 8px; text-transform: uppercase; }}
  .sa-proj {{ display: flex; align-items: center; gap: 8px; padding: 7px 10px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 6px; }}
  .sa-proj-name {{ font-size: 13px; font-weight: 600; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .sa-proj-stat {{ flex: 1; text-align: right; font-size: 11px; color: var(--sub); white-space: nowrap; }}

  .sa-prompts {{ display: flex; flex-direction: column; gap: 8px; }}
  .sa-prompt {{ background: var(--card-deep, var(--bg)); border: 1px solid var(--border); border-radius: 8px; padding: 9px 11px; }}
  .sa-prompt-meta {{ font-size: 10px; color: var(--muted); margin-bottom: 5px; letter-spacing: .3px; }}
  .sa-prompt-meta .sa-proj-tag {{ color: var(--accent); font-weight: 600; }}
  .sa-prompt-text {{ font-size: 12.5px; color: var(--sub); line-height: 1.5; white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere;
    max-height: 130px; overflow-y: auto; }}
  .sa-more {{ font-size: 11px; color: var(--accent); cursor: pointer; padding: 6px 0; text-align: center; }}
</style>
</head>
<body>
{_tb_html}
<div class="content">
  <div class="hint">按「子账号何时在哪个项目开过 claude」把会话归属到对应子账号(时间推断)。仅从开始记录时起算;极端情况(同一项目同一时段多个子账号)归属可能不精确。</div>
  <div id="root"><div class="empty">加载中…</div></div>
</div>
{_overlays}
<script>
{_tb_js}
function esc(s) {{ var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; }}
function fmtNum(n) {{ n = n || 0; if (n >= 1e6) return (n/1e6).toFixed(1)+'M'; if (n >= 1e3) return (n/1e3).toFixed(1)+'k'; return String(n); }}
function fmtTs(sec) {{ var d = new Date(parseInt(sec,10)*1000); var p = function(x){{return String(x).padStart(2,'0');}};
  return (d.getMonth()+1)+'/'+d.getDate()+' '+p(d.getHours())+':'+p(d.getMinutes()); }}

var _promptCap = 30;   // 每个账号初始展示的 prompts 条数

async function load() {{
  try {{
    var res = await fetch('/api/sub-audit', {{headers:_authHeaders()}});
    if (res.status === 401) {{ if (typeof openLoginModal === 'function') openLoginModal(load); return; }}
    if (!res.ok) throw new Error(res.status);
    render(await res.json());
  }} catch(e) {{
    document.getElementById('root').innerHTML = '<div class="empty">加载失败</div>';
  }}
}}

function render(accounts) {{
  var root = document.getElementById('root');
  if (!accounts || !accounts.length) {{ root.innerHTML = '<div class="empty">还没有子账号</div>'; return; }}
  root.innerHTML = accounts.map(function(a) {{
    var t = a.totals || {{}};
    var totalTok = (t.input_tokens||0)+(t.output_tokens||0)+(t.cache_creation_tokens||0)+(t.cache_read_tokens||0);
    var av = a.avatar ? '<img class="sa-av" src="'+esc(a.avatar)+'" alt="">' : '<span class="sa-dot"></span>';
    var projs = (a.projects && a.projects.length) ? a.projects.map(function(p) {{
      return '<div class="sa-proj"><span class="sa-proj-name">'+esc(p.project_name)+'</span>'
        + '<span class="sa-proj-stat">'+(p.messages||0)+' 条 · '+fmtNum((p.input_tokens||0)+(p.output_tokens||0))+' tok · $'+(p.estimated_cost_usd||0).toFixed(2)+'</span></div>';
    }}).join('') : '<div class="empty">该时段暂无归属会话</div>';
    var shown = (a.prompts||[]).slice(0, _promptCap);
    var prompts = shown.length ? shown.map(function(pr) {{
      return '<div class="sa-prompt"><div class="sa-prompt-meta"><span class="sa-proj-tag">'+esc(pr.project_name)+'</span> · '+fmtTs(pr.date)+'</div>'
        + '<div class="sa-prompt-text">'+esc(pr.text)+'</div></div>';
    }}).join('') : '<div class="empty">暂无 prompts</div>';
    var more = (a.prompts && a.prompts.length > shown.length)
      ? '<div class="sa-more" onclick="_expand(this)">展开剩余 '+(a.prompts.length - shown.length)+' 条</div>' : '';
    return '<div class="sa-card" data-oid="'+esc(a.open_id)+'">'
      + '<div class="sa-head">'+av+'<div class="sa-name">'+esc(a.name)+'</div>'
      + '<div class="sa-spacer"></div><span class="badge '+esc(a.status)+'">'+esc(a.status)+'</span></div>'
      + '<div class="sa-totals">'
      +   '<div class="sa-metric"><div class="sa-metric-v">$'+(t.estimated_cost_usd||0).toFixed(2)+'</div><div class="sa-metric-l">总开销</div></div>'
      +   '<div class="sa-metric"><div class="sa-metric-v">'+fmtNum(totalTok)+'</div><div class="sa-metric-l">总 token</div></div>'
      +   '<div class="sa-metric"><div class="sa-metric-v">'+(t.messages||0)+'</div><div class="sa-metric-l">消息数</div></div>'
      + '</div>'
      + '<div class="sa-section-title">按项目</div>'+projs
      + '<div class="sa-section-title">最近 prompts ('+((a.prompts||[]).length)+')</div>'
      + '<div class="sa-prompts">'+prompts+'</div>'+more
      + '</div>';
  }}).join('');
  // 缓存完整数据供展开用
  window._auditData = {{}};
  accounts.forEach(function(a) {{ window._auditData[a.open_id] = a; }});
}}

function _expand(el) {{
  var card = el.closest('.sa-card');
  var a = window._auditData[card.getAttribute('data-oid')];
  if (!a) return;
  var box = card.querySelector('.sa-prompts');
  box.innerHTML = (a.prompts||[]).map(function(pr) {{
    return '<div class="sa-prompt"><div class="sa-prompt-meta"><span class="sa-proj-tag">'+esc(pr.project_name)+'</span> · '+fmtTs(pr.date)+'</div>'
      + '<div class="sa-prompt-text">'+esc(pr.text)+'</div></div>';
  }}).join('');
  el.remove();
}}

load();
</script>
</body></html>'''
