import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from se2026.common import sha256
from se2026.web.settings import Settings

from .conftest import PASSWORD
from .synthetic import ROOT, V1


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/assignments/dtd"),
        ("get", "/api/v1/assignments/ub"),
        ("get", "/api/v1/questionnaires/dtd/DTD-0001"),
        ("get", "/api/v1/questionnaires/ub/UB-0001"),
        ("post", "/api/v1/directories/businesses/search"),
        ("get", "/api/v1/auth/users"),
    ],
)
def test_unauthenticated_individual_endpoints_rejected(portal, method, path):
    client = TestClient(portal[0], raise_server_exceptions=False)
    response = getattr(client, method)(path, **({"json": {}} if method == "post" else {}))
    assert response.status_code == 401


def test_viewer_cannot_bypass_detail_or_admin_guards(viewer):
    for path in [
        "/assignments/dtd",
        "/assignments/ub",
        "/questionnaires/dtd/DTD-0001",
        "/questionnaires/ub/UB-0001",
        "/auth/users",
    ]:
        assert viewer.get("/api/v1" + path).status_code == 403
    assert viewer.post("/api/v1/directories/businesses/search", json={}).status_code == 403
    result = viewer.get("/api/v1/analytics/summary")
    assert result.status_code == 200
    assert "SYNTHETIC_PRIVATE" not in result.text and "USAHA SINTETIS" not in result.text


def test_lists_are_paged_and_keep_assignments_without_detail(portal):
    client = portal[1]
    result = client.get("/api/v1/assignments/dtd?page_size=5").json()
    assert result["total"] == 13 and len(result["rows"]) == 5 and result["pages"] == 3
    result = client.get("/api/v1/assignments/ub").json()
    assert result["total"] == 12
    assert client.get("/api/v1/assignments/ub?q=do-not-put-names-in-url").status_code == 422
    missing = client.post(
        "/api/v1/directories/assignments/search", json={"source": "dtd", "q": "DTD-EMPTY"}
    ).json()
    assert missing["total"] == 1
    form = client.get("/api/v1/questionnaires/dtd/DTD-EMPTY").json()
    assert form["available_versions"] == [] and form["read_only"]


def test_sort_whitelist_bound_search_and_five_digit_prefix(portal):
    client = portal[1]
    bad = client.post(
        "/api/v1/directories/businesses/search", json={"sort": "title;DROP TABLE directory_rows;--"}
    )
    assert bad.status_code == 422 and "DROP TABLE" not in bad.text
    assert (
        client.post("/api/v1/directories/businesses/search", json={"q": "' OR 1=1 --"}).json()["total"] == 0
    )
    result = client.post(
        "/api/v1/directories/businesses/search", json={"source": "dtd", "kbli_prefix": "0"}
    ).json()
    assert result["total"] == 10
    assert (
        client.post("/api/v1/directories/businesses/search", json={"kbli_prefix": "123456"}).status_code
        == 422
    )


def test_nib_search_is_restricted_to_admin(portal, analyst):
    body = {"source": "ub", "q": "SYNTHETICNIB1"}
    assert portal[1].post("/api/v1/directories/businesses/search", json=body).json()["total"] > 0
    assert analyst.post("/api/v1/directories/businesses/search", json=body).json()["total"] == 0


def fields(form):
    return {q["question_id"]: q for section in form["sections"] for q in section["questions"]}


def test_exact_version_roster_and_scalar_decimal_preserved(portal):
    client = portal[1]
    response = client.get(
        "/api/v1/questionnaires/dtd/DTD-0001", params={"version": V1, "business": "002", "member": "001"}
    )
    assert response.status_code == 200
    form = response.json()
    assert len(form["sections"]) == 11
    result = fields(form)
    assert result["blokl.nama_usaha"]["value"] == "USAHA SINTETIS KEDUA"
    assert result["b_ak_lanjutan.profesi_lainnya"]["status"] == "UNMATCHED_VERSION"
    assert result["b_ak_lanjutan.nilai_pend_pekerjaan"]["value"] == "45.00"
    assert "SYNTHETIC_OPAQUE_INCOME" not in response.text
    first = fields(
        client.get("/api/v1/questionnaires/dtd/DTD-0001", params={"version": V1, "business": "001"}).json()
    )
    assert first["blokl.total_pendapatan"]["value"] == "12345678901234567890.10"
    assert first["blokl.total_pendapatan"]["numeric_value"] == "12345678901234567890.10"
    assert first["blokl.internet_pesanan"]["status"] == "SKIPPED_NOT_APPLICABLE"


