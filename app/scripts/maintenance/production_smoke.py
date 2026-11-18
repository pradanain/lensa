"""CI-only synthetic dataset/production image smoke checks; never reads real workspace data."""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "app/src"), str(ROOT / "app/tests/web")]


def prepare(folder):
    from se2026.web.bootstrap import provision
    from se2026.web.settings import Settings
    from synthetic import make_database

    folder.mkdir(parents=True, exist_ok=True)
    census = make_database(folder / "census.sqlite")
    state = folder / "state"
    state.mkdir()
    provision(
        Settings(root=ROOT, census_db=census, app_db=state / "portal.sqlite"),
        "smoke-admin",
        "Synthetic-only-password-2026!",
    )
    if os.name != "nt":
        subprocess.run(["sudo", "chown", "-R", "10001:10001", str(state)], check=True)


def verify(base):
    for _ in range(120):
        try:
            if json.load(urllib.request.urlopen(base + "/api/ready", timeout=3))["status"] == "ready":
                break
        except (OSError, urllib.error.HTTPError):
            time.sleep(2)
    else:
        raise RuntimeError("IMAGE_NOT_READY")
    from http.cookies import SimpleCookie

    cookies = SimpleCookie()
    def call(path, payload=None):
        headers = {"Cookie": "; ".join(key + "=" + item.value for key,item in cookies.items())}
        if payload is not None:
            headers.update({"Content-Type": "application/json", "Origin": "https://lensa.pradanain.id",
                            "X-CSRF-Token": cookies["portal_csrf"].value})
        request = urllib.request.Request(base + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            for value in response.headers.get_all("Set-Cookie", []):
                cookies.load(value)
            return response.status, json.load(response)

    status, session = call("/api/v1/auth/session")
    assert status == 200 and session["auth_enabled"] is True and session["setup_required"] is False
    assert session["user"] is None
    assert call("/api/v1/analytics/business-summary")[0] == 401
    status, logged_in = call("/api/v1/auth/login", {"username": "smoke-admin", "password": "Synthetic-only-password-2026!"})
    assert status == 200 and logged_in["commitment_required"] is True
    assert call("/api/v1/analytics/business-summary")[0] == 403
    assert logged_in["password_change_required"] is True
    assert call("/api/v1/auth/change-password", {"current_password": "Synthetic-only-password-2026!", "new_password": "Synthetic-New-password-2026!", "confirm_password": "Synthetic-New-password-2026!"})[0] == 200
    assert call("/api/v1/auth/commitment", {"version": logged_in["commitment_version"], "accepted": True})[0] == 200
    for path in ("/api/v1/analytics/business-summary", "/api/v1/kbli/tree"):
        assert call(path)[0] == 200
    status, evidence = call("/api/v1/activity")
    assert status == 200 and evidence["summary"]["logins"] == 1
    status, integrity = call("/api/v1/activity/integrity")
    assert status == 200 and integrity["valid"] and integrity["checked"] > 0
    assert call("/api/v1/auth/logout", {})[0] == 200
    assert call("/api/v1/analytics/business-summary")[0] == 401
    html = urllib.request.urlopen(base + "/usaha").read().decode()
    import re

    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert assets
    for asset in assets:
        with urllib.request.urlopen(base + asset) as response:
            assert response.status == 200
    print("Production image: ready, frontend assets available, login and commitment enforced.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", type=Path)
    parser.add_argument("--verify")
    args = parser.parse_args()
    prepare(args.prepare.resolve()) if args.prepare else verify(args.verify)
