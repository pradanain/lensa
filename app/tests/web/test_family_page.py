import sqlite3
from unittest.mock import patch

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
