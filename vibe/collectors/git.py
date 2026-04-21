# vibe/collectors/git.py
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

def collect_git(path: Path) -> GitInfo:
    if not (path / ".git").exists():
        return GitInfo(branch="unknown", commit_hash="", dirty_files=[], monthly_commits=0, recent_commits=[])

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path) or "unknown"
    commit_hash = _run(["git", "rev-parse", "--short", "HEAD"], path) or ""

    dirty_raw = _run(["git", "status", "--porcelain"], path)
    dirty_files = [line for line in dirty_raw.splitlines() if line.strip()] if dirty_raw else []

    since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    monthly_log = _run(["git", "log", "--oneline", f"--since={since}"], path)
    monthly_commits = len(monthly_log.splitlines()) if monthly_log else 0

    recent_log = _run(["git", "log", "--oneline", "-5"], path)
    recent_commits = recent_log.splitlines() if recent_log else []

    return GitInfo(
        branch=branch,
        commit_hash=commit_hash,
        dirty_files=dirty_files,
        monthly_commits=monthly_commits,
        recent_commits=recent_commits,
    )
