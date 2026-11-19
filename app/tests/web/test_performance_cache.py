from contextlib import contextmanager
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from se2026.analytics import Analytics
from se2026.common import sha256
from se2026.web.directory import DirectoryIndex, DirectoryQuery
from se2026.web.routers.analytics import cached_metric, warm_common_metrics


@pytest.mark.parametrize('part,metrics', [
    ('counts', ['usaha.enumerated_family_count', 'usaha.enumerated_bku_count', 'ub.enumerated_count', 'keluarga.count', 'anggota.count']),
    ('internet', ['usaha.internet_yes_rate', 'ub.internet_yes_rate']),
    ('notes', ['assignment_tgr.count', 'assignment_ub.count', 'bku.count', 'usaha.enumerated_count']),
])
def test_dashboard_parts_only_query_required_public_metrics(portal, part, metrics):
    _, client, _ = portal
    calls = []
    query = Analytics.query

    def observed(self, metric_id, *args, **kwargs):
        calls.append(metric_id)
        return query(self, metric_id, *args, **kwargs)

    with patch.object(Analytics, 'query', observed):
        response = client.get('/api/v1/analytics/dashboard', params={'part': part, 'kecamatan': '6502010'})
    assert response.status_code == 200
    assert calls == metrics
    for metric in metrics:
        expected = client.post('/api/v1/analytics/query', json={'metric_id': metric, 'filters': {'kecamatan': '6502010'}}).json()
        actual = next(item for item in response.json()['indicators'] if item['metric_id'] == metric) if part == 'internet' else {'rows': response.json()['counts'][metric]}
        assert actual['rows'] == expected['rows']


def test_dashboard_and_business_share_metric_cache_with_privacy_invalidation(portal):
    app, client, settings = portal
    settings.aggregate_cache_seconds = 300
    calls = []
    query = Analytics.query

    def observed(self, metric_id, *args, **kwargs):
        calls.append(metric_id)
        return query(self, metric_id, *args, **kwargs)

    with patch.object(Analytics, 'query', observed):
        assert client.get('/api/v1/analytics/business-summary').status_code == 200
        assert client.get('/api/v1/analytics/dashboard?part=counts').status_code == 200
        assert len(calls) == 5
        settings.minimum_contributors = 10
        assert client.post('/api/v1/analytics/query', json={'metric_id': 'keluarga.count'}).status_code == 200
        assert calls[-1] == 'keluarga.count' and len(calls) == 6


def test_old_read_transaction_cannot_populate_the_new_snapshot_cache(portal):
    app, client, settings = portal
    settings.aggregate_cache_seconds = 300
    request = SimpleNamespace(app=app)
    with sqlite3.connect(settings.census_db) as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        with Analytics(settings.census_db, settings.root) as original:
            writer.execute('INSERT INTO mart_keluarga SELECT * FROM mart_keluarga LIMIT 1')
            writer.commit()
            # This read still belongs to its valid, earlier SQLite transaction.
            assert cached_metric(request, 'keluarga.count', api=original)['rows']
        # A new read must validate and reject the now duplicated grain.
        response = client.post('/api/v1/analytics/query', json={'metric_id': 'keluarga.count'})
        assert response.status_code == 422


def test_prepared_landing_metrics_are_reused_by_normal_requests(portal):
    app, client, settings = portal
    settings.aggregate_cache_seconds = 300
    warm_common_metrics(app)
    with patch.object(Analytics, 'query', side_effect=AssertionError('UNEXPECTED_RECOMPUTATION')):
        assert client.get('/api/v1/analytics/business-summary').status_code == 200
        assert client.get('/api/v1/analytics/family-summary').status_code == 200
        assert client.get('/api/v1/analytics/dashboard?part=internet').status_code == 200


@pytest.mark.parametrize('scope', ['businesses', 'families', 'members'])
@pytest.mark.parametrize('role', ['admin', 'analyst_detail'])
def test_directory_order_survives_restart_and_uses_sql_index(portal, scope, role):
    app, _, settings = portal
    before = sha256(settings.census_db)
    payload = DirectoryQuery(source='dtd', page_size=1)
    expected = app.state.directory.search(scope, payload, role)
    restarted = DirectoryIndex(settings, app.state.app_db, app.state.references)
    traced = []
    connection = restarted.db.connection

    @contextmanager
    def observed():
        with connection() as con:
            con.set_trace_callback(lambda sql: traced.append(sql) if sql.startswith('SELECT d.record_key') else None)
            yield con

    enrichment = 'enrich_businesses' if scope == 'businesses' else 'enrich_family_records'
    import se2026.web.directory as directory
    enrich = getattr(directory, enrichment)
    sizes = []

    def bounded(settings, rows, *args):
        sizes.append(len(rows))
        return enrich(settings, rows, *args)

    with patch.object(restarted.db, 'connection', observed), patch.object(directory, enrichment, bounded):
        assert restarted.search(scope, payload, role) == expected
    assert sizes == [1]  # Restart does not enrich the full scope again.
    assert len(traced) == 1
    with connection() as con:
        plan = [row[3] for row in con.execute('EXPLAIN QUERY PLAN ' + traced[0])]
    assert any('directory_order_' in item for item in plan)
    assert not any('TEMP B-TREE FOR ORDER BY' in item for item in plan)
    assert sha256(settings.census_db) == before
