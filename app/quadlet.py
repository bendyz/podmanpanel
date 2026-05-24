import os
from pathlib import Path
from app.config import QUADLET_DIR


def _scan_dir(d: Path) -> list[dict]:
    if not d.exists():
        return []
    return [
        {
            "name": f.name,
            # quadlet `foo.container` → systemd unit `foo.service`
            "service": f.stem + ".service",
            "path": str(f),
        }
        for f in sorted(d.iterdir())
        if f.is_file() and f.suffix == ".container"
    ]


def get_quadlet_files() -> list[dict]:
    base = Path(QUADLET_DIR)
    files = _scan_dir(base)
    files += _scan_dir(base / "user")
    return files


def get_container_name_for_quadlet(path: str, filename: str) -> str:
    """Return the container name this quadlet creates.

    Parses ``ContainerName=`` from the [Container] section.
    Falls back to ``systemd-{stem}`` (podman quadlet default).
    """
    stem = Path(filename).stem
    default = f"systemd-{stem}"
    try:
        in_container = False
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    in_container = line.lower() == "[container]"
                elif in_container and line.lower().startswith("containername="):
                    name = line.split("=", 1)[1].strip()
                    if name:
                        return name
    except Exception:
        pass
    return default


def _find_path(name: str) -> Path | None:
    base = Path(QUADLET_DIR)
    for candidate in [base / name, base / "user" / name]:
        if candidate.exists():
            return candidate
    return None


def read_quadlet(name: str) -> str | None:
    path = _find_path(name)
    return path.read_text() if path else None


def write_quadlet(name: str, content: str) -> bool:
    path = _find_path(name) or Path(QUADLET_DIR) / name
    try:
        path.write_text(content)
        return True
    except Exception:
        return False
