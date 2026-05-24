import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import PODMAN_USER

router = APIRouter(prefix="/api/commands", tags=["commands"])


class CommandModel(BaseModel):
    command: str


@router.post("")
def run_command(body: CommandModel):
    try:
        result = subprocess.run(
            body.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))