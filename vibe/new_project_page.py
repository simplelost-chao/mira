# vibe/new_project_page.py
"""New project wizard page — GET /new."""


def render_new_project_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js
    _theme_css = theme_vars_css()
    _tb_css    = topbar_css()
    _tb_html   = topbar_html(title="新建项目", back_url="/")
    _overlays  = settings_overlay_html()
    _tb_js     = topbar_js()

    page_css = r"""
  .wizard-wrap { max-width: 520px; margin: 0 auto; padding: 28px 20px 60px; }

  /* Step indicator */
  .step-bar { display: flex; align-items: center; margin-bottom: 32px; }
  .step-dot { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
              justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
  .step-dot.active  { background: var(--accent); color: #000; }
  .step-dot.done    { background: transparent; border: 2px solid var(--accent); color: var(--accent); }
  .step-dot.pending { background: var(--panel-alt, #1e2433); color: var(--sub); }
  .step-line { flex: 1; height: 2px; background: var(--border); }
  .step-line.done { background: var(--accent); }
  .step-label { font-size: 9px; text-align: center; margin-top: 4px; }

  /* Step panels */
  .step-panel { display: none; }
  .step-panel.active { display: block; }

  .wizard-title { font-size: 20px; font-weight: 800; color: var(--text); margin-bottom: 6px; }
  .wizard-sub   { font-size: 12px; color: var(--sub); margin-bottom: 24px; }

  /* Inputs */
  .wz-input { width: 100%; background: var(--panel); border: 1px solid var(--border);
              border-radius: var(--radius); padding: 12px 14px; font-size: 13px;
              color: var(--text); resize: none; box-sizing: border-box; font-family: var(--mono);
              transition: border-color .15s; }
  .wz-input:focus { outline: none; border-color: var(--accent); }
  .wz-label { font-size: 11px; color: var(--sub); margin-bottom: 6px; display: block; }

  /* Model selector */
  .model-row { display: flex; align-items: center; justify-content: space-between;
               margin-top: 14px; }
  .model-sel { background: var(--panel); border: 1px solid var(--border); color: var(--text);
               border-radius: var(--radius-sm); padding: 6px 10px; font-size: 12px;
               font-family: var(--mono); cursor: pointer; }

  /* Primary button */
  .wz-btn { width: 100%; background: var(--accent); border: none; border-radius: var(--radius);
            padding: 13px; font-size: 13px; font-weight: 700; color: #000; cursor: pointer;
            margin-top: 20px; transition: opacity .15s; }
  .wz-btn:disabled { opacity: .4; cursor: not-allowed; }

  /* Candidate cards */
  .candidate-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
  .candidate-card { background: var(--panel); border: 1.5px solid var(--border);
                    border-radius: var(--radius); padding: 16px; display: flex;
                    gap: 14px; cursor: pointer; transition: border-color .15s; }
  .candidate-card:hover  { border-color: rgba(var(--accent-rgb,.5), .5); }
  .candidate-card.selected { border-color: var(--accent); }
  .candidate-logo { width: 56px; height: 56px; border-radius: 10px;
                    background: var(--bg); border: 1px solid var(--border);
                    display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .candidate-logo svg { width: 38px; height: 38px; }
  .candidate-name { font-size: 17px; font-weight: 800; color: var(--text); }
  .candidate-phonetic { font-size: 11px; color: var(--sub); margin-left: 6px; font-style: italic; }
  .candidate-meaning { font-size: 11px; color: var(--text-muted, var(--sub)); line-height: 1.6; margin-top: 5px; }
  .meaning-label { color: var(--accent); font-weight: 600; }
  .candidate-divider { border: none; border-top: 1px solid var(--border); margin: 8px 0; }

  /* Step 3 config fields */
  .config-field { margin-bottom: 16px; }

  /* Step 4 log */
  .create-log { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius);
                padding: 14px; font-size: 12px; font-family: var(--mono); line-height: 2;
                min-height: 160px; color: var(--sub); }
  .log-line.ok   { color: var(--green, #00ff9d); }
  .log-line.done { color: var(--accent); font-weight: 700; }
  .log-line.err  { color: #ff5f5f; }

  /* Error banner */
  .wz-error { background: rgba(255,95,95,.1); border: 1px solid rgba(255,95,95,.3);
              border-radius: var(--radius); padding: 10px 14px; font-size: 12px;
              color: #ff5f5f; margin-top: 12px; display: none; }
"""

    page_html = r"""
<div class="wizard-wrap">

  <!-- Step indicator -->
  <div class="step-bar" id="step-bar">
    <div style="text-align:center">
      <div class="step-dot active" id="sdot-1">1</div>
      <div class="step-label" style="color:var(--accent)">描述</div>
    </div>
    <div class="step-line" id="sline-1"></div>
    <div style="text-align:center">
      <div class="step-dot pending" id="sdot-2">2</div>
      <div class="step-label" style="color:var(--sub)">生成</div>
    </div>
    <div class="step-line" id="sline-2"></div>
    <div style="text-align:center">
      <div class="step-dot pending" id="sdot-3">3</div>
      <div class="step-label" style="color:var(--sub)">配置</div>
    </div>
    <div class="step-line" id="sline-3"></div>
    <div style="text-align:center">
      <div class="step-dot pending" id="sdot-4">4</div>
      <div class="step-label" style="color:var(--sub)">创建</div>
    </div>
  </div>

  <!-- Step 1: Describe -->
  <div class="step-panel active" id="step-1">
    <div class="wizard-title">你想做什么？</div>
    <div class="wizard-sub">一句话就够，AI 来帮你把其余的想清楚</div>
    <textarea id="desc-input" class="wz-input" rows="2"
      placeholder="例：一个追踪我每天跑步数据的工具"></textarea>
    <div class="model-row">
      <span class="wz-label" style="margin:0">选择 AI 模型</span>
      <select id="model-sel" class="model-sel"></select>
    </div>
    <div class="wz-error" id="step1-error"></div>
    <button class="wz-btn" id="btn-generate" onclick="doGenerate()">✦ 开始生成</button>
  </div>

  <!-- Step 2: Candidates -->
  <div class="step-panel" id="step-2">
    <div class="wizard-title">选择一个方向</div>
    <div class="wizard-sub" id="step2-sub">AI 生成了 3 个方案</div>
    <div class="candidate-list" id="candidate-list"></div>
    <div class="wz-error" id="step2-error"></div>
    <button class="wz-btn" id="btn-next2" onclick="goStep(3)" disabled>下一步：确认配置 →</button>
  </div>

  <!-- Step 3: Config -->
  <div class="step-panel" id="step-3">
    <div class="wizard-title">确认配置</div>
    <div class="wizard-sub">可以修改，留空的选项不会写入 vibe.yaml</div>
    <div class="config-field">
      <label class="wz-label">项目名称 *</label>
      <input id="cfg-name" class="wz-input" type="text">
    </div>
    <div class="config-field">
      <label class="wz-label">一句话描述 *</label>
      <input id="cfg-desc" class="wz-input" type="text">
    </div>
    <div class="config-field">
      <label class="wz-label">端口（选填）</label>
      <input id="cfg-port" class="wz-input" type="number" placeholder="如 8080">
    </div>
    <div class="config-field">
      <label class="wz-label">域名（选填）</label>
      <input id="cfg-domain" class="wz-input" type="text" placeholder="如 myapp.zhuchao.life">
    </div>
    <div class="wz-error" id="step3-error"></div>
    <button class="wz-btn" onclick="doCreate()">✦ 创建项目</button>
  </div>

  <!-- Step 4: Creating -->
  <div class="step-panel" id="step-4">
    <div class="wizard-title">正在创建...</div>
    <div class="wizard-sub">请稍候</div>
    <div class="create-log" id="create-log"></div>
  </div>

</div>
"""

    page_js = r"""
let _candidates = [];
let _selectedIdx = -1;
// _adminToken is declared by topbar.js, reuse it here

// Load available models
(async function() {
  try {
    const cfg = await fetch('/api/settings', {headers: {'X-Admin-Token': _adminToken}}).then(r => r.json());
    const providers = [
      {id:'deepseek',   label:'DeepSeek',  key:'deepseek_api_key'},
      {id:'openrouter', label:'OpenRouter', key:'openrouter_api_key'},
      {id:'gemini',     label:'Gemini',     key:'gemini_api_key'},
      {id:'doubao',     label:'豆包',        key:'doubao_api_key'},
    ];
    const sel = document.getElementById('model-sel');
    providers.forEach(p => {
      if (cfg[p.key] && cfg[p.key].trim()) {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.label;
        sel.appendChild(opt);
      }
    });
    if (!sel.options.length) {
      sel.innerHTML = '<option value="">未配置模型</option>';
      document.getElementById('btn-generate').disabled = true;
    }
  } catch(e) {}
})();

function goStep(n) {
  for (let i = 1; i <= 4; i++) {
    document.getElementById('step-' + i).classList.toggle('active', i === n);
    const dot = document.getElementById('sdot-' + i);
    dot.className = 'step-dot ' + (i < n ? 'done' : i === n ? 'active' : 'pending');
    dot.textContent = i < n ? '✓' : String(i);
    if (i < 4) {
      document.getElementById('sline-' + i).classList.toggle('done', i < n);
    }
  }
}

async function doGenerate() {
  const desc = document.getElementById('desc-input').value.trim();
  const model = document.getElementById('model-sel').value;
  const errEl = document.getElementById('step1-error');
  errEl.style.display = 'none';
  if (!desc) { errEl.textContent = '请输入项目描述'; errEl.style.display = 'block'; return; }
  if (!model) { errEl.textContent = '请先配置 AI 模型'; errEl.style.display = 'block'; return; }

  const btn = document.getElementById('btn-generate');
  btn.disabled = true;
  btn.textContent = '生成中...';

  try {
    const res = await fetch('/api/projects/brainstorm', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Admin-Token': _adminToken},
      body: JSON.stringify({description: desc, model})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '生成失败');
    _candidates = data.candidates;
    renderCandidates(_candidates);
    document.getElementById('step2-sub').textContent = `AI 根据「${desc}」生成了 ${_candidates.length} 个方案`;
    goStep(2);
  } catch(e) {
    errEl.textContent = e.message;
    errEl.style.display = 'block';
  } finally {
    btn.disabled = false;
    btn.textContent = '✦ 开始生成';
  }
}

function renderCandidates(candidates) {
  _selectedIdx = -1;
  document.getElementById('btn-next2').disabled = true;
  const list = document.getElementById('candidate-list');
  list.innerHTML = candidates.map((c, i) => `
    <div class="candidate-card" id="ccard-${i}" onclick="selectCandidate(${i})">
      <div class="candidate-logo"><img src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(c.logo_svg)}" style="width:38px;height:38px;object-fit:contain" alt="logo"></div>
      <div style="flex:1">
        <div>
          <span class="candidate-name">${_esc(c.name)}</span>
          <span class="candidate-phonetic">${_esc(c.phonetic)}</span>
        </div>
        <div class="candidate-meaning">
          <span class="meaning-label">命名：</span>${_esc(c.name_meaning)}
        </div>
        <hr class="candidate-divider">
        <div class="candidate-meaning">
          <span class="meaning-label">Logo：</span>${_esc(c.logo_meaning)}
        </div>
      </div>
    </div>
  `).join('');
}

function selectCandidate(i) {
  _selectedIdx = i;
  document.querySelectorAll('.candidate-card').forEach((el, j) => {
    el.classList.toggle('selected', j === i);
  });
  document.getElementById('btn-next2').disabled = false;
  // Pre-fill step 3
  const c = _candidates[i];
  document.getElementById('cfg-name').value = c.name;
  document.getElementById('cfg-desc').value = c.name_meaning;
}

function _esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

async function doCreate() {
  const name   = document.getElementById('cfg-name').value.trim();
  const desc   = document.getElementById('cfg-desc').value.trim();
  const port   = parseInt(document.getElementById('cfg-port').value) || null;
  const domain = document.getElementById('cfg-domain').value.trim() || null;
  const errEl  = document.getElementById('step3-error');
  errEl.style.display = 'none';

  if (!name) { errEl.textContent = '项目名称不能为空'; errEl.style.display = 'block'; return; }
  if (!desc) { errEl.textContent = '描述不能为空'; errEl.style.display = 'block'; return; }

  const logoSvg = _candidates[_selectedIdx]?.logo_svg || '';
  goStep(4);
  document.querySelector('#step-4 .wizard-sub').textContent = '正在创建项目，请稍候...';

  const log = document.getElementById('create-log');
  const addLog = (msg, cls='') => {
    log.innerHTML += `<div class="log-line ${cls}">${_esc(msg)}</div>`;
  };

  try {
    addLog('正在调用 API...');
    const res = await fetch('/api/projects/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Admin-Token': _adminToken},
      body: JSON.stringify({name, description: desc, logo_svg: logoSvg, port, domain})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || '创建失败');

    data.log.forEach(line => addLog(line, 'ok'));
    addLog('✦ 完成！2 秒后跳转主页...', 'done');
    document.querySelector('#step-4 .wizard-sub').textContent = '创建成功！';
    setTimeout(() => window.location.href = '/', 2000);
  } catch(e) {
    addLog('✗ ' + e.message, 'err');
    document.querySelector('#step-4 .wizard-sub').textContent = '创建失败';
  }
}
"""

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>新建项目 · Mira</title>\n"
        "<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>\n"
        '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">\n'
        f"<style>\n{_theme_css}\n{_tb_css}\n{page_css}\n</style>\n"
        "</head>\n"
        "<body>\n"
        f"{_tb_html}\n"
        f"{_overlays}\n"
        f"<div class='page-body'>\n{page_html}\n</div>\n"
        f"<script>{_tb_js}\n{page_js}</script>\n"
        "</body>\n</html>"
    )
