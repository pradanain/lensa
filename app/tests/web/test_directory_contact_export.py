"""Source-specific contact exports and the explicit Viewer disclosure policy."""

import sqlite3

import pytest

from se2026.common import sha256
from se2026.web.detail_access import full_address
from se2026.web.xlsx_export import MASKED_VALUE

from .synthetic import V1, V2
from .test_api import fields
from .test_xlsx_export import sheet


@pytest.mark.parametrize("source,aid", [("dtd", "DTD-0001"), ("ub", "UB-0001")])
def test_contact_export_exact_identity_address_maps_and_viewer_mask(portal, viewer, source, aid):
    _, admin, settings = portal
    nik, phone, mobile = "0012345678901234", "00555123", "008123456789"
    with sqlite3.connect(settings.census_db) as con:
        if source == "dtd":
            con.execute("UPDATE mart_usaha SET alamat_usaha='Jalan SINTETIS 10',geotag_latitude='2.125',geotag_longitude='117.25' WHERE assignment_id=? AND index1='001'", (aid,))
            con.execute("UPDATE mart_keluarga SET nik_kk='FAMILY_NIK_MUST_NOT_REPLACE_PJ' WHERE assignment_id=?", (aid,))
            con.execute("UPDATE mart_legalitas_usaha SET nama_pengusaha_pj='PJ SINTETIS TEPAT',nik_pengusaha_pj=?,nomor_telepon=?,nomor_hp_whatsapp=? WHERE assignment_id=? AND index1='001'", (nik, phone, mobile, aid))
            con.execute("INSERT INTO mart_legalitas_usaha(assignment_id,__version_normalized,index1,nama_pengusaha_pj,nik_pengusaha_pj,nomor_hp_whatsapp) VALUES(?,?,'002','WRONG VERSION','WRONG_NIK','WRONG_PHONE')", (aid, V2))
        else:
            con.execute("UPDATE mart_ub_a SET alamat_usaha='Jalan SINTETIS 10',nama_penanggung_jawab='PJ SINTETIS TEPAT',nik_penanggung_jawab=?,nomor_hp_usaha=?,link_google_maps='https://www.google.com/maps/search/?query=2.125,117.25' WHERE assignment_id=?", (nik, mobile, aid))
    before = sha256(settings.census_db)
    body = {"source": source, "q": aid, "page_size": 1, "page": 2}
    for user in [admin, viewer]:
        workbook = sheet(user.post(f"/api/v1/directories/businesses/export", json=body))
        records = [dict(zip(next(workbook.values), row)) for row in list(workbook.values)[1:]]
        exact = next(row for row in records if source == "ub" or row["Roster"] == "001")
        assert exact["Penanggung Jawab"] == "PJ SINTETIS TEPAT"
        assert not any("NIK" in name for name in exact)
        assert nik not in str(records)
        assert exact["Nomor HP"] == mobile
        if source == "dtd":
            assert exact["Nomor telepon"] == phone
            other = next(row for row in records if row["Roster"] == "002")
            assert other["Nomor HP"] in (None, "")
        assert exact["Alamat usaha"] == "Jalan SINTETIS 10"
        assert "Desa/Kelurahan" in exact["Alamat lengkap"]
        assert "Kecamatan" in exact["Alamat lengkap"]
        assert exact["Latitude"] == "2.125"
        assert exact["Google Maps"] == "https://www.google.com/maps/search/?api=1&query=2.125,117.25"
        for name in ["Nomor HP"]:
            column = next(workbook.values).index(name) + 1
            assert all(workbook.cell(i, column).data_type == "s" for i in range(2, workbook.max_row + 1))
        assert "WRONG_PHONE" not in str(records) and "WRONG_NIK" not in str(records)
        api_rows = user.post("/api/v1/directories/businesses/search", json={**body, "page": 1, "page_size": 100}).json()["rows"]
        if user is viewer:
            assert all(row["person_in_charge_nik"] is None for row in api_rows)
            assert nik not in str(api_rows)
    assert sha256(settings.census_db) == before


def test_ambiguous_business_identity_is_not_selected_or_multiplied(portal, viewer):
    _, _, settings = portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute("INSERT INTO mart_legalitas_usaha SELECT * FROM mart_legalitas_usaha WHERE assignment_id='DTD-0001' AND index1='001'")
        con.execute("UPDATE mart_legalitas_usaha SET nomor_hp_whatsapp='AMBIGUOUS_PHONE' WHERE assignment_id='DTD-0001'")
    rows = viewer.post("/api/v1/directories/businesses/search", json={"source": "dtd", "q": "DTD-0001", "page_size": 100}).json()["rows"]
    assert len(rows) == len({row["record_key"] for row in rows}) == 2
    assert all(row["business_mobile"] is None for row in rows)
    assert "AMBIGUOUS_PHONE" not in str(rows)


@pytest.mark.parametrize("scope", ["families", "members"])
def test_family_and_member_exports_include_source_street_for_viewer(portal, viewer, scope):
    _, _, settings = portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute("UPDATE mart_keluarga SET alamat_keluarga='Jalan SINTETIS 20' WHERE assignment_id='DTD-0001' AND __version_normalized=?", (V1,))
    workbook = sheet(viewer.post(f"/api/v1/directories/{scope}/export", json={"q": "DTD-0001"}))
    rows = [dict(zip(next(workbook.values), row)) for row in list(workbook.values)[1:]]
    assert rows and all(row["Alamat keluarga"] == "Jalan SINTETIS 20" for row in rows)
    assert all(row["Alamat lengkap"].startswith("Jalan SINTETIS 20, Desa/Kelurahan ") for row in rows)
    assert all(row["Nomor KK"] == MASKED_VALUE for row in rows)


def test_viewer_form_reads_contact_and_maps_but_keeps_nik_private(portal, viewer):
    _, _, settings = portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute("UPDATE mart_legalitas_usaha SET nik_pengusaha_pj='PRIVATE_PJ_NIK',nomor_telepon='00555123',nomor_hp_whatsapp='008123456789' WHERE assignment_id='DTD-0001'")
        con.execute("UPDATE mart_usaha SET alamat_usaha='Jalan SINTETIS 10',geotag_latitude='2.125',geotag_longitude='117.25' WHERE assignment_id='DTD-0001'")
    response = viewer.get("/api/v1/questionnaires/dtd/DTD-0001", params={"version": V1, "business": "001"})
    form = response.json()
    answers = fields(form)
    assert answers["blokl.nik_pengusaha"]["status"] == "RESTRICTED"
    assert "PRIVATE_PJ_NIK" not in response.text
    assert answers["blokl.no_telp"]["value"] == "00555123"
    assert answers["blokl.hp"]["value"] == "008123456789"
    assert answers["blokl.alamat_usaha_var"]["value"] == "Jalan SINTETIS 10"
    assert form["locations"]["business"]["latitude"] == "2.125"


def test_full_address_keeps_source_and_never_invents_streets():
    assert full_address(None, "DESA SINTETIS", "KECAMATAN SINTETIS") is None
    assert full_address("Jalan 10, Desa SINTETIS", "Desa SINTETIS", None) == "Jalan 10, Desa SINTETIS"
    assert full_address("Jalan 10", None, None) == "Jalan 10"
