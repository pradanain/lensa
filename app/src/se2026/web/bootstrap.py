"""Private, one-time admin provisioning. Never prints passwords or changes existing accounts."""

import argparse
import getpass
import re
import time
from pathlib import Path

from .database import AppDatabase
from .security import hasher, strong_password
from .settings import Settings


def provision(settings, username, password):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", username):
        raise ValueError("INVALID_ADMIN_USERNAME")
    strong_password(password)
    db = AppDatabase(settings)
    with db.connection() as con:
        con.execute("BEGIN IMMEDIATE")
        if con.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            raise ValueError("EXISTING_ACCOUNTS_PRESERVED")
        con.execute(
            "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
            (username, hasher.hash(password), "admin", int(time.time())),
        )
    db.audit(None, "PRIVATE_ADMIN_PROVISIONED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-file", type=Path)
    args = parser.parse_args()
    password = (
        args.password_file.read_text(encoding="utf-8").strip()
        if args.password_file
        else getpass.getpass("Admin password: ")
    )
    provision(Settings(app_db=args.database), args.username, password)
    print("Administrator provisioned; credentials were not logged.")


if __name__ == "__main__":
    main()
