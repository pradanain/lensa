import pytest
from fastapi.testclient import TestClient
from se2026.web.database import AppDatabase, token_hash
from se2026.common import sha256

from .conftest import PASSWORD

NEW_PASSWORD = 'Fresh1!A'  # Exactly eight characters; synthetic credentials only.


def new_account(portal):
    app, admin, _ = portal
    assert admin.post('/api/v1/auth/users', json={
        'username': 'first.user@example.test', 'password': PASSWORD, 'role': 'viewer',
    }).status_code == 200
    client = TestClient(app)
    client.headers['X-CSRF-Token'] = client.get('/api/v1/auth/session').json()['csrf_token']
    result = client.post('/api/v1/auth/login', json={'username': 'first.user@example.test', 'password': PASSWORD})
    assert result.status_code == 200 and result.json()['password_change_required']
    client.headers['X-CSRF-Token'] = result.json()['csrf_token']
    return client


def change(client, current=PASSWORD, new=NEW_PASSWORD, confirm=None):
    return client.post('/api/v1/auth/change-password', json={
        'current_password': current, 'new_password': new, 'confirm_password': new if confirm is None else confirm,
    })


@pytest.mark.parametrize('method,path,payload', [
    ('get', '/api/v1/analytics/summary', None),
    ('get', '/api/v1/questionnaires/dtd/DTD-0001', None),
    ('post', '/api/v1/directories/businesses/export', {}),
    ('post', '/api/v1/kbli/export', {}),
    ('get', '/api/v1/auth/users', None),
    ('post', '/api/v1/auth/commitment', {'version': 'privacy_commitment_v1', 'accepted': True}),
])
def test_first_login_cannot_skip_password_change(portal, method, path, payload):
    client = new_account(portal)
    response = getattr(client, method)(path, **({'json': payload} if payload is not None else {}))
    assert response.status_code == 403
    assert response.json()['detail'] == 'PASSWORD_CHANGE_REQUIRED'
    assert client.get('/api/v1/auth/session').json()['password_change_required']


@pytest.mark.parametrize('password', ['Aa1!aaa', 'alllower1!', 'ALLUPPER!!', 'NoSymbol123', 'Spaces 1A', 'Abcdef1é'])
def test_password_policy_rejects_missing_requirements(portal, password):
    client = new_account(portal)
    result = change(client, new=password)
    assert result.status_code == 422 and result.json()['detail'] == 'PASSWORD_POLICY_REQUIRED'
    assert client.get('/api/v1/auth/session').json()['password_change_required']


def test_password_must_differ_confirm_and_verify_current_password(portal):
    client = new_account(portal)
    assert change(client, new=PASSWORD).json()['detail'] == 'PASSWORD_MUST_DIFFER'
    assert change(client, confirm='Different1!').json()['detail'] == 'PASSWORD_CONFIRMATION_MISMATCH'
    assert change(client, current='Wrong-current1!').json()['detail'] == 'CURRENT_PASSWORD_INVALID'
    csrf = client.headers.pop('X-CSRF-Token')
    assert change(client).status_code == 403
    client.headers['X-CSRF-Token'] = csrf
    assert client.get('/api/v1/auth/session').json()['password_change_required']


def test_change_revokes_old_sessions_and_requires_pact_under_new_session(portal):
    app, _, _ = portal
    client = new_account(portal)
    old_token = client.cookies['portal_session']
    another = TestClient(app)
    another.cookies.set('portal_session', old_token)
    result = change(client)
    assert result.status_code == 200
    assert client.cookies['portal_session'] != old_token
    client.headers['X-CSRF-Token'] = result.json()['csrf_token']
    assert not client.get('/api/v1/auth/session').json()['password_change_required']
    assert client.get('/api/v1/analytics/summary').json()['detail'] == 'COMMITMENT_REQUIRED'
    assert another.get('/api/v1/analytics/summary').status_code == 401
    version = client.get('/api/v1/auth/session').json()['commitment_version']
    assert client.post('/api/v1/auth/commitment', json={'version': version, 'accepted': True}).status_code == 200
    assert client.get('/api/v1/analytics/summary').status_code == 200
    fresh = TestClient(app)
    fresh.headers['X-CSRF-Token'] = fresh.get('/api/v1/auth/session').json()['csrf_token']
    assert fresh.post('/api/v1/auth/login', json={'username': 'first.user@example.test', 'password': PASSWORD}).status_code == 401
    logged_in = fresh.post('/api/v1/auth/login', json={'username': 'first.user@example.test', 'password': NEW_PASSWORD})
    assert logged_in.status_code == 200 and not logged_in.json()['password_change_required']
    with app.state.app_db.connection() as con:
        assert con.execute('SELECT 1 FROM sessions WHERE token_hash=?', (token_hash(old_token),)).fetchone() is None
        assert con.execute("SELECT COUNT(*) FROM audit WHERE action='PASSWORD_CHANGED'").fetchone()[0] == 1
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []


