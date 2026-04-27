# Mira

A self-hosted project management dashboard that aggregates git status, running services, Claude AI session history, terminal output, and deployment info — all in one place.

![Mira Dashboard](docs/screenshot.png)

## Features

- **Project overview** — git branch, recent commits, open issues, service health
- **Dev terminal** — attach to tmux sessions, send commands, view ANSI-colored output
- **System architecture** — LLM-generated architecture diagrams and module maps
- **Design docs** — plans, specs, and AI-generated summaries per project
- **Multi-theme UI** — dark, neon-pixel, pixel-cyber skins
- **Admin auth** — password-protected write operations and sensitive data

## Quick Start

### Option 1 — Direct (uv)

**Requirements:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/simplelost-chao/mira.git
cd mira

# Create your config from the example
cp vibe.example.yaml vibe.yaml
# Edit vibe.yaml: set scan_dirs, admin_password, and optionally API keys

uv sync
uv run vibe serve
```

Open [http://localhost:8888](http://localhost:8888).

---

### Option 2 — Docker

```bash
git clone https://github.com/simplelost-chao/mira.git
cd mira

cp vibe.example.yaml vibe.yaml
# Edit vibe.yaml

docker compose up -d
```

Open [http://localhost:8888](http://localhost:8888).

> **Note:** Edit the `volumes:` in `docker-compose.yml` to mount the directories you want Mira to scan.

---

## Configuration

All config lives in `vibe.yaml` (gitignored). See [`vibe.example.yaml`](vibe.example.yaml) for a fully-commented template.

| Field | Required | Description |
|---|---|---|
| `scan_dirs` | yes | Directories to scan for projects |
| `admin_password` | recommended | Protects write ops; leave empty to disable |
| `port` | no | Port to listen on (default `8888`) |
| `openrouter_api_key` | no | For AI-powered project summaries |
| `deepseek_api_key` | no | Alternative LLM provider |
| `kimi_api_key` | no | Alternative LLM provider |
| `exclude` | no | File/folder patterns to skip (default: `node_modules`, `.venv`, `__pycache__`) |
| `excluded_paths` | no | Absolute paths to hide from scanning |
| `base_services` | no | Shared services shown in the services panel |

### Per-project config

Drop a `vibe.yaml` in any project root to customize how it appears:

```yaml
name: my-app
description: What this project does
domain: my-app.example.com
service:
  port: 3000
  health_path: /healthz
  health_token: my-ok
```

---

## Expose via Cloudflare Tunnel (optional)

To access Mira from anywhere without opening firewall ports:

```bash
# Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
cloudflared tunnel --url http://localhost:8888
```

For a permanent tunnel, follow the [Cloudflare Tunnel docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).

---

## CLI Commands

```bash
vibe serve          # Start the dashboard server
vibe add <path>     # Add a project to the dashboard
vibe remove <path>  # Remove a project
vibe term <name>    # Attach to a project's tmux session
```

---

## Tech Stack

- **Backend:** Python / FastAPI / uvicorn
- **Frontend:** Vanilla JS + CSS (no build step)
- **Data:** YAML config + SQLite cache
- **AI:** OpenRouter / DeepSeek / Kimi (optional)

## License

MIT
