# Mira

A self-hosted project management dashboard that aggregates git status, running services, Claude AI session history, terminal output, and deployment info — all in one place.

> **Screenshot coming soon**

## Features

- **Project overview** — git branch, recent commits, open issues, service health; cards sorted by most recent Claude session activity
- **System architecture** — LLM-generated architecture diagrams and module maps
- **Interactive terminal** — full PTY terminal via ttyd + tmux; panes grouped by project, kill-pane button, new-terminal dialog with project picker
- **Mobile terminal** — WebSocket streaming with client-side ANSI rendering, dedicated input bar that bypasses iOS keyboard issues
- **Terminal state detection** — automatically detects running / idle / awaiting-confirmation states
- **Clipboard bridge** — Cmd+C via tmux buffer for HTTP environments
- **Design docs** — plans, specs, and AI-generated summaries per project
- **Claude Code usage monitor** — real-time session + weekly usage ring charts in topbar, tap for reset countdown
- **Safari-style tab switcher** — 3D card grid on mobile with terminal preview, tap to switch, swipe to close
- **New project wizard** — AI-powered project brainstorming with DeepSeek/OpenRouter/Gemini, auto-generates logo + scaffold
- **5 theme skins** — Default / Neon Pixel / Cyber Pixel / Claude Light / Claude Dark, with per-skin ANSI color tuning
- **Settings panel** — API key management, notification sounds, flat/tree terminal list toggle
- **Balance cards** — 2-column mobile layout, expandable with 30-day sparkline on desktop
- **Mobile optimizations** — clickable URLs in terminal output, URL rejoining across line wraps, disconnect banner with reconnect, Esc/number shortcut keys
- **Unified icon topbar** — consistent 32×32 SVG icon buttons across all pages
- **Version badge** — current version displayed in the bottom-right corner
- **Admin auth** — password-protected write operations and sensitive data views

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [tmux](https://github.com/tmux/tmux) — required for the dev terminal feature
- [ttyd](https://github.com/tsl0922/ttyd) — required for the interactive PTY terminal

Install dependencies:

```bash
# macOS
brew install tmux ttyd

# Ubuntu / Debian
sudo apt install tmux
snap install ttyd --classic   # or build from source: github.com/tsl0922/ttyd

# Arch
sudo pacman -S tmux ttyd
```

Mira will start without tmux/ttyd, but the terminal tab will be non-functional.

---

## Quick Start

### Option 1 — Direct (uv)

```bash
git clone https://github.com/simplelost-chao/mira.git
cd mira

# Create your config
cp vibe.example.yaml vibe.yaml
# Edit vibe.yaml — set scan_dirs and admin_password at minimum

uv sync
uv run vibe serve
```

Open [http://localhost:8888](http://localhost:8888).

For development with auto-reload:

```bash
uv run vibe serve --reload
```

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

Edit `docker-compose.yml` to mount the directories you want Mira to scan:

```yaml
volumes:
  - ./vibe.yaml:/app/vibe.yaml:ro
  - ~/projects:/home/user/projects:ro          # add your project dirs here
  - ~/Documents/Projects:/home/user/docs:ro
```

Then update `scan_dirs` in `vibe.yaml` to match the container paths:

```yaml
scan_dirs:
  - /home/user/projects
  - /home/user/docs
```

---

## Configuration

All config lives in `vibe.yaml` (gitignored — never committed). See [`vibe.example.yaml`](vibe.example.yaml) for a fully-commented template.

| Field | Required | Description |
|---|---|---|
| `scan_dirs` | **yes** | Directories to scan for projects |
| `admin_password` | recommended | Protects write ops and sensitive data; leave empty to disable auth |
| `port` | no | Port to listen on (default: `8888`) |
| `openrouter_api_key` | no | For AI-powered project summaries (via OpenRouter) |
| `deepseek_api_key` | no | Alternative LLM provider |
| `kimi_api_key` | no | Alternative LLM provider |
| `exclude` | no | File/folder patterns to skip inside each project |
| `excluded_paths` | no | Absolute paths to hide from project discovery |
| `base_services` | no | Shared services displayed in the services panel |

### Per-project config

Drop a `vibe.yaml` in any project root to control how it appears in Mira:

```yaml
name: my-app
description: What this project does
domain: my-app.example.com   # public URL if exposed

service:
  port: 3000
  health_path: /healthz
  health_token: my-ok        # expected response token from health endpoint
```

---

## Run on Login (macOS)

Create a launchd plist to start Mira automatically:

```bash
cat > ~/Library/LaunchAgents/mira.vibe.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>mira.vibe</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/uv</string>
        <string>run</string>
        <string>vibe</string>
        <string>serve</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/mira</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/mira.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/mira.err.log</string>
</dict>
</plist>
EOF

# Replace /path/to/mira and /usr/local/bin/uv with your actual paths
# Find uv path with: which uv

launchctl load ~/Library/LaunchAgents/mira.vibe.plist
```

To restart after config changes:

```bash
launchctl stop mira.vibe && launchctl start mira.vibe
```

---

## Run as a Service (Linux / systemd)

```bash
sudo tee /etc/systemd/system/mira.service << 'EOF'
[Unit]
Description=Mira project dashboard
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/mira
ExecStart=/home/YOUR_USER/.local/bin/uv run vibe serve
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now mira
```

View logs:

```bash
journalctl -u mira -f
```

---

## Expose via Cloudflare Tunnel (optional)

To access Mira from anywhere without opening firewall ports:

```bash
# One-off (temporary URL printed to stdout)
cloudflared tunnel --url http://localhost:8888
```

For a permanent named tunnel, follow the [Cloudflare Tunnel docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/).

---

## CLI Reference

```bash
vibe serve                        # Start the dashboard (binds to 127.0.0.1:8888)
vibe serve --host 0.0.0.0         # Bind to all interfaces (for remote/Docker access)
vibe serve --port 9000            # Custom port
vibe serve --reload               # Auto-reload on file changes (dev mode)

vibe term <project>               # Open a tmux session for a project and attach it to Mira
vibe term <project> --cmd "npm run dev"   # Run a specific command in that session

vibe summarize                    # Generate AI summaries for all discovered projects
```

---

## Tech Stack

- **Backend:** Python / FastAPI / uvicorn
- **Frontend:** Vanilla JS + CSS (no build step)
- **Terminal:** ttyd (PTY) + tmux + WebSocket streaming
- **Data:** YAML config + SQLite cache
- **AI summaries:** OpenRouter / DeepSeek / Kimi (all optional)

---

## License

MIT
