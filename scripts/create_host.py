"""Create a host account. Run from the project root:

    py -m scripts.create_host
"""
from getpass import getpass

from app.db import transaction
from app.repositories import host_repository
from app.security import hash_password

username = input("Host username: ").strip()
display_name = input("Display name: ").strip()
password = getpass("Password: ")

if not username or not display_name or len(password) < 8:
    raise SystemExit("Username and name are required, and the password needs 8+ characters.")

try:
    with transaction() as cur:
        host_id = host_repository.create(cur, username, hash_password(password), display_name)
    print(f"Host created with id {host_id}")
except Exception as e:
    raise SystemExit(f"Could not create host: {e}")
