# tests/collectors/test_service.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from vibe.collectors.service import collect_service

def test_no_vibe_config(tmp_path):
    info = collect_service(tmp_path, None)
    assert info.is_running == False
    assert info.port is None

def test_port_in_use():
    vibe_cfg = {"service": {"port": 9999, "process": "test-proc"}}
    with patch("vibe.collectors.service._port_is_healthy", return_value=True):
        info = collect_service(Path("/tmp"), vibe_cfg)
    assert info.port == 9999
    assert info.is_running == True

def test_port_not_in_use():
    vibe_cfg = {"service": {"port": 9998}}
    with patch("psutil.process_iter", return_value=[]):
        info = collect_service(Path("/tmp"), vibe_cfg)
    assert info.port == 9998
    assert info.is_running == False
