import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.quadlet import get_quadlet_files, read_quadlet, write_quadlet, create_quadlet

router = APIRouter(prefix="/api/quadlet", tags=["quadlet"])


class QuadletEditModel(BaseModel):
    content: str


@router.get("")
def list_quadlet():
    return {"files": get_quadlet_files()}


class QuadletCreateModel(BaseModel):
    name: str
    content: str


@router.post("")
def create_file(body: QuadletCreateModel):
    name = body.name.strip()
    if not name.endswith(".container"):
        raise HTTPException(status_code=400, detail="Filename must end with .container")
    if "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Filename must not contain path separators")
    path = create_quadlet(name, body.content)
    if path is None:
        raise HTTPException(status_code=409, detail="File already exists")
    reload = subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        capture_output=True,
        text=True,
    )
    return {
        "ok": True,
        "path": str(path),
        "reload_ok": reload.returncode == 0,
        "reload_msg": (reload.stdout + reload.stderr).strip(),
    }


@router.get("/{name}")
def get_file(name: str):
    content = read_quadlet(name)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"name": name, "content": content}


@router.put("/{name}")
def save_file(name: str, body: QuadletEditModel):
    if not name.endswith(".container"):
        raise HTTPException(status_code=400, detail="Only .container files allowed")
    if not write_quadlet(name, body.content):
        raise HTTPException(status_code=500, detail="Failed to write file")
    # Reload systemd so it picks up the changed unit immediately
    reload = subprocess.run(
        ["systemctl", "--user", "daemon-reload"],
        capture_output=True,
        text=True,
    )
    return {
        "ok": True,
        "reload_ok": reload.returncode == 0,
        "reload_msg": (reload.stdout + reload.stderr).strip(),
    }
