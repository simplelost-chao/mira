"""Full project detail page with tabs: 全局面貌 · 设计文档 · 计划."""

def render_detail_page(project_id: str, project_name: str, inline_data: str = "null") -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css   = theme_vars_css()
    _tb_css      = topbar_css()
    _tb_html     = topbar_html()   # no title/back — detail page has its own subnav
    _overlays    = settings_overlay_html()
    _tb_js       = topbar_js()
    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{project_name} · Mira</title>
<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>
<link rel="stylesheet" href="/static/fonts/fonts.css">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
{_theme_css}
  html, body {{ height: 100vh; overflow: hidden; margin: 0; }}
  .content {{ overflow-y: auto; height: calc(100vh - 92px); }}
  body {{ background: var(--bg); color: var(--text); font-family: var(--mono); }}

{_tb_css}

  /* ── subnav ── */
  .subnav {{
    position: sticky; top: 52px; z-index: 99;
    background: var(--panel); border-bottom: 1px solid var(--border);
    backdrop-filter: blur(8px);
    display: flex; align-items: center; padding: 0 20px; height: 40px; gap: 0;
  }}
  .subnav-back {{
    font-size: 12px; color: var(--sub); text-decoration: none;
    flex-shrink: 0; transition: color .15s; white-space: nowrap;
  }}
  .subnav-back:hover {{ color: var(--text); }}
  .subnav-sep {{ width: 1px; height: 16px; background: var(--border); flex-shrink: 0; margin: 0 12px; }}
  .subnav-proj {{
    font-size: 13px; font-weight: 600; color: var(--text);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 220px; flex-shrink: 1;
  }}
  .subnav-spacer {{ flex: 1; min-width: 12px; }}
  .subnav-tabs {{ display: flex; align-items: stretch; height: 100%; flex-shrink: 0; }}
  .tab-btn {{
    height: 40px; padding: 0 14px; background: none; border: none;
    font-family: var(--mono); font-size: 12px; color: var(--sub); cursor: pointer;
    border-bottom: 2px solid transparent; transition: all .15s; white-space: nowrap;
    display: inline-flex; align-items: center; text-decoration: none;
  }}
  .tab-btn:hover {{ color: var(--text); }}
  .tab-btn.active {{ color: var(--accent); border-bottom-color: var(--accent); }}
  .refresh-btn {{
    margin-left: 8px; font-size: 13px; padding: 4px 8px; background: none;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    color: var(--sub); cursor: pointer; font-family: var(--mono); transition: all .15s; flex-shrink: 0;
  }}
  .refresh-btn:hover {{ border-color: var(--accent); color: var(--accent); }}


  /* ── content ── */
  .content {{ position: relative; z-index: 1; }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}

  /* ── Terminal quick button (summary panel) ── */
  .term-qbtn {{
    background: var(--panel); border: 1px solid var(--border);
    color: var(--text-muted); font-size: 10px; padding: 2px 8px;
    border-radius: 3px; cursor: pointer; font-family: var(--mono);
    text-decoration: none;
  }}
  .term-qbtn:hover {{ border-color: var(--accent); color: var(--accent); }}

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
    border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 1px 6px; color: var(--gold); }}
  .doc-content pre {{ background: rgba(0,0,0,.4); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 14px 16px; overflow-x: auto; margin: 10px 0; font-size: 12px; }}
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
    border-radius: var(--radius-sm); margin-bottom: 4px; font-size: 13px; line-height: 1.55;
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
    border-radius: var(--radius); color: var(--text); font-family: var(--mono); font-size: 13px;
    outline: none; margin-bottom: 20px; transition: border-color .15s;
  }}
  .prompts-search:focus {{ border-color: var(--accent); }}
  .prompt-card {{
    padding: 12px 16px; border-radius: var(--radius); border: 1px solid var(--border); box-shadow: var(--card-shadow);
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
    border-radius: var(--radius); padding: 10px 12px; box-shadow: var(--card-shadow);
    min-width: 0; overflow: hidden;
  }}
  .stats-val {{ font-size: 16px; font-weight: 700; color: var(--text); margin-bottom: 2px; font-variant-numeric: tabular-nums; }}
  .stats-lbl {{ font-size: 11px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }}
  .summary-grid {{
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 12px; margin-bottom: 12px;
  }}
  .summary-card {{
    background: rgba(255,255,255,.025); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--card-shadow);
    min-width: 0; overflow: hidden;
  }}
  .summary-card.claude-card {{
    background: rgba(var(--accent-rgb, 79,70,229),.04); border-color: rgba(var(--accent-rgb, 79,70,229),.15);
  }}
  .card-section-title {{
    font-size: 10px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: var(--muted); margin-bottom: 10px;
  }}
  .commit-list {{ display: flex; flex-direction: column; gap: 4px; margin-top: 10px; overflow: hidden; }}
  .commit-row {{ display: flex; gap: 8px; font-size: 11px; line-height: 1.5; min-width: 0; }}
  .commit-hash {{ color: var(--purple); flex-shrink: 0; font-family: var(--mono); }}
  .commit-msg {{ color: var(--sub); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }}
  .tech-full-card {{
    background: rgba(255,255,255,.025); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--card-shadow);
  }}
  /* edit modal */
  .edit-btn {{
    display: inline-flex; align-items: center; gap: 4px; cursor: pointer;
    font-size: 11px; color: var(--sub); transition: all .15s;
    background: none; border: 1px solid var(--border); border-radius: 4px;
    padding: 3px 8px; font-family: var(--mono);
  }}
  .edit-btn:hover {{ color: var(--text); border-color: var(--accent); }}
  .modal-overlay {{
    position: fixed; inset: 0; background: rgba(0,0,0,.55); z-index: 1000;
    display: flex; align-items: center; justify-content: center;
  }}
  .modal-box {{
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
    padding: 20px 24px; width: 420px; max-width: 90vw; box-shadow: 0 8px 30px rgba(0,0,0,.4);
  }}
  .modal-title {{ font-size: 14px; font-weight: 700; margin-bottom: 14px; }}
  .modal-label {{ font-size: 11px; color: var(--muted); margin-bottom: 4px; text-transform: uppercase; letter-spacing: 1px; }}
  .modal-input {{
    width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
    color: var(--text); font-family: var(--mono); padding: 6px 10px; font-size: 13px;
    margin-bottom: 12px;
  }}
  .modal-input:focus {{ outline: none; border-color: var(--accent); }}
  .modal-textarea {{ resize: vertical; min-height: 50px; }}
  .modal-actions {{ display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }}
  .modal-actions button {{
    font-size: 12px; font-family: var(--mono); padding: 5px 16px; border-radius: 4px;
    cursor: pointer; border: 1px solid var(--border); background: var(--bg); color: var(--text);
  }}
  .modal-actions button.primary {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .modal-actions button:hover {{ opacity: 0.85; }}
  .proj-desc {{ font-size: 12px; color: var(--sub); margin-bottom: 8px; line-height: 1.5; }}
  /* arch section */
  .arch-card {{
    background: rgba(255,255,255,.025); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 14px 16px; margin-top: 16px;
    box-shadow: var(--card-shadow);
  }}
  .arch-card p {{ font-size: 12px; color: var(--sub); line-height: 1.6; margin-bottom: 8px; }}
  .arch-card p:last-child {{ margin-bottom: 0; }}
  .arch-card h1,.arch-card h2,.arch-card h3 {{ font-size: 13px; font-weight: 700; color: var(--text); margin: 12px 0 6px; }}
  .arch-card h1:first-child,.arch-card h2:first-child,.arch-card h3:first-child {{ margin-top: 0; }}
  .arch-card ul,.arch-card ol {{ font-size: 12px; color: var(--sub); padding-left: 18px; margin-bottom: 8px; }}
  .arch-card li {{ margin-bottom: 3px; }}
  .arch-card code {{ font-size: 11px; background: rgba(255,255,255,.06); padding: 1px 4px; border-radius: 3px; }}
  /* ext deps */
  .dep-flow {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }}
  .dep-node {{
    font-size: 11px; padding: 5px 12px; border-radius: var(--radius);
    border: 1px solid var(--border); background: rgba(255,255,255,.03);
  }}
  .dep-arrow {{ color: var(--muted); font-size: 12px; }}
  /* code stats */
  .lang-row {{ display: flex; align-items: center; gap: 8px; font-size: 11px; margin-bottom: 4px; }}
  .lang-name {{ width: 80px; text-align: right; color: var(--sub); flex-shrink: 0; }}
  .lang-track {{ flex: 1; height: 6px; background: rgba(255,255,255,.06); border-radius: 3px; overflow: hidden; }}
  .lang-fill {{ height: 100%; border-radius: 3px; }}
  .lang-num {{ width: 40px; color: var(--muted); flex-shrink: 0; }}
  /* feature list */
  .feat-item {{ font-size: 11px; padding: 3px 0; }}
  .feat-item.done {{ color: var(--green); }}
  .feat-item.planned {{ color: var(--sub); }}
  /* hero */
  .summary-wrap {{ padding: 20px; max-width: 960px; }}
  .hero-row {{ display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }}
  .hero-left {{ flex: 1; min-width: 0; }}
  .hero-right {{ display: flex; align-items: center; gap: 10px; flex-shrink: 0; padding-top: 4px; }}
  .proj-title {{ font-size: 22px; font-weight: 700; margin-bottom: 5px; }}
  .proj-path {{ font-size: 11px; color: var(--muted); margin-bottom: 10px; }}
  .badge-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .claude-last {{ font-size: 11px; color: var(--muted); white-space: nowrap; }}
  /* badges */
  .badge {{ font-size: 11px; padding: 4px 12px; border-radius: var(--radius-pill); border: 1px solid; display: inline-flex; align-items: center; gap: 5px; }}
  .badge-green   {{ border-color: rgba(92,208,138,.25);  background: rgba(92,208,138,.08);  color: var(--green); }}
  .badge-stopped {{ border-color: rgba(255,255,255,.1);  background: rgba(255,255,255,.04); color: var(--sub); }}
  .badge-purple  {{ border-color: rgba(129,140,248,.2);  background: rgba(129,140,248,.06); color: var(--purple); }}
  .badge-dim     {{ border-color: rgba(255,255,255,.1);  background: rgba(255,255,255,.04); color: var(--sub); }}
  .badge-dot {{ width: 6px; height: 6px; border-radius: 50%; background: currentColor; }}
  /* stats val color variants */
  .stats-val.gold   {{ color: var(--gold); }}
  .stats-val.purple {{ color: var(--purple); }}
  .stats-val.green  {{ color: var(--green); }}
  /* card internals */
  .card-stats {{ display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 10px; }}
  .card-stat-val {{ font-size: 16px; font-weight: 700; margin-bottom: 2px; }}
  .card-stat-val.purple    {{ color: var(--purple); }}
  .card-stat-val.gold      {{ color: var(--gold); }}
  .card-stat-val.dirty-ok  {{ color: var(--green); }}
  .card-stat-val.dirty-warn {{ color: var(--orange); }}
  .card-stat-lbl {{ font-size: 10px; color: var(--muted); margin-top: 2px; }}
  /* todos */
  .todo-list {{ margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }}
  .todo-item {{ display: flex; align-items: flex-start; gap: 5px; font-size: 10px; }}
  .todo-dot {{ width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; margin-top: 3px; }}
  .todo-dot.done {{ background: var(--green); }}
  .todo-dot.wip  {{ background: var(--gold); }}
  .todo-dot.pend {{ background: var(--border); }}
  .todo-text.done {{ color: var(--green); }}
  .todo-text.wip  {{ color: var(--gold); }}
  .todo-text.pend {{ color: var(--sub); }}
  .summary-card-empty {{ display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 12px; }}
  /* tech stack */
  .tech-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 7px; }}
  .tech-cat-lbl {{ font-size: 9px; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; width: 60px; flex-shrink: 0; color: var(--muted); }}
  .tech-badges {{ display: flex; flex-wrap: wrap; gap: 4px; }}
  .tech-badge {{ font-size: 10px; padding: 2px 8px; border-radius: var(--radius-sm); }}
  .tech-badge.lang  {{ background: rgba(250,204,21,.08); color: var(--gold); }}
  .tech-badge.web   {{ background: rgba(129,140,248,.08); color: var(--purple); }}
  .tech-badge.ai    {{ background: rgba(167,139,250,.08); color: var(--purple); }}
  .tech-badge.db    {{ background: rgba(92,208,138,.08);  color: var(--green); }}
  .tech-badge.infra {{ background: rgba(255,255,255,.05); color: var(--sub); }}

  /* ── loading ── */
  .loading {{ display: flex; align-items: center; justify-content: center; height: calc(100vh - 92px); color: var(--muted); font-size: 13px; gap: 8px; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .spinner {{ width: 16px; height: 16px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin .8s linear infinite; }}

  /* Claude panel */
  .cl-wrap {{ max-width: 860px; padding: 24px; }}
  .cl-summary {{ display: flex; gap: 12px; margin-bottom: 20px; }}
  .cl-sum-card {{ flex: 1; padding: 12px 14px; background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--card-shadow); }}
  .cl-sum-card.purple {{ background: rgba(var(--accent-rgb, 79,70,229),.06); border-color: rgba(var(--accent-rgb, 79,70,229),.2); }}
  .cl-sum-card.green  {{ background: var(--green-dim); border-color: var(--green-border); }}
  .cl-sv {{ font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 2px; }}
  .cl-sum-card.purple .cl-sv {{ color: var(--purple); }}
  .cl-sum-card.green  .cl-sv {{ color: var(--green); }}
  .cl-sl {{ font-size: 9px; color: var(--muted); letter-spacing: 1.5px; text-transform: uppercase; }}
  .cl-section-title {{ font-size: 9px; color: var(--muted); letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; margin-top: 18px; }}
  .cl-tok-grid {{ display: flex; gap: 8px; }}
  .cl-tok-col {{ flex: 1; padding: 8px 10px; background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--card-shadow); }}
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
  .cl-todo {{ font-size: 11px; padding: 5px 8px; border-radius: var(--radius-sm); color: var(--sub); }}
  .cl-todo.done {{ color: var(--green); opacity: .6; }}
  .cl-todo.wip  {{ color: var(--accent); background: var(--panel); }}
  .cl-todo.pend {{ color: var(--muted); }}

  /* ── docs mobile views ── */
  .docs-mobile-list {{ display: none; flex-direction: column; }}
  .docs-mobile-back {{
    display: none; align-items: center; gap: 8px;
    font-size: 12px; color: var(--sub); cursor: pointer;
    padding: 12px 16px; border-bottom: 1px solid var(--border);
    background: var(--panel);
  }}
  .docs-mobile-back:hover {{ color: var(--text); }}
  .docs-mobile-item {{
    display: block; padding: 12px 16px; font-size: 13px; color: var(--sub);
    border-bottom: 1px solid var(--border); cursor: pointer;
    transition: background .15s;
  }}
  .docs-mobile-item:hover {{ background: rgba(255,255,255,.03); color: var(--text); }}
  .docs-mobile-item-name {{ font-size: 13px; margin-bottom: 3px; }}
  .docs-mobile-item-meta {{ font-size: 10px; color: var(--muted); }}
  .docs-mobile-item.stale {{ opacity: .55; }}

  @media (max-width: 640px) {{
    /* topbar */
    .topbar {{ padding: 0 12px; gap: 8px; }}
    .topbar-logo .logo-m {{ font-size: 18px; }}
    .topbar-logo .logo-ira {{ font-size: 18px; }}
    .topbar-logo .logo-cursor {{ font-size: 18px; }}
    .settings-btn {{ font-size: 0 !important; }}
    .settings-btn::before {{ content: '⚙\FE0E'; font-size: 15px; line-height: 1; }}

    /* subnav */
    .subnav {{ padding: 0 8px; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    .subnav-proj {{ max-width: 100px; }}
    .tab-btn {{ padding: 0 10px; white-space: nowrap; flex-shrink: 0; }}

    /* summary */
    .summary-wrap {{ padding: 14px; padding-bottom: 80px; overflow-x: hidden; }}
    .stats-bar {{ grid-template-columns: repeat(3, 1fr); }}
    .summary-grid {{ grid-template-columns: 1fr; }}
    .proj-title {{ font-size: 18px; word-break: break-all; }}
    .proj-path {{ word-break: break-all; }}
    .hero-row {{ flex-wrap: wrap; gap: 8px; }}
    .commit-row {{ min-width: 0; flex-wrap: wrap; }}
    .commit-msg {{ min-width: 0; white-space: normal; word-break: break-word; }}
    .card-stats {{ gap: 10px; }}
    .cl-summary {{ flex-wrap: wrap; }}
    .cl-tok-grid {{ flex-wrap: wrap; }}
    .cl-bottom {{ flex-direction: column; }}
    .badge-row {{ word-break: break-word; }}
    .badge {{ white-space: normal; word-break: break-word; }}
    .dep-flow {{ word-break: break-word; }}
    .dep-node {{ word-break: break-word; white-space: normal; }}
    .arch-card code {{ word-break: break-all; }}
    .todo-text {{ word-break: break-word; }}
    .feat-item {{ word-break: break-word; }}
    .tech-row {{ flex-wrap: wrap; }}
    .lang-name {{ width: auto; min-width: 50px; }}
    .arch-card a {{ word-break: break-all; }}
    .arch-card {{ overflow-wrap: break-word; word-break: break-word; }}
    .summary-card {{ overflow-wrap: break-word; word-break: break-word; }}

    /* plans / prompts */
    .plans-wrap {{ padding: 20px 16px; padding-bottom: 80px; }}
    .prompts-wrap {{ padding: 16px; padding-bottom: 80px; }}

    /* design docs — hide desktop sidebar, collapse layout */
    .docs-layout {{ display: block; }}
    .docs-sidebar {{ display: none; }}
    .docs-body {{ padding: 16px; max-height: none; overflow-y: visible; }}

    /* show mobile docs components */
    .docs-mobile-list {{ display: flex; }}

    .term-qbtn {{ padding: 4px 10px; font-size: 11px; }}
  }}

</style>
</head>
<body>

{_tb_html}
<div class="subnav">
  
  <div class="subnav-sep"></div>
  <span class="subnav-proj" id="proj-name">{project_name}</span>
  <div class="subnav-spacer"></div>
  <div class="subnav-tabs">
    <button class="tab-btn active" id="tab-summary" onclick="showTab('summary')">概览</button>
    <button class="tab-btn" id="tab-design" onclick="showTab('design')">设计文档</button>
    <button class="tab-btn" id="tab-prompts" onclick="showTab('prompts')">Prompts</button>
    <a class="tab-btn" href="/dev?project={project_id}">Dev ↗</a>
  </div>
  <button class="refresh-btn" onclick="reload()" title="刷新">↻</button>
</div>

<div class="content">
  <div class="tab-panel active" id="panel-summary">
    <div class="loading"><div class="spinner"></div>加载中...</div>
  </div>
  <div class="tab-panel" id="panel-design">
    <div class="loading"><div class="spinner"></div>加载中...</div>
  </div>
  <div class="tab-panel" id="panel-prompts"></div>
</div>

<script>
const PROJECT_ID = {repr(project_id)};
window._INLINE_PROJECT = {inline_data};
let projectData = null;
// Redirect #terminals to /dev?project=xxx
if (location.hash === '#terminals') {{
  location.replace('/dev?project=' + encodeURIComponent({repr(project_id)}));
}}
let activeTab = 'summary';
let summaryLoaded = false;
let designLoaded = false;
let promptsLoaded = false;

function showTab(name) {{
  activeTab = name;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const tabEl = document.getElementById('tab-' + name);
  if (tabEl) tabEl.classList.add('active');
  const panelEl = document.getElementById('panel-' + name);
  if (panelEl) panelEl.classList.add('active');
  if (name === 'summary'  && !summaryLoaded)  renderSummary();
  if (name === 'design'   && !designLoaded)   renderDesign();
  if (name === 'prompts'  && !promptsLoaded) {{
    if (!_isAdmin) {{ openLoginModal(() => {{ promptsLoaded = false; renderPrompts(); }}); return; }}
    renderPrompts();
  }}
}}

function escHtml(s) {{
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// ── ANSI renderer ─────────────────────────────────────────────────────────────
const _FG = {{
  30:'var(--ansi-k)', 31:'var(--ansi-r)', 32:'var(--ansi-g)', 33:'var(--ansi-y)',
  34:'var(--ansi-b)', 35:'var(--ansi-m)', 36:'var(--ansi-c)', 37:'var(--ansi-w)',
  90:'var(--ansi-K)', 91:'var(--ansi-R)', 92:'var(--ansi-G)', 93:'var(--ansi-Y)',
  94:'var(--ansi-B)', 95:'var(--ansi-M)', 96:'var(--ansi-C)', 97:'var(--ansi-W)',
}};
const _BG = {{
  40:'var(--ansi-k)', 41:'var(--ansi-r)', 42:'var(--ansi-g)', 43:'var(--ansi-y)',
  44:'var(--ansi-b)', 45:'var(--ansi-m)', 46:'var(--ansi-c)', 47:'var(--ansi-w)',
  100:'var(--ansi-K)', 101:'var(--ansi-R)', 102:'var(--ansi-G)', 103:'var(--ansi-Y)',
  104:'var(--ansi-B)', 105:'var(--ansi-M)', 106:'var(--ansi-C)', 107:'var(--ansi-W)',
}};
function _256color(n) {{
  if (n < 8)  return _FG[n + 30];
  if (n < 16) return _FG[n + 82];
  if (n < 232) {{
    n -= 16;
    const b = n % 6, g = Math.floor(n / 6) % 6, r = Math.floor(n / 36);
    const c = v => v ? v * 40 + 55 : 0;
    return 'rgb(' + c(r) + ',' + c(g) + ',' + c(b) + ')';
  }}
  const v = Math.round((n - 232) * 10.2 + 8);
  return 'rgb(' + v + ',' + v + ',' + v + ')';
}}
function _ansiLine(line) {{
  const RE = /\x1b\[([0-9;]*)([A-Za-z])/g;
  let out = '', last = 0, spanOpen = false;
  let fg = null, bg = null, bold = false, dim = false, ital = false, ul = false;
  function _hasStyle() {{ return fg || bg || bold || dim || ital || ul; }}
  function _close() {{ if (spanOpen) {{ out += '</span>'; spanOpen = false; }} }}
  function _open() {{
    if (spanOpen || !_hasStyle()) return;
    const s = [];
    if (fg)   s.push('color:' + fg);
    if (bg)   s.push('background:' + bg);
    if (bold) s.push('font-weight:700');
    if (dim)  s.push('opacity:.55');
    if (ital) s.push('font-style:italic');
    if (ul)   s.push('text-decoration:underline');
    out += '<span style="' + s.join(';') + '">';
    spanOpen = true;
  }}
  let m;
  while ((m = RE.exec(line)) !== null) {{
    if (m.index > last) {{ _open(); out += escHtml(line.slice(last, m.index)); }}
    last = RE.lastIndex;
    if (m[2] !== 'm') continue;
    _close();
    const ps = m[1] ? m[1].split(';') : ['0'];
    let i = 0;
    while (i < ps.length) {{
      const p = +ps[i] || 0;
      if (p === 0)  {{ fg = bg = null; bold = dim = ital = ul = false; }}
      else if (p === 1)  bold = true;
      else if (p === 2)  dim  = true;
      else if (p === 3)  ital = true;
      else if (p === 4)  ul   = true;
      else if (p === 22) {{ bold = false; dim = false; }}
      else if (p === 23) ital = false;
      else if (p === 24) ul   = false;
      else if (_FG[p])   fg   = _FG[p];
      else if (p === 38) {{
        if (ps[i+1] === '5')      {{ fg = _256color(+ps[i+2]); i += 2; }}
        else if (ps[i+1] === '2') {{ fg = 'rgb('+ps[i+2]+','+ps[i+3]+','+ps[i+4]+')'; i += 4; }}
      }}
      else if (p === 39) fg = null;
      else if (_BG[p])   bg   = _BG[p];
      else if (p === 48) {{
        if (ps[i+1] === '5')      {{ bg = _256color(+ps[i+2]); i += 2; }}
        else if (ps[i+1] === '2') {{ bg = 'rgb('+ps[i+2]+','+ps[i+3]+','+ps[i+4]+')'; i += 4; }}
      }}
      else if (p === 49) bg = null;
      i++;
    }}
  }}
  if (last < line.length) {{ _open(); out += escHtml(line.slice(last)); }}
  _close();
  return out;
}}
function _renderOutput(text) {{
  if (!text || !text.trim()) return '';
  const lines = text.split('\\n');
  if (lines.length && lines[lines.length - 1] === '') lines.pop();
  if (!lines.length) return '';
  const chunks = [];
  let cur = [];
  lines.forEach(function(line) {{
    if (line.trim() === '' && cur.length) {{ chunks.push(cur); cur = []; }}
    else {{ cur.push(line); }}
  }});
  if (cur.length) chunks.push(cur);
  let globalLine = 0;
  const pad = String(lines.length).length;
  return chunks.map(function(chunk) {{
    const rows = chunk.map(function(line) {{
      globalLine++;
      return '<div class="out-line">' +
        '<span class="out-ln">' + String(globalLine).padStart(pad, '\u00a0') + '</span>' +
        '<span class="out-code">' + _ansiLine(line) + '</span>' +
        '</div>';
    }}).join('');
    return '<div class="out-block">' + rows + '</div>';
  }}).join('');
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
      ? `<span class="badge ${{isRunning ? 'badge-green' : 'badge-stopped'}}">
           <span class="badge-dot"></span>
           ${{isRunning ? '运行中' : '停止'}} ${{svcPort}}
         </span>`
      : '';
    const domainBadge = svc.public_domain
      ? `<span class="badge badge-purple">${{escHtml(svc.public_domain)}}</span>`
      : '';
    const deployBadge = deploy.type && deploy.type !== 'none'
      ? `<span class="badge badge-dim">☁️ ${{escHtml(deploy.type)}}${{deploy.host ? ' · '+escHtml(deploy.host) : ''}}</span>`
      : '';
    const statusBadge = `<span class="badge badge-dim">${{escHtml(p.status || 'active')}}</span>`;

    let html = `<div class="summary-wrap">`;

    // Hero row
    const descText = p.description || '';
    const editBtn = _isAdmin ? `<button class="edit-btn" onclick="openEditModal()" title="编辑">✎ 编辑</button>` : '';
    html += `<div class="hero-row">
      <div class="hero-left">
        <div class="proj-title">${{escHtml(p.name || '')}}</div>
        ${{descText ? `<div class="proj-desc">${{escHtml(descText)}}</div>` : ''}}
        <div class="proj-path">${{escHtml(p.path || '')}}</div>
        <div class="badge-row">${{svcBadge}}${{domainBadge}}${{deployBadge}}${{statusBadge}}</div>
      </div>
      <div class="hero-right">
        ${{editBtn}}
        ${{p.path ? `<a class="term-qbtn" href="/dev?project=${{encodeURIComponent(PROJECT_ID)}}" title="在 Dev 页面打开该项目的终端">⬛ Dev</a>` : ''}}
        ${{caLastStr ? `<span class="claude-last">${{caLastStr}}</span>` : ''}}
      </div>
    </div>`;

    // ── Stats bar ──
    const done = features.filter(f => f.implemented);
    const featPct = features.length ? Math.round(done.length / features.length * 100) : null;
    const codeLinesStr = loc.code_lines ? (loc.code_lines >= 1000 ? (loc.code_lines/1000).toFixed(1)+'k' : String(loc.code_lines)) : '—';

    html += `<div class="stats-bar">
      <div class="stats-cell"><div class="stats-val gold">${{git.monthly_commits ?? 0}}</div><div class="stats-lbl">本月提交</div></div>
      <div class="stats-cell"><div class="stats-val purple">${{ca ? (ca._masked ? '***' : '$' + (ca.estimated_cost_usd||0).toFixed(1)) : '—'}}</div><div class="stats-lbl">Claude 花费</div></div>
      <div class="stats-cell"><div class="stats-val purple">${{ca ? (ca.session_count_30d||0) : '—'}}</div><div class="stats-lbl">30天会话</div></div>
      <div class="stats-cell"><div class="stats-val">${{codeLinesStr}}</div><div class="stats-lbl">代码行</div></div>
      <div class="stats-cell"><div class="stats-val green">${{featPct !== null ? featPct+'%' : '—'}}</div><div class="stats-lbl">功能完成</div></div>
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
        const cls = s==='completed'?'done':s==='in_progress'?'wip':'pend';
        return `<div class="todo-item">
          <div class="todo-dot ${{cls}}"></div>
          <span class="todo-text ${{cls}}">${{escHtml(t.content||'')}}</span>
        </div>`;
      }}).join('');

      html += `<div class="summary-card claude-card">
        <div class="card-section-title">Claude</div>
        <div class="card-stats">
          <div><div class="card-stat-val purple">${{ca._masked ? '***' : '$' + (ca.estimated_cost_usd||0).toFixed(1)}}</div><div class="card-stat-lbl">累计花费</div></div>
          <div><div class="card-stat-val purple">${{ca.session_count_30d||0}}</div><div class="card-stat-lbl">30天会话</div></div>
          <div><div class="card-stat-val purple">${{ca._masked ? '***' : fmtTok(ca.output_tokens||0)}}</div><div class="card-stat-lbl">输出</div></div>
        </div>
        <div class="cl-spark">${{sparkBars}}</div>
        ${{todoHtml ? `<div class="todo-list">${{todoHtml}}</div>` : ''}}
      </div>`;
    }} else {{
      html += `<div class="summary-card summary-card-empty">暂无 Claude 数据</div>`;
    }}

    // Git card
    const dirtyCount = (git.dirty_files || []).length;
    const dirtyDirtyCls = dirtyCount > 0 ? 'dirty-warn' : 'dirty-ok';
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
      <div class="card-stats">
        <div><div class="card-stat-val gold">${{git.monthly_commits ?? 0}}</div><div class="card-stat-lbl">本月提交</div></div>
        <div><div class="card-stat-val">${{codeLinesStr}}</div><div class="card-stat-lbl">代码行</div></div>
        <div><div class="card-stat-val ${{dirtyDirtyCls}}">${{dirtyCount}}</div><div class="card-stat-lbl">未提交</div></div>
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
      let techHtml = '';
      for (const [cat, items] of Object.entries(groups)) {{
        if (!items.length) continue;
        techHtml += `<div class="tech-row">
          <span class="tech-cat-lbl">${{glabels[cat]}}</span>
          <div class="tech-badges">${{items.map(n=>`<span class="tech-badge ${{cat}}">${{escHtml(n)}}</span>`).join('')}}</div>
        </div>`;
      }}
      if (techHtml) {{
        html += `<div class="tech-full-card">
          <div class="card-section-title">技术栈</div>
          ${{techHtml}}
        </div>`;
      }}
    }}

    // ── Architecture summary ──
    if (p.arch_summary) {{
      html += `<div class="arch-card">
        <div class="card-section-title">架构概述</div>
        ${{simpleMarkdown(p.arch_summary)}}
      </div>`;
    }}

    // ── External dependencies ──
    const extDeps = p.external_deps || [];
    if (extDeps.length) {{
      let depHtml = `<div class="dep-flow"><div class="dep-node" style="border-color:var(--accent);color:var(--accent)">${{escHtml(p.name||'本项目')}}</div>`;
      extDeps.forEach(d => {{
        const meta = d.port ? ':'+d.port : (d.url||'');
        depHtml += `<span class="dep-arrow">→</span><div class="dep-node">${{escHtml(d.name||'')}}${{meta ? ' <span style="color:var(--muted);font-size:10px">'+escHtml(meta)+'</span>' : ''}}</div>`;
      }});
      depHtml += `</div>`;
      html += `<div class="arch-card">
        <div class="card-section-title">服务依赖</div>
        ${{depHtml}}
      </div>`;
    }}

    // ── Deploy details ──
    if (deploy.type && deploy.type !== 'none') {{
      let dRows = '';
      if (deploy.host) dRows += `<div style="font-size:11px;margin-bottom:3px"><span style="color:var(--muted)">Host:</span> <code>${{escHtml(deploy.host)}}</code></div>`;
      if (deploy.url)  dRows += `<div style="font-size:11px;margin-bottom:3px"><span style="color:var(--muted)">URL:</span> <a href="${{escHtml(deploy.url)}}" target="_blank" style="color:var(--accent)">${{escHtml(deploy.url)}}</a></div>`;
      if (deploy.remote_dir) dRows += `<div style="font-size:11px;margin-bottom:3px"><span style="color:var(--muted)">目录:</span> <code>${{escHtml(deploy.remote_dir)}}</code></div>`;
      if (deploy.cmd)  dRows += `<div style="font-size:11px;margin-bottom:3px"><span style="color:var(--muted)">命令:</span> <code>${{escHtml(deploy.cmd)}}</code></div>`;
      if (dRows) {{
        html += `<div class="arch-card">
          <div class="card-section-title">部署信息</div>
          ${{dRows}}
        </div>`;
      }}
    }}

    // ── Code stats (languages) ──
    const langs = (loc.languages || []).slice(0, 8);
    if (langs.length) {{
      const LANG_COLORS = ['#61afef','#c678dd','#e5c07b','#52c469','#e06c75','#56b6c2','#be5046','#98c379'];
      const maxL = Math.max(...langs.map(l => l.code||0), 1);
      let langHtml = langs.map((l,i) => {{
        const lines = l.code||0;
        const pct = Math.round(lines / maxL * 100);
        const lbl = lines >= 1000 ? (lines/1000).toFixed(1)+'k' : String(lines);
        return `<div class="lang-row">
          <span class="lang-name">${{escHtml(l.name||'')}}</span>
          <div class="lang-track"><div class="lang-fill" style="width:${{pct}}%;background:${{LANG_COLORS[i%8]}}"></div></div>
          <span class="lang-num">${{lbl}}</span>
        </div>`;
      }}).join('');
      const commentPct = loc.total_lines ? Math.round((loc.comment_lines||0) / loc.total_lines * 100) : 0;
      html += `<div class="arch-card">
        <div class="card-section-title">代码分布</div>
        <div style="display:flex;gap:20px;margin-bottom:10px;font-size:11px;color:var(--muted)">
          <span>文件 ${{loc.file_count||0}}</span>
          <span>注释率 ${{commentPct}}%</span>
        </div>
        ${{langHtml}}
      </div>`;
    }}

    // ── Features ──
    const doneFeats = features.filter(f => f.implemented);
    const plannedFeats = features.filter(f => !f.implemented);
    if (doneFeats.length || plannedFeats.length) {{
      let fHtml = doneFeats.map(f => `<div class="feat-item done">✓ ${{escHtml(f.text||'')}}</div>`).join('');
      fHtml += plannedFeats.map(f => `<div class="feat-item planned">○ ${{escHtml(f.text||'')}}</div>`).join('');
      html += `<div class="arch-card">
        <div class="card-section-title">功能列表</div>
        ${{fHtml}}
      </div>`;
    }}

    html += `</div>`;  // end outer padding div
    el.innerHTML = html;
    summaryLoaded = true;
  }}

// ── Edit modal ───────────────────────────────────────────────────────────────
function openEditModal() {{
  const p = projectData || {{}};
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal-box">
    <div class="modal-title">编辑项目信息</div>
    <div class="modal-label">项目名称</div>
    <input class="modal-input" id="edit-modal-name" value="${{escHtml(p.name||'')}}" />
    <div class="modal-label">一句话简介</div>
    <textarea class="modal-input modal-textarea" id="edit-modal-desc" rows="3">${{escHtml(p.description||'')}}</textarea>
    <div class="modal-actions">
      <button onclick="closeEditModal()">取消</button>
      <button class="primary" onclick="saveEditModal()">保存</button>
    </div>
  </div>`;
  overlay.addEventListener('click', e => {{ if (e.target === overlay) closeEditModal(); }});
  document.body.appendChild(overlay);
  document.getElementById('edit-modal-name').focus();
}}
function closeEditModal() {{
  const m = document.querySelector('.modal-overlay');
  if (m) m.remove();
}}
async function saveEditModal() {{
  const nameVal = (document.getElementById('edit-modal-name').value || '').trim();
  const descVal = (document.getElementById('edit-modal-desc').value || '').trim();
  const p = projectData || {{}};
  const promises = [];
  if (nameVal && nameVal !== (p.name||'')) {{
    promises.push(fetch(`/api/projects/${{PROJECT_ID}}/name`, {{
      method: 'POST', headers: {{'Content-Type':'application/json', ..._authHeaders()}},
      body: JSON.stringify({{name: nameVal}})
    }}).then(() => {{
      projectData.name = nameVal;
      document.getElementById('proj-name').textContent = nameVal;
    }}));
  }}
  if (descVal !== (p.description||'')) {{
    promises.push(fetch(`/api/projects/${{PROJECT_ID}}/description`, {{
      method: 'POST', headers: {{'Content-Type':'application/json', ..._authHeaders()}},
      body: JSON.stringify({{description: descVal}})
    }}).then(() => {{
      projectData.description = descVal;
    }}));
  }}
  await Promise.all(promises);
  closeEditModal();
  summaryLoaded = false;
  renderSummary();
}}

// ── Design Docs ───────────────────────────────────────────────────────────────
async function renderDesign() {{
  const el = document.getElementById('panel-design');
  // design_docs is stripped from inline data to keep initial page small; fetch lazily.
  if (projectData && !projectData.design_docs) {{
    try {{
      const res = await fetch(`/api/projects/${{PROJECT_ID}}`, {{headers: _authHeaders()}});
      const full = await res.json();
      projectData.design_docs = full.design_docs;
      projectData.plans = full.plans;
    }} catch(e) {{ /* non-fatal */ }}
  }}
  const docs = (projectData && projectData.design_docs) || [];
  if (!docs.length) {{
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">📐</div><div>暂无设计文档</div></div>`;
    designLoaded = true;
    return;
  }}
  let sidebar = docs.map((d,i) => `
    <div class="doc-item${{d.possibly_stale?' stale':''}}${{i===0?' active':''}}" id="ditem-${{i}}" onclick="showDoc(${{i}})">
      ${{escHtml(d.filename)}}${{d.possibly_stale?' ⚠':''}}</div>`).join('');

  let mobileList = docs.map((d,i) => `
    <div class="docs-mobile-item${{d.possibly_stale?' stale':''}}" onclick="docsMobileSelect(${{i}})">
      <div class="docs-mobile-item-name">${{escHtml(d.filename)}}${{d.possibly_stale?' ⚠':''}}</div>
      <div class="docs-mobile-item-meta">${{new Date(d.mtime*1000).toLocaleDateString('zh-CN')}}</div>
    </div>`).join('');

  el.innerHTML = `
    <div class="docs-mobile-list" id="docs-m-list">${{mobileList}}</div>
    <div class="docs-mobile-back" id="docs-m-back" onclick="docsMobileBack()">← 文档列表</div>
    <div class="docs-layout" id="docs-desktop">
      <div class="docs-sidebar">
        <div class="docs-sidebar-title">设计文档</div>
        ${{sidebar}}
      </div>
      <div class="docs-body" id="docs-body"></div>
    </div>`;

  // On mobile: hide desktop layout initially, show list
  if (window.innerWidth <= 640) {{
    document.getElementById('docs-desktop').style.display = 'none';
    document.getElementById('docs-m-back').style.display = 'none';
  }} else {{
    document.getElementById('docs-m-list').style.display = 'none';
    document.getElementById('docs-m-back').style.display = 'none';
    showDoc(0);
  }}
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

function docsMobileSelect(i) {{
  document.getElementById('docs-m-list').style.display = 'none';
  document.getElementById('docs-m-back').style.display = 'flex';
  document.getElementById('docs-desktop').style.display = 'block';
  showDoc(i);
}}

function docsMobileBack() {{
  document.getElementById('docs-m-list').style.display = '';
  document.getElementById('docs-m-back').style.display = 'none';
  document.getElementById('docs-desktop').style.display = 'none';
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

  const masked = !!(ca._masked);

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
        <div class="cl-sv">${{masked ? '***' : fmtCost(ca.estimated_cost_usd)}}</div>
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
      <div class="cl-tok-col"><div class="cl-tv">${{masked ? '***' : fmtTok(ca.output_tokens)}}</div><div class="cl-tl">输出</div><div class="cl-tsub">$15/MTok</div></div>
      <div class="cl-tok-col"><div class="cl-tv">${{masked ? '***' : fmtTok(ca.input_tokens)}}</div><div class="cl-tl">输入</div><div class="cl-tsub">$3/MTok</div></div>
      <div class="cl-tok-col"><div class="cl-tv">${{masked ? '***' : fmtTok(ca.cache_creation_tokens)}}</div><div class="cl-tl">Cache 写</div><div class="cl-tsub">$3.75/MTok</div></div>
      <div class="cl-tok-col"><div class="cl-tv">${{masked ? '***' : fmtTok(ca.cache_read_tokens)}}</div><div class="cl-tl">Cache 读</div><div class="cl-tsub">$0.30/MTok</div></div>
    </div>
    <div class="cl-cost-bar">
      <span style="flex:${{pOut}};background:#818cf8"></span>
      <span style="flex:${{pCw}};background:#4f46e5"></span>
      <span style="flex:${{pIn}};background:#2d3555"></span>
      <span style="flex:${{Math.max(pCr,1)}};background:#1a2035"></span>
    </div>
    <div class="cl-legend">
      <span class="cl-leg-item"><span class="cl-leg-dot" style="background:#818cf8"></span>输出 ${{masked ? '***' : outCost.toFixed(2)}}</span>
      <span class="cl-leg-item"><span class="cl-leg-dot" style="background:#4f46e5"></span>Cache写 ${{masked ? '***' : cwCost.toFixed(2)}}</span>
      <span class="cl-leg-item"><span class="cl-leg-dot" style="background:#2d3555"></span>输入 ${{masked ? '***' : inCost.toFixed(2)}}</span>
      <span class="cl-leg-item"><span class="cl-leg-dot" style="background:#1a2035"></span>Cache读 ${{masked ? '***' : crCost.toFixed(2)}}</span>
    </div>

    <div class="cl-bottom">
      <div class="cl-col-l">
        <div class="cl-section-title">15天会话活跃度</div>
        <div class="cl-spark">${{sparkBars}}</div>
        <div class="cl-section-title" style="margin-top:16px">本月小结</div>
        <div class="cl-summary-text">
          7天 <b>${{ca.session_count_7d || 0}}</b> 次会话 &nbsp;·&nbsp; 活跃 <b>${{ca.active_hours || 0}}h</b><br>
          Cache 命中率 <b>${{masked ? '***' : (ca.cache_read_tokens && ca.cache_creation_tokens
            ? Math.round(ca.cache_read_tokens / (ca.cache_read_tokens + ca.cache_creation_tokens) * 100)
            : 0) + '%'}}</b>
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
    const res = await fetch(`/api/projects/${{PROJECT_ID}}/prompts`, {{headers: _authHeaders()}});
    allPrompts = await res.json();
    if (!Array.isArray(allPrompts)) allPrompts = [];
  }} catch(e) {{
    el.innerHTML = `<div class="prompts-wrap"><div class="prompts-empty">加载失败</div></div>`;
    return;
  }}

  if (!allPrompts.length) {{
    el.innerHTML = `<div class="prompts-wrap"><div class="prompts-empty">暂无 Prompt 记录</div></div>`;
    promptsLoaded = true;
    return;
  }}

  const PAGE_SIZE = 30;
  let promptPage = 0;

  function renderList(q, page) {{
    const q2 = q.trim().toLowerCase();
    const filtered = q2 ? allPrompts.filter(p => p.text.toLowerCase().includes(q2)) : allPrompts;
    if (!filtered.length) return {{ html: `<div class="prompts-empty">没有匹配的 Prompt</div>`, total: 0 }};
    const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
    const p2 = Math.max(0, Math.min(page, totalPages - 1));
    const slice = filtered.slice(p2 * PAGE_SIZE, (p2 + 1) * PAGE_SIZE);
    const cards = slice.map(p => {{
      const raw = escHtml(p.text);
      const text = q2 ? raw.replace(new RegExp(escHtml(q2).replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&'), 'gi'), m=>`<mark>${{m}}</mark>`) : raw;
      return `<div class="prompt-card">
        <div class="prompt-date">${{p.date || ''}}</div>
        <div class="prompt-text">${{text}}</div>
      </div>`;
    }}).join('');
    return {{ html: cards, total: filtered.length, totalPages, page: p2 }};
  }}

  function renderPager(page, totalPages, total) {{
    if (totalPages <= 1) return `<div style="font-size:11px;color:var(--muted);margin-bottom:12px">${{total}} 条记录</div>`;
    return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:11px;color:var(--muted)">
      <button class="refresh-btn" onclick="promptGoPage(${{page-1}})" ${{page===0?'disabled':''}} style="padding:3px 8px">‹</button>
      <span>${{page+1}} / ${{totalPages}} 页 · ${{total}} 条</span>
      <button class="refresh-btn" onclick="promptGoPage(${{page+1}})" ${{page===totalPages-1?'disabled':''}} style="padding:3px 8px">›</button>
    </div>`;
  }}

  function applyPage() {{
    const q = document.getElementById('prompts-q')?.value || '';
    const r = renderList(q, promptPage);
    promptPage = r.page ?? 0;
    document.getElementById('prompts-pager').innerHTML = renderPager(promptPage, r.totalPages || 1, r.total || 0);
    document.getElementById('prompts-list').innerHTML = r.html;
  }}

  el.innerHTML = `<div class="prompts-wrap">
    <input class="prompts-search" id="prompts-q" type="text" placeholder="搜索 Prompt…" oninput="updatePrompts()" autocomplete="off">
    <div id="prompts-pager"></div>
    <div id="prompts-list"></div>
  </div>`;

  window._promptGoPage = (p) => {{ promptPage = p; applyPage(); }};
  window._updatePrompts = () => {{ promptPage = 0; applyPage(); }};
  applyPage();
  promptsLoaded = true;
}}

function promptGoPage(p) {{ window._promptGoPage && window._promptGoPage(p); }}
function updatePrompts() {{ window._updatePrompts && window._updatePrompts(); }}


async function reload() {{
  summaryLoaded = false; designLoaded = false; promptsLoaded = false;
  document.getElementById('panel-summary').innerHTML  = '<div class="loading"><div class="spinner"></div>加载中...</div>';
  document.getElementById('panel-design').innerHTML   = '<div class="loading"><div class="spinner"></div>加载中...</div>';
  document.getElementById('panel-prompts').innerHTML  = '';
  await init();
}}

{_tb_js}

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {{
  try {{
    if (window._INLINE_PROJECT && !window._INLINE_PROJECT.claude_activity?._masked) {{
      projectData = window._INLINE_PROJECT;
    }} else {{
      // Inline data is masked or missing — re-fetch with admin token
      const res = await fetch(`/api/projects/${{PROJECT_ID}}`, {{headers: _authHeaders()}});
      projectData = await res.json();
    }}
    document.getElementById('proj-name').textContent = projectData.name || PROJECT_ID;
  }} catch(e) {{ /* non-fatal; fall back to inline data if API fails */
    if (!projectData && window._INLINE_PROJECT) projectData = window._INLINE_PROJECT;
  }}

  renderSummary();
  showTab(activeTab);
}}

_initAuth().then(() => init());

</script>

{_overlays}

</body>
</html>'''
