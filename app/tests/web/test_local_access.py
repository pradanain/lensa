from fastapi.testclient import TestClient
from se2026.common import sha256
from se2026.web.main import create_app
from se2026.web.settings import Settings

from .synthetic import ROOT, make_database


def test_default_local_access_opens_data_without_creating_accounts(tmp_path):
    census = make_database(tmp_path / "census.sqlite")
    original_hash = sha256(census)
    app = create_app(Settings(root=ROOT, census_db=census, sls_reference=census.with_suffix(".sls.json"), app_db=tmp_path / "portal.sqlite"))
    with TestClient(app) as client:
        session = client.get("/api/v1/auth/session").json()
        assert session["auth_enabled"] is False
        assert session["setup_required"] is False
        assert session["user"]["id"] is None and session["user"]["can_detail"]
        assert "portal_session" not in client.cookies
        assert client.get("/api/v1/assignments/dtd").status_code == 200
        assert client.get("/api/v1/questionnaires/ub/UB-0001").status_code == 200
        body = {"source": "dtd", "q": "USAHA SINTETIS KEDUA"}
        assert client.post("/api/v1/directories/businesses/search", json=body).status_code == 403
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        result = client.post("/api/v1/directories/businesses/search", json=body)
        assert result.status_code == 200 and result.json()["total"] == 1
        assert (
            client.post(
                "/api/v1/directories/businesses/search",
                json=body,
                headers={"Origin": "https://invalid.example"},
            ).status_code
            == 403
        )
        for path in ("setup", "login", "logout", "users"):
            response = client.post(
                "/api/v1/auth/" + path,
                json={"username": "not-created", "password": "synthetic-password-2026", "role": "admin"},
            )
            assert response.status_code == 403
        assert client.get("/api/v1/auth/users").status_code == 403
    with app.state.app_db.connection() as con:
        assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    assert sha256(census) == original_hash


def test_login_can_be_reenabled_with_existing_accounts_and_sessions(portal):
    app, signed_in, _ = portal
    app.state.settings.auth_enabled = False
    local = TestClient(app)
    assert local.get("/api/v1/questionnaires/dtd/DTD-0001").status_code == 200
    assert local.get("/api/v1/auth/users").status_code == 403
    app.state.settings.auth_enabled = True
    session = local.get("/api/v1/auth/session").json()
    assert session["auth_enabled"] is True and session["setup_required"] is False
    assert local.get("/api/v1/assignments/dtd").status_code == 401
    assert signed_in.get("/api/v1/auth/users").status_code == 200
    with app.state.app_db.connection() as con:
        assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 3
