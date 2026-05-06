"""Stats dashboard page — GET /stats."""


def render_stats_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css = theme_vars_css()
    _tb_css    = topbar_css()
    _tb_html   = topbar_html(title="统计", back_url="javascript:history.back()")
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

  /* trend chart */
  .trend-card { background: var(--panel); border: 1px solid var(--border);
                border-radius: var(--radius); padding: 16px; margin-bottom: 20px; }
  .trend-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; font-size: 11px; color: var(--sub); }
  .trend-legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }

  /* heatmap */
  .heatmap-card { background: var(--panel); border: 1px solid var(--border);
                  border-radius: var(--radius); padding: 16px; margin-bottom: 20px; overflow-x: auto; }
  .heatmap-grid { display: flex; gap: 3px; }
  .heatmap-week { display: flex; flex-direction: column; gap: 3px; }
  .heatmap-day { width: 12px; height: 12px; border-radius: 2px; cursor: default;
                 background: rgba(255,255,255,.05); transition: opacity .1s; }
  .heatmap-day:hover { opacity: .7; }
  .heatmap-labels { display: flex; gap: 3px; margin-top: 4px; font-size: 9px; color: var(--sub); }
  .heatmap-month-label { width: 12px; text-align: center; overflow: visible; white-space: nowrap; }

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
const _PRICE_IN        = 3.0   / 1e6;
const _PRICE_OUT       = 15.0  / 1e6;
const _PRICE_CACHE_W   = 3.75  / 1e6;
const _PRICE_CACHE_R   = 0.30  / 1e6;
const _TREND_COLORS    = ['#5cd08a','#4e9eff','#f0a050','#c792ea','#56b6c2'];

