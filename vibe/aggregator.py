import re
import json
from pathlib import Path
from typing import Optional
from vibe.models import ProjectInfo, TechStack, DeployInfo
from vibe.collectors.git import collect_git
from vibe.collectors.plans import collect_plans
from vibe.collectors.service import collect_service
from vibe.collectors.loc import collect_loc
from vibe.collectors.fs import collect_fs
from vibe.collectors.features import collect_features
from vibe.collectors.design_docs import collect_design_docs

_ARCH_SECTION_RE = re.compile(r"^#{1,3}\s+(架构|Architecture)", re.IGNORECASE)


def _safe(fn, *args, default=None):
    """Call fn(*args), returning default on any exception."""
    try:
        return fn(*args)
    except Exception:
        return default


def extract_arch_summary(path: Path) -> Optional[str]:
    """Extract architecture summary from README.md ## 架构 section."""
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


def extract_tech_stack(path: Path) -> list[TechStack]:
    """Extract tech stack from pyproject.toml and package.json."""
    stack = []

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
        tech_stack=_safe(extract_tech_stack, path, default=[]),
        git=_safe(collect_git, path),
        plans=_safe(collect_plans, path),
        service=_safe(collect_service, path, vibe_cfg),
        loc=_safe(collect_loc, path),
        fs=_safe(collect_fs, path),
        features=_safe(collect_features, path, default=[]),
        design_docs=_safe(collect_design_docs, path, default=[]),
        deploy=_safe(_extract_deploy, vibe_cfg),
        arch_summary=_safe(extract_arch_summary, path),
    )
