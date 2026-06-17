"""性能回归测试：/ws/status 的轻量探活不应走全量采集路径。"""
from vibe import main


def test_check_service_statuses_uses_cache_not_full_collect(monkeypatch):
    """回归：原实现每30s discover_projects 扫盘 + collect_service
    (process_iter + 串行域名HTTPS探测)。优化后应复用 _cache + 轻量 TCP 探活。"""
    def _boom_discover(*a, **k):
        raise AssertionError("不应调用 discover_projects（扫盘）")
    def _boom_collect(*a, **k):
        raise AssertionError("不应调用 collect_service（process_iter + 域名探测）")
    monkeypatch.setattr("vibe.scanner.discover_projects", _boom_discover)
    monkeypatch.setattr("vibe.collectors.service.collect_service", _boom_collect)

    # 缓存里放两个项目：一个有端口、一个无端口
    monkeypatch.setattr(main, "_cache", [
        {"id": "alpha", "path": "/tmp/alpha", "service": {"port": 8080, "process_name": "node", "domain_ok": True}},
        {"id": "beta",  "path": "/tmp/beta",  "service": {"port": None, "is_running": False}},
    ])
    monkeypatch.setattr(main, "_cache_ts", main.time.time())  # 缓存新鲜，get_all_projects 不重建

    probed = {}
    monkeypatch.setattr(main, "_check_port", lambda port, host="127.0.0.1": (probed.setdefault(port, True) or port == 8080))

    result = main._check_service_statuses()

    assert result["alpha"]["is_running"] is True   # 8080 探活通过
    assert result["alpha"]["port"] == 8080
    assert result["beta"]["is_running"] is False    # 无端口 → 回落到 service.is_running
    assert 8080 in probed                           # 确实用了 TCP 探活