let _currentRange = '30d';
let _lastData = null;

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
    _lastData = data;
    renderSummary(data.totals);
    requestAnimationFrame(function() {
      renderBarChart('chart-hours', data.days, function(d) { return d.active_hours; },
                     function(v) { return v.toFixed(1) + 'h'; }, '#5cd08a');
      renderBarChart('chart-cost',  data.days,
                     function(d) { return d.input_tokens * _PRICE_IN + d.output_tokens * _PRICE_OUT
                                        + d.cache_creation_tokens * _PRICE_CACHE_W
                                        + d.cache_read_tokens * _PRICE_CACHE_R; },
                     function(v) { return '$' + v.toFixed(2); }, '#4e9eff');
      renderTrendChart(data);
      renderHeatmap(data.heatmap || {});
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

// ── B: 费用趋势折线图 ────────────────────────────────────────────────────────
function renderTrendChart(data) {
  var el = document.getElementById('trend-svg');
  var legend = document.getElementById('trend-legend');
  if (!el || !data || !data.project_days || !data.days) return;

  var W = el.parentElement.clientWidth - 32;
  var H = 120;
  el.setAttribute('viewBox', '0 0 ' + W + ' ' + H);

  var days = data.days.map(function(d) { return d.date; });
  var projectDays = data.project_days;  // {project_id: {date: cost}}
  var projects = data.projects.slice(0, 5);
  if (!projects.length) { el.innerHTML = ''; return; }

  // Compute max cost across all projects and days
  var maxCost = 0.001;
  projects.forEach(function(p) {
    var pd = projectDays[p.project_id] || {};
    days.forEach(function(d) { maxCost = Math.max(maxCost, pd[d] || 0); });
  });

  var html = '';
  var PAD = 4;
  var usableW = W - PAD * 2;
  var usableH = H - PAD * 2 - 16;

  projects.forEach(function(p, pi) {
    var pd = projectDays[p.project_id] || {};
    var color = _TREND_COLORS[pi % _TREND_COLORS.length];
    var pts = days.map(function(d, i) {
      var cost = pd[d] || 0;
      var x = PAD + (i / Math.max(days.length - 1, 1)) * usableW;
      var y = PAD + usableH - (cost / maxCost) * usableH;
      return x.toFixed(1) + ',' + y.toFixed(1);
    });
    html += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + color +
            '" stroke-width="1.5" opacity="0.85">';
    // Tooltip on each point — use invisible rect
    html += '</polyline>';
    days.forEach(function(d, i) {
      var cost = pd[d] || 0;
      if (!cost) return;
      var x = PAD + (i / Math.max(days.length - 1, 1)) * usableW;
      var y = PAD + usableH - (cost / maxCost) * usableH;
      html += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="2" fill="' + color + '">' +
              '<title>' + _esc(p.project_name || p.project_id) + ' ' + d + ': $' + cost.toFixed(3) + '</title></circle>';
    });
  });

  // X-axis labels (first of each month)
  var lastMonth = '';
  days.forEach(function(d, i) {
    var month = d.slice(5, 7);
    if (month !== lastMonth) {
      lastMonth = month;
      var x = PAD + (i / Math.max(days.length - 1, 1)) * usableW;
      html += '<text x="' + x.toFixed(1) + '" y="' + (H - 2) + '" font-size="9" fill="var(--sub)" text-anchor="middle">' + d.slice(5, 10) + '</text>';
    }
  });

  el.innerHTML = html;

  // Legend
  legend.innerHTML = projects.map(function(p, pi) {
    var color = _TREND_COLORS[pi % _TREND_COLORS.length];
    return '<span><span class="trend-legend-dot" style="background:' + color + '"></span>' +
           _esc(p.project_name || p.project_id) + ' $' + (p.total_cost_usd || 0).toFixed(2) + '</span>';
  }).join('');
}

// ── C: 活动热力图 ────────────────────────────────────────────────────────────
function renderHeatmap(heatmap) {
  var el = document.getElementById('heatmap-container');
  if (!el) return;

  var today = new Date();
  today.setHours(0, 0, 0, 0);
  var startDate = new Date(today);
  startDate.setDate(startDate.getDate() - 364 - startDate.getDay());

  var maxHours = 0.001;
  Object.values(heatmap).forEach(function(v) { maxHours = Math.max(maxHours, v.hours || 0); });

  var weeks = [];
  var cur = new Date(startDate);
  var monthLabels = [];

  while (cur <= today) {
    var week = [];
    var startOfWeek = new Date(cur);
    for (var dow = 0; dow < 7; dow++) {
      var dateStr = cur.toISOString().slice(0, 10);
      var entry = heatmap[dateStr] || { hours: 0, sessions: 0 };
      var intensity = Math.min(1, (entry.hours || 0) / Math.max(maxHours * 0.8, 0.001));
      week.push({ date: dateStr, hours: entry.hours, sessions: entry.sessions, intensity: intensity, future: cur > today });
      cur.setDate(cur.getDate() + 1);
    }
    var m = startOfWeek.toLocaleString('zh', { month: 'short' });
    monthLabels.push(startOfWeek.getDate() <= 7 ? m : '');
    weeks.push(week);
  }

  function _intensityColor(v) {
    if (v <= 0) return 'rgba(255,255,255,.05)';
    var r = Math.round(92 * v);
    var g = Math.round(208 * (0.3 + 0.7 * v));
    var b = Math.round(138 * v);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  var gridHtml = weeks.map(function(week) {
    var cells = week.map(function(day) {
      if (day.future) return '<div class="heatmap-day" style="background:transparent"></div>';
      var color = _intensityColor(day.intensity);
      var tip = day.date + ': ' + (day.hours || 0).toFixed(1) + 'h, ' + (day.sessions || 0) + ' sessions';
      return '<div class="heatmap-day" style="background:' + color + '" title="' + tip + '"></div>';
    }).join('');
    return '<div class="heatmap-week">' + cells + '</div>';
  }).join('');

  var labelsHtml = '<div class="heatmap-labels">' +
    monthLabels.map(function(m) {
      return '<div class="heatmap-month-label">' + (m || '') + '</div>';
    }).join('') + '</div>';

  el.innerHTML = '<div class="heatmap-grid">' + gridHtml + '</div>' + labelsHtml;
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
        '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">\n'
        '<link rel="stylesheet" href="/static/fonts/fonts.css">\n'
        "<style>\n"
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

  <div class="trend-card">
    <div class="chart-title">Top 5 项目费用趋势</div>
    <svg id="trend-svg" class="chart-svg" height="120"></svg>
    <div class="trend-legend" id="trend-legend"></div>
  </div>

  <div class="heatmap-card">
    <div class="chart-title" style="margin-bottom:8px">活动热力图（近一年）</div>
    <div id="heatmap-container" style="min-height:80px"></div>
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
