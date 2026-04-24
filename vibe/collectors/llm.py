"""Detect which LLM APIs a project uses.

Scans .env files, requirements.txt, package.json, and source code for
LLM provider signals. Returns a deduplicated list of provider names.
"""
import re
from pathlib import Path

# API key env var prefix → provider name
_KEY_MAP = {
    'OPENAI':       'OpenAI',
    'ANTHROPIC':    'Claude',
    'DEEPSEEK':     'DeepSeek',
    'OPENROUTER':   'OpenRouter',
    'MOONSHOT':     'Kimi',
    'KIMI':         'Kimi',
    'DASHSCOPE':    'Qianwen',
    'QWEN':         'Qianwen',
    'GEMINI':       'Gemini',
    'GOOGLE':       'Gemini',       # GOOGLE_API_KEY often means Gemini
    'GROQ':         'Groq',
    'TOGETHER':     'Together AI',
    'MISTRAL':      'Mistral',
    'COHERE':       'Cohere',
    'PERPLEXITY':   'Perplexity',
    'XAI':          'Grok',
    'OLLAMA':       'Ollama',
}

# Model name substrings in source/config → provider
_MODEL_MAP = {
    'gpt-4':            'OpenAI',
    'gpt-3.5':          'OpenAI',
    'o1-':              'OpenAI',
    'o3-':              'OpenAI',
    'claude-':          'Claude',
    'deepseek-':        'DeepSeek',
    'qwen':             'Qianwen',
    'moonshot-':        'Kimi',
    'gemini-':          'Gemini',
    'llama':            'Ollama',
    'mistral':          'Mistral',
    'mixtral':          'Mistral',
    'groq':             'Groq',
    'grok-':            'Grok',
}

# Python packages → provider
_PKG_MAP = {
    'openai':           'OpenAI',
    'anthropic':        'Claude',
    'google-generativeai': 'Gemini',
    'google-genai':     'Gemini',
    'langchain-openai': 'OpenAI',
    'langchain-anthropic': 'Claude',
    'cohere':           'Cohere',
    'mistralai':        'Mistral',
    'groq':             'Groq',
    'together':         'Together AI',
}

_API_KEY_RE = re.compile(
    r'^([A-Z][A-Z0-9_]+?)_API_KEY[ \t]*=[ \t]*(.+)$', re.MULTILINE
)
_MODEL_RE = re.compile(r'["\']([a-z0-9][-a-z0-9._/]+)["\']')


def _scan_env(path: Path, found: set[str]) -> None:
    for name in ['.env', '.env.local', '.env.production', '.env.example', '.env.sample']:
        for base in [path] + [path / d for d in ('server', 'backend', 'api', 'app')]:
            f = base / name
            if not f.exists():
                continue
            try:
                text = f.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            for m in _API_KEY_RE.finditer(text):
                prefix = m.group(1)
                value = m.group(2).strip().strip('"\'')
                # Skip empty / placeholder values
                _PLACEHOLDERS = {'your_key', 'xxx', 'changeme', 'your-key-here', 'your_api_key'}
                if not value or value.startswith('${') or value in _PLACEHOLDERS or '...' in value:
                    continue
                for k, name_ in _KEY_MAP.items():
                    if k in prefix:
                        found.add(name_)
                        break


_PKG_SKIP_DIRS = {'node_modules', '.git', '.venv', 'venv', '__pycache__',
                  '.next', 'dist', 'build', 'out', 'coverage', 'ai-research'}


def _scan_packages(path: Path, found: set[str]) -> None:
    # requirements.txt / requirements/*.txt
    for req_file in list(path.glob('requirements*.txt')) + list(path.glob('requirements/*.txt')):
        try:
            text = req_file.read_text(errors='replace').lower()
        except Exception:
            continue
        for pkg, provider in _PKG_MAP.items():
            if pkg in text:
                found.add(provider)

    # pyproject.toml
    toml = path / 'pyproject.toml'
    if toml.exists():
        try:
            text = toml.read_text(errors='replace').lower()
            for pkg, provider in _PKG_MAP.items():
                if pkg in text:
                    found.add(provider)
        except Exception:
            pass

    # package.json
    pkg_json = path / 'package.json'
    if pkg_json.exists():
        try:
            text = pkg_json.read_text(errors='replace').lower()
            for pkg, provider in _PKG_MAP.items():
                if pkg in text:
                    found.add(provider)
            if 'openai' in text:
                found.add('OpenAI')
        except Exception:
            pass


def _scan_source(path: Path, found: set[str]) -> None:
    """Look for model name strings in source files."""
    exts = {'.py', '.ts', '.js', '.go', '.yaml', '.yml', '.json', '.toml', '.env'}
    skip = {'node_modules', '.git', '.venv', 'venv', '__pycache__', 'dist', 'build',
            '.next', '.nuxt', 'out', 'coverage', 'ai-research', 'tests', 'test', '__tests__',
            'collectors'}
    for f in path.rglob('*'):
        if f.suffix not in exts:
            continue
        if any(p in f.parts for p in skip):
            continue
        if f.stat().st_size > 200_000:
            continue
        try:
            text = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for m in _MODEL_RE.finditer(text):
            val = m.group(1).lower()
            for pattern, provider in _MODEL_MAP.items():
                if val.startswith(pattern) or pattern in val:
                    found.add(provider)


# Providers that are commonly routed through OpenRouter — hide them if OpenRouter is present
_OPENROUTER_ROUTED = {'OpenAI', 'Claude', 'Gemini', 'Groq', 'Mistral', 'Together AI', 'Perplexity', 'Grok', 'Cohere'}


def collect_llm_apis(path: Path) -> list[str]:
    """Return sorted list of detected LLM provider names for a project."""
    found: set[str] = set()
    _scan_env(path, found)
    _scan_packages(path, found)
    _scan_source(path, found)

    # If OpenRouter is present, suppress providers typically routed through it
    if 'OpenRouter' in found:
        found -= _OPENROUTER_ROUTED

    return sorted(found)
