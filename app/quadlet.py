import os
from pathlib import Path
from app.config import QUADLET_DIR


def _scan_dir(d: Path) -> list[dict]:
    if not d.exists():
        return []
    return [
        {
            "name": f.name,
            # quadlet `foo.container` maps to systemd unit `foo.service`
            "service": f.stem + ".service",
            "path": str(f),
        }
        for f in sorted(d.iterdir())
        if f.is_file() and f.suffix == ".container"
    ]


def get_quadlet_files() -> list[dict]:
    base = Path(QUADLET_DIR)
    files = _scan_dir(base)
    # Also check the `user/` subdirectory (some distros place units there)
    files += _scan_dir(base / "user")
    return files


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
