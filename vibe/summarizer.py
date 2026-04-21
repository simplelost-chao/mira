"""AI-powered project summarizer using Claude API."""
import json
from pathlib import Path
from typing import Optional


def _build_prompt(project_data: dict) -> str:
    """Build a concise prompt from collected project data."""
    name = project_data.get("name", "unknown")
    path = project_data.get("path", "")
    tech_stack = [t["name"] for t in project_data.get("tech_stack", [])]
    loc = project_data.get("loc") or {}
    git = project_data.get("git") or {}
    plans = project_data.get("plans") or {}
    features = project_data.get("features") or []
    design_docs = project_data.get("design_docs") or []
    deploy = project_data.get("deploy") or {}
    service = project_data.get("service") or {}

    sections = [f"项目名称: {name}", f"路径: {path}"]

    if tech_stack:
        sections.append(f"技术栈: {', '.join(tech_stack[:20])}")

    if loc.get("total_lines"):
        langs = [f"{l['name']}({l['code']}行)" for l in (loc.get("languages") or [])[:5]]
        sections.append(f"代码规模: {loc['total_lines']} 总行, {loc['file_count']} 文件 | {', '.join(langs)}")

    if git.get("recent_commits"):
        commits = git["recent_commits"][:5]
        sections.append("最近提交:\n" + "\n".join(f"  - {c}" for c in commits))

    if plans.get("total"):
        plan_files = plans.get("files") or []
        todo_tasks = []
        for pf in plan_files:
            for t in (pf.get("tasks") or []):
                if not t.get("done"):
                    todo_tasks.append(t["text"])
        done = plans["done"]
        total = plans["total"]
        sections.append(f"任务进度: {done}/{total} 完成")
        if todo_tasks:
            sections.append("待办任务 (前10):\n" + "\n".join(f"  - {t}" for t in todo_tasks[:10]))

    if features:
        impl = [f["text"] for f in features if f.get("implemented")][:10]
        todo = [f["text"] for f in features if not f.get("implemented")][:5]
        if impl:
            sections.append("已实现功能:\n" + "\n".join(f"  - {t}" for t in impl))
        if todo:
            sections.append("未实现功能:\n" + "\n".join(f"  - {t}" for t in todo))

    if design_docs:
        titles = [f"{d['filename']}: {d['title']}" for d in design_docs[:5]]
        sections.append("设计文档:\n" + "\n".join(f"  - {t}" for t in titles))
        # Include first doc's content snippet if small enough
        first = design_docs[0]
        content = first.get("content", "")
        if content and len(content) < 3000:
            sections.append(f"\n--- {first['filename']} 内容 ---\n{content[:2000]}")

    if service.get("port"):
        running = "运行中" if service.get("is_running") else "未运行"
        sections.append(f"服务: 端口 {service['port']} ({running})")

    if deploy.get("type") and deploy["type"] != "none":
        url = deploy.get("url", "")
        sections.append(f"部署: {deploy['type']} {url}")

    data_str = "\n".join(sections)

    return f"""你是一个代码项目分析助手。请根据以下项目信息，生成一份简洁的全局面貌总结。

{data_str}

请用中文输出以下格式（markdown，简洁，不超过500字）：

# {name}

**一句话定位**: [项目是什么，解决什么问题]

## 核心架构
[2-3句话描述技术架构和主要模块]

## 技术栈
[列出关键技术，一行]

## 主要功能
[3-5条已实现的核心功能]

## 当前状态
[开发进度、待做的重要事项]

只输出上述内容，不要解释，不要废话。"""


def generate_summary(project_data: dict, model: str = "claude-haiku-4-5-20251001") -> Optional[str]:
    """Call Claude API to generate a project summary. Returns summary text or None on error."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        prompt = _build_prompt(project_data)
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        return None


def write_summary(project_path: Path, summary: str) -> Path:
    """Write summary to docs/vibe-summary.md in the project directory."""
    docs_dir = project_path / "docs"
    docs_dir.mkdir(exist_ok=True)
    summary_file = docs_dir / "vibe-summary.md"
    summary_file.write_text(summary, encoding="utf-8")
    return summary_file


def summarize_project(project_data: dict, force: bool = False) -> tuple[bool, str]:
    """
    Generate and write AI summary for a project.
    Returns (success, message).
    Skips if docs/vibe-summary.md already exists unless force=True.
    """
    path = Path(project_data["path"])
    summary_file = path / "docs" / "vibe-summary.md"

    if summary_file.exists() and not force:
        return False, "skipped (already exists)"

    summary = generate_summary(project_data)
    if summary is None:
        return False, "failed (API error)"

    write_summary(path, summary)
    return True, "ok"
