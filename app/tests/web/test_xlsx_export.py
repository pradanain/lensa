from io import BytesIO

from openpyxl import load_workbook
from se2026.common import sha256
from se2026.web.xlsx_export import workbook_response


def sheet(response):
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert "no-store" in response.headers["cache-control"]
    return load_workbook(BytesIO(response.content)).active


def test_export_all_filtered_rows_preserves_order_grain_and_text_keys(portal):
    _, client, settings = portal
    before = sha256(settings.census_db)
    body = {
        "source": "dtd",
        "kbli_prefix": "0",
        "kecamatan": "6502010",
        "sort": "business_priority",
        "page": 2,
        "page_size": 1,
    }
    expected = client.post(
        "/api/v1/directories/businesses/search", json={**body, "page": 1, "page_size": 100}
    ).json()
    assert expected["total"] > 1
    ws = sheet(client.post("/api/v1/directories/businesses/export", json=body))
    values = list(ws.values)
    assert len(values) - 1 == expected["total"]
    assert [(r[1], r[2], r[3]) for r in values[1:]] == [
        (r["assignment_id"], r["version"], r["index1"]) for r in expected["rows"]
    ]
    columns = {name: index + 1 for index, name in enumerate(values[0])}
    for name in ["Assignment ID", "Roster", "Kode SUB-SLS", "KBLI 2025"]:
        assert ws.cell(2, columns[name]).data_type == "s"
    assert ws.cell(2, columns["KBLI 2025"]).value == "01111"
    assert ws.freeze_panes == "A2"
    assert sha256(settings.census_db) == before


def test_xlsx_strings_do_not_become_formulas_or_lose_precision():
    response = workbook_response(
        ["Kode", "Nilai"],
        [["00001234567890123456", '=HYPERLINK("https://invalid.test")'], ["01", "<teks> & \x00 baris"]],
        "synthetic",
    )
    ws = load_workbook(BytesIO(response.body)).active
    assert ws["A2"].value == "00001234567890123456"
    assert ws["A2"].data_type == "s"
    assert ws["B2"].data_type == "s"
    assert ws["B2"].hyperlink is None
    assert ws["B3"].value == "<teks> &  baris"


def test_directory_export_respects_roles_and_search_permissions(portal, viewer, analyst):
    assert viewer.post("/api/v1/directories/businesses/export", json={}).status_code == 403
    ws = sheet(analyst.post("/api/v1/directories/businesses/export", json={"source": "dtd", "q": "DTD-0001"}))
    assert "Latitude" not in next(ws.values)
    assert "Longitude" not in next(ws.values)
    assert portal[1].post("/api/v1/directories/unknown/export", json={}).status_code == 404
    # Extra controls cannot override internal pagination or authorization.
    assert analyst.post("/api/v1/directories/businesses/export", json={"all_rows": True}).status_code == 422


def test_kbli_export_matches_complete_filtered_and_suppressed_tree(portal, viewer):
    query = {"level": 5, "prefix": "01", "category": "A", "q": "", "enumerated_only": True}
    expected = viewer.get("/api/v1/kbli/tree", params={**query, "page_size": 100}).json()
    ws = sheet(viewer.post("/api/v1/kbli/export", json=query))
    values = list(ws.values)
    assert len(values) - 1 == expected["total"]
    for actual, row in zip(values[1:], expected["rows"], strict=True):
        assert actual == (
            row["category"],
            row["code"],
            row["title"],
            row.get("description") or None,
            row["reference_codes"],
            row["dtd_units"],
            row["ub_units"],
        )
    assert len(values) > 10
    empty = sheet(
        portal[1].post("/api/v1/directories/businesses/export", json={"q": "ABSENT-SYNTHETIC-ONLY"})
    )
    assert empty.max_row == 1
