# vibe/collectors/git.py
import re
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from vibe.models import GitInfo

def _run(cmd: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""

def _parse_github_url(remote: str) -> str | None:
    """Convert git remote URL to https://github.com/user/repo."""
    if not remote:
        return None
    # SSH: git@github.com:user/repo.git
    m = re.match(r'git@github\.com:([^/]+/[^/]+?)(?:\.git)?$', remote)
    if m:
        return f"https://github.com/{m.group(1)}"
    # HTTPS: https://github.com/user/repo.git
    m = re.match(r'https?://github\.com/([^/]+/[^/]+?)(?:\.git)?$', remote)
    if m:
        return f"https://github.com/{m.group(1)}"
    return None

def collect_git(path: Path) -> GitInfo:
    if not (path / ".git").exists():
        return GitInfo(branch="unknown", commit_hash="", dirty_files=[], monthly_commits=0, recent_commits=[])

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path) or "unknown"
    commit_hash = _run(["git", "rev-parse", "--short", "HEAD"], path) or ""

    dirty_raw = _run(["git", "status", "--porcelain"], path)
    if dirty_raw:
        dirty_files = []
        for line in dirty_raw.splitlines():
            if line.strip():
                # Format is "XY filename" where XY is 2 status chars + space
                # Handle renames: "R  old -> new" — take the dest path
                parts = line[3:].strip()
                if " -> " in parts:
                    parts = parts.split(" -> ")[-1]
                dirty_files.append(parts)
    else:
        dirty_files = []

    since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    monthly_log = _run(["git", "log", "--oneline", f"--since={since}"], path)
    monthly_commits = len(monthly_log.splitlines()) if monthly_log else 0

    recent_log = _run(["git", "log", "--oneline", "-5"], path)
    recent_commits = recent_log.splitlines() if recent_log else []

    remote = _run(["git", "remote", "get-url", "origin"], path)
    github_url = _parse_github_url(remote)

    # 84-day commit heatmap: index 0 = 83 days ago, index 83 = today
    today = datetime.now().date()
    heatmap_since = (today - timedelta(days=83)).strftime("%Y-%m-%d")
    heatmap_log = _run(["git", "log", "--format=%ad", "--date=short",
                         f"--since={heatmap_since}"], path)
    date_counts: dict[str, int] = {}
    for line in (heatmap_log.splitlines() if heatmap_log else []):
        line = line.strip()
        if line:
            date_counts[line] = date_counts.get(line, 0) + 1
    commit_heatmap = [
        date_counts.get((today - timedelta(days=83 - i)).strftime("%Y-%m-%d"), 0)
        for i in range(84)
    ]

    return GitInfo(
        branch=branch,
        commit_hash=commit_hash,
        dirty_files=dirty_files,
        monthly_commits=monthly_commits,
        recent_commits=recent_commits,
        github_url=github_url,
        commit_heatmap=commit_heatmap,
    )
