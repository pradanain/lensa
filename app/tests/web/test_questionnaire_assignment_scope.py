import sqlite3

import pytest
from se2026.common import sha256
from se2026.web.questionnaire import Questionnaires
from se2026.web.references import References

from .synthetic import ROOT, V1, V2, prepare_questionnaire_scope_cases
from .test_api import fields


@pytest.fixture
def scoped(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        prepare_questionnaire_scope_cases(con)
    return portal


@pytest.mark.parametrize(
    "aid,kind,number,source",
    [
        ("DTD-0002", "KELUARGA", "0010", "mart_keluarga"),
        ("DTD-0003", "BKU", "0007", "mart_bku"),
    ],
)
def test_common_building_fields_and_business_fields_use_exact_parent(scoped, aid, kind, number, source):
    before = sha256(scoped[2].census_db)
    result = scoped[1].get("/api/v1/questionnaires/dtd/" + aid, params={"version": V1}).json()
    assert result["assignment_context"]["kind"] == kind
    answer = fields(result)
    assert answer["b5.no_bang"]["value"] == number
    assert answer["b5.no_bang"]["source_object"] == source
    assert answer["b5.kode_bang"]["status"] == "ANSWERED"
    assert answer["b5.jalan_domisili"]["source_object"] == source
    assert answer["b5.jalan_domisili"]["status"] == "ANSWERED"
    for key in (
        "nama_usaha",
        "pengusaha",
        "jk",
        "umur",
        "nik_pengusaha",
        "kbli",
        "tk_laki",
        "total_pendapatan",
    ):
        # Consolidated PJ projections are shared even though the raw template has separate widgets.
        field = answer["blokl." + key]
        assert field["applicability"] == "APPLICABLE"
        assert field["status"] == "ANSWERED"
    assert answer["blokl.pengusaha"]["value"] == "PJ SINTETIS BERSAMA"
    assert sha256(scoped[2].census_db) == before


def test_family_only_blocks_and_bku_only_identity_are_explicit(scoped):
    for aid, kind in (("DTD-0002", "KELUARGA"), ("DTD-0003", "BKU")):
        form = scoped[1].get("/api/v1/questionnaires/dtd/" + aid, params={"version": V1}).json()
        sections = {s["section_id"]: s for s in form["sections"]}
        answers = fields(form)
        family_state = "APPLICABLE" if kind == "KELUARGA" else "NOT_APPLICABLE"
        bku_state = "APPLICABLE" if kind == "BKU" else "NOT_APPLICABLE"
        for block in ("b_ak", "b_ak_lanjutan", "b_perumahan"):
            assert sections[block]["applicability"] == family_state
        for question in ("b5.no_kk", "b5.nama_kk", "b5.ada_keluarga", "b5.usaha_online"):
            assert answers[question]["applicability"] == family_state
        for question in ("b5.nama_usaha_bang", "b5.ada_bang_usaha"):
            assert answers[question]["applicability"] == bku_state
        assert sections["blokl"]["applicability"] == "APPLICABLE"
        assert answers["blokl.jenis_usaha"]["applicability"] == family_state
        if kind == "KELUARGA":
            assert answers["b5.alamat_prelist"]["status"] == "NOT_EXPORTED"


def test_unknown_root_is_not_guessed_from_business_or_missing_family(scoped):
    form = scoped[1].get("/api/v1/questionnaires/dtd/DTD-0004", params={"version": V1}).json()
    assert form["assignment_context"]["kind"] == "UNKNOWN"
    assert form["assignment_context"]["status"] == "ROOT_NOT_AVAILABLE"
    assert all(s["applicability"] != "NOT_APPLICABLE" for s in form["sections"])
    assert fields(form)["blokl.nama_usaha"]["status"] == "ANSWERED"
    assert fields(form)["b5.no_bang"]["value"] is None


def test_scope_and_common_fields_do_not_cross_questionnaire_versions(scoped):
    current = scoped[1].get("/api/v1/questionnaires/dtd/DTD-0005", params={"version": V2}).json()
    old = scoped[1].get("/api/v1/questionnaires/dtd/DTD-0005", params={"version": V1}).json()
    assert current["assignment_context"]["kind"] == "BKU"
    assert old["assignment_context"]["kind"] == "KELUARGA"
    assert fields(current)["b5.no_bang"]["value"] == "0009"
    assert fields(current)["b5.no_bang"]["provenance"]["__version_normalized"] == V2
    assert fields(current)["b5.no_kk"]["status"] == "UNMATCHED_VERSION"
    assert fields(current)["b5.no_kk"]["value"] is None
    assert fields(old)["blokl.nama_usaha"]["status"] == "UNMATCHED_VERSION"


def test_mixed_roots_preserve_both_scopes_and_do_not_pick_conflicting_value(scoped):
    with sqlite3.connect(scoped[2].census_db) as con:
        con.execute("UPDATE mart_keluarga SET nomor_bangunan='0010' WHERE assignment_id='DTD-0001'")
        con.execute("UPDATE mart_bku SET nomor_bangunan='0007' WHERE assignment_id='DTD-0001'")
    form = scoped[1].get("/api/v1/questionnaires/dtd/DTD-0001", params={"version": V1}).json()
    assert form["assignment_context"]["kind"] == "KELUARGA_BKU"
    assert all(s["applicability"] != "NOT_APPLICABLE" for s in form["sections"])
    number = fields(form)["b5.no_bang"]
    assert number["source_conflict"]
    assert number["status"] == "UNVERIFIED_MAPPING" and number["value"] is None
    assert {r["source_object"] for r in number["source_candidates"]} == {"mart_keluarga", "mart_bku"}


def test_bku_with_orphan_family_module_keeps_family_scope(scoped):
    with sqlite3.connect(scoped[2].census_db) as con:
        con.execute("DELETE FROM mart_keluarga WHERE assignment_id='DTD-0001'")
    form = scoped[1].get("/api/v1/questionnaires/dtd/DTD-0001", params={"version": V1}).json()
    assert form["assignment_context"]["kind"] == "KELUARGA_BKU"
    assert next(s for s in form["sections"] if s["section_id"] == "b_ak")["applicability"] == "APPLICABLE"


def test_viewer_reads_shared_address_variants_but_not_nik(scoped, analyst):
    for aid in ("DTD-0002", "DTD-0003"):
        response = analyst.get("/api/v1/questionnaires/dtd/" + aid, params={"version": V1})
        answer = fields(response.json())
        assert answer["b5.jalan_domisili"]["status"] == "ANSWERED"
        assert answer["b5.jalan_domisili"]["value"] is not None
        assert answer["b5.nik"]["status"] == "RESTRICTED"
        assert "SYNTHETIC_PRIVATE_NIK" not in response.text


def test_alternate_source_schema_is_checked_at_startup(scoped):
    with sqlite3.connect(scoped[2].census_db) as con:
        con.execute("ALTER TABLE mart_bku RENAME COLUMN nomor_bangunan TO unexpected_column")
    with pytest.raises(ValueError, match="QUESTIONNAIRE_SCHEMA_DRIFT"):
        Questionnaires(scoped[2], References(ROOT))
