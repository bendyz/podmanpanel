#!/usr/bin/env python3
"""Helper script to generate auth configuration for podmanpanel.toml"""

import secrets
import bcrypt
import sys
import os
from pathlib import Path


def generate_auth_config(username: str, password: str) -> dict:
    """Generate auth config dict."""
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    secret_key = secrets.token_hex(32)
    return {
        "username": username,
        "password_hash": password_hash,
        "secret_key": secret_key,
    }


def write_auth_to_toml(config_path: Path, auth_config: dict):
    """Append or update [auth] section in TOML file."""
    if config_path.exists():
        content = config_path.read_text()
        # Check if [auth] section already exists
        if "[auth]" in content:
            print(f"Warning: [auth] section already exists in {config_path}")
            overwrite = input("Overwrite? [y/N]: ").strip().lower()
            if overwrite != "y":
                print("Aborted.")
                sys.exit(0)
            # Remove existing [auth] section
            lines = content.split("\n")
            new_lines = []
            skip = False
            for line in lines:
                if line.strip().startswith("[auth]"):
                    skip = True
                elif line.strip().startswith("[") and skip:
                    skip = False
                if not skip:
                    new_lines.append(line)
            content = "\n".join(new_lines).rstrip()
        content += "\n\n"
    else:
        content = ""

    # Append [auth] section
    content += "[auth]\n"
    content += f'username = "{auth_config["username"]}"\n'
    content += f'password_hash = "{auth_config["password_hash"]}"\n'
    content += f'secret_key = "{auth_config["secret_key"]}"\n'

    config_path.write_text(content)
    print(f"\n✓ Auth configuration written to {config_path}")


def main():
    print("PodmanPanel Auth Configuration Generator")
    print("=" * 50)
    print()

    # Determine config path
    config_path = Path(os.getenv("PODMANPANEL_CONFIG", "podmanpanel.toml"))

    username = input("Enter username [admin]: ").strip() or "admin"
    password = input("Enter password: ").strip()

    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)

    print("\nGenerating auth configuration...")
    auth_config = generate_auth_config(username, password)

    # Offer to write to file
    write_to_file = input(f"\nWrite to {config_path}? [Y/n]: ").strip().lower()
    if write_to_file in ("", "y", "yes"):
        write_auth_to_toml(config_path, auth_config)
        print("\nRestart podmanpanel for changes to take effect.")
    else:
        print("\nAdd this to your podmanpanel.toml:")
        print()
        print("[auth]")
        print(f'username = "{auth_config["username"]}"')
        print(f'password_hash = "{auth_config["password_hash"]}"')
        print(f'secret_key = "{auth_config["secret_key"]}"')
        print()


if __name__ == "__main__":
    main()
