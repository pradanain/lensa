import pytest
from fastapi.testclient import TestClient
from se2026.web.main import create_app
from se2026.web.bootstrap import provision
from se2026.web.settings import Settings

from .synthetic import ROOT, make_database

PASSWORD = "Synthetic-only-password-2026!"


def sign_in(client, username="admin", password=PASSWORD):
    session = client.get("/api/v1/auth/session").json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    assert client.post("/api/v1/auth/commitment", json={"version": response.json()["commitment_version"], "accepted": True}).status_code == 200
    return client


@pytest.fixture
def portal(tmp_path):
    census = make_database(tmp_path / "census.sqlite")
    settings = Settings(
        root=ROOT,
        census_db=census,
        sls_reference=census.with_suffix(".sls.json"),
        app_db=tmp_path / "portal.sqlite",
        aggregate_cache_seconds=0,
        auth_enabled=True,
    )
    provision(settings, "admin", PASSWORD)
    app = create_app(settings)
    # Established synthetic users have already completed first-login onboarding.
    with app.state.app_db.connection() as con:
        con.execute("UPDATE users SET must_change_password=0")
    with TestClient(app, raise_server_exceptions=False) as client:
        sign_in(client)
        for username, role in [("viewer", "aggregate_viewer"), ("analyst", "analyst_detail")]:
            assert (
                client.post(
                    "/api/v1/auth/users", json={"username": username, "password": PASSWORD, "role": role}
                ).status_code
                == 200
            )
        with app.state.app_db.connection() as con:
            con.execute("UPDATE users SET must_change_password=0")
        yield app, client, settings


@pytest.fixture
def viewer(portal):
    client = TestClient(portal[0], raise_server_exceptions=False)
    sign_in(client, "viewer")
    return client


@pytest.fixture
def analyst(portal):
    client = TestClient(portal[0], raise_server_exceptions=False)
    sign_in(client, "analyst")
    return client
