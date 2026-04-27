"""Dev mode page — all active tmux sessions across all projects."""


def render_dev_page() -> str:
    from vibe.topbar import theme_vars_css, topbar_css, topbar_html, settings_overlay_html, topbar_js

    page_css = r"""
  /* ── Main layout ── */
  .dev-page {
    height: calc(100vh - 52px);
    display: flex;
    overflow: hidden;
    background: var(--bg);
  }

  /* ── Sidebar (pane list) ── */
  .term-sidebar {
    width: 200px; border-right: 1px solid var(--border);
    display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden;
    background: var(--panel);
  }
  .term-sidebar-header {
    padding: 10px 14px; font-size: 10px; color: var(--muted);
    font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase;
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  #term-pane-list { flex: 1; overflow-y: auto; }
  .term-pane-row {
    padding: 10px 14px; display: flex; align-items: flex-start; gap: 8px;
    cursor: pointer; border-left: 2px solid transparent; transition: background .12s, border-color .12s;
  }
  .term-pane-row:hover { background: rgba(255,255,255,.03); }
  .term-pane-row.active { background: rgba(var(--accent-rgb),.1); border-left-color: var(--accent); }
  .term-pane-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 3px;
    transition: background .25s, box-shadow .25s;
  }
  .term-pane-dot.inactive { background: var(--border); }
  .term-pane-dot.idle     { background: var(--muted); opacity: .45; }
  .term-pane-dot.running  { background: var(--green); box-shadow: 0 0 6px rgba(63,185,80,.6); animation: pane-pulse .9s ease-in-out infinite; }
  .term-pane-dot.confirm  { background: var(--orange); box-shadow: 0 0 6px var(--orange); animation: pane-pulse 1.4s ease-in-out infinite; }
  .term-pane-dot.done     { background: var(--green); }
  .term-pane-dot.error    { background: var(--red); }
  @keyframes pane-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  .term-pane-info { min-width: 0; flex: 1; }
  .term-pane-name { font-size: 12px; color: var(--text); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-pane-proj { font-size: 10px; color: var(--sub); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-pane-cmd  { font-size: 9px; color: var(--muted); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-sidebar-footer {
    padding: 8px 14px; font-size: 10px; color: var(--muted);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
  .term-empty-sidebar { padding: 32px 16px; font-size: 12px; color: var(--muted); line-height: 1.8; }
  .term-empty-sidebar code { color: var(--sub); }
  /* ── State badge in titlebar ── */
  .term-state-badge {
    font-size: 9px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    padding: 2px 8px; border: 1px solid; border-radius: var(--radius-sm);
    flex-shrink: 0; display: none; transition: color .2s, border-color .2s;
  }

  /* ── Terminal main ── */
  .term-main { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; background: var(--bg); }
  .term-titlebar {
    padding: 7px 14px; display: flex; align-items: center;
    justify-content: space-between; border-bottom: 1px solid var(--border);
    flex-shrink: 0; gap: 8px;
  }
  .term-title-left { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
  .term-back-btn {
    display: none;
    background: none; border: none; color: var(--accent);
    font-size: 16px; padding: 0 6px 0 0; cursor: pointer; flex-shrink: 0;
    line-height: 1;
  }
  #term-title { font-size: 11px; color: var(--sub); font-family: var(--mono); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .term-quickbtns { display: flex; gap: 6px; flex-shrink: 0; }
  .term-qbtn {
    background: var(--panel); border: 1px solid var(--border);
    color: var(--muted); font-size: 10px; padding: 2px 8px;
    border-radius: var(--radius-sm); cursor: pointer; font-family: var(--mono); transition: all .12s;
  }
  .term-qbtn:hover { border-color: var(--accent); color: var(--accent); }
  /* ── ANSI 16-color palette: references theme vars wherever possible ── */
  :root {
    --ansi-k: #3a3f4b;          /* black  */
    --ansi-r: var(--red);       /* red    */
    --ansi-g: var(--green);     /* green  */
    --ansi-y: var(--yellow);    /* yellow */
    --ansi-b: #4e9eff;          /* blue   */
    --ansi-m: #c792ea;          /* magenta */
    --ansi-c: #56b6c2;          /* cyan   */
    --ansi-w: var(--text);      /* white  */
    --ansi-K: var(--muted);     /* bright black  */
    --ansi-R: var(--red);       /* bright red    */
    --ansi-G: var(--green);     /* bright green  */
    --ansi-Y: var(--orange);    /* bright yellow */
    --ansi-B: #82aaff;          /* bright blue   */
    --ansi-M: #d9a0f5;          /* bright magenta */
    --ansi-C: #89ddff;          /* bright cyan   */
    --ansi-W: #ffffff;          /* bright white  */
  }

  /* ── Terminal output (code-editor style) ── */
  .term-output {
    flex: 1; overflow-y: auto;
    font-family: var(--mono); font-size: 12.5px;
    background: var(--bg); color: var(--text);
    padding: 12px 0;
  }
  /* each "chunk" of output is wrapped in a code-block panel */
  .out-block {
    margin: 0 14px 10px;
    background: var(--panel);
    border: 1px solid rgba(255,255,255,.04);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .out-line {
    display: flex; align-items: baseline;
    min-height: 1.65em; line-height: 1.65;
    transition: background .08s;
  }
  .out-line:hover { background: rgba(255,255,255,.04); }
  .out-ln {
    flex-shrink: 0;
    width: 3.4em;
    padding: 0 .7em 0 .6em;
    text-align: center;
    color: var(--muted);
    font-size: .78em;
    user-select: none;
    border-right: 1px solid rgba(255,255,255,.06);
    line-height: 1.65;
    white-space: pre;
    background: rgba(0,0,0,.08);
  }
  .out-code {
    flex: 1; min-width: 0;
    padding: 0 16px;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.65;
  }

  /* ── Syntax-highlighted blocks (hljs) ── */
  .out-block-syntax { display: flex; align-items: stretch; }
  .out-lang-gutter {
    flex-shrink: 0; width: 3.4em;
    background: rgba(0,0,0,.08); border-right: 1px solid rgba(255,255,255,.06);
    display: flex; align-items: center; justify-content: center;
    padding: 10px 0;
    font-size: .78em; color: var(--muted);
    letter-spacing: 1.5px; text-transform: uppercase;
    user-select: none; overflow: hidden;
    writing-mode: vertical-lr; text-orientation: mixed;
  }
  .out-pre {
    flex: 1; min-width: 0; margin: 0; padding: 10px 16px;
    font-family: var(--mono); font-size: 1em; line-height: 1.65;
    white-space: pre-wrap; word-break: break-all;
    color: var(--text); background: transparent;
  }
  /* hljs token classes → theme CSS variables (auto-adapts to any skin) */
  .hljs-keyword, .hljs-selector-tag  { color: var(--accent-light); }
  .hljs-built_in                      { color: var(--accent); }
  .hljs-type                          { color: var(--accent-light); }
  .hljs-literal                       { color: var(--orange); }
  .hljs-number                        { color: var(--orange); }
  .hljs-string, .hljs-doctag          { color: var(--green); }
  .hljs-regexp                        { color: var(--orange); }
  .hljs-comment                       { color: var(--muted); font-style: italic; }
  .hljs-title,
  .hljs-title.function_,
  .hljs-title.class_                  { color: var(--yellow); }
  .hljs-section                       { color: var(--yellow); font-weight: 700; }
  .hljs-attr, .hljs-attribute,
  .hljs-property                      { color: var(--accent-light); }
  .hljs-name                          { color: var(--accent); }
  .hljs-meta                          { color: var(--muted); }
  .hljs-meta .hljs-string             { color: var(--green); }
  .hljs-symbol                        { color: var(--purple); }
  .hljs-params, .hljs-variable,
  .hljs-template-variable             { color: var(--sub); }
  .hljs-deletion  { color: var(--red);   background: rgba(239,68,68,.1); }
  .hljs-addition  { color: var(--green); background: rgba(34,197,94,.1); }
  .hljs-emphasis  { font-style: italic; }
  .hljs-strong    { font-weight: 700; }
  .hljs-link      { color: var(--accent); text-decoration: underline; }
  .hljs-operator, .hljs-punctuation   { color: var(--sub); }

  .term-empty {
    height: 100%; display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: var(--muted); font-size: 13px; text-align: center; gap: 10px; line-height: 1.7;
  }
  .term-empty code { color: var(--sub); font-size: 11px; }
  /* ── Input bar: Claude-style unified container ── */
  .term-inputbar {
    padding: 8px 12px 10px; border-top: 1px solid var(--border);
    flex-shrink: 0; background: var(--panel);
  }
  .term-input-wrap {
    background: rgba(255,255,255,.04); border: 1px solid var(--border);
    border-radius: var(--radius); transition: border-color .15s; overflow: hidden;
  }
  .term-input-wrap:focus-within { border-color: var(--accent); }
  .term-input-wrap.disabled { opacity: .45; pointer-events: none; }

  /* Attachment thumbnails inside the container */
  .term-attachments {
    display: flex; flex-wrap: wrap; gap: 8px; padding: 10px 12px 0;
  }
  .term-attachments:empty { display: none; }
  .attach-item {
    position: relative; width: 72px; height: 72px;
    border-radius: var(--radius); overflow: hidden; flex-shrink: 0;
    background: rgba(0,0,0,.3);
  }
  .attach-img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .attach-rm {
    position: absolute; top: 3px; right: 3px;
    width: 18px; height: 18px;
    background: rgba(0,0,0,.8); color: #fff; border: none;
    border-radius: 50%; font-size: 13px; line-height: 18px;
    text-align: center; cursor: pointer; padding: 0;
    opacity: 0; transition: opacity .1s, background .1s;
  }
  .attach-item:hover .attach-rm { opacity: 1; }
  .attach-rm:hover { background: var(--red); }
  .attach-item.uploading { opacity: .7; }
  .attach-uploading {
    position: absolute; inset: 0;
    background: rgba(0,0,0,.5);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 18px;
  }

  /* Textarea — borderless inside container */
  .term-input {
    width: 100%; background: none; border: none; outline: none;
    padding: 10px 12px 4px; color: var(--text);
    font-family: var(--mono); font-size: 13px;
    resize: none; overflow-y: hidden; line-height: 1.5;
    min-height: 42px; max-height: 160px;
    display: block; box-sizing: border-box;
  }
  .term-input.scrollable { overflow-y: auto; }
  .term-input::placeholder { color: var(--muted); }

  /* Bottom action row */
  .term-input-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 4px 8px 8px;
  }
  .term-attach-btn {
    background: none; border: none; border-radius: var(--radius-sm);
    color: var(--muted); width: 32px; height: 32px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; padding: 0; transition: color .12s, background .12s;
  }
  .term-attach-btn:hover:not(:disabled) { color: var(--text); background: rgba(255,255,255,.06); }
  .term-attach-btn:disabled { opacity: .3; cursor: not-allowed; }
  .term-send-btn {
    background: var(--accent); border: none; color: #fff;
    padding: 6px 16px; border-radius: var(--radius-sm); font-size: 12px;
    cursor: pointer; font-family: var(--mono); transition: opacity .12s;
    line-height: 1.4;
  }
  .term-send-btn:hover:not(:disabled) { opacity: .85; }
  .term-send-btn:disabled { opacity: .35; cursor: not-allowed; }
  .term-output-wrap { position: relative; flex: 1; overflow: hidden; display: flex; flex-direction: column; }
  .term-output-wrap .term-output { flex: 1; }
  .term-float-ctrlc {
    display: none; /* shown only on mobile */
    position: fixed; right: 10px; z-index: 100;
    background: rgba(0,0,0,.5); border: 1px solid var(--border);
    color: var(--muted); font-size: 11px; padding: 4px 10px;
    border-radius: var(--radius-sm); cursor: pointer; font-family: var(--mono);
    backdrop-filter: blur(4px); transition: opacity .15s;
  }
  .term-float-ctrlc:hover:not(:disabled) { border-color: var(--red); color: var(--red); }
  .term-float-ctrlc:disabled { opacity: 0; pointer-events: none; }

  /* iOS paste tip */
  .attach-tip {
    font-size: 11px; color: var(--sub); text-align: center;
    max-height: 0; overflow: hidden; opacity: 0;
    transition: max-height .2s, opacity .2s, padding .2s; padding: 0 12px;
  }
  .attach-tip.visible { max-height: 2em; opacity: 1; padding: 6px 12px 0; }

  /* Drop-zone overlay on output area */
  .term-output { position: relative; }
  .term-output.drag-over::after {
    content: '拖放图片';
    position: absolute; inset: 0;
    background: rgba(var(--accent-rgb), .1);
    border: 2px dashed var(--accent);
    border-radius: var(--radius-sm);
    display: flex; align-items: center; justify-content: center;
    color: var(--accent); font-size: 13px;
    pointer-events: none; z-index: 5;
  }

  /* ── Global toast ── */
  #dev-toast {
    position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
    background: rgba(30,35,50,.95); border: 1px solid var(--border);
    color: var(--text); font-size: 13px; padding: 10px 18px;
    border-radius: var(--radius); z-index: 9999; pointer-events: none;
    opacity: 0; transition: opacity .2s; white-space: nowrap;
    max-width: 90vw; overflow: hidden; text-overflow: ellipsis;
  }
  #dev-toast.show { opacity: 1; }

  /* ── Mobile: master-detail (≤ 900px) ── */
  @media (max-width: 900px) {
    .topbar { padding: 0 14px; gap: 8px; height: 48px; }
    .topbar-logo { letter-spacing: 1px; }
    .topbar-logo .logo-m { font-size: 20px; }
    .topbar-logo .logo-ira { font-size: 14px; }
    .topbar-logo .logo-cursor { font-size: 16px; }
    .topbar-page-title { display: none; }
    .topbar-sep { display: none; }
    .dev-page { height: calc(100dvh - 48px); }

    .term-sidebar { width: 100%; flex: 1; border-right: none; }
    .term-sidebar-header { padding: 14px 16px 10px; font-size: 11px; letter-spacing: .5px; text-transform: none; font-weight: 700; }
    .term-sidebar-footer { display: none; }
    #term-pane-list { padding: 0; }
    .term-pane-row {
      position: relative;
      padding: 14px 48px 14px 16px;
      border-left: none;
      border-bottom: 1px solid var(--border);
      border-radius: 0;
      gap: 10px;
    }
    .term-pane-row::after {
      content: '›';
      position: absolute; right: 16px; top: 50%;
      transform: translateY(-50%);
      color: var(--muted); font-size: 22px; line-height: 1;
    }
    .term-pane-row:hover { border-left-color: transparent; }
    .term-pane-row.active { border-left-color: transparent; background: rgba(var(--accent-rgb),.08); }
    .term-pane-dot { margin-top: 6px; }
    .term-pane-name { font-size: 14px; }
    .term-pane-proj { font-size: 12px; margin-top: 3px; }
    .term-pane-cmd  { font-size: 10px; }

    .term-main { display: none; }
    .dev-page.detail-open .term-sidebar { display: none; }
    .dev-page.detail-open .term-main { display: flex; flex: 1; }
    .term-back-btn { display: inline-flex; align-items: center; }

    /* titlebar quick buttons hidden on mobile */
    .term-quickbtns { display: none; }

    /* output area — bottom padding set by JS to avoid inputbar overlap */
    .term-output { font-size: 11px; padding: 8px 0; }
    .out-block { margin: 0 8px 8px; border-radius: var(--radius-sm); }
    .out-ln { width: 2.4em; font-size: .75em; padding: 0 .4em 0 .3em; }
    .out-code { padding: 0 10px; }
    .out-lang-gutter { width: 2.4em; }
    .out-pre { padding: 8px 10px; }

    /* ── Fixed input bar above keyboard ── */
    .dev-page.detail-open .term-inputbar {
      position: fixed;
      left: 0; right: 0; bottom: 0;
      z-index: 40;
      padding: 0 0 max(8px, env(safe-area-inset-bottom, 8px));
      flex-direction: column;
      gap: 0;
    }

    .term-inputbar { padding: 8px 10px 10px; }
    .term-input { font-size: 16px; /* prevent iOS zoom */ }
    .term-send-btn { font-size: 14px; padding: 8px 20px; border-radius: var(--radius-sm); }
    .term-float-ctrlc { display: block; }
    .term-attach-btn { width: 40px; height: 40px; }
    .attach-item { width: 60px; height: 60px; }
  }
"""

    page_js = r"""
// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── ANSI renderer ─────────────────────────────────────────────────────────────
const _FG = {
  30:'var(--ansi-k)', 31:'var(--ansi-r)', 32:'var(--ansi-g)', 33:'var(--ansi-y)',
  34:'var(--ansi-b)', 35:'var(--ansi-m)', 36:'var(--ansi-c)', 37:'var(--ansi-w)',
  90:'var(--ansi-K)', 91:'var(--ansi-R)', 92:'var(--ansi-G)', 93:'var(--ansi-Y)',
  94:'var(--ansi-B)', 95:'var(--ansi-M)', 96:'var(--ansi-C)', 97:'var(--ansi-W)',
};
const _BG = {
  40:'var(--ansi-k)', 41:'var(--ansi-r)', 42:'var(--ansi-g)', 43:'var(--ansi-y)',
  44:'var(--ansi-b)', 45:'var(--ansi-m)', 46:'var(--ansi-c)', 47:'var(--ansi-w)',
  100:'var(--ansi-K)', 101:'var(--ansi-R)', 102:'var(--ansi-G)', 103:'var(--ansi-Y)',
  104:'var(--ansi-B)', 105:'var(--ansi-M)', 106:'var(--ansi-C)', 107:'var(--ansi-W)',
};

function _256color(n) {
  if (n < 8)   return _FG[n + 30];
  if (n < 16)  return _FG[n + 82];  // bright: 90-97
  if (n < 232) {
    n -= 16;
    const b = n % 6, g = Math.floor(n / 6) % 6, r = Math.floor(n / 36);
    const c = v => v ? v * 40 + 55 : 0;
    return 'rgb(' + c(r) + ',' + c(g) + ',' + c(b) + ')';
  }
  const v = Math.round((n - 232) * 10.2 + 8);
  return 'rgb(' + v + ',' + v + ',' + v + ')';
}

// Convert one line of terminal output (may contain ANSI escapes) → safe HTML.
function _ansiLine(line) {
  const RE = /\x1b\[([0-9;]*)([A-Za-z])/g;
  let out = '', last = 0, spanOpen = false;
  let fg = null, bg = null, bold = false, dim = false, ital = false, ul = false;

  function _hasStyle() { return fg || bg || bold || dim || ital || ul; }
  function _close() { if (spanOpen) { out += '</span>'; spanOpen = false; } }
  function _open() {
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
  }

  let m;
  while ((m = RE.exec(line)) !== null) {
    if (m.index > last) { _open(); out += escHtml(line.slice(last, m.index)); }
    last = RE.lastIndex;
    if (m[2] !== 'm') continue;  // only handle SGR
    _close();
    const ps = m[1] ? m[1].split(';') : ['0'];
    let i = 0;
    while (i < ps.length) {
      const p = +ps[i] || 0;
      if (p === 0)  { fg = bg = null; bold = dim = ital = ul = false; }
      else if (p === 1)  bold = true;
      else if (p === 2)  dim  = true;
      else if (p === 3)  ital = true;
      else if (p === 4)  ul   = true;
      else if (p === 22) { bold = false; dim = false; }
      else if (p === 23) ital = false;
      else if (p === 24) ul   = false;
      else if (_FG[p])   fg   = _FG[p];
      else if (p === 38) {
        if (ps[i+1] === '5')            { fg = _256color(+ps[i+2]); i += 2; }
        else if (ps[i+1] === '2')       { fg = 'rgb('+ps[i+2]+','+ps[i+3]+','+ps[i+4]+')'; i += 4; }
      }
      else if (p === 39) fg = null;
      else if (_BG[p])   bg = _BG[p];
      else if (p === 48) {
        if (ps[i+1] === '5')            { bg = _256color(+ps[i+2]); i += 2; }
        else if (ps[i+1] === '2')       { bg = 'rgb('+ps[i+2]+','+ps[i+3]+','+ps[i+4]+')'; i += 4; }
      }
      else if (p === 49) bg = null;
      i++;
    }
  }
  if (last < line.length) { _open(); out += escHtml(line.slice(last)); }
  _close();
  return out;
}

// Strip ANSI escape codes from a string.
function _stripAnsi(s) {
  return s.replace(/\x1b\[[0-9;]*[A-Za-z]/g, '');
}

// Try hljs syntax highlighting on a chunk (strips ANSI first).
// Returns hljs result or null if unrecognised.
function _hljsChunk(lines) {
  if (!window.hljs) return null;
  const plain = _stripAnsi(lines.join('\n'));
  if (!plain.trim()) return null;
  try {
    const r = window.hljs.highlightAuto(plain);
    // Accept if hljs named a language, even with low confidence
    if (!r.language) return null;
    return r;
  } catch(e) { return null; }
}

// Render full output text as code-editor blocks grouped by blank lines.
function _renderOutput(text) {
  if (!text || !text.trim()) return '';
  const lines = text.split('\n');
  if (lines.length && lines[lines.length - 1] === '') lines.pop();
  if (!lines.length) return '';

  // Split into chunks separated by blank lines
  const chunks = [];
  let cur = [];
  lines.forEach(function(line) {
    if (line.trim() === '' && cur.length) {
      chunks.push(cur);
      cur = [];
    } else {
      cur.push(line);
    }
  });
  if (cur.length) chunks.push(cur);

  let globalLine = 0;
  const pad = String(lines.length).length;

  return chunks.map(function(chunk) {
    // Always try hljs (strips ANSI internally); use it when a language is detected
    const hl = _hljsChunk(chunk);
    if (hl) {
      globalLine += chunk.length;
      return '<div class="out-block out-block-syntax">' +
        '<div class="out-lang-gutter">' + escHtml(hl.language) + '</div>' +
        '<pre class="out-pre"><code>' + hl.value + '</code></pre>' +
        '</div>';
    }

    // Fallback: line-by-line ANSI rendering with line numbers
    const rows = chunk.map(function(line) {
      globalLine++;
      return '<div class="out-line">' +
        '<span class="out-ln">' + String(globalLine).padStart(pad, '\u00a0') + '</span>' +
        '<span class="out-code">' + _ansiLine(line) + '</span>' +
        '</div>';
    }).join('');
    return '<div class="out-block">' + rows + '</div>';
  }).join('');
}

// ── State ─────────────────────────────────────────────────────────────────────
let _currentTarget = null;
let _pollTimer = null;
let _pollGen = 0;
let _autoScroll = true;
const _paneState  = {};  // last known state per target
let _bgPollTimer  = null;

// ── State detection ────────────────────────────────────────────────────────────
function _detectState(text) {
  if (!text || !text.trim()) return 'idle';
  const lines = text.trimEnd().split('\n').filter(function(l) { return l.trim(); });
  if (!lines.length) return 'idle';
  const last = lines[lines.length - 1];
  const tail = lines.slice(-6).join('\n');
  if (/\(y\/n\)|\[Y\/n\]|\[y\/N\]|yes\/no|Do you want|Shall I|Would you like|proceed\?|continue\?|Are you sure/i.test(tail))
    return 'confirm';
  if (/\b(Error:|ERROR:|✗|FAILED|Exception:|Traceback|SyntaxError|TypeError|ValueError|ModuleNotFound)\b/.test(tail))
    return 'error';
  if (/✓|✅|\bDone\b|\bCompleted\b|\bAll done\b|\bSuccess\b|\bfinished\b|\* \w+ for \d/i.test(tail))
    return 'done';
  if (/[$❯>%#]\s*$/.test(last))
    return 'idle';
  return 'running';
}

function _updateTitleState(state) {
  const badge = document.getElementById('term-state-badge');
  if (!badge) return;
  const cfg = {
    confirm: { text: '需要确认', color: 'var(--orange)' },
    error:   { text: '出错',     color: 'var(--red)' },
    done:    { text: '完成',     color: 'var(--green)' },
    running: { text: '运行中',   color: 'var(--accent-light)' },
    idle:    { text: '',         color: '' },
  }[state] || { text: '', color: '' };
  badge.textContent = cfg.text;
  badge.style.color = cfg.color;
  badge.style.borderColor = cfg.color;
  badge.style.display = cfg.text ? '' : 'none';
}

function _maybeNotify(target, state) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const label = { confirm: '需要你确认操作', done: '任务完成了', error: '遇到了错误' }[state];
  if (!label) return;
  new Notification('Mira · ' + target, { body: label, silent: false });
}

function _onStateChange(target, newState) {
  const prev = _paneState[target];
  _paneState[target] = newState;
  if (newState === prev) return;

  // Always sync dot in sidebar, regardless of whether this is the current pane
  const row = document.querySelector(`.term-pane-row[data-target="${CSS.escape(target)}"]`);
  if (row) {
    const dot = row.querySelector('.term-pane-dot');
    if (dot) dot.className = 'term-pane-dot ' + (newState || 'inactive');
  }

  if (target === _currentTarget) {
    _updateTitleState(newState);
    if (newState === 'confirm' || newState === 'done' || newState === 'error') {
      _maybeNotify(target, newState);
    }
    return;
  }

  // Background pane reached a notable state
  if (newState === 'confirm' || newState === 'done' || newState === 'error') {
    _maybeNotify(target, newState);
  }
}

// ── Background polling (inactive panes) ───────────────────────────────────────
// Only polls panes that are in 'running' state (i.e. a command was sent).
// Stops checking a pane once it reaches a stable state (confirm/done/error).
async function _bgPoll() {
  const rows = document.querySelectorAll('.term-pane-row');
  for (const row of rows) {
    const target = row.dataset.target;
    if (target === _currentTarget) continue;
    // Only poll panes explicitly in 'running' state
    if (_paneState[target] !== 'running') continue;
    try {
      const res = await fetch(
        '/api/terminals/' + encodeURIComponent(target) + '/output?lines=30',
        {headers: _authHeaders()});
      if (!res.ok) continue;
      const data = await res.json();
      _onStateChange(target, _detectState(data.output || ''));
    } catch(e) {}
  }
  _bgPollTimer = setTimeout(_bgPoll, 4000);
}

// Request notification permission on first interaction
function _initNotifications() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}
document.addEventListener('click', _initNotifications, { once: true });

// ── Pane list ─────────────────────────────────────────────────────────────────
async function loadPanes() {
  if (!_isAdmin) { openLoginModal(init); return; }
  try {
    const res = await fetch('/api/dev/panes', {headers: _authHeaders()});
    if (res.status === 401) { openLoginModal(init); return; }
    if (!res.ok) return;
    const panes = await res.json();
    const list = document.getElementById('term-pane-list');
    if (!panes.length) {
      list.innerHTML = `<div class="term-empty-sidebar">暂无活跃终端<br><br><code>mira term &lt;project&gt;</code><br>启动新会话</div>`;
      return;
    }
    list.innerHTML = panes.map(function(p) {
      const st = _paneState[p.target];
      const dotCls = !st ? 'inactive' : st === 'idle' ? 'idle' : st;
      return `<div class="term-pane-row${_currentTarget === p.target ? ' active' : ''}"
           data-target="${escHtml(p.target)}"
           data-cmd="${escHtml(p.command || '')}">
        <div class="term-pane-dot ${dotCls}"></div>
        <div class="term-pane-info">
          <div class="term-pane-name">${escHtml(p.label)}</div>
          <div class="term-pane-proj">${escHtml(p.project_id || p.target)}</div>
          ${p.command ? `<div class="term-pane-cmd">${escHtml(p.command)}</div>` : ''}
        </div>
      </div>`;
    }).join('');
    list.querySelectorAll('.term-pane-row').forEach(row => {
      row.addEventListener('click', () => selectPane(row.dataset.target, row.dataset.cmd));
    });
    const targets = new Set(panes.map(p => p.target));
    if (_currentTarget && !targets.has(_currentTarget)) {
      _currentTarget = null; stopPoll();
    }
  } catch(e) { console.warn('dev panes:', e); }
}

// ── Pane selection ────────────────────────────────────────────────────────────
function selectPane(target, cmd) {
  // Freeze the departing pane's dot at its current state before switching
  const prev = _currentTarget;
  if (prev && prev !== target) {
    const prevState = _paneState[prev];
    const prevRow = document.querySelector(`.term-pane-row[data-target="${CSS.escape(prev)}"]`);
    if (prevRow) {
      const dot = prevRow.querySelector('.term-pane-dot');
      if (dot) dot.className = 'term-pane-dot ' + (prevState || 'idle');
    }
  }
  _pollGen++;
  _currentTarget = target;
  _autoScroll = true;
  document.querySelectorAll('.term-pane-row').forEach(r =>
    r.classList.toggle('active', r.dataset.target === target));
  document.getElementById('term-title').textContent = target + (cmd ? '  ·  ' + cmd : '');
  document.getElementById('term-input-wrap').classList.remove('disabled');
  document.getElementById('term-send-btn').disabled = false;
  document.getElementById('btn-attach').disabled = false;
  document.getElementById('btn-mobile-ctrlc').disabled = false;
  document.getElementById('term-output').innerHTML = '';
  _clearAttachments();
  document.getElementById('dev-page').classList.add('detail-open');
  stopPoll();
  fetchOutputOnce();  // show current state, don't loop
  // mobile: update bar position then focus input
  setTimeout(() => {
    _updateInputBarPos();
    if (_isMobile()) {
      const inp = document.getElementById('term-input');
      if (inp) inp.focus();
    }
  }, 50);
}

function goBackToList() {
  stopPoll();
  _currentTarget = null;
  document.getElementById('dev-page').classList.remove('detail-open');
  document.getElementById('term-input-wrap').classList.add('disabled');
  document.getElementById('term-send-btn').disabled = true;
  document.getElementById('btn-attach').disabled = true;
  document.getElementById('btn-mobile-ctrlc').disabled = true;
  document.getElementById('term-title').textContent = '';
  _clearAttachments();
  document.getElementById('term-output').innerHTML =
    `<div class="term-empty"><div style="font-size:28px;opacity:.3">⬛</div><div>从左侧选择一个终端</div><div><code>mira term &lt;project&gt;</code> 启动新会话</div></div>`;
}

// ── Output polling ────────────────────────────────────────────────────────────
// Polling only runs while a command is in-flight.
// sendKeys() starts it; reaching a stable state (confirm/done/error) stops it.

function startPoll() {
  if (_pollTimer) return;
  _pollTimer = setTimeout(runPoll, 0);
}
function stopPoll() {
  if (_pollTimer) { clearTimeout(_pollTimer); _pollTimer = null; }
  _pollGen++;
}
async function runPoll() {
  if (!_pollTimer) return;
  await fetchOutput();
  if (_pollTimer) _pollTimer = setTimeout(runPoll, 500);
}

// Fetch output once (no loop) — used when selecting a pane.
async function fetchOutputOnce() {
  if (!_currentTarget) return;
  const gen = _pollGen;
  try {
    const res = await fetch(
      `/api/terminals/${encodeURIComponent(_currentTarget)}/output?lines=200`,
      {headers: _authHeaders()});
    if (_pollGen !== gen || !res.ok) return;
    const data = await res.json();
    _applyOutput(data.output || '');
    const state = _detectState(data.output || '');
    _updateTitleState(state);
    _paneState[_currentTarget] = state;
    // If already running when selected, start fast poll automatically
    if (state === 'running') startPoll();
  } catch(e) {}
}

async function fetchOutput() {
  if (!_currentTarget) return;
  const gen = _pollGen;
  try {
    const res = await fetch(
      `/api/terminals/${encodeURIComponent(_currentTarget)}/output?lines=200`,
      {headers: _authHeaders()});
    if (_pollGen !== gen || !res.ok) return;
    const data = await res.json();
    _applyOutput(data.output || '');
    const state = _detectState(data.output || '');
    _onStateChange(_currentTarget, state);
    // Stop polling once we reach a stable state
    if (state === 'confirm' || state === 'done' || state === 'error') {
      stopPoll();
    }
  } catch(e) {}
}

function _applyOutput(text) {
  const el = document.getElementById('term-output');
  if (!el) return;
  const distFromBottom = el.scrollHeight - el.scrollTop;
  const html = _renderOutput(text);
  if (html) {
    el.innerHTML = html;
  } else if (!el.querySelector('.out-line')) {
    el.innerHTML = '<div class="term-empty" style="padding:40px 16px"><div style="font-size:22px;opacity:.25">▋</div><div>等待输出…</div></div>';
  }
  if (_autoScroll) {
    el.scrollTop = el.scrollHeight;
  } else {
    el.scrollTop = el.scrollHeight - distFromBottom;
  }
}

document.getElementById('term-output').addEventListener('scroll', function() {
  _autoScroll = Math.abs(this.scrollHeight - this.scrollTop - this.clientHeight) < 60;
});

// ── Textarea auto-resize ─────────────────────────────────────────────────────
function _resizeInput() {
  const ta = document.getElementById('term-input');
  if (!ta) return;
  ta.style.height = 'auto';
  const maxH = _isMobile() ? 160 : 120;
  const newH = Math.min(ta.scrollHeight, maxH);
  ta.style.height = newH + 'px';
  ta.classList.toggle('scrollable', ta.scrollHeight > maxH);
  _updateInputBarPos();
}

(function _bindTextarea() {
  const ta = document.getElementById('term-input');
  ta.addEventListener('input', _resizeInput);
  ta.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendKeys();
    }
  });
})();

// ── Send ──────────────────────────────────────────────────────────────────────
let _pendingSend = false; // set when user clicks send while upload in progress

function sendKeys() {
  if (!_currentTarget) {
    _showAttachTip('请先从左侧选择终端');
    return;
  }
  const ta = document.getElementById('term-input');
  let text = ta.value.trimEnd();

  // If still uploading, queue the send for when upload completes
  const uploading = _attachments.filter(function(a) { return a.uploading; });
  if (uploading.length) {
    _pendingSend = true;
    _showAttachTip('图片上传中，完成后自动发送…');
    return;
  }

  // Inject image-reading instructions for all uploaded attachments
  const uploaded = _attachments.filter(function(a) { return a.path; });
  if (uploaded.length) {
    const imgInstr = uploaded.map(function(a) { return '请读取图片文件: ' + a.path; }).join('\n');
    text = imgInstr + (text ? '\n' + text : '');
  }

  _pendingSend = false;
  ta.value = '';
  ta.style.height = '';
  ta.classList.remove('scrollable');
  // Reset state and start polling for this command's response
  _paneState[_currentTarget] = 'running';
  _updateTitleState('running');
  stopPoll();
  startPoll();
  fetch(`/api/terminals/${encodeURIComponent(_currentTarget)}/send`, {
    method: 'POST',
    headers: _authHeaders({'Content-Type': 'application/json'}),
    body: JSON.stringify({keys: text ? text + '\n' : '\n'})
  }).catch(() => {});
  _clearAttachments();
  if (_isMobile()) { ta.focus(); _updateInputBarPos(); }
}
function sendRaw(keys) {
  if (!_currentTarget) return;
  fetch(`/api/terminals/${encodeURIComponent(_currentTarget)}/send`, {
    method: 'POST',
    headers: _authHeaders({'Content-Type': 'application/json'}),
    body: JSON.stringify({keys})
  }).catch(() => {});
}
document.getElementById('btn-ctrlc').addEventListener('click', () => sendRaw('C-c'));
document.getElementById('btn-enter').addEventListener('click', () => sendRaw('\n'));

// ── Image attachments ─────────────────────────────────────────────────────────
let _attachments = [];
let _attachSeq = 0;

async function _addAttachment(file, autoSend) {
  if (!file || !file.type.startsWith('image/')) return;
  const id = ++_attachSeq;
  const url = URL.createObjectURL(file);
  _attachments.push({id, url, name: file.name, path: null, uploading: true});
  _renderAttachments();
  _updateInputBarPos();
  try {
    const form = new FormData();
    form.append('file', file, file.name);
    const res = await fetch('/api/upload/image', {
      method: 'POST',
      headers: _authHeaders(),
      body: form
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.status);
    const data = await res.json();
    const att = _attachments.find(function(a) { return a.id === id; });
    if (!att) return;
    att.path = data.path;
    att.uploading = false;
    _renderAttachments();
    if (autoSend || (_pendingSend && !_attachments.some(function(a) { return a.uploading; }))) {
      sendKeys();
    } else {
      _showAttachTip('图片已上传 ✓ 可以发送了');
    }
  } catch(e) {
    console.warn('image upload failed:', e);
    _showAttachTip('图片上传失败：' + (e.message || '未知错误'));
    const idx = _attachments.findIndex(function(a) { return a.id === id; });
    if (idx >= 0) { URL.revokeObjectURL(_attachments[idx].url); _attachments.splice(idx, 1); }
    _renderAttachments();
    _updateInputBarPos();
  }
}

function _removeAttachment(id) {
  const idx = _attachments.findIndex(function(a) { return a.id === id; });
  if (idx < 0) return;
  const att = _attachments[idx];
  URL.revokeObjectURL(att.url);
  _attachments.splice(idx, 1);
  _renderAttachments();
  _updateInputBarPos();
}

function _clearAttachments() {
  _attachments.forEach(function(a) { URL.revokeObjectURL(a.url); });
  _attachments = [];
  _renderAttachments();
}

function _renderAttachments() {
  const el = document.getElementById('term-attachments');
  if (!_attachments.length) { el.innerHTML = ''; return; }
  el.innerHTML = _attachments.map(function(a) {
    return '<div class="attach-item' + (a.uploading ? ' uploading' : '') + '">' +
      '<img class="attach-img" src="' + a.url + '" alt="' + escHtml(a.name) + '">' +
      (a.uploading
        ? '<div class="attach-uploading">↑</div>'
        : '<button class="attach-rm" onclick="_removeAttachment(' + a.id + ')" title="移除">×</button>') +
      '</div>';
  }).join('');
}

// paste image from clipboard (Cmd+V with screenshot) — catches paste anywhere on page
document.addEventListener('paste', function(e) {
  const items = e.clipboardData && e.clipboardData.items;
  if (!items) {
    _showAttachTip('粘贴事件触发，但 clipboardData 为空');
    return;
  }
  const types = Array.from(items).map(function(it) { return it.type; });
  _showAttachTip('粘贴内容: ' + (types.join(', ') || '空'));
  for (let i = 0; i < items.length; i++) {
    if (items[i].type.startsWith('image/')) {
      e.preventDefault();
      _addAttachment(items[i].getAsFile(), true);
      return;
    }
  }
});

// iOS detection — file picker always triggers action sheet, use paste instead
function _isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

// Attach button: open file picker on all platforms
document.getElementById('btn-attach').addEventListener('click', function() {
  document.getElementById('term-file-input').click();
});
document.getElementById('term-file-input').addEventListener('change', function() {
  Array.from(this.files).forEach(_addAttachment);
  this.value = '';
});

// Global toast (visible anywhere on page)
let _toastTimer = null;
function _showAttachTip(msg) {
  const el = document.getElementById('dev-toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(function() { el.classList.remove('show'); }, 3000);
}

// drag & drop onto output area
(function() {
  const out = document.getElementById('term-output');
  out.addEventListener('dragover', function(e) {
    e.preventDefault(); e.dataTransfer.dropEffect = 'copy';
    this.classList.add('drag-over');
  });
  out.addEventListener('dragleave', function(e) {
    if (!this.contains(e.relatedTarget)) this.classList.remove('drag-over');
  });
  out.addEventListener('drop', function(e) {
    e.preventDefault(); this.classList.remove('drag-over');
    Array.from(e.dataTransfer.files).forEach(_addAttachment);
  });
})();

// ── Mobile: fix inputbar above keyboard ──────────────────────────────────────
function _isMobile() { return window.innerWidth <= 900; }

function _updateInputBarPos() {
  if (!_isMobile()) return;
  const bar = document.querySelector('.term-inputbar');
  const out = document.getElementById('term-output');
  const ctrlc = document.getElementById('btn-mobile-ctrlc');
  if (!bar || !out) return;

  if (window.visualViewport) {
    const vvTop    = window.visualViewport.offsetTop;
    const vvHeight = window.visualViewport.height;
    const pageH    = document.documentElement.scrollHeight;
    const fromBottom = pageH - (vvTop + vvHeight);
    bar.style.transform = fromBottom > 10
      ? `translateY(-${window.innerHeight - vvHeight - vvTop}px)`
      : '';
  }

  // keep output from going under the fixed bar
  const barH = bar.offsetHeight;
  out.style.paddingBottom = barH + 8 + 'px';

  // pin ⌃C button just below titlebar
  if (ctrlc) {
    const tb = document.querySelector('.term-titlebar');
    const tbBottom = tb ? tb.getBoundingClientRect().bottom : 50;
    ctrlc.style.top = (tbBottom + 8) + 'px';
  }
}

if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', _updateInputBarPos);
  window.visualViewport.addEventListener('scroll', _updateInputBarPos);
}
window.addEventListener('resize', function() {
  _updateInputBarPos();
  _updatePlaceholder();
});

function _updatePlaceholder() {
  const ta = document.getElementById('term-input');
  if (!ta) return;
  ta.placeholder = _isMobile() ? '发送命令…' : '发送命令…   Ctrl+Enter 发送';
}
_updatePlaceholder();

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await _initAuth();
  if (!_isAdmin) { openLoginModal(init); return; }
  await loadPanes();
  setInterval(loadPanes, 5000);
  _bgPoll();
  _updateInputBarPos();
}
init();
"""

    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Dev · Mira</title>\n"
        "<script>document.documentElement.dataset.theme = localStorage.getItem('mira-skin') || 'default';</script>\n"
        '<link rel="stylesheet" href="/static/fonts/fonts.css">\n'
        '<script src="/static/highlight.min.js"></script>\n'
        "<style>\n"
        + theme_vars_css()
        + topbar_css()
        + page_css
        + "</style>\n</head>\n<body>\n\n"
        + topbar_html(title="Dev", back_url="javascript:history.back()", hide_dev=True) + "\n\n"
        + """\
<div class="dev-page" id="dev-page">
  <!-- Sidebar: pane list -->
  <div class="term-sidebar">
    <div class="term-sidebar-header">所有终端</div>
    <div id="term-pane-list">
      <div class="term-empty-sidebar">正在加载…</div>
    </div>
    <div class="term-sidebar-footer">每 5 秒刷新列表</div>
  </div>

  <!-- Main: terminal output -->
  <div class="term-main">
    <div class="term-titlebar">
      <div class="term-title-left">
        <button class="term-back-btn" onclick="goBackToList()">‹</button>
        <span id="term-title"></span>
        <span id="term-state-badge" class="term-state-badge"></span>
      </div>
      <div class="term-quickbtns">
        <button class="term-qbtn" id="btn-ctrlc">Ctrl+C</button>
        <button class="term-qbtn" id="btn-enter">↵ Enter</button>
      </div>
    </div>
    <div class="term-output-wrap">
      <div class="term-output" id="term-output">
        <div class="term-empty">
          <div style="font-size:28px;opacity:.3">⬛</div>
          <div>从左侧选择一个终端</div>
          <div><code>mira term &lt;project&gt;</code> 启动新会话</div>
        </div>
      </div>
      <button class="term-float-ctrlc" id="btn-mobile-ctrlc" disabled onclick="sendRaw('C-c')" title="Ctrl+C">⌃C</button>
    </div>
    <div class="term-inputbar">
      <div class="term-input-wrap disabled" id="term-input-wrap">
        <div class="term-attachments" id="term-attachments"></div>
        <textarea class="term-input" id="term-input" placeholder="发送消息…"
                  autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
                  rows="1"></textarea>
        <div class="term-input-row">
          <button class="term-attach-btn" id="btn-attach" disabled title="添加图片（或直接粘贴截图）">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>
              <path d="m21 15-5-5L5 21"/>
            </svg>
          </button>
          <button class="term-send-btn" id="term-send-btn" onclick="sendKeys()" disabled>发送</button>
        </div>
      </div>
      <input type="file" id="term-file-input"
             accept="image/jpeg,image/png,image/gif,image/webp,image/heic,image/heif"
             multiple style="display:none">
    </div>
  </div>
</div>
<div id="dev-toast"></div>

"""
        + settings_overlay_html() + "\n\n"
        + "<script>\n"
        + topbar_js() + "\n"
        + page_js
        + "</script>\n</body>\n</html>\n"
    )
