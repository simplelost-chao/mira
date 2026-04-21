from pathlib import Path
from vibe.config import load_project_config


def discover_projects(scan_dirs: list[str], exclude: list[str]) -> list[dict]:
    """Walk scan_dirs and find all .git repositories. Does not recurse into nested repos."""
    results = []
    seen = set()

    for scan_dir in scan_dirs:
        root = Path(scan_dir).expanduser().resolve()
        if not root.exists():
            continue
        _walk_for_repos(root, exclude, results, seen)

    return results


def _walk_for_repos(directory: Path, exclude: list[str], results: list, seen: set):
    try:
        entries = sorted(directory.iterdir())
    except PermissionError:
        return

    # Check if this directory contains .git (is a git repo)
    git_dir = directory / ".git"
    if git_dir.exists() and git_dir.is_dir():
        repo_path = directory.resolve()
        if str(repo_path) not in seen:
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
        return  # stop recursing into this repo

    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name in exclude or entry.name.startswith("."):
            continue
        _walk_for_repos(entry, exclude, results, seen)
