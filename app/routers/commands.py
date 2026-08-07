import subprocess
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import CUSTOM_COMMANDS

router = APIRouter(prefix="/api/commands", tags=["commands"])


class CommandModel(BaseModel):
    label: str


@router.get("")
def list_commands():
    """Return the custom commands defined in podmanpanel.toml."""
    return {
        "commands": [{"label": k, "command": v} for k, v in CUSTOM_COMMANDS.items()]
    }


@router.post("")
def run_command(body: CommandModel):
    """Run one of the commands defined in podmanpanel.toml.

    Only configured labels can be run — arbitrary shell input is never accepted.
    """
    command = CUSTOM_COMMANDS.get(body.label)
    if command is None:
        raise HTTPException(status_code=404, detail="Unknown command")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
