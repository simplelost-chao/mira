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
