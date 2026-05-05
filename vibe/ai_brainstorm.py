# vibe/ai_brainstorm.py
"""AI brainstorm — multi-model project naming & logo generation."""
from __future__ import annotations
import json
import os
import re
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any


_PROVIDERS = [
    {"id": "deepseek",    "label": "DeepSeek",    "key_field": "deepseek_api_key"},
    {"id": "openrouter",  "label": "OpenRouter",   "key_field": "openrouter_api_key"},
    {"id": "gemini",      "label": "Gemini",       "key_field": "gemini_api_key"},
    {"id": "doubao",      "label": "豆包",          "key_field": "doubao_api_key"},
]


def detect_available_models(cfg: dict) -> list[dict]:
    """Return list of {id, label} for providers that have a non-empty API key."""
    result = []
    for p in _PROVIDERS:
        key = (cfg.get(p["key_field"]) or "").strip()
        if key:
            result.append({"id": p["id"], "label": p["label"]})
    return result


_REQUIRED_FIELDS = {"name", "phonetic", "name_meaning", "logo_svg", "logo_meaning"}


def parse_candidates(raw: str) -> list[dict]:
    """Parse AI response into list of candidate dicts. Tolerates markdown fences."""
    text = raw.strip()
    # Strip ```json ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not _REQUIRED_FIELDS.issubset(item.keys()):
            continue
        result.append({k: item[k] for k in _REQUIRED_FIELDS})
    return result


_SYSTEM_PROMPT = """你是一个项目命名专家。用户描述了一个项目想法，请生成3个候选方案。
每个方案包含：
- name: 项目英文名（1个单词，简洁有力，首字母大写）
- phonetic: 国际音标（如 /straɪd/）
- name_meaning: 命名寓意（中文，1-2句，说清楚为什么取这个名字）
- logo_svg: 完整的 SVG 字符串，要求：viewBox="0 0 64 64"，深色背景友好，线条简洁，可用 linearGradient，不要文字，不要外部引用
- logo_meaning: logo图形解读（中文，1-2句，说清楚每个元素代表什么）

返回合法 JSON 数组，不要任何其他内容，不要 markdown 代码块。"""


def _make_payload(model_id: str, description: str, cfg: dict) -> tuple[str, dict, str]:
    """Return (url, headers, body_json) for the given model."""
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": description},
    ]

    if model_id == "deepseek":
        return (
            "https://api.deepseek.com/v1/chat/completions",
            {"Authorization": f"Bearer {cfg.get('deepseek_api_key', '')}", "Content-Type": "application/json"},
            json.dumps({"model": "deepseek-chat", "messages": messages, "temperature": 0.9}),
        )
    if model_id == "openrouter":
        return (
            "https://openrouter.ai/api/v1/chat/completions",
            {"Authorization": f"Bearer {cfg.get('openrouter_api_key', '')}", "Content-Type": "application/json"},
            json.dumps({"model": "anthropic/claude-3.5-haiku", "messages": messages, "temperature": 0.9}),
        )
    if model_id == "gemini":
        key = cfg.get("gemini_api_key") or ""
        if not key:
            raise RuntimeError("Gemini API key 未配置")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
        body = {"contents": [{"parts": [{"text": _SYSTEM_PROMPT + "\n\n" + description}]}]}
        return (url, {"Content-Type": "application/json"}, json.dumps(body))
    if model_id == "doubao":
        return (
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            {"Authorization": f"Bearer {cfg.get('doubao_api_key', '')}", "Content-Type": "application/json"},
            json.dumps({"model": "ep-20250117145003-bpbqm", "messages": messages, "temperature": 0.9}),
        )
    raise ValueError(f"Unknown model: {model_id}")


def _extract_content(model_id: str, resp_data: dict) -> str:
    """Extract text content from API response."""
    try:
        if model_id == "gemini":
            return resp_data["candidates"][0]["content"]["parts"][0]["text"]
        return resp_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"AI 响应格式异常: {e}，原始数据: {str(resp_data)[:200]}")


def call_brainstorm(description: str, model_id: str, cfg: dict) -> list[dict]:
    """Call AI and return parsed candidates. Raises RuntimeError on failure."""
    url, headers, body = _make_payload(model_id, description, cfg)
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        safe_url = url.split("?")[0] if "?" in url else url
        raise RuntimeError(f"AI API 错误 {e.code} ({safe_url}): {e.read().decode()[:200]}")
    except Exception as e:
        raise RuntimeError(f"AI 调用失败: {e}")

    content = _extract_content(model_id, resp_data)
    candidates = parse_candidates(content)
    if not candidates:
        raise RuntimeError(f"AI 返回内容无法解析为候选方案:\n{content[:300]}")
    return candidates


def _slugify(name: str) -> str:
    """'My Project' → 'my-project'"""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _make_vibe_yaml(name: str, description: str, port, domain) -> str:
    import yaml
    data: dict = {"name": name, "description": description}
    if port is not None:
        data["port"] = port
    if domain is not None and domain.strip():
        data["domain"] = domain.strip()
    return yaml.dump(data, allow_unicode=True, default_flow_style=False)


def _derive_favicon(logo_svg: str) -> str:
    """Produce a 32×32 favicon by replacing width/height in the SVG."""
    svg = re.sub(r'width="[^"]*"', 'width="32"', logo_svg)
    svg = re.sub(r'height="[^"]*"', 'height="32"', svg)
    if "viewBox" not in svg:
        svg = svg.replace("<svg", '<svg viewBox="0 0 64 64"', 1)
    return svg


def create_project(
    base_dir,
    name: str,
    description: str,
    logo_svg: str,
    port,
    domain,
) -> dict:
    """Create project directory with vibe.yaml, logo.svg, favicon.svg, git init.

    Returns {"project_id": str, "path": str}.
    Raises FileExistsError if directory already exists.
    """
    base_dir = Path(base_dir)
    project_id = _slugify(name)
    proj_dir = base_dir / project_id

    if proj_dir.exists():
        raise FileExistsError(f"目录已存在: {proj_dir}")

    proj_dir.mkdir(parents=True)
    try:
        (proj_dir / "vibe.yaml").write_text(_make_vibe_yaml(name, description, port, domain), encoding="utf-8")
        (proj_dir / "logo.svg").write_text(logo_svg, encoding="utf-8")
        (proj_dir / "favicon.svg").write_text(_derive_favicon(logo_svg), encoding="utf-8")

        env = {**os.environ,
               "GIT_AUTHOR_NAME": "Mira", "GIT_AUTHOR_EMAIL": "mira@local",
               "GIT_COMMITTER_NAME": "Mira", "GIT_COMMITTER_EMAIL": "mira@local"}
        subprocess.run(["git", "init"], cwd=proj_dir, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=proj_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"init: {name}"],
            cwd=proj_dir, check=True, capture_output=True, env=env,
        )
    except Exception:
        import shutil
        shutil.rmtree(proj_dir, ignore_errors=True)
        raise

    return {"project_id": project_id, "path": str(proj_dir)}
