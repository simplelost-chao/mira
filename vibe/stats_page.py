"""Stats dashboard page — GET /stats."""


def render_stats_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css = theme_vars_css()
    _tb_css    = topbar_css()
    _tb_html   = topbar_html(title="统计", back_url="/")
    _overlays  = settings_overlay_html()
    _tb_js     = topbar_js()

    page_css = r"""
  a { color: inherit; text-decoration: none; }

  /* range controls bar */
  .stats-controls {
    display: flex; align-items: center; gap: 8px; padding: 8px 20px;
    background: var(--panel); border-bottom: 1px solid var(--border);
  }
  .range-toggle { display: flex; gap: 4px; }
  .range-btn { background: none; border: 1px solid var(--border); color: var(--sub);
               border-radius: var(--radius-sm); padding: 4px 12px; font-size: 12px;
               cursor: pointer; font-family: var(--mono); transition: all .15s; }
  .range-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }

  /* main layout */
  .stats-main { max-width: 960px; margin: 0 auto; padding: 24px 20px 60px; }

  /* summary cards */
  .summary-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
                 margin-bottom: 20px; }
  .summary-card { background: var(--panel); border: 1px solid var(--border);
                  border-radius: var(--radius); padding: 16px; text-align: center; }
  .summary-val { font-size: 24px; font-weight: 700; color: var(--text);
                 margin-bottom: 4px; }
  .summary-lbl { font-size: 11px; color: var(--sub); }

  /* chart row */
  .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
               margin-bottom: 20px; }
  .chart-card { background: var(--panel); border: 1px solid var(--border);
                border-radius: var(--radius); padding: 16px; }
  .chart-title { font-size: 12px; color: var(--text); font-weight: 600;
                 margin-bottom: 12px; }
  .chart-svg { width: 100%; overflow: visible; }

  /* project ranking */
  .ranking-card { background: var(--panel); border: 1px solid var(--border);
                  border-radius: var(--radius); padding: 16px; }
  .ranking-title { font-size: 12px; color: var(--text); font-weight: 600;
                   margin-bottom: 12px; }
  .rank-row { display: grid; grid-template-columns: 110px 1fr 60px 60px;
              align-items: center; gap: 10px; margin-bottom: 10px; }
  .rank-name { font-size: 12px; color: var(--text); overflow: hidden;
               text-overflow: ellipsis; white-space: nowrap; }
  .rank-bar-bg { background: rgba(255,255,255,.06); border-radius: 3px; height: 8px; }
  .rank-bar { background: var(--green); border-radius: 3px; height: 8px;
              transition: width .3s; }
  .rank-hours { font-size: 11px; color: var(--sub); text-align: right; }
  .rank-cost  { font-size: 11px; color: var(--blue,#4e9eff); text-align: right; }

  /* empty state */
  .empty-state { text-align: center; color: var(--sub); padding: 60px 20px;
                 font-size: 14px; }

  @media (max-width: 640px) {
    .summary-row { grid-template-columns: repeat(2, 1fr); }
    .chart-row   { grid-template-columns: 1fr; }
    .rank-row    { grid-template-columns: 80px 1fr 50px; }
    .rank-cost   { display: none; }
  }
"""

    page_js = r"""
const _PRICE_IN  = 3.0  / 1e6;
const _PRICE_OUT = 15.0 / 1e6;
let _currentRange = '30d';

function _esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.getElementById('btn-30d').addEventListener('click', function() { setRange('30d'); });
document.getElementById('btn-12w').addEventListener('click', function() { setRange('12w'); });

function setRange(r) {
  _currentRange = r;
  document.getElementById('btn-30d').classList.toggle('active', r === '30d');
  document.getElementById('btn-12w').classList.toggle('active', r === '12w');
  loadStats();
}

async function loadStats() {
  try {
    const res = await fetch('/api/stats?range=' + _currentRange, { headers: _authHeaders() });
    if (res.status === 401) { openLoginModal(loadStats); return; }
    if (!res.ok) {
      document.getElementById('summary-row').innerHTML =
        '<div class="empty-state">加载失败，请刷新重试</div>';
      return;
    }
    const data = await res.json();
    renderSummary(data.totals);
    requestAnimationFrame(function() {
      renderBarChart('chart-hours', data.days, function(d) { return d.active_hours; },
                     function(v) { return v.toFixed(1) + 'h'; }, '#5cd08a');
      renderBarChart('chart-cost',  data.days,
                     function(d) { return d.input_tokens * _PRICE_IN + d.output_tokens * _PRICE_OUT; },
                     function(v) { return '$' + v.toFixed(2); }, '#4e9eff');
    });
    renderRanking(data.projects);
  } catch(e) {
    console.warn('stats load error:', e);
  }
}

function renderSummary(t) {
  if (!t) return;
  var cards = [
    [(t.active_hours != null ? t.active_hours.toFixed(1) : '0.0') + 'h', '活跃时长'],
    ['$' + (t.estimated_cost_usd != null ? t.estimated_cost_usd.toFixed(2) : '0.00'), 'Token 花费'],
    [t.sessions != null ? t.sessions : 0, '会话数'],
    [_fmtNum(t.output_tokens != null ? t.output_tokens : 0), '输出 Tokens'],
  ];
  document.getElementById('summary-row').innerHTML = cards.map(function(pair) {
    return '<div class="summary-card"><div class="summary-val">' + pair[0] + '</div>' +
           '<div class="summary-lbl">' + pair[1] + '</div></div>';
  }).join('');
}

function _fmtNum(n) {
  if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n/1e3).toFixed(0) + 'K';
  return String(n);
}

function renderBarChart(svgId, days, valFn, labelFn, color) {
  var svg = document.getElementById(svgId);
  if (!svg || !days || !days.length) return;
  var W = svg.parentElement.clientWidth - 32;
  var H = 80;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  var vals = days.map(valFn);
  var maxVal = Math.max.apply(null, vals.concat([0.001]));
  var barW = Math.max(2, (W / days.length) - 1);
  var html = '';
  days.forEach(function(d, i) {
    var v = vals[i];
    var bh = Math.max(2, (v / maxVal) * (H - 16));
    var x = i * (W / days.length);
    var y = H - bh;
    var label = d.date.slice(5);
    html += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) +
            '" width="' + barW.toFixed(1) + '" height="' + bh.toFixed(1) +
            '" fill="' + color + '" opacity="0.75" rx="2">' +
            '<title>' + label + ': ' + labelFn(v) + '</title></rect>';
  });
  svg.innerHTML = html;
}

function renderRanking(projects) {
  var el = document.getElementById('ranking-list');
  if (!projects || !projects.length) {
    el.innerHTML = '<div class="empty-state" style="padding:20px">暂无数据</div>';
    return;
  }
  var maxH = Math.max.apply(null, projects.map(function(p) { return p.total_hours || 0; }).concat([0.001]));
  el.innerHTML = projects.map(function(p) {
    var pct = ((p.total_hours || 0) / maxH * 100).toFixed(1);
    var name = _esc(p.project_name || p.project_id);
    return '<div class="rank-row">' +
      '<div class="rank-name" title="' + name + '">' + name + '</div>' +
      '<div class="rank-bar-bg"><div class="rank-bar" style="width:' + pct + '%"></div></div>' +
      '<div class="rank-hours">' + (p.total_hours || 0).toFixed(1) + 'h</div>' +
      '<div class="rank-cost">$' + (p.total_cost_usd || 0).toFixed(2) + '</div>' +
      '</div>';
  }).join('');
}

_initAuth().then(loadStats);
"""

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>开发统计 · Mira</title>\n"
        "<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>\n"
        "<style>\n"
        "  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Noto+Sans+SC:wght@400;700&display=swap');\n"
        + _theme_css
        + _tb_css
        + page_css
        + "</style>\n</head>\n<body>\n\n"
        + _tb_html + "\n\n"
        + """\
<div class="stats-controls">
  <div class="range-toggle">
    <button class="range-btn active" id="btn-30d">日 · 30天</button>
    <button class="range-btn"        id="btn-12w">周 · 12周</button>
  </div>
</div>

<div class="stats-main">
  <div id="summary-row" class="summary-row"></div>
  <div class="chart-row">
    <div class="chart-card">
      <div class="chart-title">活跃时长</div>
      <svg id="chart-hours" class="chart-svg" height="80"></svg>
    </div>
    <div class="chart-card">
      <div class="chart-title">Token 花费（USD）</div>
      <svg id="chart-cost" class="chart-svg" height="80"></svg>
    </div>
  </div>
  <div class="ranking-card">
    <div class="ranking-title">项目活跃度排行</div>
    <div id="ranking-list"></div>
  </div>
</div>

"""
        + _overlays + "\n\n"
        + "<script>\n"
        + _tb_js + "\n"
        + page_js
        + "</script>\n</body>\n</html>\n"
    )
