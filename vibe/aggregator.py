import re
import json
from pathlib import Path
from typing import Optional
from vibe.models import ProjectInfo, TechStack, DeployInfo, ClaudeActivity, CodexActivity
from vibe.collectors.git import collect_git
from vibe.collectors.plans import collect_plans
from vibe.collectors.service import collect_service
from vibe.collectors.loc import collect_loc
from vibe.collectors.fs import collect_fs
from vibe.collectors.features import collect_features
from vibe.collectors.design_docs import collect_design_docs
from vibe.collectors.deploy import collect_deploy
from vibe.collectors.dependencies import collect_dependencies
from vibe.collectors.claude_sessions import collect_claude_activity
from vibe.collectors.codex_sessions import collect_codex_activity
from vibe.collectors.llm import collect_llm_apis

_ARCH_SECTION_RE = re.compile(r"^#{1,3}\s+(架构|Architecture)", re.IGNORECASE)


def extract_description(path: Path) -> Optional[str]:
    """Extract one-line project description from README.md or vibe.yaml.

    Priority:
    1. vibe.yaml `description` field
    2. First non-empty, non-heading paragraph line in README.md after the title
    """
    # vibe.yaml description takes priority
    vibe_yaml = path / "vibe.yaml"
    if vibe_yaml.exists():
        try:
            import yaml as _yaml
            data = _yaml.safe_load(vibe_yaml.read_text(encoding="utf-8")) or {}
            desc = (data.get("description") or "").strip()
            if desc:
                return desc
        except Exception:
            pass

    readme = path / "README.md"
    if not readme.exists():
        return None

    skipped_title = False
    for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            skipped_title = True
            continue
        if skipped_title and stripped:
            # Strip markdown formatting for display
            text = re.sub(r"[*_`\[\]()]", "", stripped)
            return text[:120] if text else None
    return None


def _safe(fn, *args, default=None):
    """Call fn(*args), returning default on any exception."""
    try:
        return fn(*args)
    except Exception:
        return default


def extract_arch_summary(path: Path) -> Optional[str]:
    """Extract architecture summary: prefer docs/vibe-summary.md, fall back to README ## 架构."""
    # AI-generated summary takes priority
    vibe_summary = path / "docs" / "vibe-summary.md"
    if vibe_summary.exists():
        try:
            return vibe_summary.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            pass

    readme = path / "README.md"
    if not readme.exists():
        return None

    lines_in_section = []
    in_section = False
    for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        if _ARCH_SECTION_RE.match(line):
            in_section = True
            continue
        if in_section and line.startswith("#"):
            break
        if in_section:
            lines_in_section.append(line)

    text = "\n".join(lines_in_section).strip()
    return text if text else None


def extract_tech_stack(path: Path, vibe_cfg: Optional[dict] = None) -> list[TechStack]:
    """Extract tech stack from pyproject.toml, package.json, and vibe.yaml."""
    stack = []

    # vibe.yaml manual overrides
    if vibe_cfg:
        for item in vibe_cfg.get("tech_stack", []):
            if isinstance(item, str):
                stack.append(TechStack(name=item))
            elif isinstance(item, dict) and "name" in item:
                stack.append(TechStack(name=item["name"]))

    # pyproject.toml
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                tomllib = None

        if tomllib:
            try:
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                deps = data.get("project", {}).get("dependencies", [])
                for dep in deps:
                    # Parse "fastapi>=0.110" -> "fastapi"
                    name = re.split(r"[>=<!;\[]", dep)[0].strip().lower()
                    if name:
                        stack.append(TechStack(name=name))
            except Exception:
                pass

    # package.json
    pkg_json = path / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text())
            for name in list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys()):
                # Handle @scope/package -> scope/package (keep scope for clarity)
                display_name = name[1:] if name.startswith("@") else name
                stack.append(TechStack(name=display_name))
        except Exception:
            pass

    # Deduplicate and cap at 20
    seen = set()
    result = []
    for t in stack:
        if t.name not in seen:
            seen.add(t.name)
            result.append(t)

    return result[:20]


def _extract_deploy(vibe_cfg: Optional[dict]) -> Optional[DeployInfo]:
    """Extract deployment info from vibe config."""
    if not vibe_cfg or "deploy" not in vibe_cfg:
        return None

    d = vibe_cfg["deploy"]
    return DeployInfo(
        type=d.get("type", "none"),
        host=d.get("host"),
        user=d.get("user"),
        remote_dir=d.get("remote_dir"),
        process=d.get("process"),
        url=d.get("url"),
        cmd=d.get("cmd"),
    )


def collect_project(path: Path, name: str, vibe_cfg: Optional[dict]) -> ProjectInfo:
    """Orchestrate all collectors into a ProjectInfo object."""
    project_id = path.name
    status = (vibe_cfg or {}).get("status", "active")

    return ProjectInfo(
        id=project_id,
        name=name,
        path=str(path),
        status=status,
        description=_safe(extract_description, path),
        tech_stack=_safe(extract_tech_stack, path, vibe_cfg, default=[]),
        git=_safe(collect_git, path),
        plans=_safe(collect_plans, path),
        service=_safe(collect_service, path, vibe_cfg),
        loc=_safe(collect_loc, path),
        fs=_safe(collect_fs, path),
        features=_safe(collect_features, path, default=[]),
        design_docs=_safe(collect_design_docs, path, default=[]),
        deploy=_safe(collect_deploy, path, vibe_cfg),
        arch_summary=_safe(extract_arch_summary, path),
        external_deps=_safe(collect_dependencies, path, default=[]),
        llm_apis=_safe(collect_llm_apis, path, default=[]),
        claude_activity=_safe(_collect_claude, str(path), (vibe_cfg or {}).get("aliases", [])),
        codex_activity=_safe(_collect_codex, str(path)),
    )


def _collect_claude(project_path: str, aliases: list | None = None) -> Optional[ClaudeActivity]:
    data = collect_claude_activity(project_path, aliases=aliases)
    if not data:
        return None
    return ClaudeActivity(**data)


def _collect_codex(project_path: str) -> Optional[CodexActivity]:
    data = collect_codex_activity(project_path)
    if not data:
        return None
    return CodexActivity(**data)
