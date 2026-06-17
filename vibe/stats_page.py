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

  /* controls — two rows */
  .ctrl-bar { display: flex; align-items: center; gap: 8px; padding: 8px 20px;
              background: var(--panel); border-bottom: 1px solid var(--border); }
  .ctrl-subbar { display: flex; align-items: center; gap: 8px; padding: 5px 20px;
                 background: var(--bg); border-bottom: 1px solid var(--border); }
  .range-toggle, .mode-toggle, .sort-toggle, .view-toggle { display: flex; gap: 4px; }
  .stats-btn { background: none; border: 1px solid var(--border); color: var(--sub);
               border-radius: var(--radius-sm); padding: 4px 12px; font-size: 12px;
               cursor: pointer; font-family: var(--mono); transition: all .15s; }
  .stats-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
  .stats-btn.green.active { background: var(--green); border-color: var(--green); color: #fff; }
  .ctrl-sep { width: 1px; height: 18px; background: var(--border); margin: 0 4px; }
  .filter-input { background: var(--panel); border: 1px solid var(--border); color: var(--text);
                  border-radius: var(--radius-sm); padding: 4px 10px; font-size: 12px;
                  font-family: var(--mono); width: 160px; }
  .filter-input::placeholder { color: var(--sub); }

  /* main layout */
  .stats-main { max-width: 1060px; margin: 0 auto; padding: 24px 20px 60px; }

  /* summary cards */
  .summary-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
                 margin-bottom: 20px; }
  .summary-card { background: var(--panel); border: 1px solid var(--border);
                  border-radius: var(--radius); padding: 16px; text-align: center; }
  .summary-val { font-size: 24px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
  .summary-lbl { font-size: 11px; color: var(--sub); }

  /* chart row */
  .chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
  .chart-card { background: var(--panel); border: 1px solid var(--border);
                border-radius: var(--radius); padding: 16px; }
  .chart-title { font-size: 12px; color: var(--text); font-weight: 600; margin-bottom: 12px; }
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
  .ranking-title { font-size: 12px; color: var(--text); font-weight: 600; margin-bottom: 12px; }
  .rank-row { display: grid; grid-template-columns: 110px 1fr 60px 60px;
              align-items: center; gap: 10px; margin-bottom: 10px; }
  .rank-name { font-size: 12px; color: var(--text); overflow: hidden;
               text-overflow: ellipsis; white-space: nowrap; }
  .rank-bar-bg { background: rgba(255,255,255,.06); border-radius: 3px; height: 8px; }
  .rank-bar { background: var(--green); border-radius: 3px; height: 8px; transition: width .3s; }
  .rank-hours { font-size: 11px; color: var(--sub); text-align: right; }
  .rank-cost  { font-size: 11px; color: var(--blue,#4e9eff); text-align: right; }

  /* daily project breakdown */
  .daily-row { display: grid; grid-template-columns: 110px 1fr 64px; align-items: start;
               gap: 10px; margin-bottom: 10px; }
  .daily-name { font-size: 12px; color: var(--text); overflow: hidden;
                text-overflow: ellipsis; white-space: nowrap; }
  .daily-bar-bg { background: rgba(255,255,255,.06); border-radius: 3px; height: 10px; }
  .daily-bar { border-radius: 3px; height: 10px; transition: width .3s; min-width: 2px; }
  .daily-cost { font-size: 12px; color: var(--blue,#4e9eff); text-align: right;
                font-family: var(--mono); white-space: nowrap; }

  /* ── Sessions mode ───────────────────────────────────── */
  .token-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
  .token-card { background: var(--panel); border: 1px solid var(--border);
                border-radius: var(--radius); padding: 14px 16px; }
  .token-label { font-size: 11px; color: var(--sub); margin-bottom: 6px; display: flex;
                 align-items: center; gap: 5px; }
  .token-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .token-val { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 3px; font-family: var(--mono); }
  .token-cost { font-size: 11px; color: var(--sub); }
  .token-pct { font-size: 11px; margin-left: auto; }

  .scatter-card { background: var(--panel); border: 1px solid var(--border);
                  border-radius: var(--radius); padding: 16px; margin-bottom: 20px; }

  .token-stack-card { background: var(--panel); border: 1px solid var(--border);
                      border-radius: var(--radius); padding: 16px; margin-bottom: 20px; }
  .token-stack-row { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
  .stack-label { width: 90px; font-size: 11px; color: var(--text); overflow: hidden;
                 text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; }
  .stack-bar { flex: 1; height: 10px; border-radius: 3px; overflow: hidden; display: flex; }
  .stack-seg { height: 100%; }
  .stack-total { width: 58px; font-size: 11px; color: var(--sub); text-align: right; font-family: var(--mono); flex-shrink: 0; }

  .table-card { background: var(--panel); border: 1px solid var(--border);
                border-radius: var(--radius); padding: 16px; }
  .session-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .session-table th { text-align: left; color: var(--sub); font-weight: 500; padding: 8px 6px;
                      border-bottom: 1px solid var(--border); white-space: nowrap; }
  .session-table td { padding: 8px 6px; border-bottom: 1px solid rgba(255,255,255,.04); color: var(--text); }
  .session-table tr:hover td { background: rgba(255,255,255,.03); }
  .col-rank  { width: 30px; color: var(--sub); text-align: center; }
  .col-project { max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .col-task  { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
               color: var(--sub); font-size: 11px; }
  .col-num   { text-align: right; white-space: nowrap; font-family: var(--mono); }
  .cost-hi   { color: #f87171; font-weight: 600; }
  .cost-md   { color: #fbbf24; }
  .cost-lo   { color: var(--sub); }
  .hours-hi  { color: #34d399; font-weight: 600; }
  .tok-bar   { display: flex; height: 5px; border-radius: 2px; overflow: hidden; min-width: 60px; gap: 1px; }
  .tok-seg   { height: 100%; border-radius: 1px; }

  /* session detail modal */
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.6); z-index: 200;
                   display: flex; align-items: flex-start; justify-content: center;
                   padding: 40px 16px; overflow-y: auto; }
  .modal-box { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
               width: 100%; max-width: 760px; padding: 24px; position: relative; }
  .modal-close { position: absolute; top: 14px; right: 16px; background: none; border: none;
                 color: var(--sub); font-size: 18px; cursor: pointer; line-height: 1; }
  .modal-title { font-size: 14px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
  .modal-sub { font-size: 11px; color: var(--sub); margin-bottom: 20px; }
  .turn-row { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0;
              border-bottom: 1px solid rgba(255,255,255,.05); }
  .turn-row:last-child { border-bottom: none; }
  .turn-rank { width: 22px; font-size: 11px; color: var(--sub); text-align: center; flex-shrink: 0; padding-top: 2px; }
  .turn-body { flex: 1; min-width: 0; }
  .turn-label { font-size: 12px; color: var(--text); margin-bottom: 4px;
                overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .turn-label.inherited { color: var(--sub); font-style: italic; }
  .turn-raw { font-size: 10px; color: rgba(255,255,255,.3); margin-bottom: 5px;
              overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .turn-tok-bar { margin-bottom: 3px; }
  .turn-meta { font-size: 10px; color: var(--sub); display: flex; gap: 10px; }
  .turn-cost { width: 60px; text-align: right; flex-shrink: 0; font-family: var(--mono); font-size: 12px; padding-top: 2px; }

  /* GitHub trending */
  .gh-card { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
             padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; cursor: pointer;
             transition: border-color .15s; }
  .gh-card:hover { border-color: var(--accent); }
  .gh-card-title { font-size: 13px; font-weight: 600; color: var(--accent); }
  .gh-card-desc { font-size: 11px; color: var(--sub); line-height: 1.5; flex: 1; }
  .gh-card-meta { display: flex; gap: 12px; align-items: center; font-size: 10px; color: var(--sub); margin-top: 2px; }
  .gh-lang-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; display: inline-block; margin-right: 4px; }

  /* empty state */
  .empty-state { text-align: center; color: var(--sub); padding: 60px 20px; font-size: 14px; }

  @media (max-width: 640px) {
    .summary-row { grid-template-columns: repeat(2, 1fr); }
    .token-row   { grid-template-columns: repeat(2, 1fr); }
    .chart-row   { grid-template-columns: 1fr; }
    .rank-row    { grid-template-columns: 80px 1fr 50px; }
    .rank-cost   { display: none; }
    .col-task    { display: none; }
    .session-table { font-size: 11px; }
  }
"""

    page_js = r"""
// ── Pricing ────────────────────────────────────────────────────────────
const _CL_PRICE_IN      = 3.0   / 1e6;
const _CL_PRICE_OUT     = 15.0  / 1e6;
const _CL_PRICE_CACHE_W = 3.75  / 1e6;
const _CL_PRICE_CACHE_R = 0.30  / 1e6;

const _CX_PRICE_IN      = 15.0  / 1e6;
const _CX_PRICE_OUT     = 75.0  / 1e6;
const _CX_PRICE_CACHE   = 7.5   / 1e6;
const _CX_PRICE_REASON  = 75.0  / 1e6;

const _TREND_COLORS = ['#5cd08a','#4e9eff','#f0a050','#c792ea','#56b6c2'];
const TOK_COLORS = { inp: '#4e9eff', out: '#f0a050', cw: '#fbbf24', cr: '#5cd08a' };

let _currentRange   = '30d';
let _currentTool    = 'claude';   // 'claude' | 'codex'
let _claudeView     = 'overview'; // 'overview' | 'sessions'
let _codexView      = 'overview'; // 'overview' | 'sessions'
let _sessionSort    = 'cost';
let _cxSessionSort  = 'cost';
let _cxSessionFilter = '';
let _cxSessionData  = [];
let _sessionFilter  = '';
let _sessionData    = [];

function _esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function _fmtNum(n) {
  if (n >= 1e9) return (n/1e9).toFixed(1) + 'B';
  if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n/1e3).toFixed(0) + 'K';
  return String(n || 0);
}
function _fmtCost(v) {
  if (v >= 100) return '$' + v.toFixed(0);
  if (v >= 10)  return '$' + v.toFixed(1);
  return '$' + v.toFixed(2);
}
function _costClass(v) {
  if (v >= 100) return 'cost-hi';
  if (v >= 30)  return 'cost-md';
  return 'cost-lo';
}

// ── Controls ────────────────────────────────────────────────────────────
document.getElementById('btn-30d').addEventListener('click', function() { setRange('30d'); });
document.getElementById('btn-12w').addEventListener('click', function() { setRange('12w'); });
document.getElementById('btn-tool-claude').addEventListener('click',      function() { setTool('claude'); });
document.getElementById('btn-tool-codex').addEventListener('click',       function() { setTool('codex'); });
document.getElementById('btn-tool-github').addEventListener('click',      function() { setTool('github'); });
document.getElementById('btn-view-overview').addEventListener('click',    function() { setClaudeView('overview'); });
document.getElementById('btn-view-sessions').addEventListener('click',    function() { setClaudeView('sessions'); });
document.getElementById('btn-cx-view-overview').addEventListener('click', function() { setCodexView('overview'); });
document.getElementById('btn-cx-view-sessions').addEventListener('click', function() { setCodexView('sessions'); });
document.getElementById('btn-cx-sess-cost').addEventListener('click',  function() { setCxSessSort('cost'); });
document.getElementById('btn-cx-sess-hours').addEventListener('click', function() { setCxSessSort('hours'); });
document.getElementById('cx-sess-filter').addEventListener('input', function(e) {
  _cxSessionFilter = e.target.value.toLowerCase();
  _renderSessionsAll(_cxSessionData);  // reuse same renderer
});
document.getElementById('btn-sess-cost').addEventListener('click',  function() { setSessSort('cost'); });
document.getElementById('btn-sess-hours').addEventListener('click', function() { setSessSort('hours'); });
document.getElementById('sess-filter').addEventListener('input', function(e) {
  _sessionFilter = e.target.value.toLowerCase();
  _renderSessionsAll(_sessionData);
});

function setRange(r) {
  _currentRange = r;
  document.getElementById('btn-30d').classList.toggle('active', r === '30d');
  document.getElementById('btn-12w').classList.toggle('active', r === '12w');
  if (_currentTool === 'claude') loadClaudeStats();
}

function setSessSort(s) {
  _sessionSort = s;
  document.getElementById('btn-sess-cost').classList.toggle('active',  s === 'cost');
  document.getElementById('btn-sess-hours').classList.toggle('active', s === 'hours');
  loadSessionsData();
}

function setTool(t) {
  _currentTool = t;
  ['claude','codex','github'].forEach(function(x) {
    document.getElementById('btn-tool-' + x).classList.toggle('active', t === x);
  });
  document.getElementById('claude-subbar').style.display  = t === 'claude' ? 'flex' : 'none';
  document.getElementById('codex-subbar').style.display   = t === 'codex'  ? 'flex' : 'none';
  document.getElementById('agg-section').style.display    = t === 'github' ? 'none' : '';
  document.getElementById('sess-section').style.display   = 'none';
  document.getElementById('github-section').style.display = t === 'github' ? '' : 'none';
  if (t === 'claude') {
    setClaudeView(_claudeView);
  } else if (t === 'codex') {
    setCodexView(_codexView);
  } else if (t === 'github') {
    if (!_ghLoaded) loadGHTrending('weekly');
  }
}

function setCodexView(v) {
  _codexView = v;
  document.getElementById('btn-cx-view-overview').classList.toggle('active', v === 'overview');
  document.getElementById('btn-cx-view-sessions').classList.toggle('active', v === 'sessions');
  var isSess = v === 'sessions';
  document.getElementById('cx-sess-controls').style.display = isSess ? 'flex' : 'none';
  document.getElementById('agg-section').style.display      = isSess ? 'none' : '';
  document.getElementById('sess-section').style.display     = isSess ? '' : 'none';
  if (isSess) loadCxSessionsData();
  else        loadCodexStats();
}

function setCxSessSort(s) {
  _cxSessionSort = s;
  document.getElementById('btn-cx-sess-cost').classList.toggle('active',  s === 'cost');
  document.getElementById('btn-cx-sess-hours').classList.toggle('active', s === 'hours');
  loadCxSessionsData();
}

function setClaudeView(v) {
  _claudeView = v;
  document.getElementById('btn-view-overview').classList.toggle('active', v === 'overview');
  document.getElementById('btn-view-sessions').classList.toggle('active', v === 'sessions');
  var isSess = v === 'sessions';
  document.getElementById('range-group').style.display    = isSess ? 'none' : 'flex';
  document.getElementById('sess-controls').style.display  = isSess ? 'flex' : 'none';
  document.getElementById('agg-section').style.display    = isSess ? 'none' : '';
  document.getElementById('sess-section').style.display   = isSess ? '' : 'none';
  if (isSess) loadSessionsData();
  else        loadClaudeStats();
}

// ── Shared helpers ──────────────────────────────────────────────────────
function _clearAgg() {
  ['summary-row', 'chart-hours', 'chart-cost', 'trend-svg', 'trend-legend',
   'heatmap-container', 'ranking-list'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = '';
  });
  document.getElementById('trend-card').style.display        = 'none';
  document.getElementById('daily-stack-card').style.display  = 'none';
  document.getElementById('heatmap-card').style.display      = 'none';
}

// ── Claude mode ─────────────────────────────────────────────────────────
async function loadClaudeStats() {
  _clearAgg();
  document.getElementById('heatmap-card').style.display = '';
  try {
    const res = await fetch('/api/stats?range=' + _currentRange, { headers: _authHeaders() });
    if (res.status === 401) { openLoginModal(loadClaudeStats); return; }
    if (!res.ok) {
      document.getElementById('summary-row').innerHTML = '<div class="empty-state">加载失败</div>';
      return;
    }
    const data = await res.json();
    _renderClaudeSummary(data.totals);
    requestAnimationFrame(function() {
      _renderBarChart('chart-hours', data.days,
        function(d) { return d.active_hours; },
        function(v) { return v.toFixed(1) + 'h'; }, '#5cd08a');
      _renderBarChart('chart-cost', data.days,
        function(d) { return d.input_tokens * _CL_PRICE_IN + d.output_tokens * _CL_PRICE_OUT
                           + d.cache_creation_tokens * _CL_PRICE_CACHE_W
                           + d.cache_read_tokens * _CL_PRICE_CACHE_R; },
        function(v) { return '$' + v.toFixed(2); }, '#4e9eff');
      _renderClaudeTrend(data);
      _renderDailyProjectStack(data);
      _renderClaudeHeatmap(data.heatmap || {});
    });
    _renderClaudeRanking(data.projects);
  } catch(e) { console.warn('claude stats error:', e); }
}

function _renderClaudeSummary(t) {
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

function _renderBarChart(svgId, days, valFn, labelFn, color) {
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
    html += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) +
            '" width="' + barW.toFixed(1) + '" height="' + bh.toFixed(1) +
            '" fill="' + color + '" opacity="0.75" rx="2">' +
            '<title>' + d.date.slice(5) + ': ' + labelFn(v) + '</title></rect>';
  });
  svg.innerHTML = html;
}

function _renderClaudeTrend(data) {
  var el = document.getElementById('trend-svg');
  var legend = document.getElementById('trend-legend');
  if (!el || !data || !data.project_days || !data.days) return;
  document.getElementById('trend-card').style.display = '';
  var W = el.parentElement.clientWidth - 32;
  var H = 120;
  el.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  var days = data.days.map(function(d) { return d.date; });
  var projectDays = data.project_days;
  var projects = data.projects.slice(0, 5);
  if (!projects.length) { el.innerHTML = ''; return; }
  var maxCost = 0.001;
  projects.forEach(function(p) {
    var pd = projectDays[p.project_id] || {};
    days.forEach(function(d) { var e = pd[d]; maxCost = Math.max(maxCost, e ? (e.cost != null ? e.cost : e) : 0); });
  });
  var html = '';
  var PAD = 4;
  var usableW = W - PAD * 2;
  var usableH = H - PAD * 2 - 16;
  projects.forEach(function(p, pi) {
    var pd = projectDays[p.project_id] || {};
    var color = _TREND_COLORS[pi % _TREND_COLORS.length];
    var pts = days.map(function(d, i) {
      var _e = pd[d]; var cost = _e ? (_e.cost != null ? _e.cost : _e) : 0;
      var x = PAD + (i / Math.max(days.length - 1, 1)) * usableW;
      var y = PAD + usableH - (cost / maxCost) * usableH;
      return x.toFixed(1) + ',' + y.toFixed(1);
    });
    html += '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + color + '" stroke-width="1.5" opacity="0.85"></polyline>';
    days.forEach(function(d, i) {
      var _e = pd[d]; var cost = _e ? (_e.cost != null ? _e.cost : _e) : 0;
      if (!cost) return;
      var x = PAD + (i / Math.max(days.length - 1, 1)) * usableW;
      var y = PAD + usableH - (cost / maxCost) * usableH;
      html += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="2" fill="' + color + '">' +
              '<title>' + _esc(p.project_name || p.project_id) + ' ' + d + ': $' + cost.toFixed(3) + '</title></circle>';
    });
  });
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
  legend.innerHTML = projects.map(function(p, pi) {
    var color = _TREND_COLORS[pi % _TREND_COLORS.length];
    return '<span><span class="trend-legend-dot" style="background:' + color + '"></span>' +
           _esc(p.project_name || p.project_id) + ' $' + (p.total_cost_usd || 0).toFixed(2) + '</span>';
  }).join('');
}

var _dailyData = null;  // { projectDays, nameMap, dates }
var _dailyIdx  = 0;     // index into _dailyData.dates (0 = latest)

function _renderDailyProjectStack(data) {
  if (!data || !data.project_days || !data.days || !data.days.length) return;
  document.getElementById('daily-stack-card').style.display = '';

  // Build a name map: project_id → project_name
  var nameMap = {};
  (data.projects || []).forEach(function(p) { nameMap[p.project_id] = p.project_name || p.project_id; });

  // Collect ALL dates that have any project activity (sorted ascending)
  var dateSet = {};
  Object.keys(data.project_days).forEach(function(pid) {
    Object.keys(data.project_days[pid]).forEach(function(d) { dateSet[d] = true; });
  });
  var dates = Object.keys(dateSet).sort();  // ascending

  _dailyData = { projectDays: data.project_days, nameMap: nameMap, dates: dates };
  _dailyIdx = 0;  // latest day
  _renderDailyPage();
}

document.getElementById('daily-prev').addEventListener('click', function() {
  if (!_dailyData) return;
  if (_dailyIdx < _dailyData.dates.length - 1) { _dailyIdx++; _renderDailyPage(); }
});
document.getElementById('daily-next').addEventListener('click', function() {
  if (!_dailyData) return;
  if (_dailyIdx > 0) { _dailyIdx--; _renderDailyPage(); }
});

function _renderDailyPage() {
  if (!_dailyData || !_dailyData.dates.length) return;
  var dates = _dailyData.dates;
  var date = dates[dates.length - 1 - _dailyIdx];  // reversed: idx 0 = latest
  var pd = _dailyData.projectDays;
  var nameMap = _dailyData.nameMap;

  document.getElementById('daily-date').textContent = date;
  document.getElementById('daily-prev').disabled = _dailyIdx >= dates.length - 1;
  document.getElementById('daily-next').disabled = _dailyIdx <= 0;

  // Collect projects active on this date, sorted by cost desc
  var items = [];
  Object.keys(pd).forEach(function(pid) {
    var entry = pd[pid][date];
    if (!entry) return;
    // Support both old format (number) and new format (object)
    var cost, inp, out, cw, cr;
    if (typeof entry === 'number') {
      cost = entry; inp = out = cw = cr = 0;
    } else {
      cost = entry.cost || 0;
      inp = entry.input_tokens || 0;
      out = entry.output_tokens || 0;
      cw  = entry.cache_creation_tokens || 0;
      cr  = entry.cache_read_tokens || 0;
    }
    if (cost > 0) items.push({ pid: pid, name: nameMap[pid] || pid, cost: cost,
                               inp: inp, out: out, cw: cw, cr: cr });
  });
  items.sort(function(a, b) { return b.cost - a.cost; });

  var el = document.getElementById('daily-project-list');
  if (!items.length) {
    el.innerHTML = '<div style="text-align:center;color:var(--sub);padding:16px;font-size:12px">当天无数据</div>';
    document.getElementById('daily-total').textContent = '';
    return;
  }

  var maxCost = items[0].cost;
  el.innerHTML = items.map(function(it, i) {
    var pct = (it.cost / maxCost * 100).toFixed(1);
    var color = _TREND_COLORS[i % _TREND_COLORS.length];
    var totTok = it.inp + it.out + it.cw + it.cr;
    // Token mini bar
    var segs = [{v:it.inp,c:TOK_COLORS.inp},{v:it.out,c:TOK_COLORS.out},
                {v:it.cw,c:TOK_COLORS.cw},{v:it.cr,c:TOK_COLORS.cr}]
      .map(function(s){return '<div class="tok-seg" style="width:'+(s.v/(totTok||1)*100).toFixed(1)+'%;background:'+s.c+'"></div>';}).join('');
    var tipTok = '输入:'+_fmtNum(it.inp)+' 输出:'+_fmtNum(it.out)+' 缓存写:'+_fmtNum(it.cw)+' 缓存读:'+_fmtNum(it.cr);
    return '<div class="daily-row">' +
      '<div class="daily-name" title="' + _esc(it.name) + '">' + _esc(it.name) + '</div>' +
      '<div style="flex:1;min-width:0">' +
        '<div class="daily-bar-bg"><div class="daily-bar" style="width:' + pct + '%;background:' + color + '"></div></div>' +
        (totTok ? '<div class="tok-bar" style="height:4px;min-width:40px;margin-top:3px" title="'+tipTok+'">' + segs + '</div>' : '') +
      '</div>' +
      '<div class="daily-cost">' + _fmtCost(it.cost) +
        (totTok ? '<div style="font-size:10px;color:var(--sub);font-family:var(--mono)">'+_fmtNum(totTok)+'</div>' : '') +
      '</div></div>';
  }).join('');

  var total = items.reduce(function(s, it) { return s + it.cost; }, 0);
  var totalTok = items.reduce(function(s, it) { return s + it.inp + it.out + it.cw + it.cr; }, 0);
  document.getElementById('daily-total').textContent = '合计: ' + _fmtCost(total) + ' · ' + _fmtNum(totalTok) + ' tokens';
}

function _renderClaudeHeatmap(heatmap) {
  var el = document.getElementById('heatmap-container');
  if (!el) return;
  document.getElementById('heatmap-card').style.display = '';
  var today = new Date();
  today.setHours(0, 0, 0, 0);
  var startDate = new Date(today);
  startDate.setDate(startDate.getDate() - 364 - startDate.getDay());
  var maxHours = 0.001;
  Object.values(heatmap).forEach(function(v) { maxHours = Math.max(maxHours, v.hours || 0); });
  var weeks = [], cur = new Date(startDate), monthLabels = [];
  while (cur <= today) {
    var week = [], startOfWeek = new Date(cur);
    for (var dow = 0; dow < 7; dow++) {
      var dateStr = cur.getFullYear()+'-'+String(cur.getMonth()+1).padStart(2,'0')+'-'+String(cur.getDate()).padStart(2,'0');
      var entry = heatmap[dateStr] || { hours: 0, sessions: 0 };
      var intensity = Math.min(1, (entry.hours || 0) / Math.max(maxHours * 0.8, 0.001));
      week.push({ date: dateStr, hours: entry.hours, sessions: entry.sessions, intensity: intensity, future: cur > today });
      cur.setDate(cur.getDate() + 1);
    }
    var m = startOfWeek.toLocaleString('zh', { month: 'short' });
    monthLabels.push(startOfWeek.getDate() <= 7 ? m : '');
    weeks.push(week);
  }
  function _ic(v) {
    if (v <= 0) return 'rgba(255,255,255,.05)';
    return 'rgb(' + Math.round(92*v) + ',' + Math.round(208*(0.3+0.7*v)) + ',' + Math.round(138*v) + ')';
  }
  var gridHtml = weeks.map(function(week) {
    return '<div class="heatmap-week">' + week.map(function(day) {
      if (day.future) return '<div class="heatmap-day" style="background:transparent"></div>';
      var tip = day.date + ': ' + (day.hours||0).toFixed(1) + 'h, ' + (day.sessions||0) + ' sessions';
      return '<div class="heatmap-day" style="background:' + _ic(day.intensity) + '" title="' + tip + '"></div>';
    }).join('') + '</div>';
  }).join('');
  el.innerHTML = '<div class="heatmap-grid">' + gridHtml + '</div>' +
    '<div class="heatmap-labels">' + monthLabels.map(function(m) {
      return '<div class="heatmap-month-label">' + (m||'') + '</div>';
    }).join('') + '</div>';
}

function _renderClaudeRanking(projects) {
  var el = document.getElementById('ranking-list');
  if (!projects || !projects.length) { el.innerHTML = '<div class="empty-state" style="padding:20px">暂无数据</div>'; return; }
  var maxH = Math.max.apply(null, projects.map(function(p) { return p.total_hours||0; }).concat([0.001]));
  el.innerHTML = projects.map(function(p) {
    var pct = ((p.total_hours||0) / maxH * 100).toFixed(1);
    var name = _esc(p.project_name || p.project_id);
    return '<div class="rank-row">' +
      '<div class="rank-name" title="' + name + '">' + name + '</div>' +
      '<div class="rank-bar-bg"><div class="rank-bar" style="width:' + pct + '%"></div></div>' +
      '<div class="rank-hours">' + (p.total_hours||0).toFixed(1) + 'h</div>' +
      '<div class="rank-cost">$' + (p.total_cost_usd||0).toFixed(2) + '</div>' +
      '</div>';
  }).join('');
}

// ── Codex mode ──────────────────────────────────────────────────────────
async function loadCodexStats() {
  _clearAgg();
  try {
    const res = await fetch('/api/codex-stats', { headers: _authHeaders() });
    if (res.status === 401) { openLoginModal(loadCodexStats); return; }
    const stats = res.ok ? await res.json() : null;
    if (!stats || !stats.session_count_30d) {
      document.getElementById('summary-row').innerHTML = '<div class="empty-state">暂无 Codex 数据</div>';
      return;
    }
    var costStr = '$' + (stats.estimated_cost_usd || 0).toFixed(1);
    document.getElementById('summary-row').innerHTML =
      '<div class="summary-card"><div class="summary-val" style="color:var(--green)">' + costStr + '</div><div class="summary-lbl">预估费用</div></div>' +
      '<div class="summary-card"><div class="summary-val" style="color:var(--green)">' + (stats.session_count_30d||0) + '</div><div class="summary-lbl">30天会话</div></div>' +
      '<div class="summary-card"><div class="summary-val" style="color:var(--green)">' + _fmtNum(stats.input_tokens||0) + '</div><div class="summary-lbl">输入 Tokens</div></div>' +
      '<div class="summary-card"><div class="summary-val" style="color:var(--green)">' + _fmtNum(stats.output_tokens||0) + '</div><div class="summary-lbl">输出 Tokens</div></div>';
    _renderCodexRanking(stats);
    requestAnimationFrame(function() { _renderCodexHeatmap(stats.heatmap || {}); });
    _renderCodexTrend(stats);
  } catch(e) { console.warn('codex stats error:', e); }
}

function _renderCodexHeatmap(heatmap) {
  var el = document.getElementById('heatmap-container');
  if (!el || !Object.keys(heatmap).length) return;
  document.getElementById('heatmap-card').style.display = '';
  var today = new Date();
  today.setHours(0, 0, 0, 0);
  var startDate = new Date(today);
  startDate.setDate(startDate.getDate() - 364 - startDate.getDay());
  var maxSess = 0.001;
  Object.values(heatmap).forEach(function(v) { maxSess = Math.max(maxSess, v.sessions || 0); });
  var weeks = [], cur = new Date(startDate), monthLabels = [];
  while (cur <= today) {
    var week = [], startOfWeek = new Date(cur);
    for (var dow = 0; dow < 7; dow++) {
      var dateStr = cur.getFullYear()+'-'+String(cur.getMonth()+1).padStart(2,'0')+'-'+String(cur.getDate()).padStart(2,'0');
      var entry = heatmap[dateStr] || { sessions: 0 };
      var intensity = Math.min(1, (entry.sessions||0) / Math.max(maxSess*0.8, 0.001));
      week.push({ date: dateStr, sessions: entry.sessions, intensity: intensity, future: cur > today });
      cur.setDate(cur.getDate() + 1);
    }
    var m = startOfWeek.toLocaleString('zh', { month: 'short' });
    monthLabels.push(startOfWeek.getDate() <= 7 ? m : '');
    weeks.push(week);
  }
  function _ic(v) {
    if (v <= 0) return 'rgba(255,255,255,.05)';
    return 'rgb(' + Math.round(34*v) + ',' + Math.round(197*(0.3+0.7*v)) + ',' + Math.round(94*v) + ')';
  }
  var gridHtml = weeks.map(function(week) {
    return '<div class="heatmap-week">' + week.map(function(day) {
      if (day.future) return '<div class="heatmap-day" style="background:transparent"></div>';
      return '<div class="heatmap-day" style="background:' + _ic(day.intensity) + '" title="' + day.date + ': ' + (day.sessions||0) + ' Codex sessions"></div>';
    }).join('') + '</div>';
  }).join('');
  el.innerHTML = '<div class="heatmap-grid">' + gridHtml + '</div>' +
    '<div class="heatmap-labels">' + monthLabels.map(function(m) {
      return '<div class="heatmap-month-label">' + (m||'') + '</div>';
    }).join('') + '</div>';
}

function _renderCodexTrend(stats) {
  var el = document.getElementById('trend-svg');
  var legend = document.getElementById('trend-legend');
  if (!el) return;
  var topList = stats.project_trend || [];
  if (!topList.length) return;
  document.getElementById('trend-card').style.display = '';
  var W = el.parentElement.clientWidth - 32;
  var H = 120;
  el.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  var maxCost = Math.max.apply(null, topList.map(function(p) { return p.total_cost_usd; }).concat([0.001]));
  var PAD = 4;
  var usableW = W - PAD * 2;
  var html = '';
  var TC = ['#5cd08a','#4e9eff','#f0a050','#c792ea','#56b6c2','#e06c75','#98c379','#56b6c2'];
  topList.slice(0, 8).forEach(function(p, i) {
    var barW = Math.max(2, (p.total_cost_usd / maxCost) * (usableW - 30));
    var color = TC[i % TC.length];
    var y = PAD + i * 13;
    var label = (p.project_name || '').toString().slice(0, 14);
    html += '<text x="' + PAD + '" y="' + (y+9) + '" font-size="10" fill="var(--sub)">' + _esc(label) + '</text>';
    html += '<rect x="' + (PAD+30) + '" y="' + y + '" width="' + barW.toFixed(1) + '" height="10" fill="' + color + '" rx="2" opacity="0.8">' +
            '<title>' + _esc(p.project_name) + ': $' + p.total_cost_usd.toFixed(2) + '</title></rect>';
  });
  el.innerHTML = html;
  legend.innerHTML = '<span style="font-size:10px;color:var(--sub)">按费用排序</span>';
}

function _renderCodexRanking(stats) {
  var el = document.getElementById('ranking-list');
  var list = [];
  if (stats.projects) {
    Object.keys(stats.projects).forEach(function(name) {
      var p = stats.projects[name];
      var inp = p.input||0, cached = p.cached||0, out = p.output||0;
      var cost = Math.max(inp-cached,0)*15/1e6 + cached*7.5/1e6 + out*75/1e6;
      list.push({ name: name, sessions: p.sessions||0, cost: cost });
    });
  }
  var unc = stats.unclassified;
  if (unc && unc.sessions > 0) {
    var inp2=unc.input||0, cached2=unc.cached||0, out2=unc.output||0;
    list.push({ name: '（未归类）', sessions: unc.sessions||0, cost: Math.max(inp2-cached2,0)*15/1e6+cached2*7.5/1e6+out2*75/1e6 });
  }
  if (!list.length) { el.innerHTML = '<div class="empty-state" style="padding:20px">暂无数据</div>'; return; }
  list.sort(function(a,b) { return b.cost - a.cost; });
  var maxCost = Math.max.apply(null, list.map(function(p) { return p.cost; }).concat([0.001]));
  el.innerHTML = list.map(function(p) {
    return '<div class="rank-row">' +
      '<div class="rank-name" title="' + _esc(p.name) + '">' + _esc(p.name) + '</div>' +
      '<div class="rank-bar-bg"><div class="rank-bar" style="width:' + (p.cost/maxCost*100).toFixed(1) + '%;background:var(--green)"></div></div>' +
      '<div class="rank-hours">' + p.sessions + ' 会话</div>' +
      '<div class="rank-cost">$' + p.cost.toFixed(1) + '</div></div>';
  }).join('');
  var svg = document.getElementById('chart-hours');
  if (svg) {
    var W=svg.parentElement.clientWidth-32, H=80, maxS=Math.max.apply(null,list.map(function(p){return p.sessions;}).concat([1]));
    svg.setAttribute('viewBox','0 0 '+W+' '+H);
    var barW=Math.max(2,(W/list.length)-1);
    svg.innerHTML=list.map(function(p,i){
      var bh=Math.max(2,(p.sessions/maxS)*(H-16)), x=i*(W/list.length);
      return '<rect x="'+x.toFixed(1)+'" y="'+(H-bh).toFixed(1)+'" width="'+barW.toFixed(1)+'" height="'+bh.toFixed(1)+'" fill="#4e9eff" opacity="0.75" rx="2"><title>'+_esc(p.name)+': '+p.sessions+' 会话</title></rect>';
    }).join('');
  }
  var svg2 = document.getElementById('chart-cost');
  if (svg2) {
    var W2=svg2.parentElement.clientWidth-32, H2=80, maxC2=maxCost;
    svg2.setAttribute('viewBox','0 0 '+W2+' '+H2);
    var barW2=Math.max(2,(W2/list.length)-1);
    svg2.innerHTML=list.map(function(p,i){
      var bh2=Math.max(2,(p.cost/maxC2)*(H2-16)), x2=i*(W2/list.length);
      return '<rect x="'+x2.toFixed(1)+'" y="'+(H2-bh2).toFixed(1)+'" width="'+barW2.toFixed(1)+'" height="'+bh2.toFixed(1)+'" fill="#22c55e" opacity="0.75" rx="2"><title>'+_esc(p.name)+': $'+p.cost.toFixed(2)+'</title></rect>';
    }).join('');
  }
}

// ── Sessions mode ────────────────────────────────────────────────────────
async function loadSessionsData() {
  document.getElementById('sess-summary').innerHTML = '<div style="color:var(--sub);padding:20px;text-align:center">加载中…</div>';
  try {
    const res = await fetch('/api/top-sessions?sort=' + _sessionSort + '&limit=100', { headers: _authHeaders() });
    if (res.status === 401) { openLoginModal(loadSessionsData); return; }
    if (!res.ok) return;
    _sessionData = await res.json();
    _renderSessionsAll(_sessionData);
  } catch(e) { console.warn('sessions error:', e); }
}

async function loadCxSessionsData() {
  document.getElementById('sess-summary').innerHTML = '<div style="color:var(--sub);padding:20px;text-align:center">加载中…</div>';
  try {
    const res = await fetch('/api/top-codex-sessions?sort=' + _cxSessionSort + '&limit=100', { headers: _authHeaders() });
    if (res.status === 401) { openLoginModal(loadCxSessionsData); return; }
    if (!res.ok) return;
    _cxSessionData = await res.json();
    // Codex sessions use different field names — normalize for shared renderer
    _cxSessionData = _cxSessionData.map(function(s) {
      return Object.assign({}, s, {
        cache_creation_tokens: 0,
        cache_read_tokens: s.cached_input_tokens || 0,
      });
    });
    _renderCxSessionsAll(_cxSessionData);
  } catch(e) { console.warn('codex sessions error:', e); }
}

function _cxSessFiltered() {
  if (!_cxSessionFilter) return _cxSessionData;
  return _cxSessionData.filter(function(s) {
    return (s.project_name||'').toLowerCase().indexOf(_cxSessionFilter) >= 0;
  });
}

function _renderCxSessionsAll(data) {
  var filtered = _cxSessFiltered();
  _renderSessSummary(filtered);
  _renderTokenCards(filtered);
  requestAnimationFrame(function() {
    _renderScatter(filtered);
    _renderSessBreakdown(filtered);
    _renderTokenStacks(filtered);
  });
  _renderCxSessTable(filtered);
}

function _sessFiltered() {
  if (!_sessionFilter) return _sessionData;
  return _sessionData.filter(function(s) {
    return (s.project_name||'').toLowerCase().indexOf(_sessionFilter) >= 0;
  });
}

function _renderSessionsAll(data) {
  var filtered = _sessFiltered();
  _renderSessSummary(filtered);
  _renderTokenCards(filtered);
  requestAnimationFrame(function() {
    _renderScatter(filtered);
    _renderSessBreakdown(filtered);
    _renderTokenStacks(filtered);
  });
  _renderSessTable(filtered);
}

function _renderSessSummary(data) {
  var totalCost=0, totalHours=0;
  data.forEach(function(s) { totalCost+=s.estimated_cost_usd; totalHours+=s.active_hours; });
  var avgCost = data.length ? totalCost/data.length : 0;
  document.getElementById('sess-summary').innerHTML = [
    [data.length, '会话数'],
    [_fmtCost(totalCost), '总花费'],
    [totalHours.toFixed(1)+'h', '总时长'],
    [_fmtCost(avgCost), '均价/会话'],
  ].map(function(c) {
    return '<div class="summary-card"><div class="summary-val">' + c[0] + '</div><div class="summary-lbl">' + c[1] + '</div></div>';
  }).join('');
}

function _renderTokenCards(data) {
  var totInp=0, totOut=0, totCW=0, totCR=0;
  data.forEach(function(s) { totInp+=s.input_tokens; totOut+=s.output_tokens; totCW+=s.cache_creation_tokens; totCR+=s.cache_read_tokens; });
  var cInp=totInp*_CL_PRICE_IN, cOut=totOut*_CL_PRICE_OUT, cCW=totCW*_CL_PRICE_CACHE_W, cCR=totCR*_CL_PRICE_CACHE_R;
  var totalCost=cInp+cOut+cCW+cCR||1;
  function _card(label, color, total, cost) {
    return '<div class="token-card">' +
      '<div class="token-label"><span class="token-dot" style="background:'+color+'"></span>' + label +
        '<span class="token-pct" style="color:'+color+'">' + (cost/totalCost*100).toFixed(1) + '%</span></div>' +
      '<div class="token-val">' + _fmtNum(total) + '</div>' +
      '<div class="token-cost">' + _fmtCost(cost) + ' · $' + (total?(cost/total*1e6).toFixed(2):'0') + '/M</div>' +
      '</div>';
  }
  document.getElementById('token-cards').innerHTML =
    _card('输入 (上传)', TOK_COLORS.inp, totInp, cInp) +
    _card('输出 (下载)', TOK_COLORS.out, totOut, cOut) +
    _card('缓存写入',   TOK_COLORS.cw,  totCW,  cCW) +
    _card('缓存读取',   TOK_COLORS.cr,  totCR,  cCR);
}

function _renderScatter(data) {
  var svg = document.getElementById('scatter-svg');
  if (!svg || !data.length) return;
  var W = svg.parentElement.clientWidth - 32;
  var H = 200;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  var PAD=40;
  var maxCost  = Math.max.apply(null, data.map(function(s){return s.estimated_cost_usd;}).concat([1]));
  var maxHours = Math.max.apply(null, data.map(function(s){return s.active_hours;}).concat([1]));
  var html = '';
  html += '<line x1="'+PAD+'" y1="'+(H-PAD)+'" x2="'+(W-10)+'" y2="'+(H-PAD)+'" stroke="var(--border)" stroke-width="1"/>';
  html += '<line x1="'+PAD+'" y1="10" x2="'+PAD+'" y2="'+(H-PAD)+'" stroke="var(--border)" stroke-width="1"/>';
  html += '<text x="'+(W/2)+'" y="'+(H-5)+'" text-anchor="middle" font-size="10" fill="var(--sub)">时长 (h)</text>';
  html += '<text x="12" y="'+(H/2-20)+'" font-size="10" fill="var(--sub)" transform="rotate(-90,12,'+(H/2-20)+')">花费 ($)</text>';
  var projects={};
  var palette=['#5cd08a','#4e9eff','#f0a050','#c792ea','#56b6c2','#e06c75','#98c379','#d19a66','#61afef','#be5046'];
  data.forEach(function(s){if(!projects[s.project_name])projects[s.project_name]=Object.keys(projects).length;});
  data.forEach(function(s) {
    var x=PAD+(s.active_hours/maxHours)*(W-PAD-10);
    var y=(H-PAD)-(s.estimated_cost_usd/maxCost)*(H-PAD-10);
    var r=Math.min(12,Math.max(3,Math.sqrt(s.messages)*0.8));
    var color=palette[projects[s.project_name]%palette.length];
    var tip=_esc(s.project_name)+'\n'+(s.task_summary||'').slice(0,60)+'\n时长: '+s.active_hours+'h  花费: $'+s.estimated_cost_usd.toFixed(2)+'\n消息: '+s.messages;
    html+='<circle cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="'+r.toFixed(1)+'" fill="'+color+'" opacity="0.6" stroke="'+color+'" stroke-width="0.5"><title>'+tip+'</title></circle>';
  });
  svg.innerHTML = html;
}

function _renderSessBreakdown(data) {
  var byProject={};
  data.forEach(function(s){
    var n=s.project_name||s.project_id;
    if(!byProject[n]) byProject[n]={cost:0,hours:0};
    byProject[n].cost+=s.estimated_cost_usd; byProject[n].hours+=s.active_hours;
  });
  var list=Object.keys(byProject).map(function(k){return{name:k,cost:byProject[k].cost,hours:byProject[k].hours};});
  list.sort(function(a,b){return b.cost-a.cost;});
  var maxC=list.length?list[0].cost:1;
  document.getElementById('breakdown-cost').innerHTML='<div class="chart-title">按项目花费</div>'+
    list.slice(0,12).map(function(p){
      return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
        '<div style="width:90px;font-size:11px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+_esc(p.name)+'">'+_esc(p.name)+'</div>' +
        '<div style="flex:1;background:rgba(255,255,255,.06);border-radius:3px;height:8px"><div style="width:'+(p.cost/maxC*100).toFixed(1)+'%;background:#4e9eff;border-radius:3px;height:8px"></div></div>' +
        '<div style="width:60px;font-size:11px;color:var(--blue,#4e9eff);text-align:right">'+_fmtCost(p.cost)+'</div></div>';
    }).join('');
  var listH=list.slice().sort(function(a,b){return b.hours-a.hours;}); var maxH=listH.length?listH[0].hours:1;
  document.getElementById('breakdown-hours').innerHTML='<div class="chart-title">按项目时长</div>'+
    listH.slice(0,12).map(function(p){
      return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
        '<div style="width:90px;font-size:11px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+_esc(p.name)+'">'+_esc(p.name)+'</div>' +
        '<div style="flex:1;background:rgba(255,255,255,.06);border-radius:3px;height:8px"><div style="width:'+(p.hours/maxH*100).toFixed(1)+'%;background:#5cd08a;border-radius:3px;height:8px"></div></div>' +
        '<div style="width:60px;font-size:11px;color:var(--green);text-align:right">'+p.hours.toFixed(1)+'h</div></div>';
    }).join('');
}

function _renderTokenStacks(data) {
  var byProject={};
  data.forEach(function(s){
    var n=s.project_name||s.project_id;
    if(!byProject[n]) byProject[n]={inp:0,out:0,cw:0,cr:0,cost:0};
    byProject[n].inp+=s.input_tokens; byProject[n].out+=s.output_tokens;
    byProject[n].cw+=s.cache_creation_tokens; byProject[n].cr+=s.cache_read_tokens;
    byProject[n].cost+=s.estimated_cost_usd;
  });
  var list=Object.keys(byProject).map(function(k){
    var p=byProject[k]; return{name:k,inp:p.inp,out:p.out,cw:p.cw,cr:p.cr,total:p.inp+p.out+p.cw+p.cr,cost:p.cost};
  }).sort(function(a,b){return b.cost-a.cost;}).slice(0,12);
  var el=document.getElementById('token-stacks');
  el.innerHTML=list.map(function(p){
    var tot=p.total||1;
    var segs=[{v:p.inp,c:TOK_COLORS.inp},{v:p.out,c:TOK_COLORS.out},{v:p.cw,c:TOK_COLORS.cw},{v:p.cr,c:TOK_COLORS.cr}]
      .map(function(seg){return '<div class="stack-seg" style="width:'+(seg.v/tot*100).toFixed(1)+'%;background:'+seg.c+'"></div>';}).join('');
    return '<div class="token-stack-row" title="输入:'+_fmtNum(p.inp)+'  输出:'+_fmtNum(p.out)+'  缓存写:'+_fmtNum(p.cw)+'  缓存读:'+_fmtNum(p.cr)+'">' +
      '<div class="stack-label" title="'+_esc(p.name)+'">'+_esc(p.name)+'</div>' +
      '<div class="stack-bar">'+segs+'</div>' +
      '<div class="stack-total">'+_fmtNum(p.total)+'</div></div>';
  }).join('') +
  '<div style="display:flex;gap:16px;margin-top:10px;font-size:11px;color:var(--sub)">' +
    ['输入','输出','缓存写','缓存读'].map(function(l,i){
      var c=[TOK_COLORS.inp,TOK_COLORS.out,TOK_COLORS.cw,TOK_COLORS.cr][i];
      return '<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:'+c+';margin-right:4px"></span>'+l+'</span>';
    }).join('')+'</div>';
}

function _tokMiniBar(s) {
  var tot=(s.input_tokens+s.output_tokens+s.cache_creation_tokens+s.cache_read_tokens)||1;
  var segs=[
    {v:s.input_tokens,c:TOK_COLORS.inp},{v:s.output_tokens,c:TOK_COLORS.out},
    {v:s.cache_creation_tokens,c:TOK_COLORS.cw},{v:s.cache_read_tokens,c:TOK_COLORS.cr},
  ].map(function(seg){return '<div class="tok-seg" style="width:'+(seg.v/tot*100).toFixed(1)+'%;background:'+seg.c+'"></div>';}).join('');
  var tip='输入:'+_fmtNum(s.input_tokens)+'  输出:'+_fmtNum(s.output_tokens)+'  缓存写:'+_fmtNum(s.cache_creation_tokens)+'  缓存读:'+_fmtNum(s.cache_read_tokens);
  return '<div class="tok-bar" title="'+tip+'">'+segs+'</div>';
}

function _renderSessTable(data) {
  var el = document.getElementById('sess-table-body');
  if (!data.length) { el.innerHTML = '<tr><td colspan="8" class="empty-state">暂无数据</td></tr>'; return; }
  el.innerHTML = data.map(function(s, i) {
    var cc=_costClass(s.estimated_cost_usd), hc=s.active_hours>=20?'hours-hi':'';
    var totTok=s.input_tokens+s.output_tokens+s.cache_creation_tokens+s.cache_read_tokens;
    var onclick="openSessionTurns('"+_esc(s.session_id).replace(/'/g,"\\'")+"','"+_esc(s.project_name).replace(/'/g,"\\'")+"','"+s.date+"',"+s.estimated_cost_usd+")";
    return '<tr style="cursor:pointer" onclick="'+onclick+'" title="点击查看任务明细">' +
      '<td class="col-rank">'+(i+1)+'</td>' +
      '<td class="col-project" title="'+_esc(s.project_name)+'">'+_esc(s.project_name)+'</td>' +
      '<td class="col-task" title="'+_esc(s.task_summary||'')+'">'+_esc(s.task_summary||'-')+'</td>' +
      '<td class="col-num">'+s.date+'</td>' +
      '<td class="col-num '+cc+'">'+_fmtCost(s.estimated_cost_usd)+'</td>' +
      '<td class="col-num '+hc+'">'+s.active_hours.toFixed(1)+'h</td>' +
      '<td style="min-width:80px;padding:8px 6px">'+_tokMiniBar(s)+
        '<div style="font-size:10px;color:var(--sub);margin-top:2px;font-family:var(--mono)">'+_fmtNum(totTok)+'</div></td>' +
      '<td class="col-num" style="color:var(--sub)">'+s.messages+'</td>' +
      '</tr>';
  }).join('');
}

function _renderCxSessTable(data) {
  var el = document.getElementById('sess-table-body');
  if (!data.length) { el.innerHTML = '<tr><td colspan="7" class="empty-state">暂无数据</td></tr>'; return; }
  el.innerHTML = data.map(function(s, i) {
    var cc=_costClass(s.estimated_cost_usd), hc=s.active_hours>=20?'hours-hi':'';
    var totTok=(s.input_tokens||0)+(s.output_tokens||0)+(s.reasoning_output_tokens||0);
    var onclick="openCxSessionTurns('"+_esc(s.session_id).replace(/'/g,"\\'")+"','"+_esc(s.project_name).replace(/'/g,"\\'")+"','"+s.date+"',"+s.estimated_cost_usd+")";
    return '<tr style="cursor:pointer" onclick="'+onclick+'" title="点击查看任务明细">' +
      '<td class="col-rank">'+(i+1)+'</td>' +
      '<td class="col-project" title="'+_esc(s.project_name)+'">'+_esc(s.project_name)+'</td>' +
      '<td class="col-task" title="'+_esc(s.first_message||'')+'">'+_esc(s.first_message||'-')+'</td>' +
      '<td class="col-num">'+s.date+'</td>' +
      '<td class="col-num '+cc+'">'+_fmtCost(s.estimated_cost_usd)+'</td>' +
      '<td class="col-num '+hc+'">'+s.active_hours.toFixed(1)+'h</td>' +
      '<td style="min-width:80px;padding:8px 6px">'+_tokMiniBar(s)+
        '<div style="font-size:10px;color:var(--sub);margin-top:2px;font-family:var(--mono)">'+_fmtNum(totTok)+'</div></td>' +
      '</tr>';
  }).join('');
}

// ── Session turns modal ──────────────────────────────────────────────────
async function openSessionTurns(sessionId, projectName, date, totalCost) {
  var overlay = document.getElementById('modal-overlay');
  var box = document.getElementById('modal-box');
  overlay.style.display = 'flex';
  box.innerHTML = '<div style="text-align:center;padding:40px;color:var(--sub)">加载中…</div>';
  try {
    var res = await fetch('/api/session/'+sessionId+'/turns', { headers: _authHeaders() });
    if (res.status === 401) { overlay.style.display='none'; openLoginModal(function(){}); return; }
    var turns = res.ok ? await res.json() : [];
    if (!turns.length) {
      box.innerHTML = '<button class="modal-close" onclick="closeModal()">✕</button>' +
        '<div class="modal-title">'+_esc(projectName)+' · '+date+'</div>' +
        '<div class="empty-state">暂无任务明细（session 文件可能不在本机）</div>';
      return;
    }
    var maxCost = turns[0].estimated_cost_usd || 0.0001;
    var rows = turns.map(function(t, i) {
      var tot=t.input_tokens+t.output_tokens+t.cache_creation_tokens+t.cache_read_tokens;
      var isInherited=t.label!==t.raw_label;
      var cc=_costClass(t.estimated_cost_usd);
      var segs=[{v:t.input_tokens,c:TOK_COLORS.inp},{v:t.output_tokens,c:TOK_COLORS.out},
                {v:t.cache_creation_tokens,c:TOK_COLORS.cw},{v:t.cache_read_tokens,c:TOK_COLORS.cr}]
        .map(function(seg){return '<div class="tok-seg" style="width:'+(seg.v/(tot||1)*100).toFixed(1)+'%;background:'+seg.c+'"></div>';}).join('');
      var tipTok='输入:'+_fmtNum(t.input_tokens)+'  输出:'+_fmtNum(t.output_tokens)+'  缓存写:'+_fmtNum(t.cache_creation_tokens)+'  缓存读:'+_fmtNum(t.cache_read_tokens);
      return '<div class="turn-row">' +
        '<div class="turn-rank">'+(i+1)+'</div>' +
        '<div class="turn-body">' +
          '<div class="turn-label'+(isInherited?' inherited':'')+'" title="'+_esc(t.label)+'">'+_esc(t.label.slice(0,100))+'</div>' +
          (isInherited&&t.raw_label?'<div class="turn-raw">实际输入: '+_esc(t.raw_label.slice(0,80))+'</div>':'') +
          '<div class="turn-tok-bar"><div class="tok-bar" style="height:6px;min-width:100px" title="'+tipTok+'">'+segs+'</div></div>' +
          '<div class="turn-meta">' +
            '<span style="color:#4e9eff">↑'+_fmtNum(t.input_tokens)+'</span>' +
            '<span style="color:#f0a050">↓'+_fmtNum(t.output_tokens)+'</span>' +
            '<span style="color:#fbbf24">W'+_fmtNum(t.cache_creation_tokens)+'</span>' +
            '<span style="color:#5cd08a">R'+_fmtNum(t.cache_read_tokens)+'</span>' +
            '<span>'+_fmtNum(tot)+' total</span>' +
          '</div>' +
        '</div>' +
        '<div class="turn-cost '+cc+'">'+_fmtCost(t.estimated_cost_usd)+'</div>' +
        '</div>';
    }).join('');
    box.innerHTML =
      '<button class="modal-close" onclick="closeModal()">✕</button>' +
      '<div class="modal-title">'+_esc(projectName)+' · '+date+' · '+_fmtCost(totalCost)+'</div>' +
      '<div class="modal-sub">按任务花费排序 · 共 '+turns.length+' 个任务轮次</div>' +
      '<div style="display:flex;gap:12px;margin-bottom:12px;font-size:10px;color:var(--sub)">' +
        ['↑输入','↓输出','W缓存写','R缓存读'].map(function(l,i){
          var c=[TOK_COLORS.inp,TOK_COLORS.out,TOK_COLORS.cw,TOK_COLORS.cr][i];
          return '<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:'+c+';margin-right:3px"></span>'+l+'</span>';
        }).join('')+
        '<span style="margin-left:8px;font-style:italic">斜体 = 确认词，继承上一任务</span>' +
      '</div>' + rows;
  } catch(e) {
    box.innerHTML = '<button class="modal-close" onclick="closeModal()">✕</button>' +
      '<div class="empty-state">加载失败</div>';
  }
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}

async function openCxSessionTurns(sessionPath, projectName, date, totalCost) {
  var overlay = document.getElementById('modal-overlay');
  var box = document.getElementById('modal-box');
  overlay.style.display = 'flex';
  box.innerHTML = '<div style="text-align:center;padding:40px;color:var(--sub)">加载中…</div>';
  try {
    var res = await fetch('/api/codex-session/turns?path=' + encodeURIComponent(sessionPath), { headers: _authHeaders() });
    if (res.status === 401) { overlay.style.display='none'; openLoginModal(function(){}); return; }
    var turns = res.ok ? await res.json() : [];
    if (!turns.length) {
      box.innerHTML = '<button class="modal-close" onclick="closeModal()">✕</button>' +
        '<div class="modal-title">'+_esc(projectName)+' · '+date+'</div>' +
        '<div class="empty-state">暂无任务明细</div>';
      return;
    }
    var maxCost = turns[0].estimated_cost_usd || 0.0001;
    var rows = turns.map(function(t, i) {
      var inp=t.input_tokens, out=t.output_tokens, cach=t.cached_input_tokens||0, reas=t.reasoning_tokens||0;
      var tot = inp + out + reas;
      var isInherited = t.label !== t.raw_label;
      var cc = _costClass(t.estimated_cost_usd);
      // Codex: inp(non-cached)=blue, cached=green, out=orange, reasoning=purple
      var nonCach = Math.max(inp - cach, 0);
      var segs = [
        {v:nonCach, c:'#4e9eff'}, {v:cach, c:'#5cd08a'},
        {v:out, c:'#f0a050'}, {v:reas, c:'#c792ea'}
      ].map(function(seg){
        return '<div class="tok-seg" style="width:'+(seg.v/(tot||1)*100).toFixed(1)+'%;background:'+seg.c+'"></div>';
      }).join('');
      var tipTok = '输入:'+_fmtNum(inp)+'  缓存:'+_fmtNum(cach)+'  输出:'+_fmtNum(out)+'  推理:'+_fmtNum(reas);
      return '<div class="turn-row">' +
        '<div class="turn-rank">'+(i+1)+'</div>' +
        '<div class="turn-body">' +
          '<div class="turn-label'+(isInherited?' inherited':'')+'" title="'+_esc(t.label)+'">'+_esc(t.label.slice(0,100))+'</div>' +
          (isInherited&&t.raw_label?'<div class="turn-raw">实际输入: '+_esc(t.raw_label.slice(0,80))+'</div>':'') +
          '<div class="turn-tok-bar"><div class="tok-bar" style="height:6px;min-width:100px" title="'+tipTok+'">'+segs+'</div></div>' +
          '<div class="turn-meta">' +
            '<span style="color:#4e9eff">↑'+_fmtNum(inp)+'</span>' +
            '<span style="color:#f0a050">↓'+_fmtNum(out)+'</span>' +
            (cach?'<span style="color:#5cd08a">缓存'+_fmtNum(cach)+'</span>':'') +
            (reas?'<span style="color:#c792ea">推理'+_fmtNum(reas)+'</span>':'') +
          '</div>' +
        '</div>' +
        '<div class="turn-cost '+cc+'">'+_fmtCost(t.estimated_cost_usd)+'</div>' +
        '</div>';
    }).join('');
    box.innerHTML =
      '<button class="modal-close" onclick="closeModal()">✕</button>' +
      '<div class="modal-title">'+_esc(projectName)+' · '+date+'</div>' +
      '<div class="modal-sub">Codex 会话 · 总花费 '+_fmtCost(totalCost)+'</div>' +
      '<div>' + rows + '</div>';
  } catch(e) {
    box.innerHTML = '<button class="modal-close" onclick="closeModal()">✕</button>' +
      '<div class="empty-state">加载失败</div>';
  }
}
document.getElementById('modal-overlay').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

// ── GitHub Trending ──────────────────────────────────────────────────────
var _ghCache = {};
var _ghLoaded = false;
var _ghLangColors = {Python:'#3572A5',JavaScript:'#f1e05a',TypeScript:'#3178c6',Go:'#00ADD8',
  Rust:'#dea584',Java:'#b07219',Ruby:'#701516',C:'#555555','C++':'#f34b7d','C#':'#178600',
  Swift:'#F05138',Kotlin:'#A97BFF',Dart:'#00B4AB',PHP:'#4F5D95',Shell:'#89e051',Lua:'#000080',
  Zig:'#ec915c',Vue:'#41b883',HTML:'#e34c26',CSS:'#563d7c',Jupyter:'#DA5B0B',Scala:'#c22d40'};

async function loadGHTrending(period) {
  ['daily','weekly','monthly'].forEach(function(p) {
    document.getElementById('gh-' + p).classList.toggle('active', p === period);
  });
  var grid = document.getElementById('gh-grid');
  if (_ghCache[period]) { _renderGH(_ghCache[period]); return; }
  grid.innerHTML = '<div style="color:var(--sub);font-size:12px;padding:12px">加载中…</div>';
  try {
    var res = await fetch('/api/trending?period=' + period);
    if (!res.ok) throw new Error(res.status);
    var items = await res.json();
    _ghCache[period] = items || [];
    _ghLoaded = true;
    _renderGH(_ghCache[period]);
  } catch(e) {
    grid.innerHTML = '<div style="color:var(--sub);font-size:12px;padding:12px">加载失败</div>';
  }
}

function _renderGH(repos) {
  var grid = document.getElementById('gh-grid');
  if (!repos.length) { grid.innerHTML = '<div style="color:var(--sub)">暂无数据</div>'; return; }
  grid.innerHTML = repos.map(function(r) {
    var lang = r.language || '';
    var dot = lang ? '<span class="gh-lang-dot" style="background:' + (_ghLangColors[lang]||'#555') + '"></span>' : '';
    var desc = r.description ? _esc(r.description.slice(0,80)) + (r.description.length>80?'…':'') : '暂无描述';
    var stars = r.stargazers_count >= 1000 ? (r.stargazers_count/1000).toFixed(1)+'k' : r.stargazers_count;
    var forks = r.forks_count >= 1000 ? (r.forks_count/1000).toFixed(1)+'k' : r.forks_count;
    return '<div class="gh-card" onclick="window.open(\'' + _esc(r.html_url) + '\',\'_blank\')">' +
      '<div class="gh-card-title">' + _esc(r.full_name) + '</div>' +
      '<div class="gh-card-desc">' + desc + '</div>' +
      '<div class="gh-card-meta">' +
        (lang ? '<span>' + dot + _esc(lang) + '</span>' : '') +
        '<span>★ ' + stars + '</span>' +
        '<span>⑂ ' + forks + '</span>' +
      '</div></div>';
  }).join('');
}

// ── Init ────────────────────────────────────────────────────────────────
_initAuth().then(function() {
  setTool('claude');
});
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
<div class="ctrl-bar">
  <div class="mode-toggle">
    <button class="stats-btn active" id="btn-tool-claude">Claude</button>
    <button class="stats-btn"        id="btn-tool-codex">Codex</button>
    <button class="stats-btn"        id="btn-tool-github">GitHub</button>
  </div>
</div>
<div class="ctrl-subbar" id="claude-subbar">
  <div class="view-toggle">
    <button class="stats-btn active" id="btn-view-overview">总览</button>
    <button class="stats-btn"        id="btn-view-sessions">会话</button>
  </div>
  <div class="ctrl-sep"></div>
  <div class="range-toggle" id="range-group">
    <button class="stats-btn active" id="btn-30d">日 · 30天</button>
    <button class="stats-btn"        id="btn-12w">周 · 12周</button>
  </div>
  <div id="sess-controls" style="display:none">
    <div class="sort-toggle" style="display:flex;gap:4px">
      <button class="stats-btn active" id="btn-sess-cost">按花费</button>
      <button class="stats-btn"        id="btn-sess-hours">按时长</button>
    </div>
    <input type="text" class="filter-input" id="sess-filter" placeholder="筛选项目…" style="margin-left:8px">
  </div>
</div>
<div class="ctrl-subbar" id="codex-subbar" style="display:none">
  <div class="view-toggle">
    <button class="stats-btn active" id="btn-cx-view-overview">总览</button>
    <button class="stats-btn"        id="btn-cx-view-sessions">会话</button>
  </div>
  <div class="ctrl-sep"></div>
  <div id="cx-sess-controls" style="display:none">
    <div class="sort-toggle" style="display:flex;gap:4px">
      <button class="stats-btn active" id="btn-cx-sess-cost">按花费</button>
      <button class="stats-btn"        id="btn-cx-sess-hours">按时长</button>
    </div>
    <input type="text" class="filter-input" id="cx-sess-filter" placeholder="筛选项目…" style="margin-left:8px">
  </div>
</div>

<!-- Aggregate section (Claude / Codex) -->
<div id="agg-section">
  <div class="stats-main">
    <div id="summary-row" class="summary-row"></div>
    <div class="chart-row">
      <div class="chart-card">
        <div class="chart-title">会话数 / 项目</div>
        <svg id="chart-hours" class="chart-svg" height="80"></svg>
      </div>
      <div class="chart-card">
        <div class="chart-title">费用 / 项目</div>
        <svg id="chart-cost" class="chart-svg" height="80"></svg>
      </div>
    </div>
    <div class="trend-card" id="trend-card" style="display:none">
      <div class="chart-title">Top 5 项目费用趋势</div>
      <svg id="trend-svg" class="chart-svg" height="120"></svg>
      <div class="trend-legend" id="trend-legend"></div>
    </div>
    <div class="trend-card" id="daily-stack-card" style="display:none">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
        <div class="chart-title" style="margin-bottom:0">每日项目开销</div>
        <div style="margin-left:auto;display:flex;align-items:center;gap:6px">
          <button class="stats-btn" id="daily-prev" style="padding:3px 8px">←</button>
          <span id="daily-date" style="font-size:13px;font-weight:600;color:var(--text);min-width:90px;text-align:center"></span>
          <button class="stats-btn" id="daily-next" style="padding:3px 8px">→</button>
        </div>
      </div>
      <div id="daily-project-list"></div>
      <div id="daily-total" style="text-align:right;font-size:12px;color:var(--sub);margin-top:10px"></div>
      <div class="trend-legend" style="margin-top:8px">
        <span><span class="trend-legend-dot" style="background:#4e9eff"></span>输入</span>
        <span><span class="trend-legend-dot" style="background:#f0a050"></span>输出</span>
        <span><span class="trend-legend-dot" style="background:#fbbf24"></span>缓存写入</span>
        <span><span class="trend-legend-dot" style="background:#5cd08a"></span>缓存读取</span>
      </div>
    </div>
    <div class="heatmap-card" id="heatmap-card" style="display:none">
      <div class="chart-title" style="margin-bottom:8px">活动热力图（近一年）</div>
      <div id="heatmap-container" style="min-height:80px"></div>
    </div>
    <div class="ranking-card">
      <div class="ranking-title">项目排行</div>
      <div id="ranking-list"></div>
    </div>
  </div>
</div>

<!-- Sessions section -->
<div id="sess-section" style="display:none">
  <div class="stats-main">
    <div id="sess-summary" class="summary-row"></div>
    <div id="token-cards" class="token-row"></div>
    <div class="scatter-card">
      <div class="chart-title">花费 vs 时长（气泡大小 = 消息数）</div>
      <svg id="scatter-svg" style="width:100%;overflow:visible" height="200"></svg>
    </div>
    <div class="chart-row">
      <div class="chart-card" id="breakdown-cost"></div>
      <div class="chart-card" id="breakdown-hours"></div>
    </div>
    <div class="token-stack-card">
      <div class="chart-title">按项目 Token 构成</div>
      <div id="token-stacks"></div>
    </div>
    <div class="table-card">
      <div class="chart-title">会话明细</div>
      <table class="session-table">
        <thead>
          <tr>
            <th class="col-rank">#</th>
            <th>项目</th>
            <th>任务</th>
            <th class="col-num">日期</th>
            <th class="col-num">花费</th>
            <th class="col-num">时长</th>
            <th>Tokens</th>
            <th class="col-num">消息</th>
          </tr>
        </thead>
        <tbody id="sess-table-body"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- GitHub Trending section -->
<div id="github-section" style="display:none">
  <div class="stats-main">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <div style="font-size:14px;font-weight:600;color:var(--text)">GitHub 热门项目</div>
      <div style="margin-left:auto;display:flex;gap:4px" id="gh-period-btns">
        <button class="stats-btn" id="gh-daily" onclick="loadGHTrending('daily')">今日</button>
        <button class="stats-btn active" id="gh-weekly" onclick="loadGHTrending('weekly')">本周</button>
        <button class="stats-btn" id="gh-monthly" onclick="loadGHTrending('monthly')">本月</button>
      </div>
    </div>
    <div id="gh-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px">
      <div style="color:var(--sub);font-size:12px;padding:12px">加载中…</div>
    </div>
  </div>
</div>

<div class="modal-overlay" id="modal-overlay" style="display:none">
  <div class="modal-box" id="modal-box"></div>
</div>

"""
        + _overlays + "\n\n"
        + "<script>\n"
        + _tb_js + "\n"
        + page_js
        + "</script>\n</body>\n</html>\n"
    )
