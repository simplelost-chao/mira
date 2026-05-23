"""Session cost/duration analysis dashboard — GET /sessions."""


def render_session_dashboard() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css = theme_vars_css()
    _tb_css    = topbar_css()
    _tb_html   = topbar_html(title="会话分析", back_url="/stats")
    _overlays  = settings_overlay_html()
    _tb_js     = topbar_js()

    page_css = r"""
  a { color: inherit; text-decoration: none; }

  .dash-controls {
    display: flex; align-items: center; gap: 8px; padding: 8px 20px;
    background: var(--panel); border-bottom: 1px solid var(--border);
  }
  .dash-btn { background: none; border: 1px solid var(--border); color: var(--sub);
              border-radius: var(--radius-sm); padding: 4px 12px; font-size: 12px;
              cursor: pointer; font-family: var(--mono); transition: all .15s; }
  .dash-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; }
  .dash-sep { width: 1px; height: 18px; background: var(--border); margin: 0 4px; }

  .dash-main { max-width: 1100px; margin: 0 auto; padding: 24px 20px 60px; }

  /* summary cards */
  .summary-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
                 margin-bottom: 20px; }
  .summary-card { background: var(--panel); border: 1px solid var(--border);
                  border-radius: var(--radius); padding: 16px; text-align: center; }
  .summary-val { font-size: 24px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
  .summary-lbl { font-size: 11px; color: var(--sub); }

  /* scatter chart */
  .scatter-card { background: var(--panel); border: 1px solid var(--border);
                  border-radius: var(--radius); padding: 16px; margin-bottom: 20px; }
  .chart-title { font-size: 12px; color: var(--text); font-weight: 600; margin-bottom: 12px; }

  /* project breakdown */
  .breakdown-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
  .breakdown-card { background: var(--panel); border: 1px solid var(--border);
                    border-radius: var(--radius); padding: 16px; }

  /* session table */
  .table-card { background: var(--panel); border: 1px solid var(--border);
                border-radius: var(--radius); padding: 16px; }
  .session-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .session-table th { text-align: left; color: var(--sub); font-weight: 500; padding: 8px 6px;
                      border-bottom: 1px solid var(--border); white-space: nowrap; }
  .session-table td { padding: 8px 6px; border-bottom: 1px solid rgba(255,255,255,.04);
                      color: var(--text); }
  .session-table tr:hover td { background: rgba(255,255,255,.03); }
  .col-rank { width: 30px; color: var(--sub); text-align: center; }
  .col-project { max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .col-task { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
              color: var(--sub); font-size: 11px; }
  .col-num { text-align: right; white-space: nowrap; font-family: var(--mono); }
  .cost-hi { color: #f87171; font-weight: 600; }
  .cost-md { color: #fbbf24; }
  .cost-lo { color: var(--sub); }
  .hours-hi { color: #34d399; font-weight: 600; }

  .filter-input { background: var(--bg); border: 1px solid var(--border); color: var(--text);
                  border-radius: var(--radius-sm); padding: 4px 10px; font-size: 12px;
                  font-family: var(--mono); width: 180px; }
  .filter-input::placeholder { color: var(--sub); }

  /* token cards */
  .token-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
  .token-card { background: var(--panel); border: 1px solid var(--border);
                border-radius: var(--radius); padding: 14px 16px; }
  .token-label { font-size: 11px; color: var(--sub); margin-bottom: 6px; display: flex;
                 align-items: center; gap: 5px; }
  .token-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .token-val { font-size: 20px; font-weight: 700; color: var(--text); margin-bottom: 3px;
               font-family: var(--mono); }
  .token-cost { font-size: 11px; color: var(--sub); }
  .token-pct { font-size: 11px; margin-left: auto; }

  /* token stacked bar */
  .token-stack-card { background: var(--panel); border: 1px solid var(--border);
                      border-radius: var(--radius); padding: 16px; margin-bottom: 20px; }
  .token-stack-row { display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }
  .stack-label { width: 90px; font-size: 11px; color: var(--text); overflow: hidden;
                 text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; }
  .stack-bar { flex: 1; height: 10px; border-radius: 3px; overflow: hidden; display: flex; }
  .stack-seg { height: 100%; }
  .stack-total { width: 58px; font-size: 11px; color: var(--sub); text-align: right;
                 font-family: var(--mono); flex-shrink: 0; }

  /* token mini bar in table */
  .tok-bar { display: flex; height: 5px; border-radius: 2px; overflow: hidden; min-width: 60px; gap: 1px; }
  .tok-seg { height: 100%; border-radius: 1px; }

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
  .turn-rank { width: 22px; font-size: 11px; color: var(--sub); text-align: center;
               flex-shrink: 0; padding-top: 2px; }
  .turn-body { flex: 1; min-width: 0; }
  .turn-label { font-size: 12px; color: var(--text); margin-bottom: 4px;
                overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .turn-label.inherited { color: var(--sub); font-style: italic; }
  .turn-raw { font-size: 10px; color: rgba(255,255,255,.3); margin-bottom: 5px;
              overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .turn-tok-bar { margin-bottom: 3px; }
  .turn-meta { font-size: 10px; color: var(--sub); display: flex; gap: 10px; }
  .turn-cost { width: 60px; text-align: right; flex-shrink: 0; font-family: var(--mono);
               font-size: 12px; padding-top: 2px; }

  .empty-state { text-align: center; color: var(--sub); padding: 60px 20px; font-size: 14px; }

  @media (max-width: 640px) {
    .summary-row { grid-template-columns: repeat(2, 1fr); }
    .token-row { grid-template-columns: repeat(2, 1fr); }
    .breakdown-row { grid-template-columns: 1fr; }
    .col-task { display: none; }
    .session-table { font-size: 11px; }
  }
"""

    page_js = r"""
const _CL_PRICE_IN      = 3.0   / 1e6;
const _CL_PRICE_OUT     = 15.0  / 1e6;
const _CL_PRICE_CACHE_W = 3.75  / 1e6;
const _CL_PRICE_CACHE_R = 0.30  / 1e6;

let _sortBy = 'cost';
let _filterProject = '';
let _allData = [];

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
  if (v >= 10) return '$' + v.toFixed(1);
  return '$' + v.toFixed(2);
}
function _costClass(v) {
  if (v >= 100) return 'cost-hi';
  if (v >= 30) return 'cost-md';
  return 'cost-lo';
}

document.getElementById('btn-cost').addEventListener('click', function() { setSort('cost'); });
document.getElementById('btn-hours').addEventListener('click', function() { setSort('hours'); });
document.getElementById('filter-project').addEventListener('input', function(e) {
  _filterProject = e.target.value.toLowerCase();
  renderAll();
});

function setSort(s) {
  _sortBy = s;
  document.getElementById('btn-cost').classList.toggle('active', s === 'cost');
  document.getElementById('btn-hours').classList.toggle('active', s === 'hours');
  loadData();
}

async function loadData() {
  try {
    const res = await fetch('/api/top-sessions?sort=' + _sortBy + '&limit=100', { headers: _authHeaders() });
    if (res.status === 401) { openLoginModal(loadData); return; }
    if (!res.ok) return;
    _allData = await res.json();
    renderAll();
  } catch(e) { console.warn('load error:', e); }
}

function getFiltered() {
  if (!_filterProject) return _allData;
  return _allData.filter(function(s) {
    return (s.project_name || '').toLowerCase().indexOf(_filterProject) >= 0;
  });
}

function renderAll() {
  var data = getFiltered();
  renderSummary(data);
  renderTokenCards(data);
  renderScatter(data);
  renderBreakdown(data);
  renderTokenStacks(data);
  renderTable(data);
}

function renderSummary(data) {
  var totalCost = 0, totalHours = 0, totalMsgs = 0;
  data.forEach(function(s) {
    totalCost += s.estimated_cost_usd;
    totalHours += s.active_hours;
    totalMsgs += s.messages;
  });
  var avgCost = data.length ? totalCost / data.length : 0;
  var cards = [
    [data.length, '会话数'],
    [_fmtCost(totalCost), '总花费'],
    [totalHours.toFixed(1) + 'h', '总时长'],
    [_fmtCost(avgCost), '平均花费/会话'],
  ];
  document.getElementById('summary-row').innerHTML = cards.map(function(c) {
    return '<div class="summary-card"><div class="summary-val">' + c[0] + '</div>' +
           '<div class="summary-lbl">' + c[1] + '</div></div>';
  }).join('');
}

// Token colors: input=blue, output=orange, cache_write=yellow, cache_read=teal
var TOK_COLORS = { inp: '#4e9eff', out: '#f0a050', cw: '#fbbf24', cr: '#5cd08a' };

function renderTokenCards(data) {
  var totInp = 0, totOut = 0, totCW = 0, totCR = 0;
  data.forEach(function(s) {
    totInp += s.input_tokens;
    totOut += s.output_tokens;
    totCW  += s.cache_creation_tokens;
    totCR  += s.cache_read_tokens;
  });
  var cInp = totInp * _CL_PRICE_IN;
  var cOut = totOut * _CL_PRICE_OUT;
  var cCW  = totCW  * _CL_PRICE_CACHE_W;
  var cCR  = totCR  * _CL_PRICE_CACHE_R;
  var totalCost = cInp + cOut + cCW + cCR || 1;

  function _card(label, color, total, cost) {
    var pct = (cost / totalCost * 100).toFixed(1);
    return '<div class="token-card">' +
      '<div class="token-label"><span class="token-dot" style="background:' + color + '"></span>' +
        label + '<span class="token-pct" style="color:' + color + '">' + pct + '%</span></div>' +
      '<div class="token-val">' + _fmtNum(total) + '</div>' +
      '<div class="token-cost">' + _fmtCost(cost) + ' · $' + (total ? (cost/total*1e6).toFixed(2) : '0') + '/M</div>' +
      '</div>';
  }
  document.getElementById('token-row').innerHTML =
    _card('输入 (上传)', TOK_COLORS.inp, totInp, cInp) +
    _card('输出 (下载)', TOK_COLORS.out, totOut, cOut) +
    _card('缓存写入', TOK_COLORS.cw, totCW, cCW) +
    _card('缓存读取', TOK_COLORS.cr, totCR, cCR);
}

function renderTokenStacks(data) {
  // Aggregate by project
  var byProject = {};
  data.forEach(function(s) {
    var name = s.project_name || s.project_id;
    if (!byProject[name]) byProject[name] = { inp: 0, out: 0, cw: 0, cr: 0, cost: 0 };
    byProject[name].inp  += s.input_tokens;
    byProject[name].out  += s.output_tokens;
    byProject[name].cw   += s.cache_creation_tokens;
    byProject[name].cr   += s.cache_read_tokens;
    byProject[name].cost += s.estimated_cost_usd;
  });
  var list = Object.keys(byProject).map(function(k) {
    var p = byProject[k];
    return { name: k, inp: p.inp, out: p.out, cw: p.cw, cr: p.cr,
             total: p.inp + p.out + p.cw + p.cr, cost: p.cost };
  }).sort(function(a, b) { return b.cost - a.cost; }).slice(0, 12);

  var el = document.getElementById('token-stacks');
  el.innerHTML = list.map(function(p) {
    var tot = p.total || 1;
    var segs = [
      { key: 'inp', val: p.inp, color: TOK_COLORS.inp },
      { key: 'out', val: p.out, color: TOK_COLORS.out },
      { key: 'cw',  val: p.cw,  color: TOK_COLORS.cw  },
      { key: 'cr',  val: p.cr,  color: TOK_COLORS.cr  },
    ].map(function(seg) {
      return '<div class="stack-seg" style="width:' + (seg.val/tot*100).toFixed(1) +
             '%;background:' + seg.color + '" title="' + seg.key + ': ' + _fmtNum(seg.val) + '"></div>';
    }).join('');
    var tip = '输入: ' + _fmtNum(p.inp) + '  输出: ' + _fmtNum(p.out) +
              '  缓存写: ' + _fmtNum(p.cw) + '  缓存读: ' + _fmtNum(p.cr);
    return '<div class="token-stack-row" title="' + tip + '">' +
      '<div class="stack-label" title="' + _esc(p.name) + '">' + _esc(p.name) + '</div>' +
      '<div class="stack-bar">' + segs + '</div>' +
      '<div class="stack-total">' + _fmtNum(p.total) + '</div>' +
      '</div>';
  }).join('') +
  '<div style="display:flex;gap:16px;margin-top:10px;font-size:11px;color:var(--sub)">' +
    ['输入','输出','缓存写','缓存读'].map(function(l, i) {
      var c = [TOK_COLORS.inp, TOK_COLORS.out, TOK_COLORS.cw, TOK_COLORS.cr][i];
      return '<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + c + ';margin-right:4px"></span>' + l + '</span>';
    }).join('') +
  '</div>';
}

function renderScatter(data) {
  var svg = document.getElementById('scatter-svg');
  if (!svg || !data.length) return;
  var W = svg.parentElement.clientWidth - 32;
  var H = 200;
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);

  var PAD = 40;
  var maxCost = Math.max.apply(null, data.map(function(s) { return s.estimated_cost_usd; }).concat([1]));
  var maxHours = Math.max.apply(null, data.map(function(s) { return s.active_hours; }).concat([1]));

  var html = '';
  // Axes
  html += '<line x1="' + PAD + '" y1="' + (H-PAD) + '" x2="' + (W-10) + '" y2="' + (H-PAD) +
          '" stroke="var(--border)" stroke-width="1"/>';
  html += '<line x1="' + PAD + '" y1="10" x2="' + PAD + '" y2="' + (H-PAD) +
          '" stroke="var(--border)" stroke-width="1"/>';
  html += '<text x="' + (W/2) + '" y="' + (H-5) + '" text-anchor="middle" font-size="10" fill="var(--sub)">时长 (h)</text>';
  html += '<text x="12" y="' + (H/2-20) + '" font-size="10" fill="var(--sub)" transform="rotate(-90,12,' + (H/2-20) + ')">花费 ($)</text>';

  // Project color map
  var projects = {};
  var colorPalette = ['#5cd08a','#4e9eff','#f0a050','#c792ea','#56b6c2','#e06c75','#98c379','#d19a66','#61afef','#be5046'];
  data.forEach(function(s) { if (!projects[s.project_name]) projects[s.project_name] = Object.keys(projects).length; });

  data.forEach(function(s, i) {
    var x = PAD + (s.active_hours / maxHours) * (W - PAD - 10);
    var y = (H - PAD) - (s.estimated_cost_usd / maxCost) * (H - PAD - 10);
    var r = Math.min(12, Math.max(3, Math.sqrt(s.messages) * 0.8));
    var ci = projects[s.project_name] % colorPalette.length;
    var color = colorPalette[ci];
    var tip = _esc(s.project_name) + '\n' + (s.task_summary || '').slice(0,60) +
              '\n时长: ' + s.active_hours + 'h  花费: $' + s.estimated_cost_usd.toFixed(2) +
              '\n消息: ' + s.messages;
    html += '<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="' + r.toFixed(1) +
            '" fill="' + color + '" opacity="0.6" stroke="' + color + '" stroke-width="0.5">' +
            '<title>' + tip + '</title></circle>';
  });

  svg.innerHTML = html;
}

function renderBreakdown(data) {
  // Aggregate by project
  var byProject = {};
  data.forEach(function(s) {
    var name = s.project_name || s.project_id;
    if (!byProject[name]) byProject[name] = { cost: 0, hours: 0, count: 0 };
    byProject[name].cost += s.estimated_cost_usd;
    byProject[name].hours += s.active_hours;
    byProject[name].count += 1;
  });
  var projList = Object.keys(byProject).map(function(k) {
    return { name: k, cost: byProject[k].cost, hours: byProject[k].hours, count: byProject[k].count };
  });
  projList.sort(function(a, b) { return b.cost - a.cost; });

  // Cost breakdown
  var maxCost = projList.length ? projList[0].cost : 1;
  document.getElementById('breakdown-cost').innerHTML =
    '<div class="chart-title">按项目花费</div>' +
    projList.slice(0, 12).map(function(p) {
      var pct = (p.cost / maxCost * 100).toFixed(1);
      return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
        '<div style="width:90px;font-size:11px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + _esc(p.name) + '">' + _esc(p.name) + '</div>' +
        '<div style="flex:1;background:rgba(255,255,255,.06);border-radius:3px;height:8px">' +
          '<div style="width:' + pct + '%;background:#4e9eff;border-radius:3px;height:8px"></div></div>' +
        '<div style="width:60px;font-size:11px;color:var(--blue,#4e9eff);text-align:right">' + _fmtCost(p.cost) + '</div>' +
        '</div>';
    }).join('');

  // Hours breakdown
  var projByH = projList.slice().sort(function(a, b) { return b.hours - a.hours; });
  var maxH = projByH.length ? projByH[0].hours : 1;
  document.getElementById('breakdown-hours').innerHTML =
    '<div class="chart-title">按项目时长</div>' +
    projByH.slice(0, 12).map(function(p) {
      var pct = (p.hours / maxH * 100).toFixed(1);
      return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
        '<div style="width:90px;font-size:11px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + _esc(p.name) + '">' + _esc(p.name) + '</div>' +
        '<div style="flex:1;background:rgba(255,255,255,.06);border-radius:3px;height:8px">' +
          '<div style="width:' + pct + '%;background:#5cd08a;border-radius:3px;height:8px"></div></div>' +
        '<div style="width:60px;font-size:11px;color:var(--green);text-align:right">' + p.hours.toFixed(1) + 'h</div>' +
        '</div>';
    }).join('');
}

function _tokenMiniBar(s) {
  var tot = (s.input_tokens + s.output_tokens + s.cache_creation_tokens + s.cache_read_tokens) || 1;
  var segs = [
    { v: s.input_tokens,            c: TOK_COLORS.inp },
    { v: s.output_tokens,           c: TOK_COLORS.out },
    { v: s.cache_creation_tokens,   c: TOK_COLORS.cw  },
    { v: s.cache_read_tokens,       c: TOK_COLORS.cr  },
  ].map(function(seg) {
    return '<div class="tok-seg" style="width:' + (seg.v/tot*100).toFixed(1) + '%;background:' + seg.c + '"></div>';
  }).join('');
  var tip = '输入: ' + _fmtNum(s.input_tokens) + '  输出: ' + _fmtNum(s.output_tokens) +
            '  缓存写: ' + _fmtNum(s.cache_creation_tokens) + '  缓存读: ' + _fmtNum(s.cache_read_tokens);
  return '<div class="tok-bar" title="' + tip + '">' + segs + '</div>';
}

function renderTable(data) {
  var el = document.getElementById('session-table-body');
  if (!data.length) {
    el.innerHTML = '<tr><td colspan="8" class="empty-state">暂无数据</td></tr>';
    return;
  }
  el.innerHTML = data.map(function(s, i) {
    var cc = _costClass(s.estimated_cost_usd);
    var hc = s.active_hours >= 20 ? 'hours-hi' : '';
    var totTok = s.input_tokens + s.output_tokens + s.cache_creation_tokens + s.cache_read_tokens;
    var onclick = "openSessionTurns('" + s.session_id + "','" +
      _esc(s.project_name).replace(/'/g,"\\'") + "','" + s.date + "'," + s.estimated_cost_usd + ")";
    return '<tr style="cursor:pointer" onclick="' + onclick + '" title="点击查看任务明细">' +
      '<td class="col-rank">' + (i + 1) + '</td>' +
      '<td class="col-project" title="' + _esc(s.project_name) + '">' + _esc(s.project_name) + '</td>' +
      '<td class="col-task" title="' + _esc(s.task_summary || '') + '">' + _esc(s.task_summary || '-') + '</td>' +
      '<td class="col-num">' + s.date + '</td>' +
      '<td class="col-num ' + cc + '">' + _fmtCost(s.estimated_cost_usd) + '</td>' +
      '<td class="col-num ' + hc + '">' + s.active_hours.toFixed(1) + 'h</td>' +
      '<td style="min-width:80px;padding:8px 6px">' + _tokenMiniBar(s) +
        '<div style="font-size:10px;color:var(--sub);margin-top:2px;font-family:var(--mono)">' + _fmtNum(totTok) + '</div></td>' +
      '<td class="col-num" style="color:var(--sub)">' + s.messages + '</td>' +
      '</tr>';
  }).join('');
}

// ── Session turns modal ─────────────────────────────────────────────────
async function openSessionTurns(sessionId, projectName, date, totalCost) {
  var overlay = document.getElementById('modal-overlay');
  var box = document.getElementById('modal-box');
  overlay.style.display = 'flex';
  box.innerHTML = '<div style="text-align:center;padding:40px;color:var(--sub)">加载中…</div>';

  try {
    var res = await fetch('/api/session/' + sessionId + '/turns', { headers: _authHeaders() });
    if (res.status === 401) { overlay.style.display = 'none'; openLoginModal(function(){}); return; }
    var turns = res.ok ? await res.json() : [];

    if (!turns.length) {
      box.innerHTML = '<button class="modal-close" onclick="closeModal()">✕</button>' +
        '<div class="modal-title">' + _esc(projectName) + ' · ' + date + '</div>' +
        '<div class="empty-state">暂无任务明细（session 文件可能不在本机）</div>';
      return;
    }

    var maxCost = turns[0].estimated_cost_usd || 0.0001;
    var rows = turns.map(function(t, i) {
      var totTok = t.input_tokens + t.output_tokens + t.cache_creation_tokens + t.cache_read_tokens;
      var pct = (t.estimated_cost_usd / maxCost * 100).toFixed(1);
      var isInherited = t.label !== t.raw_label;
      var cc = _costClass(t.estimated_cost_usd);
      var segs = [
        { v: t.input_tokens,            c: TOK_COLORS.inp },
        { v: t.output_tokens,           c: TOK_COLORS.out },
        { v: t.cache_creation_tokens,   c: TOK_COLORS.cw  },
        { v: t.cache_read_tokens,       c: TOK_COLORS.cr  },
      ].map(function(seg) {
        return '<div class="tok-seg" style="width:' + (seg.v / (totTok||1) * 100).toFixed(1) +
               '%;background:' + seg.c + '"></div>';
      }).join('');
      var tipTok = '输入: ' + _fmtNum(t.input_tokens) + '  输出: ' + _fmtNum(t.output_tokens) +
                  '  缓存写: ' + _fmtNum(t.cache_creation_tokens) + '  缓存读: ' + _fmtNum(t.cache_read_tokens);
      return '<div class="turn-row">' +
        '<div class="turn-rank">' + (i+1) + '</div>' +
        '<div class="turn-body">' +
          '<div class="turn-label' + (isInherited ? ' inherited' : '') + '" title="' + _esc(t.label) + '">' +
            _esc(t.label.slice(0, 100)) + '</div>' +
          (isInherited && t.raw_label ? '<div class="turn-raw">实际输入: ' + _esc(t.raw_label.slice(0, 80)) + '</div>' : '') +
          '<div class="turn-tok-bar"><div class="tok-bar" style="height:6px;min-width:100px" title="' + tipTok + '">' + segs + '</div></div>' +
          '<div class="turn-meta">' +
            '<span style="color:#4e9eff">↑' + _fmtNum(t.input_tokens) + '</span>' +
            '<span style="color:#f0a050">↓' + _fmtNum(t.output_tokens) + '</span>' +
            '<span style="color:#fbbf24">W' + _fmtNum(t.cache_creation_tokens) + '</span>' +
            '<span style="color:#5cd08a">R' + _fmtNum(t.cache_read_tokens) + '</span>' +
            '<span>' + _fmtNum(totTok) + ' total</span>' +
          '</div>' +
        '</div>' +
        '<div class="turn-cost ' + cc + '">' + _fmtCost(t.estimated_cost_usd) + '</div>' +
        '</div>';
    }).join('');

    box.innerHTML =
      '<button class="modal-close" onclick="closeModal()">✕</button>' +
      '<div class="modal-title">' + _esc(projectName) + ' · ' + date + ' · ' + _fmtCost(totalCost) + '</div>' +
      '<div class="modal-sub">按任务花费排序 · 共 ' + turns.length + ' 个任务轮次</div>' +
      '<div style="display:flex;gap:12px;margin-bottom:12px;font-size:10px;color:var(--sub)">' +
        '<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#4e9eff;margin-right:3px"></span>↑输入</span>' +
        '<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#f0a050;margin-right:3px"></span>↓输出</span>' +
        '<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#fbbf24;margin-right:3px"></span>W缓存写</span>' +
        '<span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#5cd08a;margin-right:3px"></span>R缓存读</span>' +
        '<span style="margin-left:8px;font-style:italic">斜体标签 = 确认词继承上一任务</span>' +
      '</div>' +
      rows;
  } catch(e) {
    box.innerHTML = '<button class="modal-close" onclick="closeModal()">✕</button>' +
      '<div class="empty-state">加载失败: ' + _esc(String(e)) + '</div>';
  }
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}
document.getElementById('modal-overlay').addEventListener('click', function(e) {
  if (e.target === this) closeModal();
});

_initAuth().then(function() { loadData(); });
"""

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>会话分析 · Mira</title>\n"
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
<div class="dash-controls">
  <div style="display:flex;gap:4px">
    <button class="dash-btn active" id="btn-cost">按花费</button>
    <button class="dash-btn"        id="btn-hours">按时长</button>
  </div>
  <div class="dash-sep"></div>
  <input type="text" class="filter-input" id="filter-project" placeholder="筛选项目...">
</div>

<div class="dash-main">
  <div id="summary-row" class="summary-row"></div>

  <div id="token-row" class="token-row"></div>

  <div class="scatter-card">
    <div class="chart-title">花费 vs 时长（气泡大小 = 消息数）</div>
    <svg id="scatter-svg" style="width:100%;overflow:visible" height="200"></svg>
  </div>

  <div class="breakdown-row">
    <div class="breakdown-card" id="breakdown-cost"></div>
    <div class="breakdown-card" id="breakdown-hours"></div>
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
      <tbody id="session-table-body"></tbody>
    </table>
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
