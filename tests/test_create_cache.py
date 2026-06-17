"""创建项目后的可见性与输入校验。

回归场景：/api/projects/create 把缓存重建丢给后台线程，前端 2 秒后跳回
首页时拿到的还是旧缓存，新项目"消失"几分钟。
"""
import time

from fastapi.testclient import TestClient

from vibe import main

client = TestClient(main.api)


def _fake_cfg(tmp_path):
    return {
        "scan_dirs": [str(tmp_path)],
        "exclude": [],
        "admin_password": "",
        "extra_projects": [],
        "excluded_paths": [],
    }


def test_created_project_visible_in_next_projects_request(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "vibe.config.load_global_config", lambda *a, **k: _fake_cfg(tmp_path)
    )
    monkeypatch.setattr(main, "_rebuild_and_persist", lambda: None)
    monkeypatch.setattr(main, "_cache", [])
    monkeypatch.setattr(main, "_cache_ts", time.time())  # 缓存"新鲜"，GET 不触发重建

    resp = client.post(
        "/api/projects/create",
        json={"name": "CacheProbe", "description": "测试用", "logo_svg": "<svg></svg>"},
    )
    assert resp.status_code == 200

    resp2 = client.get("/api/projects")
    assert resp2.status_code == 200
    ids = [p["id"] for p in resp2.json()]
    assert "cacheprobe" in ids


def test_create_rejects_non_domain(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "vibe.config.load_global_config", lambda *a, **k: _fake_cfg(tmp_path)
    )
    monkeypatch.setattr(main, "_rebuild_and_persist", lambda: None)

    resp = client.post(
        "/api/projects/create",
        json={
            "name": "BadDomain",
            "description": "x",
            "logo_svg": "<svg></svg>",
            "domain": "BadDomain",
        },
    )
    assert resp.status_code == 400
