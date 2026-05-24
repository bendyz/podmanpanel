from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.podman import get_containers, container_action, update_image

router = APIRouter(prefix="/api/containers", tags=["containers"])


class ActionModel(BaseModel):
    action: str


@router.get("")
def list_containers():
    return get_containers()


@router.post("/{container_id}/action")
def do_action(container_id: str, body: ActionModel):
    valid_actions = ["start", "stop", "restart", "rm", "pause", "unpause"]
    if body.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Use: {valid_actions}")
    success = container_action(container_id, body.action)
    if not success:
        raise HTTPException(status_code=500, detail="Action failed")
    return {"ok": True}


@router.post("/{container_id}/update")
def do_update(container_id: str):
    ok, msg = update_image(container_id)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"ok": True, "message": msg}