import sqlite3

from se2026.analytics import Analytics
from se2026.common import sha256


def test_card_counts_only_completed_found_new_special_business_buildings(portal):
    _,client,settings=portal
    cases=[
        ('1','1','APPROVED BY Pengawas'),
        ('6','2','APPROVED BY Pengawas'),
        ('1','2','COMPLETED BY Admin Kabupaten'),
        ('1','3','APPROVED BY Pengawas'),
        ('1','1','DRAFT'),
        ('7','2','APPROVED BY Pengawas'),
        (None,'1','APPROVED BY Pengawas'),
        ('1','0','APPROVED BY Pengawas'),
        ('1','4','APPROVED BY Pengawas'),
        ('1','7','APPROVED BY Pengawas'),
        ('4','2','APPROVED BY Pengawas'),
        ('1','1','REVOKED BY Pengawas'),
    ]
    with sqlite3.connect(settings.census_db) as con:
        for n,(usage,status,workflow) in enumerate(cases,1):
            aid='DTD-'+str(n).zfill(4)
            con.execute('UPDATE mart_bku SET kode_penggunaan_bangunan=?,kode_keberadaan_bku=? WHERE assignment_id=?',(usage,status,aid))
            con.execute('UPDATE mart_assignment_tgr SET status_assignment=? WHERE assignment_id=?',(workflow,aid))
    before=sha256(settings.census_db)
    with Analytics(settings.census_db) as api:
        # DTD-0001 has two business children, but its building contributes once.
        assert api._query('bku.business_enumerated_count')[1][0]['value']==2
        assert api._query('bku.business_enumerated_count',filters={'kecamatan':'6502010'})[1][0]['value']==2
        assert api._query('bku.business_enumerated_count',filters={'kecamatan':'6502000'})[1][0]['value']==0
        assert api.query('bku.business_enumerated_count')['rows'][0]['suppressed']
        assert api.query('bku.business_enumerated_count')['rows'][0]['value'] is None
        assert api.query('bku.count')['rows'][0]['value']==12
    summary=client.get('/api/v1/analytics/summary').json()
    assert 'bku.business_enumerated_count' in summary['counts']
    assert summary['counts']['bku.business_enumerated_count'][0]['value'] is None
    assert summary['counts']['bku.count'][0]['value']==12
    assert sha256(settings.census_db)==before
