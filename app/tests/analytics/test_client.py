import json
import sqlite3
from decimal import Decimal

import pytest

from se2026.analytics import Analytics
from se2026.analytics.registry import AnalyticsError
from se2026.common import sha256


def test_denominator_excludes_missing_and_uses_aggregated_components(analytical_db):
    with Analytics(analytical_db) as api:
        metric,rows=api._query('usaha.internet_yes_rate')
        assert rows[0]['eligible_rows']==12
        assert rows[0]['numerator']==5 and rows[0]['denominator']==10
        assert rows[0]['percentage']=='50.000000'
        assert api.query('usaha.internet_yes_rate')['rows'][0]['value']=='50.000000'


def test_rosters_preaggregate_before_join_and_never_force_a_version(analytical_db):
    con=sqlite3.connect(analytical_db)
    con.execute("INSERT INTO mart_anggota(assignment_id,__version_normalized,index1,__row_id) VALUES('TGR-0','v2','999','99')")
    con.commit();con.close()
    with Analytics(analytical_db) as api:
        assert api._query('family_rosters.count')[1][0]['numerator']==12
        assert Decimal(api._query('family_rosters.anggota_linked_rows')[1][0]['numerator'])==14
        assert Decimal(api._query('family_rosters.meteran_linked_rows')[1][0]['numerator'])==13
        assert Decimal(api._query('family_rosters.usaha_linked_rows')[1][0]['numerator'])==13


def test_unknown_geography_retained_and_public_small_cells_suppressed(analytical_db):
    with Analytics(analytical_db) as api:
        raw=api._query('usaha.count',group_by='kecamatan')[1]
        assert sum(row['numerator'] for row in raw)==13
        unknown=[r for r in raw if r['dimensions']['kecamatan']['geo_status']=='SPECIAL_ZERO_SEGMENT']
        assert unknown[0]['numerator']==2
        public=api.query('usaha.count',group_by='kecamatan')
        assert len(public['rows'])==2 and all(r['suppressed'] for r in public['rows'])
        text=json.dumps(public)
        assert 'TGR-0' not in text and 'TGR-1' not in text


def test_filters_are_bound_and_identifiers_whitelisted(analytical_db):
    before=sha256(analytical_db)
    with Analytics(analytical_db) as api:
        row=api.query('usaha.count',filters={'status':"1' OR 1=1 --"})['rows'][0]
        assert row['eligible_rows']==0
        with pytest.raises(AnalyticsError,match='DIMENSION_NOT_ALLOWED'):api.query('usaha.count',group_by='nama_usaha')
        with pytest.raises(AnalyticsError):api.query('usaha.count',filters={'status); DROP TABLE mart_usaha;--':'1'})
        with pytest.raises(AnalyticsError,match='METRIC_NOT_ALLOWED'):api.query('usaha.count; DELETE FROM mart_usaha')
        with pytest.raises(sqlite3.OperationalError):api._connection.execute('DELETE FROM mart_usaha')
    assert sha256(analytical_db)==before


def test_duplicate_geography_master_is_rejected_before_join(analytical_db):
    con=sqlite3.connect(analytical_db)
    con.execute('INSERT INTO mart_assignment_tgr SELECT * FROM mart_assignment_tgr LIMIT 1')
    con.commit();con.close()
    with Analytics(analytical_db) as api:
        with pytest.raises(AnalyticsError,match='SOURCE_GRAIN_NOT_UNIQUE'):api.query('usaha.count',group_by='desa')


def test_worker_sum_only_uses_valid_paired_integer_responses(analytical_db):
    con=sqlite3.connect(analytical_db)
    con.execute("UPDATE mart_program_usaha SET pekerja_laki_laki=NULL WHERE assignment_id='TGR-0'")
    con.commit();con.close()
    with Analytics(analytical_db) as api:
        row=api._query('usaha.workers_total_valid')[1][0]
        assert row['numerator']=='55' and row['denominator']==11 and row['excluded_rows']==1
        assert api._query('usaha.workers_mean_valid')[1][0]['value']=='5.000000'


def test_response_geography_is_distinct_and_has_no_sls_inference(analytical_db):
    with Analytics(analytical_db) as api:
        result=api._query('ub.count',group_by='desa',location='response')[1]
        assert len(result)==1 and result[0]['numerator']==12
        geography=result[0]['dimensions']['desa']
        assert geography['concept']=='response' and geography['raw_codes']['kode_kecamatan'] is None
        with pytest.raises(AnalyticsError,match='RESPONSE_GEOGRAPHY_NOT_AVAILABLE'):api.query('ub.count',group_by='sls',location='response')


def test_registry_checks_every_definition_against_synthetic_schemas(analytical_db):
    with Analytics(analytical_db) as api:
        assert api.validate_definitions()==97


def test_numeric_small_valid_cohort_is_suppressed_even_when_module_is_large(analytical_db):
    con=sqlite3.connect(analytical_db)
    con.execute("UPDATE mart_program_usaha SET pekerja_laki_laki=NULL WHERE assignment_id NOT IN ('TGR-0','TGR-1')")
    con.commit();con.close()
    with Analytics(analytical_db) as api:
        raw=api._query('usaha.workers_total_valid')[1][0]
        assert raw['eligible_rows']==12 and raw['denominator']==2
        public=api.query('usaha.workers_total_valid')['rows'][0]
        assert public['suppressed'] and public['value'] is None and public['denominator'] is None


def test_empty_worker_cohort_is_null_not_a_zero_measure(analytical_db):
    con=sqlite3.connect(analytical_db)
    con.execute('UPDATE mart_program_usaha SET pekerja_laki_laki=NULL')
    con.commit();con.close()
    with Analytics(analytical_db) as api:
        row=api._query('usaha.workers_total_valid')[1][0]
        assert row['denominator']==0 and row['numerator'] is None and row['value'] is None


def test_narrow_social_presence_keeps_a_different_version_as_a_separate_key(analytical_db):
    con=sqlite3.connect(analytical_db)
    con.execute("INSERT INTO clean_p1_pekerjaan VALUES(999,2,?,1,0,'TGR-0','v2','001')",(b'new-version',))
    con.commit();con.close()
    with Analytics(analytical_db) as api:
        row=api._query('sosial_details.sosial_p0_coverage')[1][0]
        assert row['eligible_rows']==13 and row['numerator']==12
        assert api._query('sosial_details.p1_pekerjaan_coverage')[1][0]['numerator']==13
