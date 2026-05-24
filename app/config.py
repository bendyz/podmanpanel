import os

PODMAN_USER = os.getenv("PODMAN_USER", os.getenv("USER", "root"))
QUADLET_DIR = os.path.expanduser(f"~/.config/containers/systemd/user")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")