# tests/collectors/test_design_docs.py
import time
import os
from pathlib import Path
from vibe.collectors.design_docs import collect_design_docs

def test_no_specs_dir(tmp_path):
    docs = collect_design_docs(tmp_path)
    assert docs == []

def test_reads_spec_files(tmp_path):
    specs = tmp_path / "docs" / "superpowers" / "specs"
    specs.mkdir(parents=True)
    (specs / "2026-01-01-feature-design.md").write_text("# Feature Design\nSome content here.")
    docs = collect_design_docs(tmp_path)
    assert len(docs) == 1
    assert docs[0].filename == "2026-01-01-feature-design.md"
    assert docs[0].title == "Feature Design"
    assert "Some content" in docs[0].content

def test_stale_detection(tmp_path):
    specs = tmp_path / "docs" / "superpowers" / "specs"
    specs.mkdir(parents=True)
    old_file = specs / "old-design.md"
    old_file.write_text("# Old\nContent.")
    # Set mtime to 40 days ago
    old_time = time.time() - (40 * 86400)
    os.utime(old_file, (old_time, old_time))
    docs = collect_design_docs(tmp_path)
    assert docs[0].possibly_stale == True
