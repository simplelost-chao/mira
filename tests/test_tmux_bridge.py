import pytest
from unittest.mock import patch, MagicMock


def _make_proc(stdout='', returncode=0):
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    return m


def test_list_panes_parses_output():
    fake = (
        "work\t0\t0\tccc\t/Users/chao/projects/mira\n"
        "work\t0\t1\tnpm\t/Users/chao/projects/awalon\n"
    )
    with patch('subprocess.run', return_value=_make_proc(stdout=fake)):
        from vibe.tmux_bridge import list_panes
        panes = list_panes()
    assert len(panes) == 2
    assert panes[0]['target'] == 'work:0.0'
    assert panes[0]['command'] == 'ccc'
    assert panes[0]['cwd'] == '/Users/chao/projects/mira'
    assert panes[1]['target'] == 'work:0.1'


def test_list_panes_returns_empty_when_no_tmux():
    with patch('subprocess.run', side_effect=FileNotFoundError):
        from vibe.tmux_bridge import list_panes
        assert list_panes() == []


def test_capture_pane_returns_text():
    with patch('subprocess.run', return_value=_make_proc(stdout='hello\nworld\n')):
        from vibe.tmux_bridge import capture_pane
        out = capture_pane('work:0.0')
    assert 'hello' in out


def test_capture_pane_raises_on_bad_target():
    with patch('subprocess.run', return_value=_make_proc(stdout='', returncode=1)):
        from vibe.tmux_bridge import capture_pane
        with pytest.raises(RuntimeError, match='target'):
            capture_pane('bad:9.9')


def test_send_keys_calls_tmux():
    with patch('subprocess.run', return_value=_make_proc()) as mock_run:
        from vibe.tmux_bridge import send_keys
        send_keys('work:0.0', 'y\n')
    # 'y\n' splits into two calls: text 'y' then key 'Enter'
    calls = [c[0][0] for c in mock_run.call_args_list]
    assert any('y' in c for c in calls)
    assert any('Enter' in c for c in calls)


def test_send_keys_raises_on_failure():
    with patch('subprocess.run', return_value=_make_proc(returncode=1)):
        from vibe.tmux_bridge import send_keys
        with pytest.raises(RuntimeError, match='send-keys'):
            send_keys('bad:9.9', 'y\n')


def test_send_keys_cancels_copy_mode_first():
    # pane 在 copy-mode(滚动模式)时,send-keys -l 的字节会被静默吞掉(含 \x03),
    # 发键前必须先 -X cancel 退出,否则 Ctrl+C 连按多少次都到不了程序
    def fake_run(cmd, **kw):
        if 'display' in cmd:
            return _make_proc(stdout='1\n')
        return _make_proc()
    with patch('subprocess.run', side_effect=fake_run) as mock_run:
        from vibe.tmux_bridge import send_keys
        send_keys('work:0.0', '\x03')
    calls = [c[0][0] for c in mock_run.call_args_list]
    cancel_idx = [i for i, c in enumerate(calls) if '-X' in c and 'cancel' in c]
    send_idx = [i for i, c in enumerate(calls) if '-l' in c and '\x03' in c]
    assert cancel_idx and send_idx, f'expected cancel then send, got: {calls}'
    assert cancel_idx[0] < send_idx[0]


def test_send_keys_no_cancel_when_not_in_copy_mode():
    def fake_run(cmd, **kw):
        if 'display' in cmd:
            return _make_proc(stdout='0\n')
        return _make_proc()
    with patch('subprocess.run', side_effect=fake_run) as mock_run:
        from vibe.tmux_bridge import send_keys
        send_keys('work:0.0', '\x03')
    calls = [c[0][0] for c in mock_run.call_args_list]
    assert not any('cancel' in c for c in calls)
