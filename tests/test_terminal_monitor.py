import pytest
import time
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def reset_monitor():
    """Reset monitor state between tests."""
    import vibe.terminal_monitor as m
    m._monitored.clear()
    m._terminal_alerts.clear()
    yield
    m._monitored.clear()
    m._terminal_alerts.clear()


def test_register_and_get_panes():
    from vibe.terminal_monitor import register_pane, get_panes
    register_pane('work:0.0', label='mira claude')
    panes = get_panes()
    assert len(panes) == 1
    assert panes[0]['target'] == 'work:0.0'
    assert panes[0]['label'] == 'mira claude'
    assert panes[0]['auto'] is False


def test_unregister_pane():
    from vibe.terminal_monitor import register_pane, unregister_pane, get_panes
    register_pane('work:0.0', label='test')
    unregister_pane('work:0.0')
    assert get_panes() == []


def test_auto_discover_adds_claude_panes():
    fake_panes = [
        {'target': 'work:0.0', 'command': 'ccc', 'cwd': '/Users/chao/projects/mira', 'session': 'work', 'window': 0, 'pane': 0},
        {'target': 'work:0.1', 'command': 'node', 'cwd': '/Users/chao/projects/foo', 'session': 'work', 'window': 0, 'pane': 1},
    ]
    with patch('vibe.tmux_bridge.list_panes', return_value=fake_panes), \
         patch('vibe.tmux_bridge.capture_pane', return_value='some output'), \
         patch('vibe.terminal_monitor._match_project', return_value=None):
        from vibe.terminal_monitor import _poll_once
        _poll_once()

    from vibe.terminal_monitor import get_panes
    panes = get_panes()
    targets = [p['target'] for p in panes]
    assert 'work:0.0' in targets   # ccc → auto-discovered
    assert 'work:0.1' not in targets  # node → ignored


def test_keyword_detection_creates_alert():
    import vibe.terminal_monitor as m
    m._monitored['work:0.0'] = {
        'target': 'work:0.0', 'label': 'claude/mira', 'command': 'ccc',
        'cwd': '/tmp', 'auto': True, 'project_id': None,
        'last_output': '', 'waiting': False, 'registered_at': time.time(),
    }
    output_with_prompt = "Processing files...\nDo you want to proceed? (y/n)"
    fake_panes = [{'target': 'work:0.0', 'command': 'ccc', 'cwd': '/tmp', 'session': 'work', 'window': 0, 'pane': 0}]
    with patch('vibe.tmux_bridge.list_panes', return_value=fake_panes), \
         patch('vibe.tmux_bridge.capture_pane', return_value=output_with_prompt):
        from vibe.terminal_monitor import _poll_once
        _poll_once()

    assert m._monitored['work:0.0']['waiting'] is True
    alerts = m._terminal_alerts
    assert len(alerts) == 1
    assert alerts[0]['target'] == 'work:0.0'


def test_get_terminal_alerts_clears_queue():
    import vibe.terminal_monitor as m
    m._terminal_alerts.append({'target': 'x', 'label': 'x', 'snippet': 'x', 'ts': 0})
    from vibe.terminal_monitor import get_terminal_alerts
    alerts = get_terminal_alerts()
    assert len(alerts) == 1
    assert m._terminal_alerts == []


def test_waiting_cleared_when_prompt_gone():
    import vibe.terminal_monitor as m
    m._monitored['work:0.0'] = {
        'target': 'work:0.0', 'label': 'claude/mira', 'command': 'ccc',
        'cwd': '/tmp', 'auto': True, 'project_id': None,
        'last_output': 'Do you want to proceed? (y/n)',
        'waiting': True, 'registered_at': time.time(),
    }
    clean_output = "Proceeding with operation...\nDone."
    fake_panes = [{'target': 'work:0.0', 'command': 'ccc', 'cwd': '/tmp', 'session': 'work', 'window': 0, 'pane': 0}]
    with patch('vibe.tmux_bridge.list_panes', return_value=fake_panes), \
         patch('vibe.tmux_bridge.capture_pane', return_value=clean_output):
        from vibe.terminal_monitor import _poll_once
        _poll_once()

    assert m._monitored['work:0.0']['waiting'] is False


def test_alert_fires_only_on_rising_edge():
    """Alert should only be created when waiting transitions False→True, not on every poll."""
    import vibe.terminal_monitor as m
    m._monitored['work:0.0'] = {
        'target': 'work:0.0', 'label': 'claude/mira', 'command': 'ccc',
        'cwd': '/tmp', 'auto': True, 'project_id': None,
        'last_output': '', 'waiting': False, 'registered_at': time.time(),
    }
    output_with_prompt = "Do you want to proceed? (y/n)"
    fake_panes = [{'target': 'work:0.0', 'command': 'ccc', 'cwd': '/tmp', 'session': 'work', 'window': 0, 'pane': 0}]
    with patch('vibe.tmux_bridge.list_panes', return_value=fake_panes), \
         patch('vibe.tmux_bridge.capture_pane', return_value=output_with_prompt):
        from vibe.terminal_monitor import _poll_once
        _poll_once()  # rising edge: False → True → 1 alert
        _poll_once()  # stays True → no new alert

    assert len(m._terminal_alerts) == 1


def test_dead_pane_removed_on_poll():
    """Panes (auto or manual) are removed when their tmux target disappears."""
    from vibe.terminal_monitor import register_pane, get_panes
    register_pane('work:0.0', label='manual')

    with patch('vibe.tmux_bridge.list_panes', return_value=[]), \
         patch('vibe.tmux_bridge.capture_pane', side_effect=RuntimeError('pane not found')):
        from vibe.terminal_monitor import _poll_once
        _poll_once()

    panes = get_panes()
    assert len(panes) == 0


def test_unrecognized_pane_not_rescanned_every_poll():
    """回归：未识别 pane 原本每 2s 轮询都做两次 capture_pane subprocess，
    永远扫不出结果却反复扫。负向缓存应在间隔内跳过重扫。"""
    import vibe.terminal_monitor as m
    m._codex_scan_cache.clear()
    fake_panes = [
        {'target': 'work:0.1', 'command': 'node', 'cwd': '/tmp/foo', 'session': 'work', 'window': 0, 'pane': 1, 'title': 'foo'},
    ]
    calls = {'n': 0}
    def _counting_capture(target, lines):
        calls['n'] += 1
        return 'just a node server, not codex'
    with patch('vibe.tmux_bridge.list_panes', return_value=fake_panes), \
         patch('vibe.tmux_bridge.capture_pane', side_effect=_counting_capture), \
         patch('vibe.terminal_monitor._match_project', return_value=None):
        from vibe.terminal_monitor import _poll_once
        _poll_once()
        first = calls['n']
        _poll_once()   # 紧接着第二次 poll（在重扫间隔内）
        second = calls['n']
    assert first == 2, f"首次应扫两次(可见+回滚)，实际 {first}"
    assert second == 2, f"间隔内第二次 poll 不应再扫，实际累计 {second}"