def test_only_admin_can_create_accounts_and_public_setup_stays_closed(portal, viewer, analyst):
    app, admin, _ = portal
    app.state.settings.allow_web_setup = True  # A legacy switch cannot reopen signup.
    for client in [TestClient(app), viewer, analyst]:
        response = client.post('/api/v1/auth/users', json={'username': 'not-created', 'password': PASSWORD, 'role': 'admin'})
        assert response.status_code in (401, 403)
    session = admin.get('/api/v1/auth/session').json()
    response = admin.post('/api/v1/auth/setup', json={'username': 'not-created', 'password': PASSWORD}, headers={'X-CSRF-Token': session['csrf_token']})
    assert response.status_code == 403
    assert not session['setup_required']
    assert admin.post('/api/v1/auth/users', json={'username': 'not-created', 'password': PASSWORD, 'role': 'admin', 'must_change_password': False}).status_code == 422


def test_password_change_can_be_cancelled_only_by_logging_out(portal):
    client = new_account(portal)
    assert client.post('/api/v1/auth/logout', json={}).status_code == 200
    assert client.get('/api/v1/analytics/summary').status_code == 401


def test_legacy_accounts_keep_hashes_but_must_change_once_after_upgrade(portal):
    app, client, settings = portal
    before_census = sha256(settings.census_db)
    with app.state.app_db.connection() as con:
        accounts = [tuple(row) for row in con.execute('SELECT id,username,password_hash,role,active FROM users ORDER BY id')]
        con.execute('ALTER TABLE users DROP COLUMN must_change_password')
    AppDatabase(settings)
    with app.state.app_db.connection() as con:
        assert [tuple(row) for row in con.execute('SELECT id,username,password_hash,role,active FROM users ORDER BY id')] == accounts
        assert all(row[0] == 1 for row in con.execute('SELECT must_change_password FROM users'))
        assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
    assert client.get('/api/v1/analytics/summary').json()['detail'] == 'PASSWORD_CHANGE_REQUIRED'
    assert sha256(settings.census_db) == before_census


@pytest.mark.parametrize('temporary', ['a', '123', 'bebas', 'huruf kecil', 'A' * 256])
def test_temporary_password_has_no_complexity_requirement(portal, temporary):
    app, admin, _ = portal
    result = admin.post('/api/v1/auth/users', json={
        'username': 'short.temporary', 'password': temporary, 'role': 'viewer',
    })
    assert result.status_code == 200
    client = TestClient(app)
    client.headers['X-CSRF-Token'] = client.get('/api/v1/auth/session').json()['csrf_token']
    result = client.post('/api/v1/auth/login', json={'username': 'short.temporary', 'password': temporary})
    assert result.status_code == 200
    assert result.json()['user']['role'] == 'viewer'
    assert result.json()['password_change_required']
    assert client.get('/api/v1/questionnaires/dtd/DTD-0001').json()['detail'] == 'PASSWORD_CHANGE_REQUIRED'


@pytest.mark.parametrize('temporary', ['', 'A' * 257])
def test_temporary_password_still_requires_nonempty_bounded_input(portal, temporary):
    assert portal[1].post('/api/v1/auth/users', json={
        'username': 'invalid.temporary', 'password': temporary, 'role': 'viewer',
    }).status_code == 422


@pytest.mark.parametrize('legacy', ['analyst_detail', 'aggregate_viewer'])
def test_legacy_accounts_are_viewers_without_rewriting_account_rows(portal, legacy):
    from .conftest import sign_in
    app, admin, _ = portal
    with app.state.app_db.connection() as con:
        con.execute("UPDATE users SET role=? WHERE username='viewer'", (legacy,))
    client = sign_in(TestClient(app), 'viewer')
    user = client.get('/api/v1/auth/session').json()['user']
    assert user['role'] == 'viewer' and user['can_detail'] and not user['can_sensitive']
    assert client.post('/api/v1/directories/businesses/export', json={}).status_code == 200
    assert client.get('/api/v1/auth/users').status_code == 403
    users = admin.get('/api/v1/auth/users').json()['rows']
    assert all(row['role'] in {'admin', 'viewer'} for row in users)
    with app.state.app_db.connection() as con:
        assert con.execute("SELECT role FROM users WHERE username='viewer'").fetchone()[0] == legacy


@pytest.mark.parametrize('role', ['analyst_detail', 'aggregate_viewer', 'unknown'])
def test_only_two_roles_can_be_assigned(portal, role):
    admin = portal[1]
    assert admin.post('/api/v1/auth/users', json={
        'username': 'unsupported.role', 'password': 'a', 'role': role,
    }).status_code == 422
