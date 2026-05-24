import subprocess
import json
import os
from app.config import PODMAN_USER


def run_podman(args: list[str], user: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["podman"] + args
    if user and user != "root":
        cmd = ["su", "-", user, "-c", " ".join(cmd)]
    return subprocess.run(cmd, capture_output=True, text=True)


def get_containers(user: str = PODMAN_USER) -> list[dict]:
    result = run_podman(["ps", "--format", "json"], user)
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def get_container(id_or_name: str, user: str = PODMAN_USER) -> dict | None:
    containers = get_containers(user)
    for c in containers:
        if c.get("Id") == id_or_name or c.get("Names") == id_or_name:
            return c
    return None


def container_action(id_or_name: str, action: str, user: str = PODMAN_USER) -> bool:
    result = run_podman([action, id_or_name], user)
    return result.returncode == 0


def update_image(id_or_name: str, user: str = PODMAN_USER) -> tuple[bool, str]:
    container = get_container(id_or_name, user)
    if not container:
        return False, "Container not found"
    image = container.get("Image", "")
    if not image:
        return False, "No image info"
    result = run_podman(["pull", image], user)
    return result.returncode == 0, result.stdout + result.stderr


def pull_image(image: str, user: str = PODMAN_USER) -> tuple[bool, str]:
    result = run_podman(["pull", image], user)
    return result.returncode == 0, result.stdout + result.stderr