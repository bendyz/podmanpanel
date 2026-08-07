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


def read_container_keys(path: str) -> dict[str, list[str]]:
    """Return all ``key=value`` pairs of the [Container] section.

    Keys are lowercased; each maps to the list of values (quadlet allows the
    same key more than once, e.g. several ``PublishPort=`` lines).
    """
    keys: dict[str, list[str]] = {}
    try:
        in_container = False
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line[0] in "#;":
                    continue
                if line.startswith("["):
                    in_container = line.lower() == "[container]"
                elif in_container and "=" in line:
                    k, v = line.split("=", 1)
                    keys.setdefault(k.strip().lower(), []).append(v.strip())
    except Exception:
        pass
    return keys


def get_container_name_for_quadlet(path: str, filename: str) -> str:
    """Return the container name this quadlet creates.

    Parses ``ContainerName=`` from the [Container] section.
    Falls back to ``systemd-{stem}`` (podman quadlet default).
    """
    for name in read_container_keys(path).get("containername", []):
        if name:
            return name
    return f"systemd-{Path(filename).stem}"


def parse_publish_port(value: str) -> dict | None:
    """Parse a ``PublishPort=`` value into its parts.

    Accepted forms (same as podman): ``containerPort``, ``hostPort:containerPort``,
    ``ip:hostPort:containerPort``, ``[ipv6]:hostPort:containerPort``, each
    optionally suffixed with ``/tcp`` or ``/udp`` and using ``a-b`` ranges.
    """
    v = value.strip()
    if not v:
        return None

    proto = "tcp"
    if "/" in v.rsplit(":", 1)[-1]:
        v, _, proto = v.rpartition("/")

    host_ip = ""
    if v.startswith("["):  # bracketed IPv6 host address
        end = v.find("]")
        if end == -1:
            return None
        host_ip, rest = v[1:end], v[end + 1:].lstrip(":")
    else:
        parts = v.split(":")
        if len(parts) == 3:
            host_ip, rest = parts[0], ":".join(parts[1:])
        else:
            rest = v

    if ":" in rest:
        host_port, container_port = rest.split(":", 1)
    else:
        # Only a container port — podman picks a random host port.
        host_port, container_port = "", rest

    if not container_port and not host_port:
        return None
    return {
        "host_ip": host_ip,
        "host_port": host_port,
        "container_port": container_port,
        "proto": proto or "tcp",
    }


def get_published_ports(path: str) -> list[dict]:
    """Return the parsed ``PublishPort=`` entries of a quadlet file.

    A ``#`` comment right after a ``PublishPort=`` line (or trailing on the
    same line) becomes that port's ``label``, e.g.::

        PublishPort=8014:8014
        #Interfejs WWW
    """
    ports: list[dict] = []
    try:
        with open(path) as f:
            lines = f.readlines()
    except Exception:
        return ports

    in_container = False
    last_port: dict | None = None
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("["):
            in_container = line.lower() == "[container]"
            last_port = None
            continue
        if not in_container:
            continue
        if line[0] in "#;":
            if last_port is not None and "label" not in last_port:
                label = line[1:].strip()
                if label:
                    last_port["label"] = label
            else:
                last_port = None
            continue

        last_port = None
        if line.lower().startswith("publishport="):
            value = line.split("=", 1)[1]
            label = None
            if "#" in value:
                value, _, label = value.partition("#")
                label = label.strip() or None
            parsed = parse_publish_port(value.strip())
            if parsed:
                if label:
                    parsed["label"] = label
                ports.append(parsed)
                last_port = parsed
    return ports


def _find_path(name: str) -> Path | None:
    base = Path(QUADLET_DIR)
    for candidate in [base / name, base / "user" / name]:
        if candidate.exists():
            return candidate
    return None


def read_quadlet(name: str) -> str | None:
    path = _find_path(name)
    return path.read_text() if path else None


def create_quadlet(name: str, content: str) -> Path | None:
    """Create a new quadlet file. Returns the path on success, None if it already exists."""
    path = Path(QUADLET_DIR) / name
    if path.exists():
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path
    except Exception:
        return None


def write_quadlet(name: str, content: str) -> bool:
    path = _find_path(name) or Path(QUADLET_DIR) / name
    try:
        path.write_text(content)
        return True
    except Exception:
        return False
