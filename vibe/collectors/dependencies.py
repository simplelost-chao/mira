# vibe/collectors/dependencies.py
"""Detect external service dependencies by scanning .env, docker-compose, and config files."""
import re
import urllib.parse
from pathlib import Path
from vibe.models import ExternalDep

# Env var patterns: COSYVOICE_URL, REDIS_HOST, DATABASE_URL, OPENAI_API_BASE …
_URL_VAR_RE = re.compile(
    r'^([A-Z][A-Z0-9_]*)_(?:URL|HOST|ENDPOINT|API_BASE|BASE_URL|URI)\s*=\s*(.+)$',
    re.MULTILINE,
)
_PORT_VAR_RE = re.compile(r'^([A-Z][A-Z0-9_]*)_PORT\s*=\s*(\d+)$', re.MULTILINE)

# Map well-known service name fragments → display name
_KNOWN_SERVICES = {
    'cosyvoice': 'CosyVoice',
    'redis': 'Redis',
    'postgres': 'PostgreSQL',
    'postgresql': 'PostgreSQL',
    'mysql': 'MySQL',
    'mongo': 'MongoDB',
    'elasticsearch': 'Elasticsearch',
    'rabbitmq': 'RabbitMQ',
    'kafka': 'Kafka',
    'openai': 'OpenAI',
    'ollama': 'Ollama',
    'minio': 'MinIO',
    's3': 'S3',
    'sentry': 'Sentry',
    'celery': 'Celery',
}

# Ignore purely internal/auth vars
_IGNORE_PREFIXES = {
    'SECRET', 'TOKEN', 'KEY', 'PASSWORD', 'AUTH', 'JWT',
    'CALLBACK', 'REDIRECT', 'FRONTEND', 'BACKEND', 'CORS',
}


def _friendly_name(var_prefix: str) -> str:
    lower = var_prefix.lower()
    for fragment, display in _KNOWN_SERVICES.items():
        if fragment in lower:
            return display
    # Title-case the prefix, strip common noise
    cleaned = var_prefix.replace('_', ' ').title()
    for noise in ('Api', 'Service', 'Server', 'Db', 'Database'):
        cleaned = cleaned.replace(noise, noise)
    return cleaned


def _extract_port(url: str) -> int | None:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.port:
            return parsed.port
        if parsed.scheme == 'http':
            return 80
        if parsed.scheme == 'https':
            return 443
    except Exception:
        pass
    return None


def _should_ignore(prefix: str) -> bool:
    for p in _IGNORE_PREFIXES:
        if p in prefix:
            return True
    return False


def _scan_env_file(f: Path) -> list[ExternalDep]:
    deps = []
    try:
        text = f.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return deps

    seen_names: set[str] = set()

    for m in _URL_VAR_RE.finditer(text):
        prefix, value = m.group(1), m.group(2).strip().strip('"\'')
        if _should_ignore(prefix) or not value or value.startswith('#'):
            continue
        # Skip placeholders
        if value.startswith('${') or value in ('', 'your_value', 'change_me'):
            continue
        name = _friendly_name(prefix)
        if name in seen_names:
            continue
        seen_names.add(name)
        deps.append(ExternalDep(
            name=name,
            url=value,
            port=_extract_port(value),
            source=f'{f.name}: {prefix}',
        ))

    for m in _PORT_VAR_RE.finditer(text):
        prefix, port_str = m.group(1), m.group(2)
        if _should_ignore(prefix):
            continue
        name = _friendly_name(prefix)
        if name in seen_names:
            continue
        # Only add port-only if not localhost-obvious
        port = int(port_str)
        if port in (80, 443, 22):
            continue
        seen_names.add(name)
        deps.append(ExternalDep(name=name, port=port, source=f'{f.name}: {prefix}_PORT'))

    return deps


def _scan_docker_compose(f: Path) -> list[ExternalDep]:
    """Extract named services from docker-compose that this project depends on."""
    deps = []
    try:
        import yaml
        with open(f) as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        return deps

    services = data.get('services', {})
    for svc_name, svc_cfg in services.items():
        if not isinstance(svc_cfg, dict):
            continue
        image = svc_cfg.get('image', '')
        # Ignore the app service itself (usually has no standard image)
        if not image:
            continue
        name = _friendly_name(svc_name.upper())
        ports = svc_cfg.get('ports', [])
        port = None
        if ports:
            try:
                first = str(ports[0]).split(':')[-1].split('/')[0]
                port = int(first)
            except Exception:
                pass
        deps.append(ExternalDep(name=name, port=port, source=f'{f.name}: {svc_name}'))

    return deps


def collect_dependencies(path: Path) -> list[ExternalDep]:
    deps: list[ExternalDep] = []
    seen: set[str] = set()

    def add(d: ExternalDep):
        if d.name not in seen:
            seen.add(d.name)
            deps.append(d)

    # Scan .env files
    for env_name in ['.env', '.env.local', '.env.production', '.env.example']:
        f = path / env_name
        if f.exists():
            for d in _scan_env_file(f):
                add(d)
        # Also scan subdirectories one level deep
        for subdir in ['server', 'backend', 'api', 'app']:
            f2 = path / subdir / env_name
            if f2.exists():
                for d in _scan_env_file(f2):
                    add(d)

    # Scan docker-compose
    for dc_name in ['docker-compose.yml', 'docker-compose.yaml']:
        f = path / dc_name
        if f.exists():
            for d in _scan_docker_compose(f):
                add(d)

    return deps
