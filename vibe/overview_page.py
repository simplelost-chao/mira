"""Generate a full standalone HTML overview page for a project."""
from __future__ import annotations
import html
import re
from vibe.models import ProjectInfo

_TECH_AI    = {'openai','anthropic','claude','deepseek','ollama','gemini','dashscope','qwen',
               'cosyvoice','whisper','sentence-transformers','chromadb','faiss','hdbscan',
               'scikit-learn','transformers','langchain','llamaindex','huggingface','tenacity'}
_TECH_DB    = {'redis','postgres','postgresql','mysql','mongodb','sqlite','sqlalchemy','alembic',
               'prisma','supabase','elasticsearch','kafka','rabbitmq','minio','s3','zstandard'}
_TECH_WEB   = {'fastapi','express','nextjs','react','vue','svelte','nuxt','remix','django','flask',
               'uvicorn','gunicorn','nginx','vite','webpack','tailwind','axios','httpx','requests',
               'websocket','pydantic','jinja2','typer','click','uvloop'}
_TECH_LANG  = {'python','typescript','javascript','go','rust','java','kotlin','swift','ruby','php',
               'lua','bash','shell'}
_GROUP_LABELS = {'lang':'语言', 'web':'框架 / API', 'ai':'AI · ML', 'db':'存储', 'infra':'工具链'}
_GROUP_COLORS = {'lang':'blue', 'web':'green', 'ai':'purple', 'db':'gold', 'infra':'dim'}

LANG_COLORS = ['#61afef','#c678dd','#e5c07b','#52c469','#e06c75','#56b6c2','#be5046','#98c379']


def _classify(name: str) -> str:
    n = re.sub(r'[-_.@/]', '', name.lower())
    if any(k in n for k in _TECH_AI):   return 'ai'
    if any(k in n for k in _TECH_DB):   return 'db'
    if any(k in n for k in _TECH_WEB):  return 'web'
    if any(k in n for k in _TECH_LANG): return 'lang'
    return 'infra'


def _e(s) -> str:
    return html.escape(str(s or ''))


_FLOW_COLORS = ['blue', 'gold', 'green', 'purple', 'red', 'blue', 'gold', 'green']

def _inline(text: str) -> str:
    """Inline markdown: bold, code, italic."""
    t = _e(text)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', t)
    return t


def _render_flow_line(line: str) -> str:
    """A line with → separators → visual flow nodes."""
    parts = [p.strip() for p in re.split(r'[→➜]', line) if p.strip()]
    nodes = []
    for i, part in enumerate(parts):
        color = _FLOW_COLORS[i % len(_FLOW_COLORS)]
        # Try to split "label: detail" within a node
        m = re.match(r'^(.+?)[:：](.+)$', part)
        if m:
            name, detail = m.group(1).strip(), m.group(2).strip()
        else:
            name, detail = part, ''
        det_html = f'<div class="flow-node-detail">{_inline(detail)}</div>' if detail else ''
        nodes.append(f'<div class="flow-node {color}"><div class="flow-node-name">{_inline(name)}</div>{det_html}</div>')
    return '<div class="flow">' + '<div class="flow-arrow">→</div>'.join(nodes) + '</div>'


def _render_bullet_cards(items: list[str]) -> str:
    """Bullet list where items have — or : → rendered as module cards."""
    cards = []
    for item in items:
        # Try "name — desc" or "name: desc" or "`name` — desc"
        m = re.match(r'^`?([^`\—:]+)`?\s*(?:—|-{1,2}|[:：])\s*(.+)$', item)
        if m:
            name = m.group(1).strip(' `')
            desc = m.group(2).strip()
            cards.append(
                f'<div class="mod-card">'
                f'<div class="mod-name">{_inline(name)}</div>'
                f'<div class="mod-desc">{_inline(desc)}</div>'
                f'</div>'
            )
        else:
            cards.append(f'<div class="mod-card simple"><div class="mod-name">{_inline(item)}</div></div>')
    return f'<div class="mod-grid">{"".join(cards)}</div>'