def test_analyst_cannot_read_sensitive_values(portal, analyst):
    for system, aid in [("dtd", "DTD-0001"), ("ub", "UB-0001")]:
        response = analyst.get(
            "/api/v1/questionnaires/" + system + "/" + aid, params={"version": V1} if system == "dtd" else {}
        )
        assert response.status_code == 200
        assert "SYNTHETIC_PRIVATE" not in response.text
        assert "12345678901234567890.10" not in response.text
        assert any(q["status"] == "RESTRICTED" for q in fields(response.json()).values())
    assert analyst.get("/api/v1/auth/users").status_code == 403


def test_ub_is_assignment_join_without_version_requirement(portal):
    form = portal[1].get("/api/v1/questionnaires/ub/UB-0001").json()
    assert (
        len(form["sections"]) == 5
        and form["questionnaire_version_status"] == "QUESTIONNAIRE_VERSION_NOT_VERIFIED"
    )
    assert fields(form)["ub.5a"]["value"] == "USAHA SINTETIS 1"
    assert fields(form)["ub.7b"]["status"] == "NOT_EXPORTED"


def test_csrf_origin_and_validation_do_not_echo_input(portal):
    client = portal[1]
    assert (
        client.post(
            "/api/v1/auth/users",
            json={"username": "secret", "password": PASSWORD, "role": "admin"},
            headers={"X-CSRF-Token": ""},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/auth/logout", json={}, headers={"Origin": "https://attacker.invalid"}
        ).status_code
        == 403
    )
    response = client.post(
        "/api/v1/auth/users",
        json={"username": "private username rejected", "password": "SYNTHETIC_SECRET_BODY", "role": "bad"},
    )
    assert (
        response.status_code == 422
        and "SYNTHETIC_SECRET_BODY" not in response.text
        and "private username" not in response.text
    )
    cookies = client.get("/api/v1/auth/session").headers.get_list("set-cookie")
    assert all("SameSite=strict" in value for value in cookies)
    assert (
        client.post("/api/v1/auth/setup", json={"username": "another", "password": PASSWORD}).status_code
        == 409
    )


def test_role_change_revokes_sessions_and_self_change_rejected(portal, analyst):
    client = portal[1]
    users = client.get("/api/v1/auth/users").json()["rows"]
    analyst_id = next(row["id"] for row in users if row["username"] == "analyst")
    assert (
        client.patch(
            "/api/v1/auth/users/" + str(analyst_id), json={"role": "aggregate_viewer", "active": True}
        ).status_code
        == 200
    )
    assert analyst.get("/api/v1/assignments/dtd").status_code == 401
    self_id = next(row["id"] for row in users if row["username"] == "admin")
    assert (
        client.patch(
            "/api/v1/auth/users/" + str(self_id), json={"role": "aggregate_viewer", "active": False}
        ).status_code
        == 422
    )


def test_login_attempts_are_rate_limited_without_logging_password(portal):
    client = TestClient(portal[0], raise_server_exceptions=False)
    client.headers["X-CSRF-Token"] = client.get("/api/v1/auth/session").json()["csrf_token"]
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login", json={"username": "nobody", "password": "synthetic-wrong-password"}
        )
        assert response.status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "nobody", "password": "synthetic-wrong-password"}
        ).status_code
        == 429
    )
    with portal[0].state.app_db.connection() as con:
        audit = json.dumps([dict(row) for row in con.execute("SELECT * FROM audit")])
    assert "synthetic-wrong-password" not in audit and "DTD-0001" not in audit


