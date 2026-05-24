import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/systemctl", tags=["systemctl"])

VALID_ACTIONS = {"start", "stop", "restart", "reload", "enable", "disable"}


class ActionModel(BaseModel):
    action: str


def _run(service: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["systemctl", "--user", *args, service],
        capture_output=True,
        text=True,
    )


@router.post("/daemon-reload")
def daemon_reload():
    r = subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "output": (r.stdout + r.stderr).strip()}


@router.get("/{service}/status")
def get_status(service: str):
    r = _run(service, "status")
    enabled_r = subprocess.run(
        ["systemctl", "--user", "is-enabled", service],
        capture_output=True, text=True,
    )
    # exit code 0 = active, 3 = inactive (not failed), 4 = not found
    return {
        "ok": r.returncode == 0,
        "active": r.returncode == 0,
        "enabled": enabled_r.stdout.strip() or "unknown",
        "output": r.stdout + r.stderr,
    }


@router.post("/{service}/action")
def do_action(service: str, body: ActionModel):
    if body.action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Use: {sorted(VALID_ACTIONS)}",
        )
    r = _run(service, body.action)
    return {"ok": r.returncode == 0, "output": (r.stdout + r.stderr).strip()}
