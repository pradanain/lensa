"""Local browser-test server with synthetic data only; never seeds real accounts."""

# ruff: noqa: E402
import argparse
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app/src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from se2026.web.main import create_app
from se2026.web.security import hasher
from se2026.web.settings import Settings
from synthetic import (
    make_database,
    prepare_turnover_cases,
    prepare_questionnaire_presentation_cases,
    prepare_questionnaire_scope_cases,
)


def main():
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--empty-users", action="store_true")
    parser.add_argument("--no-login", action="store_true")
    parser.add_argument("--business-focus", action="store_true")
    parser.add_argument("--questionnaire-scopes", action="store_true")
    parser.add_argument("--turnover", action="store_true")
    args = parser.parse_args()
    temporary = Path(tempfile.mkdtemp(prefix="portal-e2e-", dir=ROOT / ".cache"))
    census = make_database(temporary / "synthetic.sqlite")
    if args.turnover:
        with sqlite3.connect(census) as con:
            prepare_turnover_cases(con)
    if args.questionnaire_scopes:
        with sqlite3.connect(census) as con:
            prepare_questionnaire_scope_cases(con)
            prepare_questionnaire_presentation_cases(con)
    settings = Settings(
        root=ROOT,
        census_db=census,
        sls_reference=census.with_suffix(".sls.json"),
        app_db=temporary / "portal.sqlite",
        allowed_origins=[f"http://127.0.0.1:{args.port}"],
        auth_enabled=not args.no_login,
        business_focus_enabled=args.business_focus,
    )
    app = create_app(settings)
    if not args.empty_users and not args.no_login:
        with app.state.app_db.connection() as con:
            for username, role in [
                ("admin", "admin"),
                ("analyst", "analyst_detail"),
                ("viewer", "aggregate_viewer"),
            ]:
                con.execute(
                    "INSERT INTO users(username,password_hash,role,created_at,must_change_password) VALUES(?,?,?,?,0)",
                    (username, hasher.hash("Synthetic-only-password-2026!"), role, int(time.time())),
                )
    uvicorn.run(
        app, host="127.0.0.1", port=args.port, access_log=False, proxy_headers=False, log_level="warning"
    )


if __name__ == "__main__":
    main()
