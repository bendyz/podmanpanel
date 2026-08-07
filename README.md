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

On first run, you'll be prompted to set up authentication (optional). The web UI will be available at `http://localhost:8080` (or the host/port configured in `podmanpanel.toml`).

## Running as systemd user service

To run PodmanPanel automatically at boot:

```bash
# Create service file
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/podmanpanel.service <<EOF
[Unit]
Description=PodmanPanel Web UI
After=network.target

[Service]
Type=simple
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/.venv/bin/podmanpanel
Restart=on-failure

[Install]
WantedBy=default.target
EOF

# Enable and start
systemctl --user enable --now podmanpanel.service

# Enable user services to start at boot (without login)
sudo loginctl enable-linger $USER

# Check status
systemctl --user status podmanpanel
journalctl --user -u podmanpanel -f
```

## Configuration

Create `podmanpanel.toml` in the project directory:

```toml
[server]
host = "0.0.0.0"   # 0.0.0.0 = accessible from local network, 127.0.0.1 = localhost only
port = 8080

[auth]
username = "admin"
password_hash = "$2b$12$..."  # bcrypt hash - see below
secret_key = "your-secret-key-here"  # generate with: python3 -c "import secrets; print(secrets.token_hex(32))"

[commands]
"Restart Nginx" = "systemctl restart nginx"
"Update System" = "sudo apt update && sudo apt upgrade -y"
```

### Authentication setup

Authentication is configured on first run (interactive prompt) or later via:

```bash
# Interactive helper script (auto-writes to podmanpanel.toml)
python3 generate_auth.py

# Or manually generate and add to config:
python3 -c "import bcrypt; print(bcrypt.hashpw(b'your-password', bcrypt.gensalt()).decode())"
python3 -c "import secrets; print(secrets.token_hex(32))"
```

The `[auth]` section is optional. If not present, authentication is disabled. Sessions are valid for 365 days.

Configuration is read at startup. Restart the server after making changes.

Use `PODMANPANEL_CONFIG` environment variable to specify a different config file path.

## Features

- **Containers**: View and manage Podman containers (start/stop/restart/pull)
- **Quadlet Files**: Create, edit, and manage `.container` files in `~/.config/containers/systemd/`
- **Systemd Integration**: Control services via `systemctl --user` (start/stop/restart/enable/disable)
- **Live Journal**: Real-time log streaming from `journalctl -f` with syntax highlighting
- **Published Ports**: Ports from `PublishPort=` (or the running container) shown per service as clickable links
- **Quick Commands**: Predefined shell commands from the config file — only labels listed in `[commands]` can be run
- **Auto-refresh**: Container and service status updates every 30 seconds

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PODMAN_USER` | `$USER` | User context for podman commands |
| `PODMANPANEL_CONFIG` | `podmanpanel.toml` | Path to config file |
