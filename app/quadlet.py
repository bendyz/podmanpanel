import os
from app.config import QUADLET_DIR


def get_quadlet_files() -> list[str]:
    if not os.path.exists(QUADLET_DIR):
        return []
    return [f for f in os.listdir(QUADLET_DIR) if f.endswith(".container")]


def read_quadlet(name: str) -> str | None:
    path = os.path.join(QUADLET_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read()


def write_quadlet(name: str, content: str) -> bool:
    path = os.path.join(QUADLET_DIR, name)
    try:
        with open(path, "w") as f:
            f.write(content)
        return True
    except Exception:
        return False