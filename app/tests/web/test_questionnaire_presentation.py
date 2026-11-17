import sqlite3

import pytest
from se2026.common import sha256
from se2026.web.questionnaire import template_choice_label

from .synthetic import V1, V2, prepare_questionnaire_presentation_cases
from .test_api import fields


def test_static_choices_restore_labels_and_keep_codes_and_database(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        prepare_questionnaire_presentation_cases(con)
    before = sha256(portal[2].census_db)
    answers = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0002").json())
    for key, value, label in [
        ("tidak_nib", "4", "4. Tidak tahu tentang NIB"),
        ("badan_usaha", "13", "13. Bukan Badan Usaha"),
        ("lap_keuangan", "2", "2. Tidak"),
    ]:
        assert answers["blokl." + key]["value"] == value
        assert answers["blokl." + key]["label"] == label
        assert answers["blokl." + key]["label_status"] == "TEMPLATE"
    assert answers["blokl.tahun_operasi"]["display_format"] == "text"
    assert sha256(portal[2].census_db) == before


def test_choice_codes_keep_leading_zeros_and_unknown_codes_are_not_guessed(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_legalitas_usaha SET badan_usaha='01a',alasan_tidak_punya_nib='99' WHERE assignment_id='DTD-0001'"
        )
    answer = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())
    assert answer["blokl.badan_usaha"]["value"] == "01a"
    assert "Perseroan" in answer["blokl.badan_usaha"]["label"]
    assert answer["blokl.tidak_nib"]["label"] is None
    assert answer["blokl.tidak_nib"]["label_status"] == "UNRECOGNIZED_CODE"


def test_source_labels_take_priority_and_multi_choices_require_every_code():
    schema = {"choices": {"1": "1. Ya", "2": "2. Tidak"}}
    assert template_choice_label(schema, "1", "Label sumber") == ("Label sumber", "SOURCE")
    assert template_choice_label(schema, '["1","2"]', None) == ("1. Ya; 2. Tidak", "TEMPLATE_MULTI")
    assert template_choice_label(schema, '["1","99"]', None)[0] is None
    assert template_choice_label(schema, "1. Ya", None) == ("1. Ya", "SOURCE")
    assert template_choice_label(schema, "Ya", None) == (None, "SOURCE_TEXT")


def test_asset_range_is_a_label_rather_than_a_decimal(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_ekonomi_tahunan SET rentang_aset_2025='3. Lebih dari Rp 1 miliar s.d. Rp 5 miliar' WHERE assignment_id='DTD-0001'"
        )
    field = fields(portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json())["blokl.rentang_aset_thn"]
    assert field["converter"] == "text" and field["parse_status"] is None
    assert field["status"] == "ANSWERED" and field["label_status"] == "SOURCE"
    assert not field.get("unit")


def test_tagging_uses_exact_business_roster_and_version(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_usaha SET geotag_latitude='1.25',geotag_longitude='100.5' WHERE assignment_id='DTD-0001' AND index1='001'"
        )
        con.execute(
            "UPDATE mart_usaha SET geotag_latitude='2.25',geotag_longitude='101.75' WHERE assignment_id='DTD-0001' AND index1='002'"
        )
    first = (
        portal[1]
        .get("/api/v1/questionnaires/dtd/DTD-0001", params={"version": V1, "business": "001"})
        .json()["locations"]["business"]
    )
    second = (
        portal[1]
        .get("/api/v1/questionnaires/dtd/DTD-0001", params={"version": V1, "business": "002"})
        .json()["locations"]["business"]
    )
    assert first["latitude"] == "1.25" and second["latitude"] == "2.25"
    assert first["provenance"] == "QUESTIONNAIRE_ROOT_TAG"
    unmatched = (
        portal[1]
        .get("/api/v1/questionnaires/dtd/DTD-0001", params={"version": V2})
        .json()["locations"]["business"]
    )
    assert unmatched == {"status": "UNMATCHED_VERSION"}


def test_root_coordinate_conflict_and_duplicate_business_are_not_selected(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_keluarga SET geotag_latitude='1.25',geotag_longitude='100.5' WHERE assignment_id='DTD-0001'"
        )
        con.execute(
            "UPDATE mart_bku SET geotag_latitude='2.25',geotag_longitude='101.75' WHERE assignment_id='DTD-0001'"
        )
        con.execute(
            "INSERT INTO mart_usaha SELECT * FROM mart_usaha WHERE assignment_id='DTD-0001' AND index1='001'"
        )
    locations = portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json()["locations"]
    assert locations["root"] == {"status": "SOURCE_CONFLICT"}
    assert locations["business"] == {"status": "SOURCE_CONFLICT"}


def test_coordinate_precision_alone_does_not_create_a_conflict(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_keluarga SET geotag_latitude='1.25',geotag_longitude='100.5' WHERE assignment_id='DTD-0001'"
        )
        con.execute(
            "UPDATE mart_bku SET geotag_latitude='1.2500',geotag_longitude='100.500' WHERE assignment_id='DTD-0001'"
        )
    location = portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json()["locations"]["root"]
    assert location["status"] == "AVAILABLE"


@pytest.mark.parametrize("lat,lon", [("91", "100"), ("NaN", "100"), ("0", "0"), ("1", "181")])
def test_invalid_coordinates_never_become_map_links(portal, lat, lon):
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_usaha SET geotag_latitude=?,geotag_longitude=? WHERE assignment_id='DTD-0001'",
            (lat, lon),
        )
    location = portal[1].get("/api/v1/questionnaires/dtd/DTD-0001").json()["locations"]["business"]
    assert location == {"status": "UNAVAILABLE"}


def test_analyst_receives_no_coordinate_or_map_link(portal, analyst):
    with sqlite3.connect(portal[2].census_db) as con:
        prepare_questionnaire_presentation_cases(con)
    for system, aid in [("dtd", "DTD-0002"), ("ub", "UB-0002")]:
        location = analyst.get("/api/v1/questionnaires/" + system + "/" + aid).json()["locations"]
        assert location == {"root": {"status": "RESTRICTED"}, "business": {"status": "RESTRICTED"}}


def test_ub_reads_exported_coordinates_without_trusting_arbitrary_urls(portal):
    with sqlite3.connect(portal[2].census_db) as con:
        prepare_questionnaire_presentation_cases(con)
    location = portal[1].get("/api/v1/questionnaires/ub/UB-0002").json()["locations"]["root"]
    assert location["latitude"] == "2.25" and location["longitude"] == "101.75"
    with sqlite3.connect(portal[2].census_db) as con:
        con.execute(
            "UPDATE mart_ub_a SET link_google_maps='https://example.invalid/maps/search/?query=2.25,101.75' WHERE assignment_id='UB-0002'"
        )
    assert portal[1].get("/api/v1/questionnaires/ub/UB-0002").json()["locations"]["root"] == {
        "status": "UNAVAILABLE"
    }
