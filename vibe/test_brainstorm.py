import json
import pytest
from vibe.ai_brainstorm import detect_available_models


def test_detect_no_models():
    cfg = {}
    assert detect_available_models(cfg) == []


def test_detect_deepseek():
    cfg = {"deepseek_api_key": "sk-abc"}
    models = detect_available_models(cfg)
    assert any(m["id"] == "deepseek" for m in models)


def test_detect_multiple():
    cfg = {"deepseek_api_key": "sk-abc", "openrouter_api_key": "sk-or-xyz"}
    models = detect_available_models(cfg)
    ids = [m["id"] for m in models]
    assert "deepseek" in ids
    assert "openrouter" in ids


def test_detect_ignores_empty_key():
    cfg = {"deepseek_api_key": "", "openrouter_api_key": "sk-or-xyz"}
    models = detect_available_models(cfg)
    ids = [m["id"] for m in models]
    assert "deepseek" not in ids
    assert "openrouter" in ids


from vibe.ai_brainstorm import parse_candidates


def test_parse_valid_candidates():
    raw = json.dumps([
        {
            "name": "Stride",
            "phonetic": "/straɪd/",
            "name_meaning": "稳步前进",
            "logo_svg": "<svg>...</svg>",
            "logo_meaning": "圆形代表循环"
        }
    ])
    result = parse_candidates(raw)
    assert len(result) == 1
    assert result[0]["name"] == "Stride"
    assert result[0]["phonetic"] == "/straɪd/"


def test_parse_strips_markdown_fences():
    raw = '```json\n[{"name":"X","phonetic":"","name_meaning":"","logo_svg":"<svg/>","logo_meaning":""}]\n```'
    result = parse_candidates(raw)
    assert result[0]["name"] == "X"


def test_parse_invalid_returns_empty():
    result = parse_candidates("not json at all")
    assert result == []


def test_parse_missing_fields_skipped():
    raw = json.dumps([
        {"name": "Good", "phonetic": "/g/", "name_meaning": "ok", "logo_svg": "<svg/>", "logo_meaning": "dot"},
        {"name": "Bad"},  # missing required fields
    ])
    result = parse_candidates(raw)
    assert len(result) == 1
    assert result[0]["name"] == "Good"


import os
import subprocess
from pathlib import Path
from vibe.ai_brainstorm import create_project


def test_create_project_basic(tmp_path):
    result = create_project(
        base_dir=tmp_path,
        name="Stride",
        description="追踪跑步数据",
        logo_svg='<svg width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="32" r="20" fill="#00ff9d"/></svg>',
        port=None,
        domain=None,
    )
    assert result["project_id"] == "stride"
    proj_dir = tmp_path / "stride"
    assert proj_dir.is_dir()
    assert (proj_dir / ".git").is_dir()
    assert (proj_dir / "vibe.yaml").exists()
    assert (proj_dir / "logo.svg").exists()
    assert (proj_dir / "favicon.svg").exists()


def test_create_project_vibe_yaml_content(tmp_path):
    create_project(tmp_path, "Stride", "追踪跑步数据", "<svg/>", port=8090, domain="stride.example.com")
    content = (tmp_path / "stride" / "vibe.yaml").read_text()
    assert "name: Stride" in content
    assert "description:" in content
    assert "port: 8090" in content
    assert "domain: stride.example.com" in content


def test_create_project_no_port_no_domain(tmp_path):
    create_project(tmp_path, "Stride", "追踪跑步数据", "<svg/>", port=None, domain=None)
    content = (tmp_path / "stride" / "vibe.yaml").read_text()
    assert "port" not in content
    assert "domain" not in content


def test_create_project_duplicate_raises(tmp_path):
    import pytest
    create_project(tmp_path, "Stride", "first", "<svg/>", port=None, domain=None)
    with pytest.raises(FileExistsError):
        create_project(tmp_path, "Stride", "second", "<svg/>", port=None, domain=None)
