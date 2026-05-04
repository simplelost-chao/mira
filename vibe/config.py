from pathlib import Path
from typing import Optional
import yaml

_DEFAULT_EXCLUDE = ["node_modules", ".venv", "__pycache__"]


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        raise RuntimeError(f"Failed to load config from {path}: {e}") from e


def load_global_config(config_path: Optional[Path] = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "vibe.yaml"
    # Merge home config (~/.vibe.yaml) with project config
    home_data = _read_yaml(Path.home() / ".vibe.yaml")
    proj_data = _read_yaml(config_path)
    data = {**home_data, **proj_data}  # project overrides home
    return {
        "scan_dirs": [str(Path(d).expanduser()) for d in data.get("scan_dirs", [])],
        "exclude": data.get("exclude", _DEFAULT_EXCLUDE),
        "port": data.get("port", 8888),
        "openrouter_api_key": data.get("openrouter_api_key"),
        "deepseek_api_key": data.get("deepseek_api_key"),
        "kimi_api_key": data.get("kimi_api_key"),
        "extra_projects": [str(Path(d).expanduser()) for d in data.get("extra_projects", [])],
        "excluded_paths": [str(Path(d).expanduser()) for d in data.get("excluded_paths", [])],
        "base_services": data.get("base_services", []),
        "admin_password": data.get("admin_password"),
        "notification_sound": data.get("notification_sound", "Pop"),
        "remote_hosts": data.get("remote_hosts", []),
    }


def _project_vibe_yaml() -> Path:
    return Path(__file__).parent.parent / "vibe.yaml"


def add_extra_project(project_path: str) -> None:
    """Add a path to extra_projects in vibe.yaml."""
    cfg_path = _project_vibe_yaml()
    data = _read_yaml(cfg_path)
    extras = data.get("extra_projects", [])
    norm = str(Path(project_path).expanduser().resolve())
    if norm not in [str(Path(e).expanduser().resolve()) for e in extras]:
        extras.append(norm)
        data["extra_projects"] = extras
        cfg_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))


def exclude_project(project_path: str) -> None:
    """Add a path to excluded_paths in vibe.yaml (hides it from discovery)."""
    cfg_path = _project_vibe_yaml()
    data = _read_yaml(cfg_path)
    excluded = data.get("excluded_paths", [])
    norm = str(Path(project_path).expanduser().resolve())
    if norm not in [str(Path(e).expanduser().resolve()) for e in excluded]:
        excluded.append(norm)
        data["excluded_paths"] = excluded
        cfg_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))
    # Also remove from extra_projects if present
    extras = data.get("extra_projects", [])
    new_extras = [e for e in extras if str(Path(e).expanduser().resolve()) != norm]
    if len(new_extras) != len(extras):
        data["extra_projects"] = new_extras
        cfg_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False))


def load_project_config(project_path: Path) -> Optional[dict]:
    vibe_yaml = project_path / "vibe.yaml"
    if not vibe_yaml.exists():
        return None
    try:
        with open(vibe_yaml) as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        raise RuntimeError(f"Failed to load config from {vibe_yaml}: {e}") from e
