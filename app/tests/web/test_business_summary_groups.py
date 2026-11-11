import sqlite3

from se2026.analytics import Analytics
from se2026.common import sha256


def test_summary_groups_count_units_and_keep_unclassified_without_double_count(portal):
    _,client,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        # Default synthetic parents overlap. Make explicit mutually exclusive paths.
        con.execute("DELETE FROM mart_bku WHERE assignment_id IN ('DTD-0001','DTD-0003')")
        con.execute("DELETE FROM mart_keluarga WHERE assignment_id NOT IN ('DTD-0001','DTD-0003')")
        con.execute("UPDATE mart_bku SET kode_penggunaan_bangunan='1'")
        con.execute("UPDATE mart_bku SET kode_penggunaan_bangunan='6' WHERE assignment_id='DTD-0004'")
        # A parent at another questionnaire version must not be filled forward.
        con.execute("UPDATE mart_keluarga SET __version_normalized='2025-01-01T00:00:00.000000' WHERE assignment_id='DTD-0003'")
    before=sha256(settings.census_db)
    with Analytics(settings.census_db) as api:
        def count(mid):return api._query(mid)[1][0]['value']
        assert count('usaha.enumerated_family_count')==2  # two rosters, one family
        assert count('usaha.enumerated_bku_count')==9
        assert count('usaha.enumerated_unclassified_count')==2  # wrong version and non-target
        assert sum(count('usaha.enumerated_'+name+'_count') for name in ('family','bku','unclassified'))==count('usaha.enumerated_count')==13
        assert api.query('usaha.enumerated_family_count')['rows'][0]['value'] is None
    summary=client.get('/api/v1/analytics/summary').json()
    assert summary['counts']['usaha.enumerated_bku_count'][0]['value']==9
    assert summary['counts']['usaha.enumerated_family_count'][0]['value'] is None
    assert sha256(settings.census_db)==before
