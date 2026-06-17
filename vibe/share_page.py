"""公开分享的设计文档只读页(免登录,任何人可访问)。

内容实时读取:每次访问由 main.public_shared_doc 取当前文档内容传进来,
这里只负责把 markdown 渲染成一个干净的只读页面(复用 detail 页的 simpleMarkdown 与样式)。
"""
import json

from vibe.topbar import theme_vars_css


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# 用 __TOKEN__ 占位再 .replace,避免在含大量 { } 的内嵌 JS 上做 f-string 大括号转义。
_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · __PROJ__</title>
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<style>
__THEME__
  html, body { background: var(--bg); color: var(--text); font-family: var(--mono); }
  .wrap { max-width: 820px; margin: 0 auto; padding: 48px 24px 96px; }
  .doc-title { font-size: 24px; font-weight: 700; color: var(--text); margin-bottom: 6px; word-break: break-word; }
  .doc-meta { font-size: 12px; color: var(--muted); margin-bottom: 32px; }
  .doc-content { font-size: 14px; color: var(--sub); line-height: 1.85; }
  .doc-content h1,.doc-content h2,.doc-content h3 { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: var(--gold); margin: 24px 0 10px; padding-bottom: 5px; border-bottom: 1px solid rgba(217,179,107,.15); }
  .doc-content h1:first-child,.doc-content h2:first-child { margin-top: 0; }
  .doc-content p { margin: 0 0 12px; }
  .doc-content ul { margin: 4px 0 12px 20px; }
  .doc-content li { margin-bottom: 4px; }
  .doc-content strong { color: var(--text); }
  .doc-content code { font-family: var(--mono); font-size: 12px; background: rgba(255,255,255,.07); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 1px 6px; color: var(--gold); word-break: break-word; }
  .doc-content pre { background: rgba(0,0,0,.4); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; overflow-x: auto; margin: 12px 0; font-size: 12px; }
  .doc-content pre code { background: none; border: none; padding: 0; }
  .doc-content hr { border: none; border-top: 1px solid var(--border); margin: 18px 0; }
  .doc-content blockquote { border-left: 3px solid var(--gold); padding-left: 14px; color: var(--sub); margin: 0 0 12px; }
  .footer { margin-top: 56px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 11px; color: var(--muted); text-align: center; }
  .footer a { color: var(--accent); text-decoration: none; }
</style>
</head>
<body>
<div class="wrap">
  <div class="doc-title">__TITLE__</div>
  <div class="doc-meta">__FILENAME__ · __PROJ__</div>
  <div class="doc-content" id="content"></div>
  <div class="footer">由 <a href="/">Mira</a> 分享</div>
</div>
<script>
const _MD = __CONTENT_JS__;
function escHtml(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
function simpleMarkdown(md){
  if (!md) return '';
  let t = escHtml(md);
  t = t.replace(/```[\\w]*\\n?([\\s\\S]*?)```/g, (_,c)=>`<pre><code>${c.trim()}</code></pre>`);
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
  t = t.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
  t = t.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  t = t.replace(/^## (.+)$/gm,  '<h2>$1</h2>');
  t = t.replace(/^# (.+)$/gm,   '<h1>$1</h1>');
  t = t.replace(/^---+$/gm, '<hr>');
  t = t.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  t = t.replace(/^[*\\-] (.+)$/gm, '<li>$1</li>');
  t = t.replace(/^\\d+\\. (.+)$/gm, '<li>$1</li>');
  t = t.replace(/(<li>[\\s\\S]*?<\\/li>\\n?)+/g, m=>`<ul>${m}</ul>`);
  t = t.replace(/^(?!<[a-z\\/]|$)(.+)$/gm, '<p>$1</p>');
  return t;
}
document.getElementById('content').innerHTML = simpleMarkdown(_MD);
</script>
</body>
</html>"""


def render_share_page(doc: dict, project_name: str) -> str:
    title = doc.get("title") or doc.get("filename") or "文档"
    filename = doc.get("filename", "")
    content = doc.get("content", "")
    # JSON 编码 + 转义 < ,防止文档里出现 </script> 截断脚本
    content_js = json.dumps(content).replace("<", "\\u003c")
    # 内容最后替换:文档里若恰好含 __TITLE__ 等占位串,也不会被后续 replace 误伤
    return (_TEMPLATE
            .replace("__THEME__", theme_vars_css())
            .replace("__TITLE__", _esc(title))
            .replace("__PROJ__", _esc(project_name))
            .replace("__FILENAME__", _esc(filename))
            .replace("__CONTENT_JS__", content_js))
