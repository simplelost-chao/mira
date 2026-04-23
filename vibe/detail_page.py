"""Full project detail page with tabs: 全局面貌 · 设计文档 · 计划."""

def render_detail_page(project_id: str, project_name: str) -> str:
    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>{project_name} · Mira</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Noto+Sans+SC:wght@400;700&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #080c14; --panel: rgba(14,20,36,.95); --border: rgba(255,255,255,.07);
    --text: #eef1f7; --sub: #7a8499; --muted: #4a5060;
    --accent: #4f46e5;
    --gold: #d9b36b; --gold-dim: rgba(217,179,107,.15); --gold-border: rgba(217,179,107,.3);
    --blue: #4e9eff; --blue-dim: rgba(78,158,255,.12); --blue-border: rgba(78,158,255,.3);
    --green: #5cd08a; --green-dim: rgba(92,208,138,.12); --green-border: rgba(92,208,138,.3);
    --purple: #b07cff; --purple-dim: rgba(176,124,255,.12); --purple-border: rgba(176,124,255,.3);
    --orange: #e5a650;
    --red: #e06c75;
    --mono: 'JetBrains Mono', monospace;
    --sans: 'Noto Sans SC', sans-serif;
  }}
  [data-theme="neon-pixel"] {{
    --bg: #0a0a0a; --panel: rgba(20,20,20,.95); --border: #00ff00;
    --text: #e0e0ff; --sub: #a0a0cc; --muted: #505070;
    --accent: #ff00ff;
    --gold: #ffff00; --gold-dim: rgba(255,255,0,.12); --gold-border: rgba(255,255,0,.3);
    --blue: #00ffff; --blue-dim: rgba(0,255,255,.12); --blue-border: rgba(0,255,255,.3);
    --green: #00ff00; --green-dim: rgba(0,255,0,.12); --green-border: rgba(0,255,0,.3);
    --purple: #ff00ff; --purple-dim: rgba(255,0,255,.12); --purple-border: rgba(255,0,255,.3);
    --orange: #ff8800; --red: #ff0040;
  }}
  [data-theme="pixel-cyber"] {{
    --bg: #020c1a; --panel: rgba(10,31,56,.95); --border: #00d4ff;
    --text: #eef8ff; --sub: #a8daf0; --muted: #6bbad8;
    --accent: #ff0055;
    --gold: #ffaa00; --gold-dim: rgba(255,170,0,.12); --gold-border: rgba(255,170,0,.3);
    --blue: #00d4ff; --blue-dim: rgba(0,212,255,.12); --blue-border: rgba(0,212,255,.3);
    --green: #00ff88; --green-dim: rgba(0,255,136,.12); --green-border: rgba(0,255,136,.3);
    --purple: #dd00ff; --purple-dim: rgba(221,0,255,.12); --purple-border: rgba(221,0,255,.3);
    --orange: #ffaa00; --red: #ff3355;
  }}
  [data-theme="pixel-cyber"] body {{
    background-image: linear-gradient(rgba(0,212,255,0.04) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(0,212,255,0.04) 1px, transparent 1px);
    background-size: 8px 8px;
  }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--mono); min-height: 100vh; }}

  /* ── topbar (matches main page) ── */
  .topbar {{
    position: sticky; top: 0; z-index: 100;
    background: var(--panel); border-bottom: 1px solid var(--border);
    backdrop-filter: blur(12px);
    display: flex; align-items: center; gap: 8px; padding: 0 20px; height: 52px;
  }}
  .topbar-brand {{
    font-size: 15px; font-weight: 700; color: var(--text);
    text-decoration: none; letter-spacing: -0.3px; flex-shrink: 0;
  }}
  .topbar-sep {{
    width: 1px; height: 18px; background: var(--border); flex-shrink: 0; margin: 0 4px;
  }}
  .back-btn {{
    display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--sub);
    text-decoration: none; transition: color .15s; flex-shrink: 0;
  }}
  .back-btn:hover {{ color: var(--text); }}
  .proj-name {{
    font-size: 13px; font-weight: 600; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 260px;
  }}
  .topbar-spacer {{ flex: 1; }}
  .refresh-btn {{
    font-size: 11px; padding: 5px 10px; background: none; border: 1px solid var(--border);
    border-radius: 5px; color: var(--sub); cursor: pointer; font-family: var(--mono);
    transition: all .15s;
  }}
  .refresh-btn:hover {{ border-color: var(--accent); color: var(--accent); }}

  /* ── subnav (tab bar) ── */
  .subnav {{
    position: sticky; top: 52px; z-index: 99;
    background: var(--panel); border-bottom: 1px solid var(--border);
    backdrop-filter: blur(8px);
    display: flex; align-items: stretch; padding: 0 20px; height: 40px; gap: 2px;
  }}
  .tab-btn {{
    height: 100%; padding: 0 16px; background: none; border: none;
    font-family: var(--mono); font-size: 12px; color: var(--sub); cursor: pointer;
    border-bottom: 2px solid transparent; transition: all .15s;
  }}
  .tab-btn:hover {{ color: var(--text); }}
  .tab-btn.active {{ color: var(--accent); border-bottom-color: var(--accent); }}

  /* ── content ── */
  .content {{ position: relative; z-index: 1; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* ── overview iframe ── */
  .overview-frame {{
    width: 100%; border: none; min-height: calc(100vh - 92px);
    background: var(--bg);
  }}

  /* ── design docs ── */
  .docs-layout {{ display: grid; grid-template-columns: 220px 1fr; min-height: calc(100vh - 92px); }}
  .docs-sidebar {{
    border-right: 1px solid var(--border); padding: 20px 0;
    background: rgba(0,0,0,.2);
  }}
  .docs-sidebar-title {{
    font-size: 10px; font-weight: 700; letter-spacing: 2px; color: var(--muted);
    text-transform: uppercase; padding: 0 16px 12px;
  }}
  .doc-item {{
    display: block; padding: 9px 16px; font-size: 12px; color: var(--sub);
    cursor: pointer; border-left: 2px solid transparent; transition: all .15s;
    text-overflow: ellipsis; overflow: hidden; white-space: nowrap;
  }}
  .doc-item:hover {{ color: var(--text); background: rgba(255,255,255,.03); }}
  .doc-item.active {{ color: var(--accent); border-left-color: var(--accent); background: rgba(79,70,229,.06); }}
  .doc-item.stale {{ opacity: .55; }}
  .docs-body {{ padding: 32px 40px; overflow-y: auto; max-height: calc(100vh - 92px); }}
  .doc-title {{ font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 6px; }}
  .doc-meta  {{ font-size: 11px; color: var(--muted); margin-bottom: 24px; }}
  .doc-content {{
    font-size: 13px; color: var(--sub); line-height: 1.8;
  }}
  .doc-content h1,.doc-content h2,.doc-content h3 {{
    font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;
    color: var(--gold); margin: 20px 0 8px; padding-bottom: 5px;
    border-bottom: 1px solid rgba(217,179,107,.15);
  }}
  .doc-content h1:first-child,.doc-content h2:first-child {{ margin-top: 0; }}
  .doc-content p {{ margin: 0 0 10px; }}
  .doc-content ul {{ margin: 4px 0 10px 20px; }}
  .doc-content li {{ margin-bottom: 4px; }}
  .doc-content strong {{ color: var(--text); }}
  .doc-content code {{ font-family: var(--mono); font-size: 11px; background: rgba(255,255,255,.07);
    border: 1px solid var(--border); border-radius: 4px; padding: 1px 6px; color: var(--gold); }}
  .doc-content pre {{ background: rgba(0,0,0,.4); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px 16px; overflow-x: auto; margin: 10px 0; font-size: 12px; }}
  .doc-content pre code {{ background: none; border: none; padding: 0; }}
  .doc-content hr {{ border: none; border-top: 1px solid var(--border); margin: 16px 0; }}
  .doc-content blockquote {{ border-left: 3px solid var(--gold); padding-left: 14px; color: var(--sub); }}
  .empty-state {{ display: flex; flex-direction: column; align-items: center; justify-content: center;
    height: calc(100vh - 92px); color: var(--muted); gap: 10px; font-size: 13px; }}
  .empty-icon {{ font-size: 40px; opacity: .3; }}

  /* ── plans ── */
  .plans-wrap {{ padding: 32px 40px; max-width: 860px; }}
  .plan-file-header {{
    display: flex; align-items: center; gap: 10px;
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px;
    color: var(--gold); margin: 28px 0 14px;
  }}
  .plan-file-header::before {{ content: ''; display: inline-block; width: 20px; height: 1px; background: var(--gold); opacity: .5; }}
  .plan-progress-row {{
    display: flex; align-items: center; gap: 10px; margin-bottom: 14px; font-size: 12px; color: var(--sub);
  }}
  .plan-track {{ flex: 1; max-width: 200px; height: 4px; background: rgba(255,255,255,.07); border-radius: 2px; overflow: hidden; }}
  .plan-fill  {{ height: 100%; background: var(--green); border-radius: 2px; transition: width .3s; }}
  .task-item {{
    display: flex; align-items: flex-start; gap: 10px; padding: 8px 12px;
    border-radius: 6px; margin-bottom: 4px; font-size: 13px; line-height: 1.55;
    transition: background .15s;
  }}
  .task-item:hover {{ background: rgba(255,255,255,.03); }}
  .task-check {{ flex-shrink: 0; margin-top: 2px; width: 16px; height: 16px;
    border-radius: 50%; border: 1.5px solid; display: flex; align-items: center; justify-content: center; font-size: 9px; }}
  .task-check.done {{ background: var(--green-dim); border-color: var(--green); color: var(--green); }}
  .task-check.todo {{ border-color: var(--muted); color: transparent; }}
  .task-text.done {{ color: var(--sub); text-decoration: line-through; }}
  .task-text.todo {{ color: var(--text); }}

  /* ── prompts ── */
  .prompts-wrap {{ padding: 24px 32px; max-width: 860px; }}
  .prompts-search {{
    width: 100%; padding: 9px 14px; background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-family: var(--mono); font-size: 13px;
    outline: none; margin-bottom: 20px; transition: border-color .15s;
  }}
  .prompts-search:focus {{ border-color: var(--accent); }}
  .prompt-card {{
    padding: 12px 16px; border-radius: 8px; border: 1px solid var(--border);
    background: rgba(255,255,255,.02); margin-bottom: 10px;
    transition: border-color .15s; cursor: default;
  }}
  .prompt-card:hover {{ border-color: rgba(255,255,255,.14); background: rgba(255,255,255,.03); }}
  .prompt-date {{ font-size: 10px; color: var(--muted); margin-bottom: 6px; font-family: var(--mono); }}
  .prompt-text {{ font-size: 13px; color: var(--sub); line-height: 1.7; white-space: pre-wrap; word-break: break-word; }}
  .prompt-text mark {{ background: rgba(79,70,229,.35); color: var(--text); border-radius: 2px; padding: 0 1px; }}
  .prompts-empty {{ padding: 60px 0; text-align: center; color: var(--muted); font-size: 13px; }}

  /* ── summary tab ── */
  .stats-bar {{
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 8px; margin-bottom: 16px;
  }}
  .stats-cell {{
    background: rgba(255,255,255,.03); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 12px;
  }}
  .stats-val {{ font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 2px; font-variant-numeric: tabular-nums; }}
  .stats-lbl {{ font-size: 9px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }}
  .summary-grid {{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 12px; margin-bottom: 12px;
  }}
  .summary-card {{
    background: rgba(255,255,255,.025); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px 16px;
  }}
  .summary-card.claude-card {{
    background: rgba(var(--accent-rgb, 79,70,229),.04); border-color: rgba(var(--accent-rgb, 79,70,229),.15);
  }}
  .card-section-title {{
    font-size: 9px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: var(--muted); margin-bottom: 10px;
  }}
  .commit-list {{ display: flex; flex-direction: column; gap: 4px; margin-top: 10px; }}
  .commit-row {{ display: flex; gap: 8px; font-size: 11px; line-height: 1.5; }}
  .commit-hash {{ color: var(--purple); flex-shrink: 0; font-family: var(--mono); }}
  .commit-msg {{ color: var(--sub); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .tech-full-card {{
    background: rgba(255,255,255,.025); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px 16px;
  }}

  /* ── loading ── */
  .loading {{ display: flex; align-items: center; justify-content: center; height: calc(100vh - 92px); color: var(--muted); font-size: 13px; gap: 8px; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .spinner {{ width: 16px; height: 16px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite; }}

  /* Claude panel */
  .cl-wrap {{ max-width: 860px; padding: 24px; }}
  .cl-summary {{ display: flex; gap: 12px; margin-bottom: 20px; }}
  .cl-sum-card {{ flex: 1; padding: 12px 14px; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; }}
  .cl-sum-card.purple {{ background: rgba(var(--accent-rgb, 79,70,229),.06); border-color: rgba(var(--accent-rgb, 79,70,229),.2); }}
  .cl-sum-card.green  {{ background: var(--green-dim); border-color: var(--green-border); }}
  .cl-sv {{ font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 2px; }}
  .cl-sum-card.purple .cl-sv {{ color: var(--purple); }}
  .cl-sum-card.green  .cl-sv {{ color: var(--green); }}
  .cl-sl {{ font-size: 9px; color: var(--muted); letter-spacing: 1.5px; text-transform: uppercase; }}
  .cl-section-title {{ font-size: 9px; color: var(--muted); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; margin-top: 18px; }}
  .cl-tok-grid {{ display: flex; gap: 8px; }}
  .cl-tok-col {{ flex: 1; padding: 8px 10px; background: var(--panel); border: 1px solid var(--border); border-radius: 6px; }}
  .cl-tv {{ font-size: 14px; font-weight: 700; color: var(--text); }}
  .cl-tl {{ font-size: 9px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-top: 2px; }}
  .cl-tsub {{ font-size: 10px; color: var(--muted); margin-top: 3px; }}
  .cl-cost-bar {{ display: flex; height: 5px; border-radius: 3px; overflow: hidden; margin-top: 10px; }}
  .cl-legend {{ display: flex; gap: 16px; margin-top: 8px; flex-wrap: wrap; }}
  .cl-leg-item {{ font-size: 10px; color: var(--sub); display: flex; align-items: center; gap: 4px; }}
  .cl-leg-dot {{ width: 8px; height: 8px; border-radius: 2px; display: inline-block; }}
  .cl-bottom {{ display: flex; gap: 16px; margin-top: 4px; }}
  .cl-col-l {{ flex: 1.4; }}
  .cl-col-r {{ flex: 1; }}
  .cl-spark {{ display: flex; gap: 3px; align-items: flex-end; height: 48px; margin-top: 6px; }}
  .cl-bar {{ flex: 1; border-radius: 2px 2px 0 0; background: var(--border); min-height: 2px; }}
  .cl-bar.on {{ background: var(--accent); }}
  .cl-bar.hi {{ background: var(--purple); }}
  .cl-summary-text {{ font-size: 12px; color: var(--sub); line-height: 1.9; margin-top: 6px; }}
  .cl-summary-text b {{ color: var(--text); }}
  .cl-todos {{ display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }}
  .cl-todo {{ font-size: 11px; padding: 5px 8px; border-radius: 4px; color: var(--sub); }}
  .cl-todo.done {{ color: var(--green); opacity: .6; }}
  .cl-todo.wip  {{ color: var(--accent); background: var(--panel); }}
  .cl-todo.pend {{ color: var(--muted); }}

</style>
</head>
<body>

<div class="topbar">
  <a class="topbar-brand" href="/">✦ Mira</a>
  <div class="topbar-sep"></div>
  <a class="back-btn" href="/">← 项目列表</a>
  <div class="topbar-sep"></div>
  <span class="proj-name" id="proj-name">{project_name}</span>
  <div class="topbar-spacer"></div>
  <button class="refresh-btn" onclick="reload()">↻</button>
</div>
<div class="subnav">
  <button class="tab-btn active" id="tab-summary" onclick="showTab('summary')">概览</button>
  <button class="tab-btn" id="tab-overview" onclick="showTab('overview')">系统架构</button>
  <button class="tab-btn" id="tab-design" onclick="showTab('design')">设计文档</button>
  <button class="tab-btn" id="tab-prompts" onclick="showTab('prompts')">Prompts</button>
</div>

<div class="content">
  <div class="tab-panel active" id="panel-summary">
    <div class="loading"><div class="spinner"></div>加载中...</div>
  </div>
  <div class="tab-panel" id="panel-overview">
    <div class="loading"><div class="spinner"></div>加载中...</div>
  </div>
  <div class="tab-panel" id="panel-design">
    <div class="loading"><div class="spinner"></div>加载中...</div>
  </div>
  <div class="tab-panel" id="panel-prompts"></div>
</div>

<script>
const PROJECT_ID = {repr(project_id)};
let projectData = null;
let activeTab = 'summary';
let summaryLoaded = false;
let overviewLoaded = false;
let designLoaded = false;
let promptsLoaded = false;

function showTab(name) {{
  activeTab = name;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
  if (name === 'summary'  && !summaryLoaded)  renderSummary();
  if (name === 'overview' && !overviewLoaded) loadOverview();
  if (name === 'design'   && !designLoaded)   renderDesign();
  if (name === 'prompts'  && !promptsLoaded)  renderPrompts();
}}

function escHtml(s) {{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function simpleMarkdown(md) {{
  if (!md) return '';
  let t = escHtml(md);
  t = t.replace(/```[\\w]*\\n?([\\s\\S]*?)```/g, (_,c)=>`<pre><code>${{c.trim()}}</code></pre>`);
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
  t = t.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
  t = t.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  t = t.replace(/^## (.+)$/gm,  '<h2>$1</h2>');
  t = t.replace(/^# (.+)$/gm,   '<h1>$1</h1>');
  t = t.replace(/^---+$/gm, '<hr>');
  t = t.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  t = t.replace(/^[*\\-] (.+)$/gm, '<li>$1</li>');
  t = t.replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>');
  t = t.replace(/(<li>[\\s\\S]*?<\\/li>\\n?)+/g, m=>`<ul>${{m}}</ul>`);
  t = t.replace(/^(?!<[a-z\\/]|$)(.+)$/gm, '<p>$1</p>');
  return t;
}}

// ── Overview ──────────────────────────────────────────────────────────────────
async function loadOverview() {{
  const el = document.getElementById('panel-overview');
  try {{
    const res = await fetch(`/projects/${{PROJECT_ID}}/overview`);
    const html = await res.text();
    // Inject the overview page content into an iframe
    const iframe = document.createElement('iframe');
    iframe.className = 'overview-frame';
    iframe.srcdoc = html;
    el.innerHTML = '';
    el.appendChild(iframe);
    overviewLoaded = true;
  }} catch(e) {{
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">🌐</div><div>加载失败: ${{e.message}}</div></div>`;
  }}
}}

// ── Summary Tab: stats bar + 2-col grid ──────────────────────────────────────
  function renderSummary() {{
    const el = document.getElementById('panel-summary');
    const p = projectData || {{}};
    const ca = p.claude_activity || null;
    const svc = p.service || {{}};
    const deploy = p.deploy || {{}};
    const techStack = p.tech_stack || [];
    const features = p.features || [];
    const git = p.git || {{}};
    const loc = p.loc || {{}};

    function fmtTok(t) {{
      if (!t) return '—';
      if (t >= 1e9) return (t/1e9).toFixed(1)+'B';
      if (t >= 1e6) return (t/1e6).toFixed(1)+'M';
      if (t >= 1e3) return (t/1e3).toFixed(0)+'k';
      return String(t);
    }}

    const isRunning = svc.is_running;
    const svcPort = svc.port ? `:${{svc.port}}` : '';
    let caLastStr = '';
    if (ca && ca.last_session) {{
      const diff = (Date.now() - new Date(ca.last_session)) / 1000;
      caLastStr = diff < 3600 ? Math.round(diff/60)+'m前' : diff < 86400 ? Math.round(diff/3600)+'h前' : Math.round(diff/86400)+'d前';
    }}

    // ── Hero ──
    const svcBadge = svc.port
      ? `<span style="font-size:11px;padding:4px 12px;border-radius:20px;border:1px solid ${{isRunning ? 'rgba(92,208,138,.25)' : 'rgba(255,255,255,.1)'}};background:${{isRunning ? 'rgba(92,208,138,.08)' : 'rgba(255,255,255,.04)'}};color:${{isRunning ? 'var(--green)' : 'var(--sub)'}};display:inline-flex;align-items:center;gap:5px">
          <span style="width:6px;height:6px;border-radius:50%;background:${{isRunning ? 'var(--green)' : 'var(--border)'}}"></span>
          ${{isRunning ? '运行中' : '停止'}} ${{svcPort}}
        </span>`
      : '';
    const domainBadge = svc.public_domain
      ? `<span style="font-size:11px;padding:4px 12px;border-radius:20px;border:1px solid rgba(129,140,248,.2);background:rgba(129,140,248,.06);color:var(--purple)">${{escHtml(svc.public_domain)}}</span>`
      : '';
    const deployBadge = deploy.type && deploy.type !== 'none'
      ? `<span style="font-size:11px;padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);color:var(--sub)">☁️ ${{escHtml(deploy.type)}}${{deploy.host ? ' · '+escHtml(deploy.host) : ''}}</span>`
      : '';
    const statusBadge = `<span style="font-size:11px;padding:4px 12px;border-radius:20px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);color:var(--sub)">${{escHtml(p.status || 'active')}}</span>`;

    let html = `<div style="padding:20px;max-width:960px">`;

    // Hero row
    html += `<div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:20px">
      <div>
        <div style="font-size:22px;font-weight:700;margin-bottom:5px">${{escHtml(p.name || '')}}</div>
        <div style="font-size:11px;color:var(--muted);margin-bottom:10px">${{escHtml(p.path || '')}}</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px">${{svcBadge}}${{domainBadge}}${{deployBadge}}${{statusBadge}}</div>
      </div>
      ${{caLastStr ? `<div style="font-size:11px;color:var(--muted);flex-shrink:0;padding-top:4px">Claude ${{caLastStr}}</div>` : ''}}
    </div>`;

    // ── Stats bar ──
    const done = features.filter(f => f.implemented);
    const featPct = features.length ? Math.round(done.length / features.length * 100) : null;
    const codeLinesStr = loc.code_lines ? (loc.code_lines >= 1000 ? (loc.code_lines/1000).toFixed(1)+'k' : String(loc.code_lines)) : '—';

    html += `<div class="stats-bar">
      <div class="stats-cell">
        <div class="stats-val" style="color:var(--gold)">${{git.monthly_commits ?? 0}}</div>
        <div class="stats-lbl">本月提交</div>
      </div>
      <div class="stats-cell">
        <div class="stats-val" style="color:var(--purple)">${{ca ? '$' + (ca.estimated_cost_usd||0).toFixed(1) : '—'}}</div>
        <div class="stats-lbl">Claude 花费</div>
      </div>
      <div class="stats-cell">
        <div class="stats-val" style="color:var(--purple)">${{ca ? (ca.session_count_30d||0) : '—'}}</div>
        <div class="stats-lbl">30天会话</div>
      </div>
      <div class="stats-cell">
        <div class="stats-val">${{codeLinesStr}}</div>
        <div class="stats-lbl">代码行</div>
      </div>
      <div class="stats-cell">
        <div class="stats-val" style="color:var(--green)">${{featPct !== null ? featPct+'%' : '—'}}</div>
        <div class="stats-lbl">功能完成</div>
      </div>
    </div>`;

    // ── 2-col grid: Claude | Git ──
    html += `<div class="summary-grid">`;

    // Claude card
    if (ca) {{
      const spark = ca.session_spark_15d || [];
      const sparkMax = Math.max(...spark, 0.1);
      const sparkBars = spark.map(v => {{
        const h = v === 0 ? 100 : Math.min(100, Math.max(15, Math.round((v/12)*100)));
        const cls = v === 0 ? '' : (v >= 12 || v >= sparkMax*0.7) ? ' hi' : ' on';
        return `<span class="cl-bar${{cls}}" style="height:${{h}}%" title="${{v.toFixed(1)}}h"></span>`;
      }}).join('');

      const todos = (ca.todos || []).slice(0, 4);
      const todoHtml = todos.map(t => {{
        const s = t.status || 'pending';
        const dotColor = s==='completed'?'var(--green)':s==='in_progress'?'var(--gold)':'var(--border)';
        const textColor = s==='completed'?'var(--green)':s==='in_progress'?'var(--gold)':'var(--sub)';
        return `<div style="display:flex;align-items:flex-start;gap:5px;font-size:10px">
          <div style="width:5px;height:5px;border-radius:50%;background:${{dotColor}};flex-shrink:0;margin-top:3px"></div>
          <span style="color:${{textColor}}">${{escHtml(t.content||'')}}</span>
        </div>`;
      }}).join('');

      html += `<div class="summary-card claude-card">
        <div class="card-section-title">Claude</div>
        <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:10px">
          <div><div style="font-size:16px;font-weight:700;color:var(--purple)">${{ca ? '$' + (ca.estimated_cost_usd||0).toFixed(1) : '—'}}</div><div style="font-size:9px;color:var(--muted);margin-top:2px">累计花费</div></div>
          <div><div style="font-size:16px;font-weight:700;color:var(--purple)">${{ca.session_count_30d||0}}</div><div style="font-size:9px;color:var(--muted);margin-top:2px">30天会话</div></div>
          <div><div style="font-size:16px;font-weight:700;color:var(--purple)">${{fmtTok(ca.output_tokens||0)}}</div><div style="font-size:9px;color:var(--muted);margin-top:2px">输出</div></div>
        </div>
        <div class="cl-spark">${{sparkBars}}</div>
        ${{todoHtml ? `<div style="margin-top:10px;display:flex;flex-direction:column;gap:4px">${{todoHtml}}</div>` : ''}}
      </div>`;
    }} else {{
      html += `<div class="summary-card" style="display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:12px">暂无 Claude 数据</div>`;
    }}

    // Git card
    const dirtyCount = (git.dirty_files || []).length;
    const dirtyColor = dirtyCount > 0 ? 'var(--orange)' : 'var(--green)';
    const recentCommits = (git.recent_commits || []).slice(0, 3);
    const commitHtml = recentCommits.map(c => {{
      const h = typeof c === 'object' ? (c.hash || c.sha || '').slice(0,7) : '';
      const m = typeof c === 'object' ? (c.message || c.msg || String(c)) : String(c);
      return `<div class="commit-row">
        ${{h ? `<span class="commit-hash">${{escHtml(h)}}</span>` : ''}}
        <span class="commit-msg">${{escHtml(m)}}</span>
      </div>`;
    }}).join('');

    html += `<div class="summary-card">
      <div class="card-section-title">代码库</div>
      <div style="display:flex;gap:14px;flex-wrap:wrap">
        <div><div style="font-size:16px;font-weight:700;color:var(--gold)">${{git.monthly_commits ?? 0}}</div><div style="font-size:9px;color:var(--muted);margin-top:2px">本月提交</div></div>
        <div><div style="font-size:16px;font-weight:700;color:var(--text)">${{codeLinesStr}}</div><div style="font-size:9px;color:var(--muted);margin-top:2px">代码行</div></div>
        <div><div style="font-size:16px;font-weight:700;color:${{dirtyColor}}">${{dirtyCount}}</div><div style="font-size:9px;color:var(--muted);margin-top:2px">未提交</div></div>
      </div>
      ${{commitHtml ? `<div class="commit-list">${{commitHtml}}</div>` : ''}}
    </div>`;

    html += `</div>`;  // end summary-grid

    // ── Tech stack (full width) ──
    if (techStack.length) {{
      const groups = {{lang:[],web:[],ai:[],db:[],infra:[]}};
      const AI_SET   = new Set(['openai','anthropic','claude','deepseek','ollama','gemini','dashscope','qwen','cosy','whisper','sentence-transformers','chromadb','faiss','langchain','huggingface']);
      const DB_SET   = new Set(['redis','postgres','postgresql','mysql','mongodb','sqlite','sqlalchemy','alembic','prisma','supabase','elasticsearch']);
      const WEB_SET  = new Set(['fastapi','express','nextjs','react','vue','svelte','nuxt','django','flask','uvicorn','gunicorn','nginx','vite','tailwind','axios','httpx','requests','websocket']);
      const LANG_SET = new Set(['python','typescript','javascript','go','rust','java','kotlin','swift','c++','c#','ruby','php']);
      techStack.forEach(t => {{
        const n = (t.name||t).toLowerCase();
        if (AI_SET.has(n))        groups.ai.push(t.name||t);
        else if (DB_SET.has(n))   groups.db.push(t.name||t);
        else if (WEB_SET.has(n))  groups.web.push(t.name||t);
        else if (LANG_SET.has(n)) groups.lang.push(t.name||t);
        else                      groups.infra.push(t.name||t);
      }});
      const glabels = {{lang:'语言',web:'框架',ai:'AI',db:'存储',infra:'工具链'}};
      const gcolors = {{
        lang:'rgba(250,204,21,.08);color:var(--gold)',
        web:'rgba(129,140,248,.08);color:var(--purple)',
        ai:'rgba(167,139,250,.08);color:var(--purple)',
        db:'rgba(92,208,138,.08);color:var(--green)',
        infra:'rgba(255,255,255,.05);color:var(--sub)'
      }};
      let techHtml = '';
      for (const [cat, items] of Object.entries(groups)) {{
        if (!items.length) continue;
        techHtml += `<div style="display:flex;align-items:center;gap:10px;margin-bottom:7px">
          <span style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;width:60px;flex-shrink:0;color:var(--muted)">${{glabels[cat]}}</span>
          <div style="display:flex;flex-wrap:wrap;gap:4px">${{items.map(n=>`<span style="font-size:10px;padding:2px 8px;border-radius:4px;background:${{gcolors[cat]}}">${{escHtml(n)}}</span>`).join('')}}</div>
        </div>`;
      }}
      if (techHtml) {{
        html += `<div class="tech-full-card">
          <div class="card-section-title">技术栈</div>
          ${{techHtml}}
        </div>`;
      }}
    }}

    html += `</div>`;  // end outer padding div
    el.innerHTML = html;
    summaryLoaded = true;
  }}

// ── Design Docs ───────────────────────────────────────────────────────────────
function renderDesign() {{
  const el = document.getElementById('panel-design');
  const docs = (projectData && projectData.design_docs) || [];
  if (!docs.length) {{
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">📐</div><div>暂无设计文档</div></div>`;
    designLoaded = true;
    return;
  }}
  let sidebar = docs.map((d,i) => `
    <div class="doc-item${{d.possibly_stale?' stale':''}}${{i===0?' active':''}}" id="ditem-${{i}}" onclick="showDoc(${{i}})">
      ${{escHtml(d.filename)}}${{d.possibly_stale?' ⚠':''}}</div>`).join('');

  el.innerHTML = `<div class="docs-layout">
    <div class="docs-sidebar">
      <div class="docs-sidebar-title">设计文档</div>
      ${{sidebar}}
    </div>
    <div class="docs-body" id="docs-body"></div>
  </div>`;
  showDoc(0);
  designLoaded = true;
}}

function showDoc(i) {{
  const docs = (projectData && projectData.design_docs) || [];
  const d = docs[i];
  if (!d) return;
  document.querySelectorAll('.doc-item').forEach((el,j) => el.classList.toggle('active', j===i));
  const mtime = new Date(d.mtime * 1000).toLocaleDateString('zh-CN');
  document.getElementById('docs-body').innerHTML = `
    <div class="doc-title">${{escHtml(d.title || d.filename)}}</div>
    <div class="doc-meta">${{escHtml(d.filename)}} · ${{mtime}}${{d.possibly_stale?' · <span style="color:var(--red)">⚠ 可能已过期</span>':''}}</div>
    <div class="doc-content">${{simpleMarkdown(d.content)}}</div>`;
}}

// ── Features / Roadmap ────────────────────────────────────────────────────────
function renderPlans() {{
  const el = document.getElementById('panel-plans');
  const features = (projectData && projectData.features) || [];
  const git = (projectData && projectData.git) || {{}};
  const githubUrl = git.github_url || null;

  const done = features.filter(f => f.implemented);
  const todo = features.filter(f => !f.implemented);

  let html = `<div class="plans-wrap">`;

  // GitHub links bar
  if (githubUrl) {{
    html += `<div style="display:flex;gap:10px;margin-bottom:24px;flex-wrap:wrap">
      <a href="${{escHtml(githubUrl)}}/issues" target="_blank"
         style="display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:6px;
                background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);
                color:var(--sub);font-size:13px;text-decoration:none;transition:all .15s"
         onmouseover="this.style.borderColor='#818cf8';this.style.color='#818cf8'"
         onmouseout="this.style.borderColor='rgba(255,255,255,.1)';this.style.color='var(--sub)'">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z"/><path d="M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z"/></svg>
        Issues
      </a>
      <a href="${{escHtml(githubUrl)}}/issues/new" target="_blank"
         style="display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:6px;
                background:rgba(79,70,229,.1);border:1px solid rgba(79,70,229,.3);
                color:#818cf8;font-size:13px;text-decoration:none;transition:all .15s"
         onmouseover="this.style.background='rgba(79,70,229,.2)'"
         onmouseout="this.style.background='rgba(79,70,229,.1)'">
        + 新建 Issue
      </a>
      <a href="${{escHtml(githubUrl)}}" target="_blank"
         style="display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:6px;
                background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);
                color:var(--sub);font-size:13px;text-decoration:none;transition:all .15s"
         onmouseover="this.style.borderColor='#818cf8';this.style.color='#818cf8'"
         onmouseout="this.style.borderColor='rgba(255,255,255,.1)';this.style.color='var(--sub)'">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/></svg>
        GitHub
      </a>
    </div>`;
  }}

  // No features at all
  if (!features.length) {{
    html += `<div style="text-align:center;padding:40px 0;color:var(--muted)">
      <div style="font-size:32px;margin-bottom:12px">📋</div>
      <div style="font-size:14px;margin-bottom:8px">暂无功能列表</div>
      <div style="font-size:12px;color:#555">在 <code>docs/vibe-summary.md</code> 中用 <code>- 功能描述</code> 格式维护已实现功能，<br>用「尚未实现」章节标记规划中的功能</div>
    </div>`;
    html += '</div>';
    el.innerHTML = html;
    plansLoaded = true;
    return;
  }}

  // Progress summary
  const pct = Math.round(done.length / features.length * 100);
  html += `<div style="display:flex;align-items:center;gap:12px;margin-bottom:24px">
    <div style="flex:1;height:6px;background:rgba(255,255,255,.07);border-radius:3px;overflow:hidden">
      <div style="width:${{pct}}%;height:100%;background:linear-gradient(90deg,#4f46e5,#22c55e);border-radius:3px;transition:width .3s"></div>
    </div>
    <span style="font-size:13px;color:var(--sub);white-space:nowrap">${{done.length}} / ${{features.length}} 已实现 (${{pct}}%)</span>
  </div>`;

  // Implemented
  if (done.length) {{
    html += `<div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:10px">已实现</div>`;
    for (const f of done) {{
      html += `<div class="task-item">
        <div class="task-check done">✓</div>
        <div class="task-text done">${{escHtml(f.text)}}</div>
      </div>`;
    }}
  }}

  // Planned / unimplemented
  if (todo.length) {{
    html += `<div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin:20px 0 10px">规划中</div>`;
    for (const f of todo) {{
      html += `<div class="task-item">
        <div class="task-check todo"></div>
        <div class="task-text todo">${{escHtml(f.text)}}</div>
      </div>`;
    }}
  }}

  // Edit hint
  html += `<div style="margin-top:24px;padding:12px 14px;border-radius:6px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);font-size:12px;color:#555">
    在 <code style="font-size:11px;color:#666">docs/vibe-summary.md</code> 中维护此列表 ·
    已实现功能放在正文，规划中功能放在「尚未实现」章节
  </div>`;

  html += '</div>';
  el.innerHTML = html;
  plansLoaded = true;
}}

// ── Claude Activity ───────────────────────────────────────────────────────────
function renderClaude() {{
  const el = document.getElementById('panel-claude');
  const ca = (projectData && projectData.claude_activity) || null;

  function fmtTok(t) {{
    if (!t) return '—';
    if (t >= 1e9) return (t/1e9).toFixed(1) + 'B';
    if (t >= 1e6) return (t/1e6).toFixed(1) + 'M';
    if (t >= 1e3) return (t/1e3).toFixed(0) + 'k';
    return String(t);
  }}
  function fmtAge(iso) {{
    if (!iso) return '—';
    const diffH = Math.floor((Date.now() - new Date(iso)) / 3600000);
    const diffD = Math.floor(diffH / 24);
    return diffH < 1 ? '刚刚' : diffH < 24 ? diffH + 'h 前' : diffD + 'd 前';
  }}
  function fmtCost(c) {{
    if (!c) return '—';
    return c < 1 ? '$' + c.toFixed(2) : c < 100 ? '$' + c.toFixed(1) : '$' + Math.round(c);
  }}

  if (!ca || !ca.last_session) {{
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">🤖</div><div>暂无 Claude 会话记录</div></div>`;
    claudeLoaded = true;
    return;
  }}

  // 15-day spark
  const spark = (ca.session_spark_15d && ca.session_spark_15d.length === 15) ? ca.session_spark_15d : Array(15).fill(0);
  const sparkMax = Math.max(...spark, 1);
  const sparkBars = spark.map(v => {{
    const h = v === 0 ? 100 : Math.min(100, Math.max(15, Math.round((v / 12) * 100)));
    const cls = v === 0 ? 'cl-bar' : (v >= 12 || v >= sparkMax * 0.7) ? 'cl-bar hi' : 'cl-bar on';
    return `<span class="${{cls}}" style="height:${{h}}%" title="${{v.toFixed(1)}}h 活跃"></span>`;
  }}).join('');

  // cost breakdown bar widths
  const outCost  = (ca.output_tokens         || 0) * 15.00 / 1e6;
  const cwCost   = (ca.cache_creation_tokens || 0) * 3.75  / 1e6;
  const inCost   = (ca.input_tokens          || 0) * 3.00  / 1e6;
  const crCost   = (ca.cache_read_tokens     || 0) * 0.30  / 1e6;
  const totalCost = outCost + cwCost + inCost + crCost || 1;
  const pOut = Math.round(outCost / totalCost * 100);
  const pCw  = Math.round(cwCost  / totalCost * 100);
  const pIn  = Math.round(inCost  / totalCost * 100);
  const pCr  = 100 - pOut - pCw - pIn;

  // todos
  const todos = ca.todos || [];
  const todoHtml = todos.length ? todos.map(t => {{
    const s = t.status || 'pending';
    const icon = s === 'completed' ? '✓' : s === 'in_progress' ? '⟳' : '⬜';
    const cls  = s === 'completed' ? 'cl-todo done' : s === 'in_progress' ? 'cl-todo wip' : 'cl-todo pend';
    return `<div class="${{cls}}">${{icon}} ${{escHtml(t.content || '')}}</div>`;
  }}).join('') : '<div style="color:#2d3555;font-size:12px">无 Todo 记录</div>';

  el.innerHTML = `
  <div class="cl-wrap">

    <div class="cl-summary">
      <div class="cl-sum-card purple">
        <div class="cl-sv">${{fmtCost(ca.estimated_cost_usd)}}</div>
        <div class="cl-sl">累计费用</div>
      </div>
      <div class="cl-sum-card">
        <div class="cl-sv">${{ca.active_hours || 0}}h</div>
        <div class="cl-sl">活跃时长</div>
      </div>
      <div class="cl-sum-card">
        <div class="cl-sv">${{ca.session_count_30d || 0}}</div>
        <div class="cl-sl">30天会话</div>
      </div>
      <div class="cl-sum-card green">
        <div class="cl-sv">${{fmtAge(ca.last_session)}}</div>
        <div class="cl-sl">上次会话</div>
      </div>
    </div>

    <div class="cl-section-title">Token 用量</div>
    <div class="cl-tok-grid">
      <div class="cl-tok-col"><div class="cl-tv">${{fmtTok(ca.output_tokens)}}</div><div class="cl-tl">输出</div><div class="cl-tsub">$15/MTok</div></div>
      <div class="cl-tok-col"><div class="cl-tv">${{fmtTok(ca.input_tokens)}}</div><div class="cl-tl">输入</div><div class="cl-tsub">$3/MTok</div></div>
      <div class="cl-tok-col"><div class="cl-tv">${{fmtTok(ca.cache_creation_tokens)}}</div><div class="cl-tl">Cache 写</div><div class="cl-tsub">$3.75/MTok</div></div>
      <div class="cl-tok-col"><div class="cl-tv">${{fmtTok(ca.cache_read_tokens)}}</div><div class="cl-tl">Cache 读</div><div class="cl-tsub">$0.30/MTok</div></div>
    </div>
    <div class="cl-cost-bar">
      <span style="flex:${{pOut}};background:#818cf8"></span>
      <span style="flex:${{pCw}};background:#4f46e5"></span>
      <span style="flex:${{pIn}};background:#2d3555"></span>
      <span style="flex:${{Math.max(pCr,1)}};background:#1a2035"></span>
    </div>
    <div class="cl-legend">
      <span class="cl-leg-item"><span class="cl-leg-dot" style="background:#818cf8"></span>输出 ${{outCost.toFixed(2)}}</span>
      <span class="cl-leg-item"><span class="cl-leg-dot" style="background:#4f46e5"></span>Cache写 ${{cwCost.toFixed(2)}}</span>
      <span class="cl-leg-item"><span class="cl-leg-dot" style="background:#2d3555"></span>输入 ${{inCost.toFixed(2)}}</span>
      <span class="cl-leg-item"><span class="cl-leg-dot" style="background:#1a2035"></span>Cache读 ${{crCost.toFixed(2)}}</span>
    </div>

    <div class="cl-bottom">
      <div class="cl-col-l">
        <div class="cl-section-title">15天会话活跃度</div>
        <div class="cl-spark">${{sparkBars}}</div>
        <div class="cl-section-title" style="margin-top:16px">本月小结</div>
        <div class="cl-summary-text">
          7天 <b>${{ca.session_count_7d || 0}}</b> 次会话 &nbsp;·&nbsp; 活跃 <b>${{ca.active_hours || 0}}h</b><br>
          Cache 命中率 <b>${{ca.cache_read_tokens && ca.cache_creation_tokens
            ? Math.round(ca.cache_read_tokens / (ca.cache_read_tokens + ca.cache_creation_tokens) * 100)
            : 0}}%</b>
        </div>
      </div>
      <div class="cl-col-r">
        <div class="cl-section-title">当前 Todo</div>
        <div class="cl-todos">${{todoHtml}}</div>
      </div>
    </div>

  </div>`;
  claudeLoaded = true;
}}

// ── Prompts ───────────────────────────────────────────────────────────────────
async function renderPrompts() {{
  const el = document.getElementById('panel-prompts');
  el.innerHTML = '<div class="loading"><div class="spinner"></div>加载中...</div>';

  let allPrompts = [];
  try {{
    const res = await fetch('/api/prompts');
    const data = await res.json();
    const proj = (data.projects || []).find(p => p.id === PROJECT_ID);
    allPrompts = proj ? proj.prompts : [];
  }} catch(e) {{
    el.innerHTML = `<div class="prompts-wrap"><div class="prompts-empty">加载失败</div></div>`;
    return;
  }}

  if (!allPrompts.length) {{
    el.innerHTML = `<div class="prompts-wrap"><div class="prompts-empty">暂无 Prompt 记录</div></div>`;
    promptsLoaded = true;
    return;
  }}

  function renderList(q) {{
    const q2 = q.trim().toLowerCase();
    const filtered = q2 ? allPrompts.filter(p => p.text.toLowerCase().includes(q2)) : allPrompts;
    if (!filtered.length) return `<div class="prompts-empty">没有匹配的 Prompt</div>`;
    return filtered.map(p => {{
      const raw = escHtml(p.text);
      const text = q2 ? raw.replace(new RegExp(escHtml(q2).replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&'), 'gi'), m=>`<mark>${{m}}</mark>`) : raw;
      return `<div class="prompt-card">
        <div class="prompt-date">${{p.date || ''}}</div>
        <div class="prompt-text">${{text}}</div>
      </div>`;
    }}).join('');
  }}

  el.innerHTML = `<div class="prompts-wrap">
    <input class="prompts-search" id="prompts-q" type="text" placeholder="搜索 Prompt…" oninput="updatePrompts()" autocomplete="off">
    <div style="font-size:11px;color:var(--muted);margin-bottom:16px">${{allPrompts.length}} 条记录</div>
    <div id="prompts-list">${{renderList('')}}</div>
  </div>`;

  window._renderPromptList = renderList;
  promptsLoaded = true;
}}

function updatePrompts() {{
  const q = document.getElementById('prompts-q').value;
  document.getElementById('prompts-list').innerHTML = window._renderPromptList(q);
}}

async function reload() {{
  summaryLoaded = false; overviewLoaded = false; designLoaded = false; promptsLoaded = false;
  document.getElementById('panel-summary').innerHTML  = '<div class="loading"><div class="spinner"></div>加载中...</div>';
  document.getElementById('panel-overview').innerHTML = '<div class="loading"><div class="spinner"></div>加载中...</div>';
  document.getElementById('panel-design').innerHTML   = '<div class="loading"><div class="spinner"></div>加载中...</div>';
  document.getElementById('panel-prompts').innerHTML  = '';
  await init();
}}

async function init() {{
  try {{
    const res = await fetch(`/api/projects/${{PROJECT_ID}}`);
    projectData = await res.json();
    document.getElementById('proj-name').textContent = projectData.name || PROJECT_ID;
    document.getElementById('proj-path').textContent = projectData.path || '';
  }} catch(e) {{ /* non-fatal */ }}

  renderSummary();
  if (activeTab === 'overview') loadOverview();
  if (activeTab === 'design')   renderDesign();
}}

init();

</script>
</body>
</html>'''
