import hashlib

import pytest
from fastapi.testclient import TestClient

from se2026.web.database import AppDatabase
from se2026.web.matcher_account import provision_matcher

from .conftest import PASSWORD, sign_in


@pytest.fixture
def matcher(portal):
    app, admin, _ = portal
    assert admin.post('/api/v1/auth/users', json={
        'username': 'matcher', 'password': PASSWORD, 'role': 'matcher',
    }).status_code == 200
    with app.state.app_db.connection() as con:
        con.execute("UPDATE users SET must_change_password=0 WHERE username='matcher'")
    return sign_in(TestClient(app), 'matcher')


def test_matcher_has_viewer_directory_data_and_filters_only(portal, viewer, matcher):
    settings = portal[2]
    before = hashlib.sha256(settings.census_db.read_bytes()).hexdigest()
    session = matcher.get('/api/v1/auth/session').json()
    assert session['user']['role'] == 'matcher'
    assert not session['user']['can_detail']
    assert not session['user']['can_sensitive']
    for source in ['dtd', 'ub']:
        for query in [{}, {'q': 'SINTETIS'}, {'page': 2, 'page_size': 10},
                      {'kbli_prefix': '47'}, {'status': '1'}, {'kecamatan': '6502010'}]:
            body = {'source': source, **query}
            actual = matcher.post('/api/v1/directories/businesses/search', json=body)
            assert actual.status_code == 200
            assert actual.json() == viewer.post('/api/v1/directories/businesses/search', json=body).json()
        assert matcher.get('/api/v1/directory-statuses', params={'scope': 'businesses', 'source': source}).status_code == 200
    for level in ['kecamatan', 'desa', 'sls', 'subsls']:
        assert matcher.get('/api/v1/geography', params={'level': level}).status_code == 200
    assert matcher.get('/api/v1/kbli/catalog').status_code == 200
    assert hashlib.sha256(settings.census_db.read_bytes()).hexdigest() == before


@pytest.mark.parametrize('method,path,body', [
    ('GET', '/api/v1/questionnaires/dtd/DTD-0001?business=001', None),
    ('GET', '/api/v1/questionnaires/ub/UB-0001', None),
    ('GET', '/api/v1/assignments/dtd', None),
    ('POST', '/api/v1/directories/businesses/export', {}),
    ('POST', '/api/v1/directories/families/export', {}),
    ('POST', '/api/v1/directories/assignments/export', {}),
    ('POST', '/api/v1/directories/members/export', {}),
    ('POST', '/api/v1/directories/families/search', {}),
    ('POST', '/api/v1/directories/members/search', {}),
    ('POST', '/api/v1/directories/assignments/search', {}),
    ('GET', '/api/v1/directory-statuses?scope=families', None),
    ('GET', '/api/v1/directory-statuses', None),
    ('GET', '/api/v1/analytics/dashboard', None),
    ('GET', '/api/v1/analytics/business-summary', None),
    ('GET', '/api/v1/analytics/family-summary', None),
    ('GET', '/api/v1/analytics/metrics', None),
    ('POST', '/api/v1/analytics/query', {'metric_id': 'usaha.enumerated_count'}),
    ('GET', '/api/v1/kbli/tree', None),
    ('POST', '/api/v1/kbli/export', {}),
    ('GET', '/api/v1/references/summary', None),
    ('GET', '/api/v1/references/countries', None),
    ('GET', '/api/v1/data-quality/summary', None),
    ('GET', '/api/v1/auth/users', None),
    ('POST', '/api/v1/auth/users', {'username': 'forbidden', 'password': PASSWORD, 'role': 'admin'}),
    ('PATCH', '/api/v1/auth/users/1', {'role': 'matcher', 'active': False}),
    ('GET', '/api/v1/activity', None),
    ('GET', '/api/v1/activity/sessions', None),
    ('GET', '/api/v1/activity/integrity', None),
    ('POST', '/api/v1/activity/export', {}),
])
def test_matcher_cannot_bypass_ui_restrictions(matcher, method, path, body):
    response = matcher.request(method, path, json=body)
    assert response.status_code == 403
    assert response.json()['detail'] == 'MATCHER_DIRECTORY_ONLY'


