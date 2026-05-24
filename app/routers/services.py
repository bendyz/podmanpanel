"""Unified view: merges quadlet files + running containers into one list."""
import subprocess
from fastapi import APIRouter
from app.quadlet import get_quadlet_files, get_container_name_for_quadlet
from app.podman import get_containers

router = APIRouter(prefix="/api/services", tags=["services"])


def _is_enabled(service: str) -> str:
    """Return the systemctl is-enabled string (enabled/disabled/not-found/…)."""
    r = subprocess.run(
        ["systemctl", "--user", "is-enabled", service],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip() or "unknown"


@router.get("")
def list_services():
    quadlets = get_quadlet_files()
    containers = get_containers()

    by_name: dict[str, dict] = {c["Names"]: c for c in containers}
    matched_ids: set[str] = set()
    result = []

    for q in quadlets:
        cname = get_container_name_for_quadlet(q["path"], q["name"])
        container = by_name.get(cname)
        if container:
            matched_ids.add(container["Id"])

        result.append({
            "service": q["service"],
            "quadlet_file": q["name"],
            "container_id": container["Id"] if container else None,
            "container_name": cname,
            "image": container["Image"] if container else None,
            "state": container["State"] if container else None,
            "enabled": _is_enabled(q["service"]),
        })

    # Containers with no matching quadlet file
    for c in containers:
        if c["Id"] not in matched_ids:
            result.append({
                "service": None,
                "quadlet_file": None,
                "container_id": c["Id"],
                "container_name": c["Names"],
                "image": c["Image"],
                "state": c["State"],
                "enabled": None,
            })

    return result
