import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from .conftest import PASSWORD, sign_in


def rows(app, action=None):
    with app.state.app_db.connection() as con:
        return [dict(r) for r in con.execute("SELECT * FROM activity_events" + (" WHERE action=?" if action else "") + " ORDER BY id", (action,) if action else ())]


def test_server_login_search_detail_export_and_no_respondent_values(portal):
    app, client, settings = portal
    before = hashlib.sha256(settings.census_db.read_bytes()).hexdigest()
    client.post('/api/v1/directories/members/search', json={'source': 'dtd', 'q': 'SECRET-SEARCH-65029999', 'page': 1, 'page_size': 10})
    client.get('/api/v1/questionnaires/dtd/SECRET-ASSIGNMENT?version=SECRET-VERSION&member=SECRET-ROSTER', headers={'X-Forwarded-For': '10.11.12.13'})
    export = client.post('/api/v1/directories/members/export', json={'source': 'dtd', 'q': 'SECRET-SEARCH-65029999'})
    assert export.status_code == 200
    login = rows(app, 'LOGIN')[-1]
    assert json.loads(rows(app, 'USER_CREATE')[-1]['context'])['target_user_id'] > 1
    assert login['user_id'] and login['session_ref'] and login['status'] == 200
    search = rows(app, 'DIRECTORY_SEARCH')[-1]
    assert json.loads(search['context'])['has_search'] is True
    detail = rows(app, 'DETAIL_VIEW')[-1]
    assert detail['ip'] != '10.11.12.13'
    assert len(json.loads(detail['context'])['resource_ref']) == 32
    reference = json.loads(detail['context'])['resource_ref']
    assert client.get('/api/v1/activity?account_scope=all&resource_ref='+reference).json()['rows'][0]['id'] == detail['id']
    client.post('/api/v1/activity/events', json={'event': 'PAGE_VIEW', 'screen': 'questionnaire', 'assignment': 'SECRET-ASSIGNMENT', 'system': 'dtd', 'version': 'SECRET-VERSION', 'member': 'SECRET-ROSTER'})
    assert json.loads(rows(app, 'PAGE_VIEW')[-1]['context'])['resource_ref'] == reference
    exported = rows(app, 'EXPORT')[-1]
    assert exported['response_bytes'] > 0 and exported['session_ref'] == login['session_ref']
    raw = json.dumps(rows(app))
    for secret in ['SECRET-SEARCH', 'SECRET-ASSIGNMENT', 'SECRET-VERSION', 'SECRET-ROSTER', PASSWORD, client.cookies.get('portal_session'), client.headers['X-CSRF-Token']]:
        assert secret not in raw
    assert before == hashlib.sha256(settings.census_db.read_bytes()).hexdigest()


def test_admin_only_filters_export_csrf_and_sessions(portal, analyst, viewer):
    app, client, settings = portal
    anonymous = TestClient(app)
    for other, status in [(anonymous, 401), (analyst, 403), (viewer, 403)]:
        for path in ['/activity', '/activity/sessions', '/activity/integrity']:
            assert other.get('/api/v1' + path).status_code == status
        assert other.post('/api/v1/activity/export', json={}).status_code == status
    assert client.post('/api/v1/activity/export', json={}, headers={'X-CSRF-Token': 'bad'}).status_code == 403
    page = client.get('/api/v1/activity?account_scope=all&action=LOGIN&outcome=success&page_size=1').json()
    assert len(page['rows']) == 1 and page['total'] >= 3
    assert page['rows'][0]['action'] == 'LOGIN'
    assert client.get('/api/v1/activity?action=NOT_AN_ACTION').status_code == 422
    assert client.get('/api/v1/activity?since=100&until=1').status_code == 422
    export = client.post('/api/v1/activity/export', json={'action': 'LOGIN'})
    assert export.status_code == 200 and export.content.startswith(b'PK')
    assert rows(app, 'MONITOR_EXPORT')[-1]['user_id']
    session = client.get('/api/v1/activity/sessions?account_scope=all').json()['rows'][0]
    assert session['active'] is True
    ref = rows(app, 'LOGIN')[0]['session_ref']
    assert client.post('/api/v1/auth/logout', json={}).status_code == 200
    sign_in(client)
    sessions = client.get('/api/v1/activity/sessions?account_scope=all').json()['rows']
    assert next(row for row in sessions if row['session_ref'] == ref)['active'] is False
    assert rows(app, 'LOGOUT')[-1]['session_ref'] == ref


def test_browser_reports_are_classified_and_payload_bounded(portal):
    app, client, settings = portal
    response = client.post('/api/v1/activity/events', json={'event': 'PAGE_VIEW', 'screen': 'keluarga', 'tab': 'anggota'})
    assert response.status_code == 200
    event = rows(app, 'PAGE_VIEW')[-1]
    assert event['evidence'] == 'browser' and event['request_id'] == response.headers['X-Request-ID']
    for bad in [{'text': 'SECRET-NAME'}, {'event': 'LOGIN'}, {'screen': 'SECRET-NAME'}, {'block': 'SECRET-NAME'}]:
        assert client.post('/api/v1/activity/events', json={'event': 'PAGE_VIEW', 'screen': 'usaha', **bad}).status_code == 422
    assert 'SECRET-NAME' not in json.dumps(rows(app))


