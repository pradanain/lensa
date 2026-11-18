import time

import pytest
from fastapi.testclient import TestClient
from se2026.common import sha256
from se2026.web import security
from se2026.web.database import AppDatabase, token_hash

from .conftest import PASSWORD


def pending_login(app, username='admin'):
    client = TestClient(app, raise_server_exceptions=False)
    client.headers['X-CSRF-Token'] = client.get('/api/v1/auth/session').json()['csrf_token']
    response = client.post('/api/v1/auth/login', json={'username': username, 'password': PASSWORD})
    assert response.status_code == 200 and response.json()['commitment_required']
    client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    return client


def accept(client, version=None):
    return client.post('/api/v1/auth/commitment', json={
        'version': version or client.get('/api/v1/auth/session').json()['commitment_version'],
        'accepted': True,
    })


@pytest.mark.parametrize('method,path,payload', [
    ('get', '/api/v1/analytics/business-summary', None),
    ('post', '/api/v1/analytics/query', {'metric_id': 'keluarga.count'}),
    ('get', '/api/v1/geography?source=dtd&level=kecamatan', None),
    ('get', '/api/v1/kbli/tree', None),
    ('get', '/api/v1/auth/users', None),
    ('get', '/api/v1/questionnaires/dtd/DTD-0001', None),
    ('get', '/api/v1/questionnaires/ub/UB-0001', None),
    ('post', '/api/v1/directories/members/search', {}),
    ('post', '/api/v1/directories/businesses/export', {}),
    ('post', '/api/v1/kbli/export', {}),
])
def test_login_alone_cannot_open_data_or_exports(portal, method, path, payload):
    app, _, _ = portal
    client = pending_login(app)
    response = getattr(client, method)(path, **({'json': payload} if payload is not None else {}))
    assert response.status_code == 403
    assert response.json()['detail'] == 'COMMITMENT_REQUIRED'
    assert client.get('/api/v1/auth/session').json()['commitment_required']


def test_acceptance_requires_csrf_version_and_explicit_decision(portal):
    client = pending_login(portal[0])
    assert accept(client, 'old-version').status_code == 409
    version = client.get('/api/v1/auth/session').json()['commitment_version']
    assert client.post('/api/v1/auth/commitment', json={'version': version, 'accepted': False}).status_code == 422
    token = client.headers.pop('X-CSRF-Token')
    assert accept(client).status_code == 403
    client.headers['X-CSRF-Token'] = token
    assert client.post('/api/v1/auth/commitment', json={'version': version, 'accepted': True}, headers={'Origin': 'https://invalid.example'}).status_code == 403
    assert client.get('/api/v1/analytics/business-summary').status_code == 403
    assert accept(client).status_code == 200
    assert not client.get('/api/v1/auth/session').json()['commitment_required']
    assert client.get('/api/v1/analytics/business-summary').status_code == 200


def test_acceptance_is_per_session_version_and_audited_once(portal, monkeypatch):
    app, _, settings = portal
    before_hash = sha256(settings.census_db)
    client = pending_login(app)
    key = token_hash(client.cookies['portal_session'])
    with app.state.app_db.connection() as con:
        users_before = [tuple(row) for row in con.execute('SELECT * FROM users ORDER BY id')]
        before = con.execute("SELECT COUNT(*) FROM audit WHERE action LIKE 'COMMITMENT_ACCEPTED:%'").fetchone()[0]
    assert accept(client).status_code == 200
    assert accept(client).status_code == 200
    with app.state.app_db.connection() as con:
        row = con.execute('SELECT version,accepted_at FROM session_commitments WHERE token_hash=?', (key,)).fetchone()
        assert row['version'] == security.COMMITMENT_VERSION and row['accepted_at'] <= int(time.time())
        assert con.execute("SELECT COUNT(*) FROM audit WHERE action LIKE 'COMMITMENT_ACCEPTED:%'").fetchone()[0] == before + 1
    another = pending_login(app)
    assert another.get('/api/v1/analytics/business-summary').status_code == 403
    assert client.get('/api/v1/analytics/business-summary').status_code == 200
    monkeypatch.setattr(security, 'COMMITMENT_VERSION', 'privacy_commitment_v2_test')
    assert client.get('/api/v1/analytics/business-summary').status_code == 403
    assert client.get('/api/v1/auth/session').json()['commitment_required']
    assert accept(client).status_code == 200
    assert client.get('/api/v1/analytics/business-summary').status_code == 200
    with app.state.app_db.connection() as con:
        assert [tuple(row) for row in con.execute('SELECT * FROM users ORDER BY id')] == users_before
        assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
    assert sha256(settings.census_db) == before_hash


@pytest.mark.parametrize('accepted', [False, True])
def test_logout_is_available_before_and_after_consent_and_removes_session(portal, accepted):
    app, _, _ = portal
    client = pending_login(app)
    token = client.cookies['portal_session']
    if accepted:
        assert accept(client).status_code == 200
    assert client.post('/api/v1/auth/logout', json={}).status_code == 200
    with app.state.app_db.connection() as con:
        assert con.execute('SELECT 1 FROM sessions WHERE token_hash=?', (token_hash(token),)).fetchone() is None
        assert con.execute('SELECT 1 FROM session_commitments WHERE token_hash=?', (token_hash(token),)).fetchone() is None
    client.cookies.set('portal_session', token)
    assert client.get('/api/v1/analytics/business-summary').status_code == 401


def test_expired_or_revoked_session_cannot_accept(portal):
    app, _, _ = portal
    client = pending_login(app)
    with app.state.app_db.connection() as con:
        con.execute('UPDATE sessions SET expires_at=0 WHERE token_hash=?', (token_hash(client.cookies['portal_session']),))
    assert accept(client, security.COMMITMENT_VERSION).status_code == 401
    client = pending_login(app)
    with app.state.app_db.connection() as con:
        con.execute("UPDATE users SET active=0 WHERE username='admin'")
    assert accept(client, security.COMMITMENT_VERSION).status_code == 401


def test_legacy_app_database_preserves_accounts_and_requires_new_consent(portal):
    app, client, settings = portal
    with app.state.app_db.connection() as con:
        users_before = [tuple(row) for row in con.execute('SELECT * FROM users ORDER BY id')]
        con.execute('DROP TABLE session_commitments')
    AppDatabase(settings)
    assert client.get('/api/v1/auth/session').json()['commitment_required']
    assert client.get('/api/v1/analytics/business-summary').status_code == 403
    with app.state.app_db.connection() as con:
        assert [tuple(row) for row in con.execute('SELECT * FROM users ORDER BY id')] == users_before


def test_email_username_uses_the_same_login_and_consent_guard(portal):
    app, admin, _ = portal
    response = admin.post('/api/v1/auth/users', json={
        'username': 'mail.admin@example.test', 'password': PASSWORD, 'role': 'admin',
    })
    assert response.status_code == 200
    client = pending_login(app, 'mail.admin@example.test')
    assert client.get('/api/v1/auth/session').json()['password_change_required']
    changed = client.post('/api/v1/auth/change-password', json={'current_password': PASSWORD, 'new_password': 'Synthetic-New-password-2026!', 'confirm_password': 'Synthetic-New-password-2026!'})
    assert changed.status_code == 200
    client.headers['X-CSRF-Token'] = changed.json()['csrf_token']
    assert client.get('/api/v1/analytics/business-summary').status_code == 403
    assert accept(client).status_code == 200
    assert client.get('/api/v1/analytics/business-summary').status_code == 200
