#!/usr/bin/env python3
"""Helper script to generate auth configuration for podmanpanel.toml"""

import secrets
import bcrypt
import sys


def main():
    print("PodmanPanel Auth Configuration Generator")
    print("=" * 50)
    print()

    username = input("Enter username [admin]: ").strip() or "admin"
    password = input("Enter password: ").strip()

    if not password:
        print("Error: Password cannot be empty")
        sys.exit(1)

    # Generate bcrypt hash
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Generate secret key
    secret_key = secrets.token_hex(32)

    print()
    print("Add this to your podmanpanel.toml:")
    print()
    print("[auth]")
    print(f'username = "{username}"')
    print(f'password_hash = "{password_hash}"')
    print(f'secret_key = "{secret_key}"')
    print()


if __name__ == "__main__":
    main()
