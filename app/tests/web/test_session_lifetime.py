import time
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from se2026.common import sha256
from se2026.web import security
from se2026.web.database import token_hash
from se2026.web.settings import Settings

from .conftest import PASSWORD


def test_session_default_and_maximum_are_twelve_hours(monkeypatch):
    monkeypatch.delenv('SE2026_SESSION_HOURS', raising=False)
    assert Settings(_env_file=None).session_hours == 12
    with pytest.raises(ValidationError):
        Settings(_env_file=None, session_hours=13)


def test_absolute_expiry_rejects_replay_and_removes_session_and_pact(portal, monkeypatch):
    app, client, settings = portal
    settings.session_hours = 12
    before = sha256(settings.census_db)
    now = int(time.time())
    clock = [now]
    monkeypatch.setattr(security, 'time', SimpleNamespace(time=lambda: clock[0]))
    response = client.post('/api/v1/auth/login', json={'username': 'admin', 'password': PASSWORD})
    assert response.status_code == 200
    assert 'Max-Age=43200' in response.headers['set-cookie']
    token = client.cookies['portal_session']
    key = token_hash(token)
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    assert client.post('/api/v1/auth/commitment', json={
        'version': security.COMMITMENT_VERSION, 'accepted': True,
    }).status_code == 200

    clock[0] = now + 43200 - 1
    session = client.get('/api/v1/auth/session').json()
    assert session['user'] and session['expires_at'] == now + 43200
    assert session['server_time'] == clock[0]
    assert client.get('/api/v1/analytics/business-summary').status_code == 200
    with app.state.app_db.connection() as con:
        assert con.execute('SELECT expires_at FROM sessions WHERE token_hash=?', (key,)).fetchone()[0] == now + 43200

    clock[0] += 1
    assert client.get('/api/v1/analytics/business-summary').status_code == 401
    with app.state.app_db.connection() as con:
        assert con.execute('SELECT 1 FROM sessions WHERE token_hash=?', (key,)).fetchone() is None
        assert con.execute('SELECT 1 FROM session_commitments WHERE token_hash=?', (key,)).fetchone() is None
    session = client.get('/api/v1/auth/session')
    assert session.json()['user'] is None and session.json()['expires_at'] is None
    assert 'Max-Age=0' in session.headers['set-cookie']
    assert sha256(settings.census_db) == before


def test_logout_removes_cookies_and_old_token_cannot_open_data(portal):
    app, client, _ = portal
    token = client.cookies['portal_session']
    response = client.post('/api/v1/auth/logout', json={})
    assert response.status_code == 200
    assert 'portal_session' not in client.cookies
    assert 'portal_csrf' not in client.cookies
    with app.state.app_db.connection() as con:
        assert con.execute('SELECT 1 FROM sessions WHERE token_hash=?', (token_hash(token),)).fetchone() is None
    response = client.get('/api/v1/analytics/business-summary', headers={'Cookie': 'portal_session=' + token})
    assert response.status_code == 401
    assert response.headers['cache-control'] == 'no-store, private'


def test_password_rotation_preserves_original_deadline(portal, monkeypatch):
    app, client, _ = portal
    original = client.get('/api/v1/auth/session').json()['expires_at']
    with app.state.app_db.connection() as con:
        before = con.execute('SELECT expires_at FROM sessions WHERE token_hash=?',
                             (token_hash(client.cookies['portal_session']),)).fetchone()[0]
    now = int(time.time()) + 3600
    monkeypatch.setattr(security, 'time', SimpleNamespace(time=lambda: now))
    response = client.post('/api/v1/auth/change-password', json={
        'current_password': PASSWORD, 'new_password': 'NewSynthetic1!', 'confirm_password': 'NewSynthetic1!',
    })
    assert response.status_code == 200
    assert f'Max-Age={original - now}' in response.headers['set-cookie']
    with app.state.app_db.connection() as con:
        assert con.execute('SELECT expires_at FROM sessions WHERE token_hash=?',
                           (token_hash(client.cookies['portal_session']),)).fetchone()[0] == before