def test_shared_account_keeps_sessions_independent_and_admin_can_revoke(portal, matcher):
    app, admin, _ = portal
    second = sign_in(TestClient(app), 'matcher')
    assert matcher.cookies['portal_session'] != second.cookies['portal_session']
    assert matcher.post('/api/v1/auth/logout').status_code == 200
    assert second.post('/api/v1/directories/businesses/search', json={}).status_code == 200
    user = next(u for u in admin.get('/api/v1/auth/users').json()['rows'] if u['username'] == 'matcher')
    assert user['role'] == 'matcher'
    assert admin.patch('/api/v1/auth/users/' + str(user['id']), json={'role': 'viewer', 'active': True}).status_code == 200
    assert second.post('/api/v1/directories/businesses/search', json={}).status_code == 401
    viewer = sign_in(TestClient(app), 'matcher')
    assert viewer.get('/api/v1/questionnaires/dtd/DTD-0001').status_code == 200
    assert admin.patch('/api/v1/auth/users/' + str(user['id']), json={'role': 'matcher', 'active': True}).status_code == 200
    restricted = sign_in(TestClient(app), 'matcher')
    assert restricted.get('/api/v1/questionnaires/dtd/DTD-0001').status_code == 403
    with app.state.app_db.connection() as con:
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert con.execute("PRAGMA quick_check").fetchone()[0] == 'ok'


def test_existing_accounts_and_sessions_survive_app_schema_upgrade(portal, viewer):
    app, _, settings = portal
    with app.state.app_db.connection() as con:
        accounts = [tuple(r) for r in con.execute('SELECT * FROM users ORDER BY id')]
        sessions = [tuple(r) for r in con.execute('SELECT * FROM sessions ORDER BY token_hash')]
        con.execute('ALTER TABLE users DROP COLUMN role_override')
    AppDatabase(settings)
    AppDatabase(settings)
    with app.state.app_db.connection() as con:
        assert [tuple(r) for r in con.execute('SELECT * FROM users ORDER BY id')] == accounts
        assert [tuple(r) for r in con.execute('SELECT * FROM sessions ORDER BY token_hash')] == sessions
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
    assert viewer.get('/api/v1/auth/session').json()['user']['role'] == 'viewer'


def test_private_shared_account_provisioning_preserves_existing_users(portal):
    app, _, settings = portal
    with app.state.app_db.connection() as con:
        previous = [tuple(r) for r in con.execute('SELECT * FROM users ORDER BY id')]
    provision_matcher(settings, 'matcher.private', PASSWORD)
    with app.state.app_db.connection() as con:
        assert [tuple(r) for r in con.execute('SELECT * FROM users ORDER BY id')][:-1] == previous
        assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        assert con.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
    client = sign_in(TestClient(app), 'matcher.private')
    assert not client.get('/api/v1/auth/session').json()['password_change_required']
    assert client.get('/api/v1/auth/session').json()['user']['role'] == 'matcher'
    assert client.post('/api/v1/directories/businesses/search', json={}).status_code == 200
    assert client.get('/api/v1/questionnaires/dtd/DTD-0001').status_code == 403
    with pytest.raises(ValueError, match='EXISTING_ACCOUNT_PRESERVED'):
        provision_matcher(settings, 'matcher.private', PASSWORD)
    assert client.post('/api/v1/directories/businesses/search', json={}).status_code == 200


def test_matcher_created_in_ui_must_complete_onboarding_and_commitment(portal):
    app, admin, _ = portal
    assert admin.post('/api/v1/auth/users', json={
        'username': 'matcher.new', 'password': 'a', 'role': 'matcher',
    }).status_code == 200
    client = TestClient(app)
    client.headers['X-CSRF-Token'] = client.get('/api/v1/auth/session').json()['csrf_token']
    login = client.post('/api/v1/auth/login', json={'username': 'matcher.new', 'password': 'a'})
    assert login.json()['password_change_required']
    client.headers['X-CSRF-Token'] = login.json()['csrf_token']
    assert client.post('/api/v1/directories/businesses/search', json={}).json()['detail'] == 'PASSWORD_CHANGE_REQUIRED'
    changed = client.post('/api/v1/auth/change-password', json={
        'current_password': 'a', 'new_password': PASSWORD, 'confirm_password': PASSWORD,
    })
    assert changed.status_code == 200
    client.headers['X-CSRF-Token'] = changed.json()['csrf_token']
    assert client.post('/api/v1/directories/businesses/search', json={}).json()['detail'] == 'COMMITMENT_REQUIRED'
    assert client.post('/api/v1/auth/commitment', json={
        'version': login.json()['commitment_version'], 'accepted': True,
    }).status_code == 200
    assert client.post('/api/v1/directories/businesses/search', json={}).status_code == 200
