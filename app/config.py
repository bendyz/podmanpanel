import os
import tomllib
from pathlib import Path

PODMAN_USER = os.getenv("PODMAN_USER", os.getenv("USER", "root"))
# Quadlet files live directly in ~/.config/containers/systemd/ (and optionally user/ subdir)
QUADLET_DIR = os.path.expanduser("~/.config/containers/systemd")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

_CONFIG_PATH = Path(os.getenv("PODMANPANEL_CONFIG", "podmanpanel.toml"))


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


_config = _load_config()

SERVER_HOST: str = _config.get("server", {}).get("host", "127.0.0.1")
SERVER_PORT: int = int(_config.get("server", {}).get("port", 8080))
CUSTOM_COMMANDS: dict[str, str] = _config.get("commands", {})