def test_master_reference_counts_leading_zero_and_unknown_buckets(portal, viewer):
    result = viewer.get("/api/v1/references/summary").json()
    assert (
        result["kbli_codes"] == 1559
        and result["categories"] == 22
        and result["outside_se_codes"] == 184
        and result["countries"] == 250
    )
    nodes = viewer.get("/api/v1/kbli/tree?level=5&prefix=01111").json()
    assert nodes["rows"][0]["prefix"] == "01111" and nodes["rows"][0]["reference_codes"] == 1
    assert nodes["rows"][0]["outside_se_codes"] == 1
    unknown = nodes["unknown_buckets"]["dtd"]
    assert {r["code"] for r in unknown} >= {"MISSING", "INVALID_FORMAT", "UNKNOWN_REFERENCE"}
    assert all(r["units"] is None for r in unknown if r["code"] != "VALID")
    professions = viewer.get("/api/v1/references/professions?q=tidak%20bekerja").json()
    assert professions["rows"][0]["code"] == "000"


def test_full_kbli_hierarchy_labels_definitions_and_technical_zero(viewer):
    summary = viewer.get("/api/v1/references/summary").json()
    assert summary["category_labels"]["A"] == "PERTANIAN, KEHUTANAN, DAN PERIKANAN"
    catalog = viewer.get("/api/v1/kbli/catalog").json()["rows"]
    assert len(catalog) == 2444
    division = next(r for r in catalog if r["code"] == "01")
    assert division["parent_code"] == "A" and division["level"] == 2
    assert "PERTANIAN TANAMAN" in division["title"]
    data = viewer.get("/api/v1/kbli/tree?category=A&prefix=01&level=3").json()
    assert [r["code"] for r in data["selection"]] == ["A", "0", "01"]
    assert data["selection"][-1]["description"]
    assert all(r["code"].startswith("01") and r["is_official"] for r in data["rows"])
    assert next(r for r in data["rows"] if r["code"] == "011")["title"] == "PERTANIAN TANAMAN SEMUSIM"
    zero = viewer.get("/api/v1/kbli/tree?level=1&prefix=0").json()["rows"][0]
    assert zero["is_official"] is False and zero["categories"] == ["A", "B"]
    assert zero["category"] == "" and "bukan tingkatan resmi" in zero["description"]
    fallback = viewer.get("/api/v1/kbli/tree?category=R").json()["selection"][0]
    assert fallback["description_status"] == "CHILD_TITLES_ONLY"
    assert "Cakupan menurut golongan pokok" in fallback["description"]


def test_kbli_search_paging_and_unchanged_leaf_metadata(viewer):
    first = viewer.get("/api/v1/kbli/tree?level=5&page_size=10").json()
    second = viewer.get("/api/v1/kbli/tree?level=5&page_size=10&page=2").json()
    assert first["total"] == 1559 and len(first["rows"]) == len(second["rows"]) == 10
    assert set(r["code"] for r in first["rows"]).isdisjoint(r["code"] for r in second["rows"])
    found = viewer.get(
        "/api/v1/kbli/tree", params={"level": 5, "q": "pertanian jagung", "category": "A"}
    ).json()
    assert any(
        r["code"] == "01111"
        and r["title"] == "Pertanian Jagung"
        and r["description"]
        and r["outside_se_codes"] == 1
        for r in found["rows"]
    )
    invalid = viewer.get("/api/v1/kbli/tree?prefix=01&level=1")
    assert invalid.status_code == 422
    assert viewer.get("/api/v1/kbli/tree?page_size=1000").status_code == 422


def test_list_defaults_and_reference_paging_are_ten_rows(portal, viewer):
    assert portal[1].get("/api/v1/assignments/dtd").json()["page_size"] == 10
    assert portal[1].post("/api/v1/directories/assignments/search", json={}).json()["page_size"] == 10
    first = viewer.get("/api/v1/references/countries").json()
    second = viewer.get("/api/v1/references/countries?page=2").json()
    assert first["page_size"] == 10 and first["total"] == 250 and len(first["rows"]) == 10
    assert first["rows"] != second["rows"]
    for size in (10, 25, 50, 100):
        result = viewer.get("/api/v1/references/countries", params={"page_size": size}).json()
        assert len(result["rows"]) == size
    tree = viewer.get("/api/v1/kbli/tree?level=5").json()
    assert tree["page_size"] == 10 and len(tree["rows"]) == 10 and tree["total"] == 1559


