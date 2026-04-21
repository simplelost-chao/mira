import pytest
from pathlib import Path
from vibe.config import load_global_config, load_project_config


def test_load_global_config_defaults(tmp_path):
    cfg = load_global_config(tmp_path / "nonexistent.yaml")
    assert cfg["scan_dirs"] == []
    assert cfg["exclude"] == ["node_modules", ".venv", "__pycache__"]
    assert cfg["port"] == 8888


def test_load_global_config_from_file(tmp_path):
    (tmp_path / "vibe.yaml").write_text("scan_dirs:\n  - ~/projects\nport: 9000\n")
    cfg = load_global_config(tmp_path / "vibe.yaml")
    assert "~/projects" in cfg["scan_dirs"]
    assert cfg["port"] == 9000


def test_load_project_config_missing(tmp_path):
    cfg = load_project_config(tmp_path)
    assert cfg is None


def test_load_project_config_present(tmp_path):
    (tmp_path / "vibe.yaml").write_text("name: TestProj\nstatus: active\n")
    cfg = load_project_config(tmp_path)
    assert cfg["name"] == "TestProj"
    assert cfg["status"] == "active"
