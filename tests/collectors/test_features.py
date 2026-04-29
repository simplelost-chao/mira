# tests/collectors/test_features.py
from pathlib import Path
from vibe.collectors.features import collect_features

def test_readme_features(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Project\n## 功能\n- User login\n- Dashboard view\n## Other\n- not a feature\n"
    )
    features = collect_features(tmp_path)
    texts = [f.text for f in features]
    assert "User login" in texts
    assert "Dashboard view" in texts
    for f in features:
        if f.text in ("User login", "Dashboard view"):
            assert f.source == "readme"

def test_plan_features_not_collected(tmp_path):
    """Plans are TDD artifacts, not user-facing features — they should NOT appear."""
    plans_dir = tmp_path / "docs" / "superpowers" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "plan.md").write_text("- [x] Implement auth\n- [ ] Add dashboard\n")
    features = collect_features(tmp_path)
    texts = [f.text for f in features]
    assert "Implement auth" not in texts

def test_no_duplicates(tmp_path):
    (tmp_path / "README.md").write_text("## Features\n- Auth system\n")
    plans_dir = tmp_path / "docs" / "superpowers" / "plans"
    plans_dir.mkdir(parents=True)
    (plans_dir / "plan.md").write_text("- [x] Auth system\n")
    features = collect_features(tmp_path)
    texts = [f.text for f in features]
    assert texts.count("Auth system") == 1

def test_readme_checkbox_items_stripped(tmp_path):
    (tmp_path / "README.md").write_text(
        "## Features\n- [x] Auth system\n- [ ] Billing\n- Plain feature\n"
    )
    features = collect_features(tmp_path)
    texts = [f.text for f in features]
    assert "Auth system" in texts  # not "[x] Auth system"
    assert "Billing" in texts
    assert "Plain feature" in texts
    assert not any(t.startswith("[") for t in texts)