def _rich_arch(text: str) -> str:
    """
    Parse arch_summary markdown into rich visual HTML:
    - ## heading  → gold section label
    - lines with → → flow diagram nodes
    - bullet lists with : or — → module card grid
    - plain paragraphs → styled text
    """
    lines = text.splitlines()
    out = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip blank lines
        if not stripped:
            i += 1
            continue

        # H1 (project title) — skip, already in page header
        if re.match(r'^# [^#]', stripped):
            i += 1
            continue

        # H2/H3 → gold label
        m2 = re.match(r'^#{1,3}\s+(.+)$', stripped)
        if m2:
            out.append(f'<div class="arch-section-label">{_inline(m2.group(1))}</div>')
            i += 1
            continue

        # HR
        if re.match(r'^---+$', stripped):
            out.append('<div class="arch-hr"></div>')
            i += 1
            continue

        # Flow line: contains → arrow
        if '→' in stripped or '➜' in stripped:
            out.append(_render_flow_line(stripped))
            i += 1
            continue

        # Bullet list block — collect consecutive items
        if re.match(r'^[-*]\s', stripped):
            bullets = []
            while i < len(lines) and re.match(r'^[-*]\s', lines[i].strip()):
                bullets.append(re.sub(r'^[-*]\s+', '', lines[i].strip()))
                i += 1
            out.append(_render_bullet_cards(bullets))
            continue

        # Numbered list block
        if re.match(r'^\d+\.\s', stripped):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
                items.append(re.sub(r'^\d+\.\s+', '', lines[i].strip()))
                i += 1
            out.append(_render_bullet_cards(items))
            continue

        # Plain paragraph (possibly bold one-liner like **一句话定位**: ...)
        m_bold = re.match(r'^\*\*([^*]+)\*\*[:：]\s*(.+)$', stripped)
        if m_bold:
            label, content = m_bold.group(1), m_bold.group(2)
            out.append(
                f'<div class="arch-kv">'
                f'<span class="arch-kv-label">{_inline(label)}</span>'
                f'<span class="arch-kv-val">{_inline(content)}</span>'
                f'</div>'
            )
        else:
            out.append(f'<p class="arch-p">{_inline(stripped)}</p>')
        i += 1

    return '\n'.join(out)


def _flow_node(label: str, name: str, detail: str = '', color: str = '') -> str:
    cls = f' {color}' if color else ''
    det = f'<div class="flow-node-detail">{_e(detail)}</div>' if detail else ''
    return f'''<div class="flow-node{cls}">
  <div class="flow-node-label">{_e(label)}</div>
  <div class="flow-node-name">{_e(name)}</div>
  {det}
</div>'''


def _arrow() -> str:
    return '<div class="flow-arrow">→</div>'


def _section(num: str, title: str, body: str) -> str:
    return f'''<div class="section">
  <div class="section-label">{_e(num)} · {_e(title)}</div>
  {body}
</div>'''


