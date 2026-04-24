# vibe/collectors/features.py
import re
from pathlib import Path
from vibe.models import Feature

_FEATURE_SECTION_RE = re.compile(r"^#{1,3}\s+(功能|Features?|Capabilities|What it does)", re.IGNORECASE)
_IMPL_SECTION_RE    = re.compile(r"^#{1,3}\s+(已实现|已完成|Implemented)", re.IGNORECASE)
_LIST_ITEM_RE       = re.compile(r"^\s*[-*]\s+(.+)")
_DONE_RE            = re.compile(r"^\s*-\s*\[x\]\s+(.+)", re.IGNORECASE)
_TODO_RE            = re.compile(r"^\s*-\s*\[ \]\s+(.+)")
# Task header in superpowers plan format: "### Task N: Description"
_TASK_HEADER_RE     = re.compile(r"^#{1,4}\s+Task\s+[\d.]+\s*[—–-]\s*(.+)", re.IGNORECASE)
_TASK_STATUS_RE     = re.compile(r"\*\*Status\*\*:\s*(\w+)", re.IGNORECASE)
# TDD step lines to skip in plan files
_STEP_RE            = re.compile(r"\*\*Step\s+\d+", re.IGNORECASE)


def _from_readme(path: Path) -> list[Feature]:
    readme = path / "README.md"
    if not readme.exists():
        return []
    features = []
    in_section = False
    for line in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        if _FEATURE_SECTION_RE.match(line):
            in_section = True
            continue
        if in_section and line.startswith("#"):
            in_section = False
        if in_section:
            m_done = _DONE_RE.match(line)
            m_todo = _TODO_RE.match(line)
            m_plain = _LIST_ITEM_RE.match(line)
            if m_done:
                features.append(Feature(text=m_done.group(1).strip(), source="readme", implemented=True))
            elif m_todo:
                features.append(Feature(text=m_todo.group(1).strip(), source="readme", implemented=False))
            elif m_plain:
                text = m_plain.group(1).strip()
                if not text.startswith("["):
                    features.append(Feature(text=text, source="readme", implemented=True))
    return features


_STUB_SECTION_RE = re.compile(r"^#{1,4}\s+.*(尚未实现|未实现|规划中|TODO)", re.IGNORECASE)


def _from_vibe_summary(path: Path) -> list[Feature]:
    """Read feature bullets from docs/vibe-summary.md.

    Scans the entire file for bullet points, skipping sections that are
    explicitly about unimplemented/stub/planned features.
    """
    summary = path / "docs" / "vibe-summary.md"
    if not summary.exists():
        return []
    features = []
    in_stub_section = False
    stub_depth = 0
    for line in summary.read_text(encoding="utf-8", errors="replace").splitlines():
        # Detect stub/unimplemented section header
        if _STUB_SECTION_RE.match(line):
            in_stub_section = True
            stub_depth = len(line) - len(line.lstrip("#"))
            continue
        # Exit stub section when we see a heading at same depth or higher
        if in_stub_section and re.match(r"^#+\s+", line):
            depth = len(line) - len(line.lstrip("#"))
            if depth <= stub_depth:
                in_stub_section = False
            continue
        if in_stub_section:
            continue

        m_done = _DONE_RE.match(line)
        m_todo = _TODO_RE.match(line)
        m_plain = _LIST_ITEM_RE.match(line)
        if m_done:
            features.append(Feature(text=m_done.group(1).strip(), source="summary", implemented=True))
        elif m_todo:
            features.append(Feature(text=m_todo.group(1).strip(), source="summary", implemented=False))
        elif m_plain:
            text = m_plain.group(1).strip()
            if not text.startswith("[") and not _STEP_RE.search(text):
                features.append(Feature(text=text, source="summary", implemented=True))
    return features


def _from_plans(path: Path) -> list[Feature]:
    """Extract Task-level headings from superpowers plan files (not TDD step checkboxes)."""
    plans_dir = path / "docs" / "superpowers" / "plans"
    if not plans_dir.exists():
        return []
    features = []
    for md in sorted(plans_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        current_task: str | None = None
        current_done = False
        for line in text.splitlines():
            # Task header
            m = _TASK_HEADER_RE.match(line)
            if m:
                current_task = m.group(1).strip()
                current_done = False
                continue
            # Status line following task header
            if current_task:
                ms = _TASK_STATUS_RE.search(line)
                if ms:
                    current_done = ms.group(1).lower() == "done"
                    features.append(Feature(text=current_task, source="plan", implemented=current_done))
                    current_task = None
    return features


def collect_features(path: Path) -> list[Feature]:
    seen: set[str] = set()
    result: list[Feature] = []
    # Priority: vibe-summary > readme
    # Plans are TDD implementation artifacts, not user-facing features
    for feature in [*_from_vibe_summary(path), *_from_readme(path)]:
        key = feature.text.lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(feature)
    return result
