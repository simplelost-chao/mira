# vibe/collectors/service.py
import re
import socket
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
            # Only match cwd OR the script/executable itself being inside the project.
            # Don't match on arbitrary arguments (e.g. --voice_refs /project/...)
            script = next((a for a in (proc.info.get('cmdline') or []) if a.endswith('.py') or a.endswith('.js')), '')
            in_project = (
                (cwd == path_str or cwd.startswith(path_str + '/')) or
                script.startswith(path_str + '/')
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


def _port_is_healthy(port: int, health_path: str = '/', health_token: str | None = None) -> bool:
    """TCP check + HTTP health check with optional token verification."""
    import urllib.request, urllib.error
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            pass
    except OSError:
        return False

    req = urllib.request.Request(
        f'http://127.0.0.1:{port}{health_path}',
        headers={'User-Agent': 'mira-healthcheck/1.0'},
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status >= 500:
                return False
            if health_token:
                body = resp.read().decode('utf-8', errors='replace')
                return health_token in body
            return True
    except urllib.error.HTTPError as e:
        return e.code < 500 and not health_token  # token required but got error → down
    except Exception:
        return not health_token  # non-HTTP service: ok if no token required


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
                script = next((a for a in (proc.info.get('cmdline') or []) if a.endswith('.py') or a.endswith('.js')), '')
                if cwd == path_str or cwd.startswith(path_str + '/') or script.startswith(path_str + '/'):
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


def _domain_is_healthy(domain: str, health_path: str = '/', health_token: str | None = None) -> bool:
    """Check public domain via HTTPS with optional token verification."""
    import urllib.request, urllib.error
    url = f'https://{domain}{health_path}'
    req = urllib.request.Request(url, headers={'User-Agent': 'mira-healthcheck/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status >= 500:
                return False
            if health_token:
                body = resp.read().decode('utf-8', errors='replace')
                return health_token in body
            return True
    except urllib.error.HTTPError as e:
        return e.code < 500 and not health_token
    except Exception:
        return False


def collect_service(path: Path, vibe_cfg: Optional[dict]) -> ServiceInfo:
    cfg_port = None
    cfg_process = None
    deploy_url = None
    cfg_domain = None
    health_path = '/'
    health_token = None
    domain_health_path = None
    if vibe_cfg:
        svc = vibe_cfg.get('service', {})
        cfg_port = svc.get('port')
        cfg_process = svc.get('process')
        health_path = svc.get('health_path', '/')
        health_token = svc.get('health_token')
        domain_health_path = svc.get('domain_health_path')    # optional path override for domain check
        domain_health_token = svc.get('domain_health_token')  # explicit override; falls back to health_token
        deploy_url = vibe_cfg.get('deploy', {}).get('url')
        domains_val = vibe_cfg.get('domains') or vibe_cfg.get('domain')
        if isinstance(domains_val, list):
            cfg_domain = domains_val[0] if domains_val else None
        else:
            cfg_domain = domains_val

    # 1. Determine the expected port from config or code scan
    port = cfg_port or _scan_code_for_port(path)

    # Check domain health — always verify health_token (暗号) if configured
    domain_ok: Optional[bool] = None
    if cfg_domain:
        d_path = domain_health_path or health_path
        d_token = domain_health_token if domain_health_token is not None else health_token
        domain_ok = _domain_is_healthy(cfg_domain, d_path, d_token)

    # 2. Check if expected port is healthy (TCP + HTTP + optional token)
    if port and _port_is_healthy(port, health_path, health_token):
        proc_name = cfg_process
        if not proc_name:
            listening = _find_listening_procs(path)
            if listening:
                proc_name = listening[0][0].name()
        return ServiceInfo(
            port=port,
            process_name=proc_name,
            is_running=True,
            url=deploy_url,
            public_domain=cfg_domain,
            domain_ok=domain_ok,
        )

    # 3. If no expected port, fall back to checking any listening process (no token check)
    if not port:
        listening = _find_listening_procs(path)
        if listening:
            proc, ports = listening[0]
            actual_port = ports[0]
            return ServiceInfo(
                port=actual_port,
                process_name=cfg_process or proc.name(),
                is_running=True,
                url=deploy_url,
                public_domain=cfg_domain,
                domain_ok=domain_ok,
            )
        return ServiceInfo(url=deploy_url, public_domain=cfg_domain, domain_ok=domain_ok)

    # 4. Port not open locally — but domain may still be reachable (remote deployment)
    return ServiceInfo(
        port=port,
        process_name=cfg_process,
        is_running=bool(domain_ok),  # running if domain is up, even if local port is closed
        url=deploy_url,
        public_domain=cfg_domain,
        domain_ok=domain_ok,
    )
