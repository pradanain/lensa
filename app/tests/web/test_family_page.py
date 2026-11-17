import sqlite3
from unittest.mock import patch

import pytest

from se2026.analytics import Analytics
from se2026.common import sha256
from se2026.web.family_directory import enrich_family_records

from .synthetic import V1, V2
from .test_xlsx_export import sheet


def test_family_summary_only_queries_family_and_member_metrics(portal, viewer):
    _, client, settings = portal
    before = sha256(settings.census_db)
    calls = []
    original = Analytics.query

    def query(self, metric_id, *args, **kwargs):
        calls.append(metric_id)
        return original(self, metric_id, *args, **kwargs)

    with patch.object(Analytics, "query", query):
        result = client.get("/api/v1/analytics/family-summary", params={"kecamatan": "6502010"})
    assert result.status_code == 200
    assert calls == ["keluarga.count", "anggota.count"]
    for metric in calls:
        expected = client.post("/api/v1/analytics/query", json={"metric_id": metric, "filters": {"kecamatan": "6502010"}}).json()
        assert result.json()["counts"][metric] == expected["rows"]
    assert viewer.get("/api/v1/analytics/family-summary").status_code == 200
    small = client.get("/api/v1/analytics/family-summary", params={"desa": "6502000000"}).json()
    assert all(rows[0]["value"] is None and rows[0]["suppressed"] for rows in small["counts"].values())
    assert sha256(settings.census_db) == before


def test_family_maps_and_member_heads_use_exact_version_and_access(portal, analyst, viewer):
    _, client, settings = portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute("UPDATE mart_keluarga SET nama_kk='SYNTHETIC EXACT HEAD',geotag_latitude='2.125',geotag_longitude='117.25' WHERE assignment_id='DTD-0001' AND __version_normalized=?", (V1,))
        con.execute("UPDATE mart_keluarga SET __version_normalized=? WHERE assignment_id='DTD-0002'", (V2,))
        con.execute("INSERT INTO mart_keluarga(assignment_id,__version_normalized,nama_kk) VALUES('DTD-0001',?,'SYNTHETIC OTHER HEAD')", (V2,))
    before = sha256(settings.census_db)
    body = {"source": "dtd", "q": "DTD-0001", "page_size": 100}
    result = client.post("/api/v1/directories/families/search", json=body).json()
    exact = next(row for row in result["rows"] if row["version"] == V1)
    assert exact["map_coordinates"] == {"latitude": "2.125", "longitude": "117.25"}
    assert any(row["version"] == V2 for row in result["rows"])
    assert all(row["map_coordinates"] is None for row in result["rows"] if row["version"] != V1)
    restricted = analyst.post("/api/v1/directories/families/search", json=body).json()
    assert all(row["map_coordinates"] is None and row["map_status"] == "RESTRICTED" for row in restricted["rows"])
    assert "117.25" not in str(restricted)
    members = client.post("/api/v1/directories/members/search", json=body).json()["rows"]
    assert all(row["family_head"] == "SYNTHETIC EXACT HEAD" for row in members if row["version"] == V1)
    unmatched = client.post("/api/v1/directories/members/search", json={"source": "dtd", "q": "DTD-0002"}).json()["rows"]
    assert unmatched and all(row["family_head"] is None for row in unmatched)
    assert len({row["record_key"] for row in members}) == len(members)
    assert viewer.post("/api/v1/directories/families/search", json=body).status_code == 403
    for user, has_coordinates in [(client, True), (analyst, False)]:
        workbook = sheet(user.post("/api/v1/directories/families/export", json=body))
        headers = [cell.value for cell in workbook[1]]
        assert ("Latitude" in headers) is has_coordinates
        assert workbook.cell(2, 1).value == "DTD"
    assert sha256(settings.census_db) == before


def test_duplicate_family_root_does_not_choose_a_tag_or_multiply_member_rows(portal):
    _, client, settings = portal
    rows = client.post("/api/v1/directories/members/search", json={"source": "dtd", "q": "DTD-0001", "page_size": 100}).json()["rows"]
    expected = len(rows)
    with sqlite3.connect(settings.census_db) as con:
        con.execute("INSERT INTO mart_keluarga SELECT * FROM mart_keluarga WHERE assignment_id='DTD-0001' AND __version_normalized=?", (V1,))
    rows = enrich_family_records(settings, rows, "admin", "members")
    assert len(rows) == len({row["record_key"] for row in rows}) == expected
    assert all(row["family_head"] is None for row in rows if row["version"] == V1)
    family = enrich_family_records(settings, [{"assignment_id": "DTD-0001", "version": V1}], "admin", "families")[0]
    assert family["map_coordinates"] is None and family["map_status"] == "SOURCE_CONFLICT"


