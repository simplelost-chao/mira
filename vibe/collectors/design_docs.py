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

# Root-level markdown files that are typically design/architecture docs
_ROOT_DOC_FILES = [
    "ARCHITECTURE.md", "DESIGN.md", "SPEC.md", "PROTOCOL.md",
    "RUNBOOK.md", "CHANGELOG.md",
]
# Subdirectories under docs/ that typically contain design docs
_DOC_SUBDIRS = ["design", "specs", "architecture", "superpowers/specs"]

def _candidate_doc_files(path: Path) -> list[Path]:
    """Return design doc candidates, superpowers/specs first, then fallbacks."""
    superpowers = path / "docs" / "superpowers" / "specs"
    if superpowers.exists() and any(superpowers.glob("*.md")):
        return sorted(superpowers.glob("*.md"))

    candidates = []
    # Root-level named docs
    for name in _ROOT_DOC_FILES:
        f = path / name
        if f.exists():
            candidates.append(f)
    # docs/ top-level .md files
    docs_dir = path / "docs"
    if docs_dir.exists():
        for f in sorted(docs_dir.glob("*.md")):
            candidates.append(f)
        # docs/design/, docs/architecture/, etc.
        for subdir in _DOC_SUBDIRS:
            sub = docs_dir / subdir
            if sub.exists():
                for f in sorted(sub.glob("*.md")):
                    candidates.append(f)
    return candidates

def collect_design_docs(path: Path) -> list[DesignDoc]:
    docs = []
    now = time.time()
    superpowers_dir = path / "docs" / "superpowers" / "specs"
    for md_file in _candidate_doc_files(path):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            mtime = md_file.stat().st_mtime
            # superpowers files: just filename. Others: relative path from project root.
            try:
                rel = md_file.relative_to(path)
                if md_file.parent == superpowers_dir:
                    display_name = md_file.name
                else:
                    display_name = str(rel) if len(rel.parts) > 1 else md_file.name
            except ValueError:
                display_name = md_file.name
            docs.append(DesignDoc(
                filename=display_name,
                title=_extract_title(content),
                content=content,
                mtime=mtime,
                possibly_stale=(now - mtime) > _STALE_THRESHOLD,
            ))
        except Exception:
            continue
    # vibe-summary.md always first
    docs.sort(key=lambda d: (0 if d.filename in ("vibe-summary.md", "docs/vibe-summary.md") else 1, d.filename))
    return docs
