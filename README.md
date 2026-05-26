# PodmanPanel

Minimal web UI for managing Podman containers and Quadlet systemd unit files.

## Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate  # or: source .venv/bin/activate.fish
pip install -e .

# Run
podmanpanel
```

The web UI will be available at `http://localhost:8080` (or the host/port configured in `podmanpanel.toml`).

## Configuration

Create `podmanpanel.toml` in the project directory:

```toml
[server]
host = "0.0.0.0"   # 0.0.0.0 = accessible from local network, 127.0.0.1 = localhost only
port = 8080

[commands]
"Restart Nginx" = "systemctl restart nginx"
"Update System" = "sudo apt update && sudo apt upgrade -y"
```

Configuration is read at startup. Restart the server after making changes.

Use `PODMANPANEL_CONFIG` environment variable to specify a different config file path.

## Features

- **Containers**: View and manage Podman containers (start/stop/restart/pull)
- **Quadlet Files**: Create, edit, and manage `.container` files in `~/.config/containers/systemd/`
- **Systemd Integration**: Control services via `systemctl --user` (start/stop/restart/enable/disable)
- **Live Journal**: Real-time log streaming from `journalctl -f` with syntax highlighting
- **Quick Commands**: Custom shell commands from config file
- **Auto-refresh**: Container and service status updates every 30 seconds

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PODMAN_USER` | `$USER` | User context for podman commands |
| `PODMANPANEL_CONFIG` | `podmanpanel.toml` | Path to config file |