def test_failed_login_has_no_authenticated_actor(portal):
    app, admin, settings = portal
    client = TestClient(app)
    session = client.get('/api/v1/auth/session').json()
    result = client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'NOT-THE-PASSWORD'}, headers={'X-CSRF-Token': session['csrf_token']})
    assert result.status_code == 401
    event = rows(app, 'LOGIN')[-1]
    assert event['user_id'] is None and event['session_ref'] == ''
    assert json.loads(event['context'])['attempted_account_ref']
    evidence = admin.get('/api/v1/activity?account_scope=all&user_id=1&action=LOGIN&outcome=failure').json()
    assert any(row['id'] == event['id'] for row in evidence['rows'])
    assert 'NOT-THE-PASSWORD' not in json.dumps(rows(app))


def test_integrity_append_only_concurrency_and_tamper_detection(portal):
    app, client, settings = portal
    prototype = rows(app)[0]
    from se2026.web.activity import FIELDS
    values = {key: prototype[key] for key in FIELDS if key != 'previous_hash'}
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: app.state.activity.append(**values), range(12)))
    assert client.get('/api/v1/activity/integrity').json()['valid'] is True
    with app.state.app_db.connection() as con:
        import pytest
        with pytest.raises(sqlite3.IntegrityError):
            con.execute('UPDATE activity_events SET status=999 WHERE id=1')
        with pytest.raises(sqlite3.IntegrityError):
            con.execute('DELETE FROM activity_events WHERE id=1')
    with app.state.app_db.connection() as con:
        con.execute('DROP TRIGGER activity_no_update')
        con.execute('UPDATE activity_events SET status=999 WHERE id=1')
    result = client.get('/api/v1/activity/integrity').json()
    assert result['valid'] is False and result['failed_id'] == 1


def test_log_failure_blocks_delivery_and_cannot_skip_gate(portal, monkeypatch):
    app, client, settings = portal
    with app.state.app_db.connection() as con:
        con.execute("UPDATE users SET must_change_password=1 WHERE username='admin'")
    assert client.get('/api/v1/activity').status_code == 403
    assert client.get('/api/v1/activity/integrity').status_code == 403
    assert client.post('/api/v1/activity/events', json={'event': 'PAGE_VIEW', 'screen': 'password'}).status_code == 200
    with app.state.app_db.connection() as con:
        con.execute('UPDATE users SET must_change_password=0')
    def broken(**kwargs):
        raise sqlite3.OperationalError('synthetic disk failure')
    monkeypatch.setattr(app.state.activity, 'append', broken)
    response = client.get('/api/v1/geography')
    assert response.status_code == 503 and response.json()['detail'] == 'ACTIVITY_RECORD_UNAVAILABLE'
    assert response.headers['Cache-Control'] == 'no-store, private'


def test_non_admin_default_pagination_summary_sessions_and_export(portal, viewer):
    from io import BytesIO
    from openpyxl import load_workbook

    app, admin, settings = portal
    for _ in range(3):
        viewer.post('/api/v1/activity/events', json={'event': 'PAGE_VIEW', 'screen': 'usaha'})
    viewer_id = next(row['id'] for row in admin.get('/api/v1/auth/users').json()['rows'] if row['username'] == 'viewer')
    all_before = rows(app)
    expected = [row for row in all_before if row['role'] != 'admin']
    first = admin.get('/api/v1/activity?page_size=2').json()
    second = admin.get('/api/v1/activity?page_size=2&page=2').json()
    assert first['total'] == first['summary']['total'] == len(expected)
    assert len(first['rows']) == len(second['rows']) == 2
    assert not ({row['id'] for row in first['rows']} & {row['id'] for row in second['rows']})
    assert all(row['role'] != 'admin' for row in first['rows'] + second['rows'])
    assert first['summary']['accounts'] == len({row['user_id'] for row in expected if row['user_id'] is not None})
    sessions = admin.get('/api/v1/activity/sessions').json()['rows']
    assert sessions and all(row['user_id'] == viewer_id for row in sessions)
    assert all(row['user_id'] == 1 for row in admin.get('/api/v1/activity/sessions?account_scope=admin').json()['rows'])
    response = admin.post('/api/v1/activity/export', json={})
    exported = list(load_workbook(BytesIO(response.content)).active.values)
    role_index = exported[0].index('role')
    assert len(exported) - 1 == len(expected)
    assert all(row[role_index] != 'admin' for row in exported[1:])
    explicit = admin.get('/api/v1/activity?account_scope=all&user_id=1').json()
    assert explicit['rows'] and all(row['user_id'] == 1 for row in explicit['rows'])
    admins = admin.get('/api/v1/activity?account_scope=admin').json()
    assert admins['rows'] and all(row['role'] == 'admin' for row in admins['rows'])
    assert admin.get('/api/v1/activity?account_scope=invalid').status_code == 422
    assert admin.post('/api/v1/activity/export', json={'account_scope': 'invalid'}).status_code == 422
    # No filtering changes or deletes stored evidence; the full chain still verifies.
    assert {row['id']: row['event_hash'] for row in rows(app) if row['id'] <= all_before[-1]['id']} == {row['id']: row['event_hash'] for row in all_before}
    assert admin.get('/api/v1/activity/integrity').json()['valid'] is True


def test_failed_admin_login_is_available_only_when_admins_are_selected(portal):
    app, admin, settings = portal
    other = TestClient(app)
    session = other.get('/api/v1/auth/session').json()
    other.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'SYNTHETIC-WRONG'}, headers={'X-CSRF-Token': session['csrf_token']})
    event = rows(app, 'LOGIN')[-1]
    assert event['user_id'] is None
    default_ids = {row['id'] for row in admin.get('/api/v1/activity?action=LOGIN').json()['rows']}
    assert event['id'] not in default_ids
    chosen_ids = {row['id'] for row in admin.get('/api/v1/activity?account_scope=admin&action=LOGIN').json()['rows']}
    assert event['id'] in chosen_ids
