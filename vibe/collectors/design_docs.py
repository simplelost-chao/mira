# vibe/collectors/design_docs.py
import re
import time
from pathlib import Path
from vibe.models import DesignDoc

_STALE_THRESHOLD = 30 * 86400  # 30 days in seconds
_TITLE_RE = re.compile(r"^#\s+(.+)")

def _extract_title(content: str) -> str:
    for line in content.splitlines():
        m = _TITLE_RE.match(line)
        if m:
            return m.group(1).strip()
    return "Untitled"

def collect_design_docs(path: Path) -> list[DesignDoc]:
    specs_dir = path / "docs" / "superpowers" / "specs"
    if not specs_dir.exists():
        return []

    docs = []
    now = time.time()
    for md_file in sorted(specs_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            mtime = md_file.stat().st_mtime
            docs.append(DesignDoc(
                filename=md_file.name,
                title=_extract_title(content),
                content=content,
                mtime=mtime,
                possibly_stale=(now - mtime) > _STALE_THRESHOLD,
            ))
        except Exception:
            continue
    return docs
