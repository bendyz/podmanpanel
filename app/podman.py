import subprocess
import json
import os
from app.config import PODMAN_USER


def run_podman(args: list[str], user: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["podman"] + args
    current_user = os.getenv("USER", "")
    # Only wrap with `su` when targeting a *different* user — su'ing to yourself
    # requires a password in non-interactive contexts and will fail.
    if user and user != "root" and user != current_user:
        cmd = ["su", "-", user, "-c", " ".join(cmd)]
    return subprocess.run(cmd, capture_output=True, text=True)


def _normalize(c: dict) -> dict:
    """Normalize podman JSON fields that differ across versions."""
    names = c.get("Names") or c.get("Name") or ""
    if isinstance(names, list):
        names = names[0] if names else ""
    return {
        "Id": c.get("Id") or c.get("ID", ""),
        "Names": names,
        "Image": c.get("Image", ""),
        "State": c.get("State") or c.get("Status") or "unknown",
    }


def get_containers(user: str = PODMAN_USER) -> list[dict]:
    result = run_podman(["ps", "-a", "--format", "json"], user)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout)
        if not data:
            return []
        return [_normalize(c) for c in data]
    except (json.JSONDecodeError, TypeError):
        return []


def container_action(id_or_name: str, action: str, user: str = PODMAN_USER) -> bool:
    result = run_podman([action, id_or_name], user)
    return result.returncode == 0


def update_image(id_or_name: str, user: str = PODMAN_USER) -> tuple[bool, str]:
    result = run_podman(["ps", "-a", "--format", "json"], user)
    try:
        data = json.loads(result.stdout) or []
        container = next(
            (c for c in data if c.get("Id") == id_or_name or
             (c.get("Names") or [""])[0] == id_or_name),
            None
        )
    except (json.JSONDecodeError, TypeError):
        container = None

    if not container:
        return False, "Container not found"
    image = container.get("Image", "")
    if not image:
        return False, "No image info"
    r = run_podman(["pull", image], user)
    return r.returncode == 0, r.stdout + r.stderr
