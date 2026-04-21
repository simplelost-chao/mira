# vibe/collectors/service.py
import re
from pathlib import Path
from typing import Optional
import psutil
from vibe.models import ServiceInfo

# Patterns to scan source code for configured ports
_PORT_RE = re.compile(r'(?:port|PORT)\s*[=:]\s*(\d{3,5})', re.IGNORECASE)
_UVICORN_RE = re.compile(r'uvicorn\.run\([^)]*port\s*=\s*(\d+)')

# Utility processes that are never servers
_NON_SERVER_NAMES = {
    'tail', 'grep', 'rg', 'find', 'git', 'zsh', 'bash', 'sh', 'fish',
    'vim', 'nvim', 'nano', 'less', 'cat', 'awk', 'sed', 'sort', 'wc',
    'ssh', 'rsync', 'cp', 'mv', 'rm', 'ls', 'ps', 'top', 'htop',
    'make', 'cargo', 'rustc', 'gcc', 'clang',
}


def _find_listening_procs(path: Path) -> list[tuple[psutil.Process, list[int]]]:
    """
    Find processes with cwd inside this project that are LISTENING on ports.
    Returns [(proc, [ports])]. Ignores utility processes with no open ports.
    """
    path_str = str(path.resolve())
    results = []
    for proc in psutil.process_iter(['pid', 'name', 'cwd', 'cmdline']):
        try:
            name = (proc.info.get('name') or '').lower()
            if name in _NON_SERVER_NAMES:
                continue
            cwd = proc.info.get('cwd') or ''
            cmdline = ' '.join(proc.info.get('cmdline') or [])
            in_project = (
                (cwd == path_str or cwd.startswith(path_str + '/')) or
                (path_str in cmdline)
            )
            if not in_project:
                continue
            ports = _get_listening_ports(proc)
            if ports:
                results.append((proc, ports))
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            continue
    return results


def _get_listening_ports(proc: psutil.Process) -> list[int]:
    """Get ports this process is actively listening on."""
    ports = []
    try:
        for conn in (proc.connections(kind='inet') or []):
            if conn.status == 'LISTEN' and hasattr(conn.laddr, 'port'):
                ports.append(conn.laddr.port)
    except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
        pass
    return ports


def _port_owner_project(port: int, path: Path) -> bool:
    """Check if the process listening on this port has cwd inside this project."""
    path_str = str(path.resolve())
    try:
        for proc in psutil.process_iter(['cwd', 'cmdline']):
            try:
                ports = _get_listening_ports(proc)
                if port not in ports:
                    continue
                cwd = proc.info.get('cwd') or ''
                cmdline = ' '.join(proc.info.get('cmdline') or [])
                if cwd == path_str or cwd.startswith(path_str + '/') or path_str in cmdline:
                    return True
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                continue
    except Exception:
        pass
    return False


def _scan_code_for_port(path: Path) -> Optional[int]:
    """Scan source entry-point files for a configured port number."""
    candidates = []
    for name in ['main.py', 'app.py', 'server.py', 'run.py', 'manage.py',
                 'index.js', 'server.js', 'app.js']:
        f = path / name
        if f.exists():
            try:
                text = f.read_text(encoding='utf-8', errors='replace')
                for m in _UVICORN_RE.finditer(text):
                    candidates.append(int(m.group(1)))
                for m in _PORT_RE.finditer(text):
                    p = int(m.group(1))
                    if 1024 <= p <= 65535:
                        candidates.append(p)
            except Exception:
                pass
    env_file = path / '.env'
    if env_file.exists():
        try:
            for m in _PORT_RE.finditer(env_file.read_text(encoding='utf-8', errors='replace')):
                p = int(m.group(1))
                if 1024 <= p <= 65535:
                    candidates.append(p)
        except Exception:
            pass
    return candidates[0] if candidates else None


def collect_service(path: Path, vibe_cfg: Optional[dict]) -> ServiceInfo:
    cfg_port = None
    cfg_process = None
    deploy_url = None
    if vibe_cfg:
        svc = vibe_cfg.get('service', {})
        cfg_port = svc.get('port')
        cfg_process = svc.get('process')
        deploy_url = vibe_cfg.get('deploy', {}).get('url')

    # 1. Find processes in this project that are actually listening on ports
    listening = _find_listening_procs(path)
    if listening:
        proc, ports = listening[0]
        return ServiceInfo(
            port=cfg_port or ports[0],
            process_name=cfg_process or proc.name(),
            is_running=True,
            url=deploy_url,
        )

    # 2. Determine port from config or code scan
    port = cfg_port or _scan_code_for_port(path)
    if not port:
        return ServiceInfo(url=deploy_url)

    # 3. Check if this port is owned by a process in this project
    is_running = _port_owner_project(port, path)

    return ServiceInfo(
        port=port,
        process_name=cfg_process,
        is_running=is_running,
        url=deploy_url,
    )
