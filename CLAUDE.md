# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PodmanPanel is a minimal FastAPI web UI for managing Podman containers and Quadlet (systemd) unit files. It wraps `podman` CLI commands and `systemctl --user` via subprocess and exposes a REST API consumed by a single-page frontend.

## Commands

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate.fish   # or: source .venv/bin/activate
pip install -e .
```

### Run
```bash
podmanpanel                                              # uses podmanpanel.toml for host/port
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload  # dev with auto-reload
```

### Configuration
Edit `podmanpanel.toml` (read at startup; restart required after changes):
```toml
[server]
host = "0.0.0.0"   # 0.0.0.0 = local network; 127.0.0.1 = localhost only
port = 8080

[commands]
"Restart Nginx" = "systemctl restart nginx"
```

`PODMANPANEL_CONFIG` env var overrides the config file path.

## Architecture

### Request flow
Browser → FastAPI (`app/main.py`) → Router (`app/routers/`) → Helper (`app/podman.py` / `app/quadlet.py`) → `podman` / `systemctl` subprocess

### Key files

| File | Role |
|---|---|
| `app/config.py` | Loads `podmanpanel.toml` via stdlib `tomllib`; exports `SERVER_HOST`, `SERVER_PORT`, `CUSTOM_COMMANDS`, `QUADLET_DIR`, `PODMAN_USER` |
| `app/podman.py` | Wraps `podman` CLI. Uses `su - user` only when the target user differs from `$USER` (su'ing to yourself fails in non-interactive contexts). `get_containers()` runs `podman ps -a`. `_normalize()` handles `Names` being a list in newer podman versions. |
| `app/quadlet.py` | Scans `~/.config/containers/systemd/` and its `user/` subdir for `.container` files. Returns `{name, service, path}` dicts where `service = stem + ".service"`. |
| `app/routers/containers.py` | `GET /api/containers`, `POST /api/containers/{id}/action`, `POST /api/containers/{id}/update` |
| `app/routers/quadlet.py` | `GET /api/quadlet`, `GET /api/quadlet/{name}`, `PUT /api/quadlet/{name}` |
| `app/routers/commands.py` | `GET /api/commands` (lists from config), `POST /api/commands` (runs shell command, 60 s timeout, `shell=True`) |
| `app/routers/systemctl.py` | `GET /api/systemctl/{service}/status`, `POST /api/systemctl/{service}/action` — runs `systemctl --user` |
| `app/main.py` | FastAPI app; `/api/info` endpoint; `INDEX_HTML` embedded frontend; `main()` entry point reads host/port from config |
| `podmanpanel.toml` | User-edited config (not committed with secrets) |
| `static/` | Optional: `static/index.html` overrides the embedded `INDEX_HTML` for frontend development |

### Frontend
Single HTML page embedded as `INDEX_HTML` in `app/main.py`. Tailwind CSS from CDN. Four panels:
- **Containers** — `podman ps -a`, start/stop/restart/pull, auto-refreshes every 30 s
- **Quadlet Files** — lists `.container` files, systemctl start/stop/restart/status per file, inline output, edit modal
- **Quick Commands** — buttons from `[commands]` in `podmanpanel.toml`, ⏳/✅/❌ indicator, output below
- **Run Command** — freeform shell input, Ctrl+Enter submits

### Env vars
| Variable | Default | Purpose |
|---|---|---|
| `PODMAN_USER` | `$USER` | Which user's podman context to target |
| `PODMANPANEL_CONFIG` | `podmanpanel.toml` | Path to config file |

### Quadlet notes
Only `.container` files are managed. `~/.config/containers/systemd/` must exist and contain files for the Quadlet section to show anything. The systemd service name is derived as `<stem>.service` from the filename. `systemctl --user` is used (rootless podman).
