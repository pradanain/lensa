"""Privately create one shared Matcher account without changing existing users."""

import argparse
import getpass
import re
import time
from pathlib import Path

from .database import AppDatabase
from .security import hasher, strong_password
from .settings import Settings


def provision_matcher(settings, username, password):
    if not re.fullmatch(r"[A-Za-z0-9_.@+-]{3,128}", username):
        raise ValueError("INVALID_USERNAME")
    strong_password(password)
    db = AppDatabase(settings)
    with db.connection() as con:
        con.execute("BEGIN IMMEDIATE")
        if not con.execute("SELECT 1 FROM users WHERE role='admin' AND active=1").fetchone():
            raise ValueError("EXISTING_ADMIN_REQUIRED")
        if con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            raise ValueError("EXISTING_ACCOUNT_PRESERVED")
        con.execute(
            "INSERT INTO users(username,password_hash,role,role_override,created_at,must_change_password) "
            "VALUES(?,?,'analyst_detail','matcher',?,0)",
            (username, hasher.hash(password), int(time.time())),
        )
        con.execute(
            "INSERT INTO audit(occurred_at,user_id,action,outcome) VALUES(?,NULL,'PRIVATE_MATCHER_PROVISIONED','OK')",
            (int(time.time()),),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--username', default='matcher')
    args = parser.parse_args()
    password = getpass.getpass('Kata sandi bersama Matcher: ')
    if password != getpass.getpass('Ulangi kata sandi: '):
        parser.error('PASSWORD_CONFIRMATION_MISMATCH')
    provision_matcher(Settings(app_db=args.database), args.username, password)
    print('Akun Matcher dibuat. Akun existing dipertahankan; kata sandi tidak dicatat.')


if __name__ == '__main__':
    main()
