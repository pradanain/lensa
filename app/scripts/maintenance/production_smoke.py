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
    for path in ("/api/v1/analytics/business-summary", "/api/v1/kbli/tree"):
        try:
            urllib.request.urlopen(base + path)
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("UNAUTHENTICATED_DATA_ACCESS")
    html = urllib.request.urlopen(base + "/usaha").read().decode()
    import re

    assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', html)
    assert assets
    for asset in assets:
        with urllib.request.urlopen(base + asset) as response:
            assert response.status == 200
    print("Production image: ready, frontend assets available, anonymous data access denied.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", type=Path)
    parser.add_argument("--verify")
    args = parser.parse_args()
    prepare(args.prepare.resolve()) if args.prepare else verify(args.verify)
