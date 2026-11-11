import importlib.util
import json
import re
import sqlite3
from zipfile import ZipFile

from openpyxl import Workbook
from se2026.common import sha256
from se2026.web.database import AppDatabase
from se2026.web.directory import DirectoryQuery
from se2026.web.settings import Settings
from se2026.web.sls_reference import SlsReference

from .synthetic import ROOT


def test_workbook_import_reads_bad_dimension_and_excludes_private_columns(tmp_path):
    module_path = ROOT / "app/scripts/maintenance/import_subsls_reference.py"
    spec = importlib.util.spec_from_file_location("subsls_import", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "reference.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "idsubsls",
            "semester",
            "kdprov",
            "kdkab",
            "kdkec",
            "kddesa",
            "kdsls",
            "kdsubsls",
            "nmsls",
            "jenis",
            "nama_ketua",
            "contact_person",
        ]
    )
    sheet.append(
        [
            "6502010001000100",
            "2025_2",
            "65",
            "02",
            "010",
            "001",
            "0001",
            "00",
            "RT 001 / RW 002",
            "SLS",
            "SYNTHETIC_PRIVATE_CHAIR",
            "SYNTHETIC_PRIVATE_CONTACT",
        ]
    )
    sheet.append(
        [6502010001000200, "2025_2", "65", "02", "010", "001", "0002", "00", "RT 002", "SLS", None, None]
    )
    workbook.save(path)
    # Reproduce the supplied workbook's incorrect A1 dimension without changing cells.
    short = tmp_path / "short-dimension.xlsx"
    with ZipFile(path) as source, ZipFile(short, "w") as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                data = re.sub(rb'<dimension ref="[^"]+"', b'<dimension ref="A1"', data)
            target.writestr(item, data)
    result = module.extract(short)
    assert len(result["rows"]) == 2 and result["period"] == "2025_2"
    assert result["numeric_ids_verified_against_components"] == 1
    assert result["rows"][1]["rw"] is None
    assert "SYNTHETIC_PRIVATE" not in json.dumps(result)
    assert "nama_ketua" not in json.dumps(result) and "contact_person" not in json.dumps(result)


def test_exact_geographic_lookup_preserves_missing_rw_and_rejects_wrong_parent(tmp_path):
    path = tmp_path / "reference.json"
    path.write_text(
        json.dumps(
            {
                "period": "2025_2",
                "rows": [
                    {
                        "code": "6502010001000100",
                        "sls": "65020100010001",
                        "label": "RT 001",
                        "rt": "001",
                        "rw": None,
                    },
                    {
                        "code": "6502010002000100",
                        "sls": "65020100020001",
                        "label": "RT 001 / RW 003",
                        "rt": "001",
                        "rw": "003",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    refs = SlsReference(tmp_path, path)
    first = refs.describe("65020100010001", "6502010001000100")
    assert first["rt"] == "001" and first["rw"] is None
    assert refs.describe("65020100020001", "6502010002000100")["rw"] == "003"
    wrong = refs.describe("65020100010001", "6502010002000100")
    assert wrong["rt"] is None and wrong["geography_reference_status"] == "INCONSISTENT_CODES"
    missing = refs.describe("65029999990001", "6502999999000100")
    assert missing["sls_label"] is None and missing["rt"] is None
    assert "referensi belum tersedia" in refs.choice_label("sls", "65029999990001")


def test_differing_subsls_labels_are_not_arbitrarily_combined(tmp_path):
    path = tmp_path / "reference.json"
    path.write_text(
        json.dumps(
            {
                "rows": [
                    {"code": "6502010001000101", "sls": "65020100010001", "label": "RT 001", "rt": "001"},
                    {"code": "6502010001000102", "sls": "65020100010001", "label": "RT 002", "rt": "002"},
                ]
            }
        ),
        encoding="utf-8",
    )
    refs = SlsReference(tmp_path, path)
    assert refs.describe("65020100010001")["sls_label"] is None
    assert refs.describe("65020100010001", "6502010001000102")["rt"] == "002"


def test_subsls_filter_and_labels_preserve_grain_and_snapshot(portal):
    app, client, settings = portal
    baseline = sha256(settings.census_db)
    before = app.state.directory.search("assignments", DirectoryQuery(source="dtd", page_size=100), "admin")
    assert before["total"] == 13
    sls = client.get(
        "/api/v1/geography", params={"level": "sls", "source": "dtd", "parent": "6502010001"}
    ).json()["rows"]
    assert sls[0]["code"] == "65020100010001" and "RT 001 / RW 002" in sls[0]["label"]
    subsls = client.get(
        "/api/v1/geography", params={"level": "subsls", "source": "dtd", "parent": "65020100010001"}
    ).json()["rows"]
    assert len(subsls) == 1 and "SUB-SLS 01" in subsls[0]["label"]
    result = client.post(
        "/api/v1/directories/businesses/search",
        json={"source": "dtd", "sls": "65020100010001", "subsls": "6502010001000101", "page_size": 100},
    ).json()
    assert result["total"] == 11
    assert len({row["record_key"] for row in result["rows"]}) == result["total"]
    assert all(row["rt"] == "001" and row["rw"] == "002" for row in result["rows"])
    assert all(row["subsls"] == "6502010001000101" for row in result["rows"])
    assert all(row["geography_reference_period"] == "2025_2" for row in result["rows"])
    mismatch = client.post(
        "/api/v1/directories/businesses/search",
        json={"source": "dtd", "sls": "65020000000000", "subsls": "6502010001000101"},
    ).json()
    # Original inconsistent source codes remain queryable, but gain no invented RT/RW.
    assert all(row["rt"] is None and row["rw"] is None for row in mismatch["rows"])
    assert sha256(settings.census_db) == baseline


def test_old_portal_cache_migration_is_additive_and_repeatable(tmp_path):
    path = tmp_path / "portal.sqlite"
    with sqlite3.connect(path) as con:
        con.execute(
            "CREATE TABLE directory_rows(id INTEGER PRIMARY KEY,scope TEXT,source TEXT,record_key TEXT,assignment_id TEXT,version TEXT,index1 TEXT,title TEXT,status TEXT,status_label TEXT,kecamatan TEXT,desa TEXT,sls TEXT,kecamatan_label TEXT,desa_label TEXT,kbli TEXT,kategori TEXT,kind TEXT,kbli_state TEXT)"
        )
        con.execute(
            "INSERT INTO directory_rows(scope,source,assignment_id,title) VALUES('assignments','dtd','SYNTHETIC','SYNTHETIC')"
        )
    settings = Settings(root=ROOT, census_db=tmp_path / "census.sqlite", app_db=path)
    AppDatabase(settings)
    AppDatabase(settings)
    with sqlite3.connect(path) as con:
        assert "subsls" in {row[1] for row in con.execute("PRAGMA table_info(directory_rows)")}
        assert con.execute("SELECT COUNT(*) FROM directory_rows").fetchone()[0] == 1
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
