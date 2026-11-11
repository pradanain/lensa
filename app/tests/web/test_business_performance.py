import os
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from se2026.web.routers.analytics import AggregateCache


def test_business_summary_only_queries_three_registry_metrics(portal):
    from se2026.analytics import Analytics

    _, client, _ = portal
    calls = []
    original = Analytics.query

    def query(self, metric_id, *args, **kwargs):
        calls.append(metric_id)
        return original(self, metric_id, *args, **kwargs)

    with patch.object(Analytics, "query", query):
        response = client.get("/api/v1/analytics/business-summary", params={"kecamatan": "6502010"})
    assert response.status_code == 200
    assert calls == ["usaha.enumerated_family_count", "usaha.enumerated_bku_count", "ub.enumerated_count"]
    for metric_id in calls:
        expected = client.post(
            "/api/v1/analytics/query", json={"metric_id": metric_id, "filters": {"kecamatan": "6502010"}}
        ).json()
        assert response.json()["counts"][metric_id] == expected["rows"]


def cache_settings(tmp_path):
    source = tmp_path / "source.sqlite"
    source.write_bytes(b"synthetic")
    folder = tmp_path / "app/config/analytics"
    folder.mkdir(parents=True)
    definition = folder / "test.json"
    definition.write_text("{}")
    return SimpleNamespace(
        root=tmp_path, census_db=source, aggregate_cache_seconds=300, minimum_contributors=5
    ), definition


def test_cache_invalidates_on_database_definition_and_privacy_policy_change(tmp_path):
    settings, definition = cache_settings(tmp_path)
    cache = AggregateCache(settings)
    calls = []

    def build():
        calls.append(1)
        return {"rows": [{"value": len(calls)}]}

    first = cache.get("a", build)
    first["rows"][0]["value"] = 999
    assert cache.get("a", build)["rows"][0]["value"] == 1
    for path in (settings.census_db, definition):
        stamp = path.stat()
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1000000))
        cache.get("a", build)
    settings.minimum_contributors = 10
    cache.get("a", build)
    assert len(calls) == 4


def test_cache_does_not_serialize_independent_requests_and_coalesces_same_key(tmp_path):
    settings, _ = cache_settings(tmp_path)
    cache = AggregateCache(settings)
    started, release = threading.Event(), threading.Event()
    calls = []

    def slow():
        calls.append(1)
        started.set()
        assert release.wait(5)
        return 7

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(cache.get, "slow", slow)
        assert started.wait(2)
        second = pool.submit(cache.get, "slow", slow)
        independent = pool.submit(cache.get, "fast", lambda: 9)
        try:
            assert independent.result(timeout=2) == 9
        finally:
            release.set()
        assert first.result(timeout=2) == second.result(timeout=2) == 7
    assert len(calls) == 1


def test_cache_failure_is_not_cached_or_left_waiting(tmp_path):
    settings, _ = cache_settings(tmp_path)
    cache = AggregateCache(settings)
    with pytest.raises(ValueError):
        cache.get("a", lambda: (_ for _ in ()).throw(ValueError("synthetic")))
    assert cache.get("a", lambda: 1) == 1
    settings.aggregate_cache_seconds = 0
    assert cache.get("a", lambda: 2) == 2


def test_focused_pages_return_403_without_removing_business_routes(portal):
    app, client, _ = portal
    app.state.settings.business_focus_enabled = True
    for path in (
        "/dashboard",
        "/dashboard/",
        "/keluarga",
        "/keluarga/test",
        "/data",
        "/data/dtd",
        "/data/ub",
    ):
        assert client.get(path).status_code == 403
    assert client.get("/usaha").status_code == 200
    assert client.get("/api/v1/auth/session").json()["business_focus_enabled"] is True


def test_static_assets_are_compressed_and_cacheable_while_data_remain_private(portal):
    _, client, settings = portal
    assets = list((settings.root / "app/web/dist/assets").glob("index-*.js"))
    assert assets
    response = client.get("/assets/" + assets[0].name, headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert "immutable" in response.headers["cache-control"]
    assert "no-store" in client.get("/api/v1/auth/session").headers["cache-control"]
    assert "no-store" in client.get("/usaha").headers["cache-control"]
