import asyncio
import subprocess
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
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


@router.get("/{service}/journal")
def get_journal(service: str, lines: int = Query(default=200, ge=1, le=5000)):
    r = subprocess.run(
        ["journalctl", "--user", "-u", service, "--no-pager", "-n", str(lines)],
        capture_output=True,
        text=True,
    )
    return {"output": (r.stdout + r.stderr).strip()}


@router.get("/{service}/journal/stream")
async def stream_journal(service: str, lines: int = Query(default=100, ge=0, le=5000)):
    async def generate():
        proc = await asyncio.create_subprocess_exec(
            "journalctl", "--user", "-u", service,
            "--no-pager", "-n", str(lines), "-f",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                yield f"data: {line.decode(errors='replace').rstrip()}\n\n"
        finally:
            proc.kill()
            await proc.wait()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{service}/action")
def do_action(service: str, body: ActionModel):
    if body.action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action. Use: {sorted(VALID_ACTIONS)}",
        )
    r = _run(service, body.action)
    return {"ok": r.returncode == 0, "output": (r.stdout + r.stderr).strip()}
