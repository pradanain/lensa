import sqlite3

from se2026.analytics import Analytics
from se2026.common import sha256


def test_enumerated_count_filters_status_workflow_without_multiplying_grain(portal):
    app, client, settings = portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute("UPDATE mart_assignment_tgr SET status_assignment='DRAFT'")
        con.execute(
            "UPDATE mart_assignment_tgr SET status_assignment='APPROVED BY Pengawas' WHERE assignment_id='DTD-0001'"
        )
        con.execute(
            "UPDATE mart_assignment_tgr SET status_assignment='COMPLETED BY Admin Kabupaten' WHERE assignment_id IN ('DTD-0002','DTD-0003')"
        )
        con.execute("UPDATE mart_usaha SET kode_keberadaan_usaha='2' WHERE assignment_id='DTD-0002'")
        con.execute("UPDATE mart_usaha SET kode_keberadaan_usaha='3' WHERE assignment_id='DTD-0003'")
        con.execute("UPDATE mart_assignment_ub SET status_assignment='DRAFT'")
        con.execute(
            "UPDATE mart_assignment_ub SET status_assignment='APPROVED BY Pengawas' WHERE assignment_id IN ('UB-0001','UB-0002')"
        )
        con.execute(
            "UPDATE mart_ub_integrated SET status_keberadaan='2. Ditemukan tetapi bukan cakupan survei' WHERE assignment_id='UB-0002'"
        )
        con.execute(
            "UPDATE mart_ub_a SET status_keberadaan='2. Ditemukan tetapi bukan cakupan survei' WHERE assignment_id='UB-0002'"
        )
    baseline = sha256(settings.census_db)
    with Analytics(settings.census_db) as api:
        # Two roster records on DTD-0001, one new business on DTD-0002.
        total = api._query("usaha.enumerated_count")[1][0]["value"]
        assert api.query("usaha.enumerated_count")["rows"][0]["value"] is None
        assert total == 3
        assert api._query("ub.enumerated_count")[1][0]["value"] == 1
        assert api.query("ub.enumerated_count")["rows"][0]["value"] is None
        assert api.query("usaha.count")["rows"][0]["value"] == 13
        grouped = api.query("usaha.enumerated_count", group_by="status")
        assert all(row["value"] is None for row in grouped["rows"])  # small cells stay protected
    result = client.post(
        "/api/v1/directories/businesses/search",
        json={"source": "dtd", "enumerated_only": True, "page_size": 100},
    ).json()
    assert result["total"] == total
    assert len({row["record_key"] for row in result["rows"]}) == total
    assert {row["assignment_id"] for row in result["rows"]} == {"DTD-0001", "DTD-0002"}
    assert sha256(settings.census_db) == baseline


def test_new_completed_businesses_without_scale_stay_in_operational_total(portal):
    _,client,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute('DELETE FROM mart_bku')
        con.execute("UPDATE mart_usaha SET skala_usaha='UMKM',nama_pengusaha_pj=NULL,alamat_usaha=NULL,code_identity=NULL")
        con.execute('UPDATE mart_legalitas_usaha SET nib=NULL')
        con.execute("UPDATE mart_usaha SET skala_usaha=NULL,kode_keberadaan_usaha='2' WHERE assignment_id='DTD-0001'")
    before=sha256(settings.census_db)
    with Analytics(settings.census_db) as api:
        assert api._query('usaha.enumerated_count')[1][0]['value']==13
        assert api._query('usaha.qualified_count')[1][0]['value']==11
    completed=client.post('/api/v1/directories/businesses/search',json={'source':'dtd','enumerated_only':True,'page_size':100}).json()
    assert completed['total']==13
    assert sum(r['assignment_id']=='DTD-0001' for r in completed['rows'])==2
    tree=client.get('/api/v1/kbli/tree?enumerated_only=true&level=2&prefix=01').json()
    assert tree['population']=='ENUMERATED_SOURCE_RECORDS'
    assert tree['rows'][0]['dtd_units']==10  # the three unavailable/non-reference codes remain separate
    assert sha256(settings.census_db)==before
