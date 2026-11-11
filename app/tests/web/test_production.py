import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from se2026.web.bootstrap import provision
from se2026.web.main import create_app
from se2026.web.settings import Settings

from .synthetic import ROOT, make_database


def production_settings(tmp_path):
    census = make_database(tmp_path / "synthetic.sqlite")
    return Settings(
        root=ROOT,
        census_db=census,
        sls_reference=census.with_suffix(".sls.json"),
        app_db=tmp_path / "portal.sqlite",
        environment="production",
        auth_enabled=True,
        secure_cookies=True,
        allow_web_setup=False,
        allowed_hosts=["testserver"],
        allowed_origins=["https://testserver"],
    )


def test_production_refuses_unsafe_auth_configuration():
    with pytest.raises(ValidationError):
        Settings(environment="production")
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            auth_enabled=True,
            secure_cookies=True,
            allow_web_setup=False,
            allowed_origins=["http://testserver"],
        )


def test_production_requires_private_admin_before_startup(tmp_path):
    settings = production_settings(tmp_path)
    with pytest.raises(RuntimeError, match="PRODUCTION_ADMIN_NOT_PROVISIONED"):
        with TestClient(create_app(settings), base_url="https://testserver"):
            pass


def test_production_login_deferred_preserves_accounts_and_data(tmp_path):
    from se2026.common import sha256

    settings = production_settings(tmp_path)
    settings.auth_enabled = False
    # Validate the real environment configuration, not only a mutable setting.
    settings = Settings(**settings.model_dump())
    original_hash = sha256(settings.census_db)
    app = create_app(settings)
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/api/ready").status_code == 200
        session = client.get("/api/v1/auth/session").json()
        assert session["auth_enabled"] is False
        assert session["setup_required"] is False
        assert client.get("/api/v1/analytics/business-summary").status_code == 200
        assert client.get("/api/v1/questionnaires/ub/UB-0001").status_code == 200
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        assert client.post("/api/v1/directories/businesses/search", json={}).status_code == 200
        assert client.post("/api/v1/auth/setup", json={}).status_code == 403
        assert client.post("/api/v1/auth/login", json={}).status_code == 403
    assert sha256(settings.census_db) == original_hash
    with app.state.app_db.connection() as con:
        assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_private_admin_and_https_session_guard_production_data(tmp_path):
    settings = production_settings(tmp_path)
    provision(settings, "production-admin", "Synthetic-only-password-2026!")
    with pytest.raises(ValueError, match="EXISTING_ACCOUNTS_PRESERVED"):
        provision(settings, "replacement-admin", "Synthetic-only-password-2026!")
    with TestClient(create_app(settings), base_url="https://testserver") as client:
        assert client.get("/api/ready").json() == {"status": "ready"}
        assert client.get("/api/v1/analytics/business-summary").status_code == 401
        session = client.get("/api/v1/auth/session")
        assert "Secure" in session.headers["set-cookie"]
        client.headers["X-CSRF-Token"] = session.json()["csrf_token"]
        assert (
            client.post(
                "/api/v1/auth/setup",
                json={"username": "attacker", "password": "Synthetic-only-password-2026!"},
            ).status_code
            == 403
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "production-admin", "password": "Synthetic-only-password-2026!"},
            headers={"Origin": "https://testserver"},
        )
        assert login.status_code == 200
        assert "Secure" in login.headers["set-cookie"] and "HttpOnly" in login.headers["set-cookie"]
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        assert client.get("/api/v1/analytics/business-summary").status_code == 200
        assert (
            client.post(
                "/api/v1/directories/businesses/search",
                json={},
                headers={"Origin": "https://invalid.example"},
            ).status_code
            == 403
        )
    with sqlite3.connect(settings.app_db) as con:
        assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
