# vibe/collectors/git.py
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
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

    today = datetime.now().date()
    since_30d = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    heatmap_since = (today - timedelta(days=83)).strftime("%Y-%m-%d")

    # Run all git commands in parallel
    cmds = {
        "branch":   ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        "hash":     ["git", "rev-parse", "--short", "HEAD"],
        "status":   ["git", "status", "--porcelain"],
        "monthly":  ["git", "log", "--oneline", f"--since={since_30d}"],
        "recent":   ["git", "log", "--oneline", "-5"],
        "remote":   ["git", "remote", "get-url", "origin"],
        "heatmap":  ["git", "log", "--format=%ad", "--date=short", f"--since={heatmap_since}"],
    }
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(cmds)) as pool:
        futs = {pool.submit(_run, cmd, path): name for name, cmd in cmds.items()}
        for fut in as_completed(futs):
            results[futs[fut]] = fut.result()

    dirty_raw = results["status"]
    dirty_files = []
    if dirty_raw:
        for line in dirty_raw.splitlines():
            if line.strip():
                parts = line[3:].strip()
                if " -> " in parts:
                    parts = parts.split(" -> ")[-1]
                dirty_files.append(parts)

    monthly_log = results["monthly"]
    monthly_commits = len(monthly_log.splitlines()) if monthly_log else 0

    date_counts: dict[str, int] = {}
    for line in (results["heatmap"].splitlines() if results["heatmap"] else []):
        line = line.strip()
        if line:
            date_counts[line] = date_counts.get(line, 0) + 1
    commit_heatmap = [
        date_counts.get((today - timedelta(days=83 - i)).strftime("%Y-%m-%d"), 0)
        for i in range(84)
    ]

    return GitInfo(
        branch=results["branch"] or "unknown",
        commit_hash=results["hash"] or "",
        dirty_files=dirty_files,
        monthly_commits=monthly_commits,
        recent_commits=results["recent"].splitlines() if results["recent"] else [],
        github_url=_parse_github_url(results["remote"]),
        commit_heatmap=commit_heatmap,
    )
