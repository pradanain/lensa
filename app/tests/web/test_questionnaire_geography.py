import sqlite3

import pytest
from se2026.common import sha256
from se2026.web.questionnaire import Questionnaires
from se2026.web.references import References

from .synthetic import ROOT, V1, V2
from .test_api import fields


def test_assignment_geography_is_available_without_inventing_root_answers(portal):
    before = sha256(portal[2].census_db)
    form = portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json()
    answers = fields(form)
    expected = {
        "prov": ("65", "Kalimantan Utara"),
        "kab": ("6502", "Bulungan"),
        "kec": ("6502010", "KECAMATAN SINTETIS"),
        "desa": ("6502010001", "DESA SINTETIS"),
        "kode_sls": ("6502010001000101", None),
        "nama_sls": ("SUB SINTETIS", None),
    }
    for key, (value, label) in expected.items():
        field = answers["b1_p." + key]
        assert field["status"] == "ANSWERED"
        assert field["value"] == value and field["label"] == label
        assert field["source_object"] == "mart_assignment_tgr"
        assert field["source_version_scope"] == "assignment"
        assert "__version_normalized" not in field["provenance"]
    for key in [
        "ubah_wilayah",
        "kab_baru",
        "kec_baru",
        "desa_baru",
        "klas_desa",
        "ubah_sls",
        "nama_sls_lap",
        "kodepos",
    ]:
        assert answers["b1_p." + key]["status"] == "NOT_EXPORTED"
        assert answers["b1_p." + key]["value"] is None
    assert sha256(portal[2].census_db) == before
    assert answers["b1_p.nama_sls"]["reference_label"] == "RT 001 / RW 002"
    assert answers["b1_p.nama_sls"]["reference_period"] == "2025_2"


def test_assignment_geography_uses_operational_snapshot_independently_of_selected_root(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_assignment_tgr SET assignment_date_modified=?, __version_normalized=? WHERE assignment_id='DTD-0001'",
            (V2, V2),
        )
        con.execute("DELETE FROM mart_keluarga WHERE assignment_id='DTD-0001'")
        con.execute("DELETE FROM mart_bku WHERE assignment_id='DTD-0001'")
    form = portal[1].get("/api/v1/questionnaires/dtd/DTD-0001", params={"version": V1}).json()
    assert form["version"] == V1
    field = fields(form)["b1_p.kec"]
    assert field["status"] == "ANSWERED"
    assert field["provenance"]["assignment_date_modified"] == V2
    assert fields(form)["b5.no_bang"]["value"] is None


def test_sls_falls_back_to_exact_parent_without_changing_codes(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_assignment_tgr SET kode_subsls=NULL,subsls=NULL WHERE assignment_id='DTD-0001'"
        )
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    assert answer["b1_p.kode_sls"]["value"] == "65020100010001"
    assert answer["b1_p.nama_sls"]["value"] == "SLS SINTETIS"


def test_inconsistent_sls_codes_do_not_get_a_matching_name(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_assignment_tgr SET kode_subsls='6502010002000101' WHERE assignment_id='DTD-0001'"
        )
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    for key in ["kode_sls", "nama_sls"]:
        assert answer["b1_p." + key]["source_conflict"]
        assert answer["b1_p." + key]["value"] is None


def test_unknown_geography_codes_never_get_bulungan_labels(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute("UPDATE mart_assignment_tgr SET kode_kabupaten='0099' WHERE assignment_id='DTD-0001'")
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    assert answer["b1_p.prov"]["value"] == "00" and answer["b1_p.prov"]["label"] is None
    assert answer["b1_p.kab"]["value"] == "0099" and answer["b1_p.kab"]["label"] is None


def test_informant_is_not_substituted_with_family_head_or_business_contact(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_legalitas_usaha SET nomor_telepon='SYNTHETIC_BUSINESS_PHONE',email='SYNTHETIC_BUSINESS_EMAIL' WHERE assignment_id='DTD-0001'"
        )
    form = portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json()
    section = next(s for s in form["sections"] if s["section_id"] == "ket_jawaban")
    assert section["collapse_not_exported"]
    assert all(f["status"] == "NOT_EXPORTED" and f["value"] is None for f in section["questions"])
    assert "SYNTHETIC_BUSINESS_PHONE" not in str(section)
    assert fields(form)["blokl.no_telp"]["status"] == "ANSWERED"


def test_analyst_gets_geography_without_gaining_sensitive_columns(portal, analyst):
    form = analyst.get("/api/v1/questionnaires/dtd/DTD-0001").json()
    assert fields(form)["b1_p.kec"]["status"] == "ANSWERED"
    assert fields(form)["b5.no_kk"]["status"] == "RESTRICTED"


def test_assignment_geography_context_columns_are_validated(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute("ALTER TABLE mart_assignment_tgr RENAME COLUMN subsls TO unexpected_subsls")
    with pytest.raises(ValueError, match="QUESTIONNAIRE_CONTEXT_DRIFT"):
        Questionnaires(portal[2], References(ROOT))


def test_unmatched_reference_keeps_source_name_without_inventing_rt(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_assignment_tgr SET kode_sls='65020100020001',kode_subsls='6502010002000101' WHERE assignment_id='DTD-0001'"
        )
    field = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())["b1_p.nama_sls"]
    assert field["value"] == "SUB SINTETIS"
    assert not field.get("reference_label")


def test_exact_reference_can_supply_label_when_assignment_name_is_blank(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute("UPDATE mart_assignment_tgr SET subsls=NULL WHERE assignment_id='DTD-0001'")
    field = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())["b1_p.nama_sls"]
    assert field["status"] == "ANSWERED" and field["value"] is None
    assert field["label"] == "RT 001 / RW 002"
