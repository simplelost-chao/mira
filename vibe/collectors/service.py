# vibe/collectors/service.py
from pathlib import Path
from typing import Optional
import psutil
from vibe.models import ServiceInfo

def _is_port_in_use(port: int) -> bool:
    """Check if a port is in use. Works without root on macOS."""
    try:
        for proc in psutil.process_iter(['connections']):
            try:
                for conn in (proc.info.get('connections') or []):
                    if hasattr(conn.laddr, 'port') and conn.laddr.port == port:
                        return True
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
    except Exception:
        pass
    return False

def collect_service(path: Path, vibe_cfg: Optional[dict]) -> ServiceInfo:
    if not vibe_cfg or "service" not in vibe_cfg:
        return ServiceInfo()

    svc = vibe_cfg["service"]
    port = svc.get("port")
    process_name = svc.get("process")
    deploy_url = vibe_cfg.get("deploy", {}).get("url")

    is_running = False
    if port:
        is_running = _is_port_in_use(port)

    return ServiceInfo(
        port=port,
        process_name=process_name,
        is_running=is_running,
        url=deploy_url,
    )