def render_overview_page(p: ProjectInfo, embed: bool = False) -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css = theme_vars_css()
    _tb_css    = topbar_css()
    _tb_html   = "" if embed else topbar_html()
    _overlays  = "" if embed else settings_overlay_html()
    _tb_js     = "" if embed else topbar_js()

    git    = p.git    or type('', (), {'branch': None, 'commit_hash': None, 'dirty_files': [],
                                       'monthly_commits': 0, 'recent_commits': []})()
    deploy = p.deploy or type('', (), {'type': None, 'host': None, 'url': None,
                                       'remote_dir': None, 'cmd': None})()
    loc    = p.loc    or type('', (), {'total_lines': 0, 'code_lines': 0, 'comment_lines': 0,
                                       'blank_lines': 0, 'file_count': 0, 'languages': []})()
    svc    = p.service or type('', (), {'port': None, 'is_running': False})()

    # ── build sections ──────────────────────────────────────────────────────────
    sections = []
    sec_num = 0

    def ns():
        nonlocal sec_num
        sec_num += 1
        return f'{sec_num:02d}'

    # ── 架构描述 ──
    if p.arch_summary:
        body = f'<div class="arch-body">{_rich_arch(p.arch_summary)}</div>'
        sections.append(_section(ns(), '架构描述', body))

    # ── 技术栈 ──
    if p.tech_stack:
        groups: dict[str, list[str]] = {'lang': [], 'web': [], 'ai': [], 'db': [], 'infra': []}
        for t in p.tech_stack:
            n = t.name if hasattr(t, 'name') else str(t)
            groups[_classify(n)].append(n)

        rows = ''
        for cat, items in groups.items():
            if not items:
                continue
            color = _GROUP_COLORS[cat]
            pills = ''.join(f'<span class="pill pill-{color}">{_e(i)}</span>' for i in items)
            rows += f'''<div class="tech-group">
  <div class="tech-group-label" style="color:var(--{color})">{_GROUP_LABELS[cat]}</div>
  <div class="tech-pills">{pills}</div>
</div>'''
        sections.append(_section(ns(), '技术栈', f'<div class="tech-grid">{rows}</div>'))

    # ── 服务依赖图 ──
    ext_deps = p.external_deps or []
    if ext_deps:
        # shared detection
        shared: dict[str, list[str]] = {}
        # (we don't have all projects here, so just annotate port/url)
        nodes_html = _flow_node('本项目', p.name, f':{svc.port}' if svc.port else '', 'blue')
        for d in ext_deps:
            meta = f':{d.port}' if d.port else ''
            if not meta and d.url:
                try:
                    from urllib.parse import urlparse
                    meta = urlparse(d.url if d.url.startswith('http') else 'http://' + d.url).hostname or ''
                except Exception:
                    pass
            nodes_html += _arrow() + _flow_node('外部服务', d.name, meta, 'gold')

        body = f'<div class="card"><div class="flow">{nodes_html}</div></div>'
        sections.append(_section(ns(), '服务依赖', body))

    # ── 部署 ──
    if deploy.type and deploy.type != 'none':
        rows = ''
        if deploy.host:
            rows += f'<tr><td class="k">Host</td><td><code>{_e(deploy.host)}</code></td></tr>'
        if deploy.url:
            rows += f'<tr><td class="k">URL</td><td><a href="{_e(deploy.url)}" target="_blank">{_e(deploy.url)}</a></td></tr>'
        if deploy.remote_dir:
            rows += f'<tr><td class="k">目录</td><td><code>{_e(deploy.remote_dir)}</code></td></tr>'
        if deploy.cmd:
            rows += f'<tr><td class="k">命令</td><td><code>{_e(deploy.cmd)}</code></td></tr>'
        badge_color = {'ec2':'green','netlify':'blue','docker':'blue','vps':'gold','local':'dim'}.get(
            (deploy.type or '').lower(), 'dim')
        body = f'''<div class="card">
  <div style="margin-bottom:14px"><span class="pill pill-{badge_color}" style="font-size:12px">{_e(deploy.type)}</span></div>
  <table class="kv-table">{rows}</table>
</div>'''
        sections.append(_section(ns(), '部署信息', body))

    # ── Git ──
    if git.branch:
        dirty = git.dirty_files or []
        commits = (git.recent_commits or [])[:8]
        commit_rows = ''
        for c in commits:
            if isinstance(c, dict):
                h = (c.get('hash') or '')[:7]
                m = c.get('message') or c.get('msg') or str(c)
            else:
                h, m = '', str(c)
            hash_cell = f'<code style="color:var(--sub);font-size:11px">{_e(h)}</code>' if h else ''
            commit_rows += f'<tr><td>{hash_cell}</td><td>{_e(m)}</td></tr>'

        dirty_html = ''
        if dirty:
            flags = {'M': 'orange', 'A': 'green', 'D': 'red', '?': 'sub'}
            items = ''
            for f in dirty[:20]:
                parts = f.strip().split()
                flag = parts[0] if parts else '??'
                name = ' '.join(parts[1:]) if len(parts) > 1 else f
                col = next((v for k, v in flags.items() if k in flag), 'sub')
                items += f'<div style="font-size:11px;color:var(--{col});font-family:var(--mono)">{_e(flag)} {_e(name)}</div>'
            dirty_html = f'<div style="margin-top:14px;display:flex;flex-direction:column;gap:3px">{items}</div>'

        body = f'''<div class="stat-row">
  <div class="stat-card"><div class="stat-num">{_e(git.branch)}</div><div class="stat-label">分支</div></div>
  <div class="stat-card"><div class="stat-num" style="font-size:16px">{_e((git.commit_hash or '')[:7])}</div><div class="stat-label">最新 commit</div></div>
  <div class="stat-card"><div class="stat-num">{git.monthly_commits or 0}</div><div class="stat-label">本月提交</div></div>
  <div class="stat-card"><div class="stat-num" style="color:{'var(--orange)' if dirty else 'var(--green)'}">{len(dirty)}</div><div class="stat-label">未提交文件</div></div>
</div>
{dirty_html}
{f'<div class="card" style="margin-top:16px;padding:0;overflow:hidden"><table class="ws-table">{commit_rows}</table></div>' if commit_rows else ''}'''
        sections.append(_section(ns(), 'Git 状态', body))

    # ── 代码规模 ──
    if loc.total_lines or loc.code_lines:
        comment_pct = round((loc.comment_lines or 0) / max(loc.total_lines, 1) * 100)
        lang_bars = ''
        langs = (loc.languages or [])[:8]
        max_lines = max((l.code or 0 for l in langs), default=1)
        for i, l in enumerate(langs):
            lines = l.code or 0
            pct = round(lines / max(max_lines, 1) * 100)
            color = LANG_COLORS[i % len(LANG_COLORS)]
            k_label = f'{lines/1000:.1f}k' if lines >= 1000 else str(lines)
            lang_bars += f'''<div class="lang-row">
  <span class="lang-name">{_e(l.name or '')}</span>
  <div class="lang-track"><div class="lang-fill" style="width:{pct}%;background:{color}"></div></div>
  <span class="lang-num">{k_label}</span>
</div>'''

        body = f'''<div class="stat-row">
  <div class="stat-card"><div class="stat-num">{loc.total_lines/1000:.1f}k</div><div class="stat-label">总行数</div></div>
  <div class="stat-card"><div class="stat-num">{loc.code_lines/1000:.1f}k</div><div class="stat-label">代码行</div></div>
  <div class="stat-card"><div class="stat-num">{loc.file_count or 0}</div><div class="stat-label">文件数</div></div>
  <div class="stat-card"><div class="stat-num">{comment_pct}%</div><div class="stat-label">注释率</div></div>
</div>
{f'<div class="card" style="margin-top:16px"><div class="lang-list">{lang_bars}</div></div>' if lang_bars else ''}'''
        sections.append(_section(ns(), '代码规模', body))

    # ── 功能列表 ──
    features = [f for f in (p.features or []) if f.implemented]
    planned  = [f for f in (p.features or []) if not f.implemented]
    if features or planned:
        rows = ''
        for f in features:
            rows += f'<div class="feat-item done">✓ {_e(f.text)}</div>'
        for f in planned:
            rows += f'<div class="feat-item planned">○ {_e(f.text)}</div>'
        sections.append(_section(ns(), '功能列表',
            f'<div class="card"><div class="feat-list">{rows}</div></div>'))

    # ── sub-title (one-liner) ──
    sub = ''
    if p.arch_summary:
        sub = next((l.strip() for l in p.arch_summary.splitlines()
                   if l.strip() and not l.startswith('#')), '')
        sub = re.sub(r'^\*\*[^*]+\*\*[:：]\s*', '', sub)

    svc_badge = ''
    if svc.port:
        cls = 'green' if svc.is_running else 'red'
        label = '● 运行中' if svc.is_running else '○ 停止'
        svc_badge = f'<span class="pill pill-{cls}" style="font-size:12px">{label} :{svc.port}</span>'

    status_badge = f'<span class="pill pill-dim" style="font-size:12px">{_e(p.status or "active")}</span>'
    deploy_badge = ''
    if deploy.type and deploy.type != 'none':
        extra = f' · {_e(deploy.host)}' if deploy.host else ''
        deploy_badge = f'<span class="pill pill-blue" style="font-size:12px">{_e(deploy.type)}{extra}</span>'

    sections_html = '\n'.join(sections)

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(p.name)} · 全局面貌</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<link rel="stylesheet" href="/static/fonts/fonts.css">
<style>
{_theme_css}
{_tb_css}
  /* ── extra color tokens used by this page ── */
  :root {{
    --gold:          #d9b36b; --gold-dim:   rgba(217,179,107,.15); --gold-border:   rgba(217,179,107,.3);
    --blue-dim:      rgba(78,158,255,.12);  --blue-border:   rgba(78,158,255,.3);
    --red-dim:       rgba(255,95,95,.12);   --red-border:    rgba(255,95,95,.3);
    --green-dim:     rgba(92,208,138,.12);  --green-border:  rgba(92,208,138,.3);
    --purple:        #b07cff; --purple-dim: rgba(176,124,255,.12); --purple-border: rgba(176,124,255,.3);
    --dim:           #3a3f4b; --radius-pill: 20px; --card-shadow: none;
  }}
  [data-theme="neon-pixel"] {{
    --gold: #ffff00; --gold-dim: rgba(255,255,0,.12); --gold-border: rgba(255,255,0,.3);
    --blue-dim: rgba(0,255,255,.12); --blue-border: rgba(0,255,255,.3);
    --red-dim: rgba(255,0,64,.12); --red-border: rgba(255,0,64,.3);
    --green-dim: rgba(0,255,0,.12); --green-border: rgba(0,255,0,.3);
    --purple: #ff00ff; --purple-dim: rgba(255,0,255,.12); --purple-border: rgba(255,0,255,.3);
    --dim: #282840; --radius-pill: 0px; --card-shadow: 2px 2px 0 var(--border);
  }}
  [data-theme="pixel-cyber"] {{
    --gold: #ffaa00; --gold-dim: rgba(255,170,0,.12); --gold-border: rgba(255,170,0,.3);
    --blue-dim: rgba(0,212,255,.12); --blue-border: rgba(0,212,255,.3);
    --red-dim: rgba(255,51,85,.12); --red-border: rgba(255,51,85,.3);
    --green-dim: rgba(0,255,136,.12); --green-border: rgba(0,255,136,.3);
    --purple: #dd00ff; --purple-dim: rgba(221,0,255,.12); --purple-border: rgba(221,0,255,.3);
    --dim: #2a5570; --radius-pill: 0px; --card-shadow: 2px 2px 0 var(--border);
  }}
  body {{ padding: 28px 32px 80px; }}
  body::before {{
    content: ''; position: fixed; inset: 0;
    background-image:
      linear-gradient(rgba(217,179,107,.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(217,179,107,.025) 1px, transparent 1px);
    background-size: 40px 40px; pointer-events: none; z-index: 0;
  }}
  .wrap {{ position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; }}

  /* ── page header ── */
  .page-header {{ margin-bottom: 52px; }}
  .page-header-eyebrow {{
    font-size: 10px; letter-spacing: 4px; color: var(--gold);
    text-transform: uppercase; margin-bottom: 10px;
  }}
  .page-header h1 {{
    font-family: var(--sans); font-size: 36px; font-weight: 900;
    color: var(--text); letter-spacing: 2px; margin-bottom: 8px;
  }}
  .page-header-sub {{ font-size: 13px; color: var(--sub); line-height: 1.6; margin-bottom: 14px; }}
  .badge-row {{ display: flex; gap: 8px; flex-wrap: wrap; }}

  /* ── section ── */
  .section {{ margin-bottom: 48px; }}
  .section-label {{
    display: inline-flex; align-items: center; gap: 10px;
    font-size: 11px; font-weight: 600; letter-spacing: 3px;
    color: var(--gold); text-transform: uppercase; margin-bottom: 20px;
  }}
  .section-label::before {{
    content: ''; display: inline-block; width: 20px; height: 1px;
    background: var(--gold); opacity: .5;
  }}

  /* ── card ── */
  .card {{
    background: var(--panel); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 24px 28px; box-shadow: var(--card-shadow);
  }}
  /* ── rich arch body ── */
  .arch-body {{ display: flex; flex-direction: column; gap: 14px; }}
  .arch-section-label {{
    font-size: 11px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase;
    color: var(--gold); display: flex; align-items: center; gap: 10px;
    margin-top: 6px;
  }}
  .arch-section-label::before {{
    content: ''; display: inline-block; width: 18px; height: 1px; background: var(--gold); opacity: .5;
  }}
  .arch-hr {{ height: 1px; background: linear-gradient(90deg, transparent, rgba(217,179,107,.2), transparent); }}
  .arch-p {{
    font-size: 13px; color: rgba(238,241,247,.75); line-height: 1.75; margin: 0;
  }}
  .arch-kv {{
    display: flex; align-items: baseline; gap: 10px; font-size: 13px;
    background: rgba(255,255,255,.03); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 12px 16px;
  }}
  .arch-kv-label {{
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;
    color: var(--gold); white-space: nowrap; flex-shrink: 0;
  }}
  .arch-kv-val {{ color: rgba(238,241,247,.8); line-height: 1.6; }}

  /* ── module cards ── */
  .mod-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }}
  .mod-card {{
    background: rgba(255,255,255,.03); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 14px 16px;
  }}
  .mod-card.simple {{ padding: 10px 14px; }}
  .mod-name {{
    font-size: 12px; font-weight: 700; color: var(--text); margin-bottom: 5px;
    font-family: var(--mono);
  }}
  .mod-desc {{ font-size: 11px; color: var(--sub); line-height: 1.55; }}

  /* ── tech stack ── */
  .tech-grid {{ display: flex; flex-direction: column; gap: 16px; }}
  .tech-group {{ display: flex; align-items: flex-start; gap: 14px; }}
  .tech-group-label {{ font-size: 10px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; width: 90px; flex-shrink: 0; padding-top: 3px; }}
  .tech-pills {{ display: flex; flex-wrap: wrap; gap: 6px; }}

  /* ── pills ── */
  .pill {{ display: inline-block; font-size: 11px; padding: 3px 10px;
    border-radius: var(--radius-sm); border: 1px solid; font-weight: 600; }}
  .pill-blue   {{ background: var(--blue-dim);   border-color: var(--blue-border);   color: var(--blue); }}
  .pill-green  {{ background: var(--green-dim);  border-color: var(--green-border);  color: var(--green); }}
  .pill-purple {{ background: var(--purple-dim); border-color: var(--purple-border); color: var(--purple); }}
  .pill-gold   {{ background: var(--gold-dim);   border-color: var(--gold-border);   color: var(--gold); }}
  .pill-red    {{ background: var(--red-dim);    border-color: var(--red-border);    color: var(--red); }}
  .pill-dim    {{ background: rgba(255,255,255,.05); border-color: var(--border);    color: var(--sub); }}

  /* ── service flow ── */
  .flow {{ display: flex; align-items: center; flex-wrap: wrap; gap: 0; row-gap: 14px; }}
  .flow-node {{ flex-shrink: 0; border-radius: var(--radius); padding: 14px 18px;
    border: 1px solid var(--border); background: rgba(255,255,255,.03); min-width: 120px; }}
  .flow-node.blue   {{ border-color: var(--blue-border);   background: var(--blue-dim); }}
  .flow-node.gold   {{ border-color: var(--gold-border);   background: var(--gold-dim); }}
  .flow-node.green  {{ border-color: var(--green-border);  background: var(--green-dim); }}
  .flow-node.purple {{ border-color: var(--purple-border); background: var(--purple-dim); }}
  .flow-node-label {{ font-size: 9px; color: var(--sub); letter-spacing: 2px; margin-bottom: 5px; text-transform: uppercase; }}
  .flow-node-name  {{ font-size: 13px; font-weight: 700; color: var(--text); }}
  .flow-node-detail{{ font-size: 11px; color: var(--sub); margin-top: 4px; line-height: 1.5; }}
  .flow-arrow {{ color: var(--sub); font-size: 18px; padding: 0 10px; flex-shrink: 0; }}

  /* ── stats ── */
  .stat-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .stat-card {{ background: var(--panel); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 18px 16px; box-shadow: var(--card-shadow); }}
  .stat-num {{ font-size: 26px; font-weight: 700; color: var(--text);
    font-variant-numeric: tabular-nums; margin-bottom: 4px; }}
  .stat-label {{ font-size: 11px; color: var(--sub); letter-spacing: .5px; }}

  /* ── lang bars ── */
  .lang-list {{ display: flex; flex-direction: column; gap: 8px; }}
  .lang-row {{ display: flex; align-items: center; gap: 10px; font-size: 12px; }}
  .lang-name {{ width: 90px; color: var(--sub); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .lang-track {{ flex: 1; height: 5px; background: rgba(255,255,255,.05); border-radius: 3px; overflow: hidden; }}
  .lang-fill {{ height: 100%; border-radius: 3px; }}
  .lang-num {{ width: 50px; text-align: right; color: var(--sub); }}

  /* ── kv table ── */
  .kv-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .kv-table td {{ padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,.04); vertical-align: top; }}
  .kv-table tr:last-child td {{ border-bottom: none; }}
  .kv-table td.k {{ color: var(--sub); width: 80px; font-size: 11px; letter-spacing: 1px; padding-top: 10px; }}
  .kv-table a {{ color: var(--blue); }}
  code {{ font-family: var(--mono); font-size: 11px; background: rgba(255,255,255,.06);
    padding: 2px 6px; border-radius: var(--radius-sm); color: var(--gold); }}

  /* ── commit table ── */
  .ws-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .ws-table td {{ padding: 9px 16px; border-bottom: 1px solid rgba(255,255,255,.04);
    color: rgba(238,241,247,.7); line-height: 1.5; }}
  .ws-table tr:last-child td {{ border-bottom: none; }}

  /* ── features ── */
  .feat-list {{ display: flex; flex-direction: column; gap: 7px; }}
  .feat-item {{ font-size: 13px; line-height: 1.5; }}
  .feat-item.done {{ color: rgba(238,241,247,.8); }}
  .feat-item.planned {{ color: var(--sub); }}
  .feat-item.done::first-letter {{ color: var(--green); }}

  @media (max-width: 640px) {{
    body {{ padding: 24px 16px 40px; }}

    .page-header {{ margin-bottom: 28px; }}
    .page-header h1 {{ font-size: 22px; letter-spacing: 1px; }}

    .card {{ padding: 16px; border-radius: var(--radius); }}
    .section {{ margin-bottom: 28px; }}

    /* stat grid: 2 columns */
    .stat-row {{ grid-template-columns: repeat(2, 1fr); }}
    .stat-card {{ padding: 14px 12px; }}
    .stat-num {{ font-size: 20px; }}

    /* tech stack: stack label above pills */
    .tech-group {{ flex-direction: column; gap: 6px; }}
    .tech-group-label {{ width: auto; }}

    /* module grid: single column */
    .mod-grid {{ grid-template-columns: 1fr; }}

    /* flow: vertical */
    .flow {{ flex-direction: column; align-items: stretch; }}
    .flow-arrow {{ transform: rotate(90deg); text-align: center; padding: 4px 0; }}

    /* arch kv: stack */
    .arch-kv {{ flex-direction: column; gap: 4px; }}
  }}
</style>
</head>
<body>
{_tb_html}
<div class="wrap">
  <div class="page-header">
    <div class="page-header-eyebrow">全局面貌 · {_e(p.path)}</div>
    <h1>{_e(p.name)}</h1>
    {f'<div class="page-header-sub">{_e(sub)}</div>' if sub else ''}
    <div class="badge-row">{svc_badge}{deploy_badge}{status_badge}</div>
  </div>

  {sections_html}
</div>
{_overlays}
<script>
{_tb_js}
</script>
</body>
</html>'''
