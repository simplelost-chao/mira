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


def test_list_panes_excludes_viewer_sessions():
    fake = (
        "work\t0\t0\tccc\t/Users/chao/projects/mira\n"
        "v-abcdef123456\t3\t0\tccc\t/Users/chao/projects/vt-b\n"
    )
    with patch('subprocess.run', return_value=_make_proc(stdout=fake)):
        from vibe.tmux_bridge import list_panes
        panes = list_panes()
    assert len(panes) == 1
    assert panes[0]['session'] == 'work'


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


# ── viewer 会话:每条观看连接一个独立分组会话(隔离"当前窗口",防串台) ──────────

def test_create_viewer_session_groups_and_selects_window():
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        return _make_proc()
    with patch('subprocess.run', side_effect=fake_run):
        from vibe.tmux_bridge import create_viewer_session
        name = create_viewer_session('mira:3.0')
    assert name.startswith('v-') and len(name) == 14
    joined = [' '.join(c) for c in calls]
    assert any('new-session' in c and '-t mira' in c and f'-s {name}' in c for c in joined)
    assert any('select-window' in c and f'{name}:3' in c for c in joined)
    assert any('prefix None' in c for c in joined)
    assert any('status off' in c for c in joined)


def test_create_viewer_session_cleans_up_on_failure():
    # select-window 失败时不能留下半成品会话
    def fake_run(cmd, **kw):
        if 'select-window' in cmd:
            return _make_proc(returncode=1)
        return _make_proc()
    with patch('subprocess.run', side_effect=fake_run) as mock_run:
        from vibe.tmux_bridge import create_viewer_session
        with pytest.raises(RuntimeError):
            create_viewer_session('mira:3.0')
    joined = [' '.join(c[0][0]) for c in mock_run.call_args_list]
    assert any('kill-session' in c for c in joined)


def test_kill_viewer_session_refuses_non_viewer_names():
    # 只杀 v-* 前缀,防止误杀真实会话
    with patch('subprocess.run') as mock_run:
        from vibe.tmux_bridge import kill_viewer_session
        kill_viewer_session('mira')
    mock_run.assert_not_called()


def test_window_size_parses_output():
    with patch('subprocess.run', return_value=_make_proc(stdout='120 40\n')):
        from vibe.tmux_bridge import window_size
        assert window_size('mira:3.0') == (120, 40)


def test_cleanup_orphan_viewers_kills_only_old_detached():
    import time as _time
    now = int(_time.time())
    listing = (f"v-aaaaaaaaaaaa\t0\t{now - 600}\n"    # 孤儿:该杀
               f"v-bbbbbbbbbbbb\t1\t{now - 600}\n"    # 有人看着:留
               f"v-cccccccccccc\t0\t{now - 10}\n"     # 刚建(attach 还在路上):留
               f"mira\t1\t{now - 99999}\n")           # 真实会话:碰都不碰
    killed = []
    def fake_run(cmd, **kw):
        if 'list-sessions' in cmd:
            return _make_proc(stdout=listing)
        if 'kill-session' in cmd:
            killed.append(cmd[-1])
        return _make_proc()
    with patch('subprocess.run', side_effect=fake_run):
        from vibe.tmux_bridge import cleanup_orphan_viewers
        n = cleanup_orphan_viewers(max_age_seconds=300)
    assert n == 1 and killed == ['v-aaaaaaaaaaaa']