def test_census_unchanged_and_read_only_under_portal_use(portal):
    settings = portal[2]
    before = sha256(settings.census_db)
    for path in [
        "/api/v1/assignments/dtd",
        "/api/v1/questionnaires/dtd/DTD-0001",
        "/api/v1/questionnaires/ub/UB-0001",
    ]:
        assert portal[1].get(path).status_code == 200
    from se2026.web.database import census_connection

    with census_connection(settings) as con:
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DELETE FROM mart_usaha")
    assert sha256(settings.census_db) == before
    with portal[0].state.app_db.connection() as con:
        assert con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 3


def test_app_database_cannot_alias_census_or_protected_storage(tmp_path):
    census = tmp_path / "census.sqlite"
    census.touch()
    with pytest.raises(ValueError):
        Settings(root=ROOT, census_db=census, app_db=census)
    with pytest.raises(ValueError):
        Settings(root=ROOT, census_db=census, app_db=ROOT / "data/processed/another.sqlite")


def test_stricter_disclosure_policy_and_assignment_kind(portal, viewer):
    portal[0].state.settings.minimum_contributors = 20
    result = viewer.get("/api/v1/analytics/summary").json()
    assert result["counts"]["assignment_tgr.count"][0]["value"] is None
    assert result["region"]["suppression"]["minimum_contributors"] == 20
    assert all(r["value"] is None for r in result["region"]["rows"] if r.get("suppressed"))
    quality = viewer.get("/api/v1/data-quality/summary").json()
    assert quality["minimum_contributors"] == 20
    assert all(r["records"] is None for r in quality["directory_counts"])
    assert all("total_rows" not in r and "unmatched_rows" not in r for r in quality["p1_classification"])
    rows = portal[1].post("/api/v1/directories/assignments/search", json={"kind": "KELUARGA_BKU"}).json()
    assert rows["total"] == 12


def test_summary_geographic_filter_reconciles_and_cache_is_separate(portal, viewer):
    global_summary = viewer.get("/api/v1/analytics/summary").json()
    no_match = viewer.get("/api/v1/analytics/summary?kecamatan=NO_SUCH_LOCAL_CODE").json()
    assert global_summary["counts"]["assignment_tgr.count"][0]["value"] == 13
    assert no_match["counts"]["assignment_tgr.count"][0]["value"] == 0
    assert no_match["filters"] == {"kecamatan": "NO_SUCH_LOCAL_CODE"}
    assert viewer.get("/api/v1/analytics/summary").json()["counts"] == global_summary["counts"]


def test_assignment_kind_uses_source_presence_even_with_missing_name(tmp_path):
    from se2026.web.directory import DirectoryQuery
    from se2026.web.main import create_app

    from .synthetic import make_database

    census = make_database(tmp_path / "census.sqlite")
    with sqlite3.connect(census) as con:
        con.execute("UPDATE mart_keluarga SET nama_kk=NULL WHERE assignment_id='DTD-0001'")
    app = create_app(Settings(root=ROOT, census_db=census, sls_reference=census.with_suffix(".sls.json"), app_db=tmp_path / "portal.sqlite"))
    result = app.state.directory.search("assignments", DirectoryQuery(q="DTD-0001"), "analyst_detail")
    assert result["total"] == 1
    assert result["rows"][0]["kind"] == "KELUARGA_BKU"
    assert result["rows"][0]["version"] is None


def test_status_options_use_source_labels_and_preserve_filter_codes(portal):
    app, client, _ = portal
    with app.state.app_db.connection() as con:
        con.execute("UPDATE directory_rows SET status='00',status_label='0. Tidak Ditemukan' WHERE scope='businesses' AND source='dtd' AND assignment_id='DTD-0001'")
    result = client.get('/api/v1/directory-statuses?scope=businesses&source=dtd').json()
    option = next(row for row in result['options'] if row['code'] == '00')
    assert option['label'] == 'Tidak Ditemukan'
    assert '00' in result['rows']
    filtered = client.post('/api/v1/directories/businesses/search',json={'source':'dtd','status':'00'}).json()
    assert filtered['total'] > 0
    assert all(row['status'] == '00' for row in filtered['rows'])
