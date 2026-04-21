from pathlib import Path
from vibe.config import load_project_config


def discover_projects(
    scan_dirs: list[str],
    exclude: list[str],
    extra_projects: list[str] | None = None,
    excluded_paths: list[str] | None = None,
) -> list[dict]:
    """Walk scan_dirs and find all .git repositories. Does not recurse into nested repos."""
    results = []
    seen = set()
    excluded = {str(Path(p).resolve()) for p in (excluded_paths or [])}

    for scan_dir in scan_dirs:
        root = Path(scan_dir).expanduser().resolve()
        if not root.exists():
            continue
        _walk_for_repos(root, exclude, results, seen, excluded)

    # Add explicitly imported projects not already discovered
    for proj_path in (extra_projects or []):
        resolved = str(Path(proj_path).resolve())
        if resolved in seen or resolved in excluded:
            continue
        p = Path(resolved)
        if p.exists() and (p / ".git").exists():
            seen.add(resolved)
            try:
                vibe_cfg = load_project_config(p)
            except RuntimeError:
                vibe_cfg = None
            results.append({
                "path": resolved,
                "name": vibe_cfg.get("name", p.name) if vibe_cfg else p.name,
                "vibe_config": vibe_cfg,
            })

    return results


def _walk_for_repos(directory: Path, exclude: list[str], results: list, seen: set, excluded: set):
    try:
        entries = sorted(directory.iterdir())
    except PermissionError:
        return

    git_dir = directory / ".git"
    if git_dir.exists() and git_dir.is_dir():
        repo_path = directory.resolve()
        if str(repo_path) not in seen and str(repo_path) not in excluded:
            seen.add(str(repo_path))
            try:
                vibe_cfg = load_project_config(repo_path)
            except RuntimeError:
                vibe_cfg = None
            results.append({
                "path": str(repo_path),
                "name": vibe_cfg.get("name", repo_path.name) if vibe_cfg else repo_path.name,
                "vibe_config": vibe_cfg,
            })
        return

    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name in exclude or entry.name.startswith("."):
            continue
        _walk_for_repos(entry, exclude, results, seen, excluded)
