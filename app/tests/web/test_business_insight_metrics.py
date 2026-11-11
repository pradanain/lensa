import sqlite3

import pytest

from se2026.analytics import Analytics
from se2026.analytics.numeric import worker_band
from se2026.common import sha256


@pytest.mark.parametrize('male,female,total,flag,expected',[
    ('0','0','0','SESUAI','ZERO'),('2','2','4','SESUAI','ONE_FOUR'),
    ('2','3','5','SESUAI','FIVE_NINETEEN'),('9','10','19',None,'FIVE_NINETEEN'),
    ('10','10','20',None,'TWENTY_NINETYNINE'),('50','49','99',None,'TWENTY_NINETYNINE'),
    ('50','50','100',None,'HUNDRED_PLUS'),(None,'1','1',None,'UNAVAILABLE'),
    ('1','1','3',None,'UNAVAILABLE'),('1','1','2','UNVERIFIED','UNAVAILABLE'),
    ('-1','2','1',None,'UNAVAILABLE'),('0.5','0.5','1',None,'UNAVAILABLE'),
])
def test_worker_intervals_preserve_invalid_missing_and_zero(male,female,total,flag,expected):
    assert worker_band(male,female,total,flag)==expected


def test_worker_sources_keep_cohort_version_and_grain(portal):
    _,client,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute("UPDATE mart_assignment_tgr SET status_assignment='DRAFT'")
        con.execute("UPDATE mart_assignment_tgr SET status_assignment='APPROVED BY Pengawas' WHERE assignment_id IN ('DTD-0001','DTD-0002','DTD-0003')")
        con.execute("UPDATE mart_usaha SET kode_keberadaan_usaha='3' WHERE assignment_id='DTD-0003'")
        con.execute("UPDATE mart_program_usaha SET __version_normalized='2026-09-02T00:00:00.000000' WHERE assignment_id='DTD-0002'")
        # Two eligible roster children on one parent do not multiply the one linked response.
    with Analytics(settings.census_db) as api:
        metric,rows=api._query('usaha.completed_workers_total')
        assert rows[0]['value']=='5' and rows[0]['denominator']==1
        assert api._query('usaha.completed_worker_bands')[1][0]['value']==1
        assert api.query('usaha.completed_workers_total')['rows'][0]['value'] is None
    # UB retains ID-only matching despite an unrelated version label.
    with sqlite3.connect(settings.census_db) as con:
        con.execute("UPDATE mart_ub_b SET __version_normalized='different-historical-version'")
    baseline=sha256(settings.census_db)
    with Analytics(settings.census_db) as api:
        assert api._query('ub.completed_workers_total')[1][0]['denominator']==12
    response=client.post('/api/v1/analytics/query',json={'metric_id':'usaha.completed_worker_bands'}).json()
    assert all(row['value'] is None for row in response['rows'])
    assert sha256(settings.census_db)==baseline


def test_substantive_yes_no_rates_exclude_missing_and_skip(portal):
    _,_,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute('UPDATE mart_legalitas_usaha SET punya_nib=NULL')
        con.execute("UPDATE mart_legalitas_usaha SET punya_nib='1' WHERE assignment_id IN ('DTD-0001','DTD-0002','DTD-0003','DTD-0004','DTD-0005')")
        con.execute("UPDATE mart_legalitas_usaha SET punya_nib='2' WHERE assignment_id IN ('DTD-0006','DTD-0007')")
        con.execute("UPDATE mart_digital_usaha SET kode_menggunakan_internet='2',internet_promosi='1'")
        con.execute("UPDATE mart_digital_usaha SET kode_menggunakan_internet='1',internet_promosi='1' WHERE assignment_id IN ('DTD-0001','DTD-0002','DTD-0003','DTD-0004','DTD-0005','DTD-0006')")
        con.execute("UPDATE mart_digital_usaha SET internet_promosi='2' WHERE assignment_id='DTD-0005'")
        con.execute("UPDATE mart_digital_usaha SET internet_promosi=NULL WHERE assignment_id='DTD-0006'")
    before=sha256(settings.census_db)
    with Analytics(settings.census_db) as api:
        nib=api._query('usaha.completed_nib_rate')[1][0]
        assert nib['numerator']==5 and nib['denominator']==7 and nib['eligible_rows']==12
        assert api.query('usaha.completed_nib_rate')['rows'][0]['value'] is None  # complement 2 is small
        promotion=api._query('usaha.completed_promotion_rate')[1][0]
        assert promotion['eligible_rows']==6 and promotion['denominator']==5 and promotion['numerator']==4
    assert sha256(settings.census_db)==before


def test_economic_periods_and_coverage_are_not_money_totals(portal):
    _,_,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute('UPDATE mart_ekonomi_tahunan SET total_pendapatan_2025=NULL')
        con.execute("UPDATE mart_ekonomi_tahunan SET total_pendapatan_2025='0' WHERE assignment_id='DTD-0001'")
    with Analytics(settings.census_db) as api:
        annual=api._query('usaha.annual_income_coverage')[1][0]
        assert annual['numerator']==1 and annual['denominator']==12  # zero is an explicit recorded answer
        assert api.registry.get('usaha.annual_income_coverage')['period']!=api.registry.get('usaha.monthly_income_coverage')['period']
        assert api.registry.get('usaha.annual_income_coverage')['kind']=='rate'
