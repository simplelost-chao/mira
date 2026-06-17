"""基础服务看门狗：启动基线行为的测试。

回归场景：机器重启后服务已挂，mira 启动时基线把它记为 down，
循环里永远等不到 up→down 跳变，导致永不自动重启。
"""
import time

from vibe import main


def _wait_for(cond, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(0.05)
    return cond()


def test_check_anomalies_does_not_clobber_watchdog_alerts():
    """回归：每120s的异常扫描曾用 _alerts.clear() 把看门狗线程刚写入的
    运行时告警一起清掉，导致"服务已停止/已重启"通知静默丢失。"""
    with main._alerts_lock:
        main._alerts.clear()
        main._alerts.append("[10:01] svc-x 服务已停止")  # 看门狗写入的运行时事件
    # 异常扫描发现另一个项目有问题
    proj = {
        "name": "proj-a", "status": "active",
        "service": {"port": 8080, "is_running": False},
        "git": {"monthly_commits": 3},
    }
    main._check_anomalies([proj])
    # 看门狗事件必须存活，异常也要被记录
    with main._alerts_lock:
        alerts = list(main._alerts)
        anomalies = list(main._anomalies)
    assert any("svc-x 服务已停止" in a for a in alerts), "看门狗告警被异常扫描清掉了"
    assert any("proj-a" in a for a in anomalies), "异常未被记录"


def test_get_alerts_returns_and_drains_both_feeds(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(main, "_is_admin", lambda request: True)
    client = TestClient(main.api)
    with main._alerts_lock:
        main._alerts.clear(); main._anomalies.clear()
        main._alerts.append("[10:01] svc-y 自动重启成功")
        main._anomalies.append("[10:00] proj-b 服务应运行在 :9000 但当前未运行")
    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    body = " ".join(resp.json()["alerts"])
    assert "svc-y 自动重启成功" in body and "proj-b" in body
    # 两个 feed 都应被清空（消费式）
    with main._alerts_lock:
        assert not main._alerts and not main._anomalies


def test_baseline_restarts_down_service_with_restart_cmd(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "_check_port", lambda port, host="127.0.0.1": False)
    monkeypatch.setattr(
        main, "_auto_restart", lambda name, cmd, port, sound: calls.append(name)
    )
    cfg = {
        "notification_sound": "Pop",
        "base_services": [
            {"name": "svc-a", "port": 1234, "restart_cmd": "echo hi"},
            {"name": "svc-b", "port": 1235},  # 无 restart_cmd → 只记状态不重启
        ],
    }
    main._establish_baseline(cfg)
    assert _wait_for(lambda: calls)
    time.sleep(0.2)  # 确认 svc-b 没有跟着被重启
    assert calls == ["svc-a"]
    assert main._base_svc_state["svc-a"] is False
    assert main._base_svc_state["svc-b"] is False


def test_baseline_does_not_restart_running_service(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "_check_port", lambda port, host="127.0.0.1": True)
    monkeypatch.setattr(
        main, "_auto_restart", lambda name, cmd, port, sound: calls.append(name)
    )
    cfg = {
        "base_services": [{"name": "svc-c", "port": 1234, "restart_cmd": "echo hi"}],
    }
    main._establish_baseline(cfg)
    time.sleep(0.2)
    assert calls == []
    assert main._base_svc_state["svc-c"] is True


def test_auto_restart_failure_is_reported(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr("subprocess.run", boom)
    with main._alerts_lock:
        main._alerts.clear()
    main._auto_restart("svc-x", "whatever", None, "Pop")
    assert any("svc-x" in a and "失败" in a for a in main._alerts)
