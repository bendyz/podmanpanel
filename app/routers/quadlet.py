from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.quadlet import get_quadlet_files, read_quadlet, write_quadlet

router = APIRouter(prefix="/api/quadlet", tags=["quadlet"])


class QuadletEditModel(BaseModel):
    content: str


@router.get("")
def list_quadlet():
    return {"files": get_quadlet_files()}


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
    if write_quadlet(name, body.content):
        return {"ok": True}
    raise HTTPException(status_code=500, detail="Failed to write file")
