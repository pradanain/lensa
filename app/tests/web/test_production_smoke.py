"""Exercise the exact release smoke checker against the real synthetic ASGI app."""

import importlib.util
from email.message import Message
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from se2026.web.bootstrap import provision
from se2026.web.main import create_app
from se2026.web.settings import Settings

from .synthetic import ROOT, make_database


def test_release_smoke_validates_admin_login_with_non_admin_monitoring_default(tmp_path, monkeypatch, capsys):
    census = make_database(tmp_path / "synthetic.sqlite")
    settings = Settings(
        root=ROOT, census_db=census, app_db=tmp_path / "portal.sqlite",
        sls_reference=census.with_suffix(".sls.json"), auth_enabled=True,
        allowed_origins=["https://lensa.pradanain.id"],
    )
    provision(settings, "smoke-admin", "Synthetic-only-password-2026!")
    spec = importlib.util.spec_from_file_location(
        "release_smoke", ROOT / "app/scripts/maintenance/production_smoke.py"
    )
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)

    class Response:
        def __init__(self, response):
            self.status = response.status_code
            self.body = response.content
            self.headers = Message()
            for name, value in response.headers.multi_items():
                self.headers[name] = value

        def read(self):
            return self.body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        def urlopen(request, timeout=None):
            # Keep the smoke checker's cookie jar authoritative, as in the real
            # HTTP checker; TestClient must not add an authenticated session.
            client.cookies.clear()
            if isinstance(request, str):
                url, method, headers, body = request, "GET", {}, None
            else:
                url, method, headers, body = request.full_url, request.get_method(), dict(request.header_items()), request.data
            target = urlsplit(url)
            path = target.path + ("?" + target.query if target.query else "")
            return Response(client.request(method, path, headers=headers, content=body))

        monkeypatch.setattr(smoke.urllib.request, "urlopen", urlopen)
        smoke.verify("http://127.0.0.1")
    assert "Production image: ready" in capsys.readouterr().out
