# vibe/collectors/features.py
import re
from pathlib import Path
from vibe.models import Feature

_FEATURE_SECTION_RE = re.compile(r"^#{1,3}\s+(功能|Features?|Capabilities|What it does)", re.IGNORECASE)
_LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+(.+)")
_DONE_RE = re.compile(r"^\s*-\s*\[x\]\s+(.+)", re.IGNORECASE)
_TODO_RE = re.compile(r"^\s*-\s*\[ \]\s+(.+)")

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
                # Only add if it's not a checkbox (those are handled above)
                text = m_plain.group(1).strip()
                if not text.startswith("["):
                    features.append(Feature(text=text, source="readme", implemented=True))
    return features

def _from_plans(path: Path) -> list[Feature]:
    plans_dir = path / "docs" / "superpowers" / "plans"
    if not plans_dir.exists():
        return []
    features = []
    for md in sorted(plans_dir.glob("*.md")):
        for line in md.read_text(encoding="utf-8", errors="replace").splitlines():
            m_done = _DONE_RE.match(line)
            m_todo = _TODO_RE.match(line)
            if m_done:
                features.append(Feature(text=m_done.group(1).strip(), source="plan", implemented=True))
            elif m_todo:
                features.append(Feature(text=m_todo.group(1).strip(), source="plan", implemented=False))
    return features

def collect_features(path: Path) -> list[Feature]:
    seen: set[str] = set()
    result: list[Feature] = []
    for feature in [*_from_readme(path), *_from_plans(path)]:
        key = feature.text.lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(feature)
    return result