@pytest.mark.parametrize("scope,new_code,missing_code", [("families", "2", "0"), ("members", "5", "7")])
def test_family_priority_is_global_before_pagination_and_shared_by_export(portal, scope, new_code, missing_code):
    app, client, settings = portal
    app.state.directory.ensure()
    before = sha256(settings.census_db)
    with app.state.app_db.connection() as con:
        con.execute("UPDATE directory_rows SET status='unknown',title='OTHER' WHERE scope=?", (scope,))
        for aid, code, title in [
            ("DTD-0001", missing_code, "AAA MISSING"),
            ("DTD-0002", "3" if scope == "families" else "2", "AAA INACTIVE"),
            ("DTD-0003", new_code, "ZZZ NEW"),
            ("DTD-0004", "1", "zebra FOUND"),
            ("DTD-0005", "1", "alpha FOUND"),
        ]:
            con.execute("UPDATE directory_rows SET status=?,title=? WHERE scope=? AND assignment_id=?", (code, title, scope, aid))
    body = {"source": "dtd", "sort": "family_priority", "page_size": 100}
    endpoint = "/api/v1/directories/" + scope
    result = client.post(endpoint + "/search", json=body).json()
    assert [row["title"] for row in result["rows"][:3]] == ["alpha FOUND", "zebra FOUND", "ZZZ NEW"]
    assert len(result["rows"]) == len({row["record_key"] for row in result["rows"]})
    first = client.post(endpoint + "/search", json={**body, "page_size": 2, "page": 1}).json()
    second = client.post(endpoint + "/search", json={**body, "page_size": 2, "page": 2}).json()
    assert [row["record_key"] for row in first["rows"] + second["rows"]] == [row["record_key"] for row in result["rows"][:4]]
    # Default API requests and exports follow the same global order.
    default = client.post(endpoint + "/search", json={"source": "dtd", "page_size": 100}).json()
    assert [row["record_key"] for row in default["rows"]] == [row["record_key"] for row in result["rows"]]
    exported = sheet(client.post(endpoint + "/export", json={**body, "page_size": 2, "page": 2}))
    assert [row[4] for row in exported.iter_rows(min_row=2, values_only=True)] == [row["title"] for row in result["rows"]]
    assert sha256(settings.census_db) == before


@pytest.mark.parametrize("scope", ["families", "members"])
def test_family_completeness_precedes_name_and_uses_only_visible_fields(portal, analyst, scope):
    app, client, settings = portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute("UPDATE mart_keluarga SET geotag_latitude='2.125',geotag_longitude='117.25' WHERE assignment_id='DTD-0001'")
        if scope == "members":
            con.execute("UPDATE mart_keluarga SET nama_kk=NULL WHERE assignment_id='DTD-0002'")
    app.state.directory.ensure()
    with app.state.app_db.connection() as con:
        con.execute("UPDATE directory_rows SET status='unknown' WHERE scope=?", (scope,))
        con.execute("UPDATE directory_rows SET status='1',title='ZZZ COMPLETE' WHERE scope=? AND assignment_id='DTD-0001'", (scope,))
        con.execute("UPDATE directory_rows SET status='1',title='AAA LESS COMPLETE' WHERE scope=? AND assignment_id='DTD-0002'", (scope,))
    before = sha256(settings.census_db)
    body = {"source": "dtd", "sort": "family_priority", "page_size": 100, "status": "1"}
    endpoint = "/api/v1/directories/" + scope + "/search"
    admin_rows = client.post(endpoint, json=body).json()["rows"]
    analyst_rows = analyst.post(endpoint, json=body).json()["rows"]
    assert admin_rows[0]["title"] == "ZZZ COMPLETE"
    # A hidden family tag must not influence analyst order. The visible parent
    # name on member rows can influence both roles, without using member tags.
    assert analyst_rows[0]["title"] == ("AAA LESS COMPLETE" if scope == "families" else "ZZZ COMPLETE")
    assert all(row.get("map_coordinates") is None for row in analyst_rows)
    assert sha256(settings.census_db) == before
