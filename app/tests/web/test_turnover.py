"""Synthetic integration checks across registry, filtering, forms and export."""
from io import BytesIO
import sqlite3

from openpyxl import load_workbook
import pytest

from se2026.analytics import Analytics
from se2026.analytics.turnover import classify, lookup, record
from se2026.common import sha256
from .synthetic import V1, V2


def configure(settings):
    with sqlite3.connect(settings.census_db) as con:
        con.execute('DELETE FROM mart_ekonomi_bulanan')
        con.execute('DELETE FROM mart_ekonomi_tahunan WHERE index1<>\'001\'')
        con.execute("UPDATE mart_ekonomi_tahunan SET tahun_mulai_operasi='2000',__key_valid='1',__conflict='0'")
        values = ['0','2000000000','2000000000.01','15000000000','15000000000.01',
                  '50000000000','50000000000.01',None,None,None,None,'-1']
        for n,value in enumerate(values,1):
            con.execute('UPDATE mart_ekonomi_tahunan SET pendapatan_utama_2025=? WHERE assignment_id=?',
                        (value,'DTD-'+str(n).zfill(4)))
        for n,value in [(8,'200000000'),(9,'1250000000'),(10,'0'),(11,None)]:
            con.execute('DELETE FROM mart_ekonomi_tahunan WHERE assignment_id=?',('DTD-'+str(n).zfill(4),))
            con.execute('INSERT INTO mart_ekonomi_bulanan '
                '(assignment_id,__version_normalized,index1,tahun_mulai_operasi,pendapatan_utama_bln,__key_valid,__conflict) '
                'VALUES(?,?,?,?,?,?,?)',('DTD-'+str(n).zfill(4),V1,'001','2026',value,'1','0'))
        con.execute("UPDATE mart_ub_b SET pendapatan_utama='3000000000',__version_normalized='unrelated-version'")


def search(client, **values):
    response = client.post('/api/v1/directories/businesses/search',json={'source':'dtd',**values})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('value,monthly,group,annual', [
    ('0',False,'MIKRO','0'),('2000000000',False,'MIKRO','2000000000'),
    ('2000000000.01',False,'KECIL','2000000000.01'),
    ('15000000000',False,'KECIL','15000000000'),
    ('50000000000',False,'MENENGAH','50000000000'),
    ('50000000000.01',False,'BESAR','50000000000.01'),
    ('200000000',True,'KECIL','2400000000'),
    (None,True,'UNAVAILABLE',None),('-1',True,'REVIEW',None),('1.000,00',True,'REVIEW',None),
])
def test_money_boundaries_and_monthly_estimate(value,monthly,group,annual):
    item=classify(value,monthly=monthly)
    assert item.group==group and item.annual==annual
    assert item.basis==('ESTIMATE_MONTHLY_X12' if monthly else 'REPORTED_ANNUAL')


def test_filter_precedes_pagination_and_matches_registry(portal):
    _,client,settings=portal
    configure(settings)
    before=sha256(settings.census_db)
    result=search(client,turnover_group='KECIL',page_size=1,page=2)
    assert result['total']==4 and result['pages']==4 and len(result['rows'])==1
    with Analytics(settings.census_db) as api:
        assert api._query('usaha.enumerated_count',filters={'turnover_group':'KECIL'})[1][0]['value']==4
        raw=api._query('usaha.turnover_distribution')[1]
        assert sum(row['value'] for row in raw)==13
        public=api.query('usaha.turnover_distribution')
        assert all(row['value'] is None and row['percentage'] is None for row in public['rows'])
    response=client.get('/api/v1/analytics/business-summary',params={'turnover_group':'KECIL'})
    assert response.status_code==200
    for metric in response.json()['counts']:
        expected=client.post('/api/v1/analytics/query',json={'metric_id':metric,'filters':{'turnover_group':'KECIL'}})
        assert response.json()['counts'][metric]==expected.json()['rows']
    assert sha256(settings.census_db)==before


def test_monthly_basis_and_form_use_the_same_exact_roster(portal):
    _,client,settings=portal
    configure(settings)
    data=search(client,turnover_group='KECIL',turnover_basis='ESTIMATE_MONTHLY_X12')
    assert data['total']==2
    row=next(r for r in data['rows'] if r['assignment_id']=='DTD-0008')
    assert row['turnover']['annual']=='2400000000' and row['turnover']['monthly']=='200000000'
    form=client.get('/api/v1/questionnaires/dtd/DTD-0008',params={'version':V1,'business':'001'}).json()
    assert form['turnover']==row['turnover']
    # Another roster on the same family has no financial module: never borrow by name/parent.
    second=next(r for r in search(client,q='USAHA SINTETIS KEDUA')['rows'] if r['index1']=='002')
    assert second['turnover']['group']=='UNAVAILABLE' and second['turnover']['annual'] is None


def test_versions_conflicts_missing_and_snapshot_invalidation(portal):
    _,_,settings=portal
    configure(settings)
    assert record(lookup(settings.census_db),'dtd','DTD-0002',V1,'001').group=='MIKRO'
    with sqlite3.connect(settings.census_db) as con:
        con.execute('UPDATE mart_ekonomi_tahunan SET __version_normalized=? WHERE assignment_id=?',(V2,'DTD-0002'))
        con.execute("INSERT INTO mart_ekonomi_tahunan SELECT * FROM mart_ekonomi_tahunan WHERE assignment_id='DTD-0003'")
        con.execute("UPDATE mart_ekonomi_bulanan SET tahun_mulai_operasi='2025' WHERE assignment_id='DTD-0008'")
    states=lookup(settings.census_db)
    assert record(states,'dtd','DTD-0002',V1,'001').group=='UNAVAILABLE'
    assert record(states,'dtd','DTD-0003',V1,'001').group=='REVIEW'
    assert record(states,'dtd','DTD-0008',V1,'001').group=='REVIEW'
    assert record(states,'ub','UB-0001','ignored-version','ignored-index').group=='KECIL'


def test_nominal_is_admin_only_but_aggregate_categories_remain_accessible(portal,analyst,viewer):
    _,admin,settings=portal
    configure(settings)
    row=search(analyst,turnover_group='KECIL')['rows'][0]
    assert row['turnover']['amount_status']=='RESTRICTED'
    assert 'annual' not in row['turnover'] and 'monthly' not in row['turnover']
    form=analyst.get('/api/v1/questionnaires/dtd/DTD-0008',params={'business':'001'}).json()
    assert 'annual' not in form['turnover'] and 'monthly' not in form['turnover']
    assert viewer.post('/api/v1/directories/businesses/search',json={'source':'dtd'}).status_code==200
    assert viewer.post('/api/v1/analytics/query',json={'metric_id':'usaha.turnover_distribution'}).status_code==200
    assert search(admin,turnover_group='KECIL')['rows'][0]['turnover']['amount_status']=='AVAILABLE'


def test_excel_and_kbli_keep_filters_and_sensitive_column_policy(portal,analyst):
    _,client,settings=portal
    configure(settings)
    payload={'source':'dtd','turnover_group':'KECIL','turnover_basis':'ESTIMATE_MONTHLY_X12','page_size':1}
    for user,sensitive in [(client,True),(analyst,False)]:
        response=user.post('/api/v1/directories/businesses/export',json=payload)
        assert response.status_code==200
        rows=list(load_workbook(BytesIO(response.content)).active.values)
        assert len(rows)==3  # all matches, beyond the first page
        assert 'Omzet tahunan (Rp)' in rows[0]
        if not sensitive:
            assert all(row[rows[0].index('Omzet tahunan (Rp)')] == '\u2022' * 8 for row in rows[1:])
        assert all(row[rows[0].index('Dasar omzet')]=='Estimasi bulanan × 12' for row in rows[1:])
    response=client.get('/api/v1/kbli/tree',params={'level':5,'prefix':'01111',
        'turnover_group':'KECIL','turnover_basis':'ESTIMATE_MONTHLY_X12'})
    assert response.status_code==200
    assert response.json()['rows'][0]['dtd_units'] is None  # small count is not exposed
    assert client.post('/api/v1/directories/businesses/search',json={'turnover_group':'bad'}).status_code==422
    assert client.post('/api/v1/directories/families/search',json={'turnover_group':'MIKRO'}).status_code==422


def test_total_distribution_does_not_reveal_small_estimated_component(portal):
    _,_,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute('DELETE FROM mart_ekonomi_bulanan')
        con.execute("DELETE FROM mart_ekonomi_tahunan WHERE assignment_id NOT IN ('DTD-0001','DTD-0002','DTD-0003','DTD-0004','DTD-0005','DTD-0006')")
        con.execute("UPDATE mart_ekonomi_tahunan SET tahun_mulai_operasi='2000',pendapatan_utama_2025='100'")
        con.execute('INSERT INTO mart_ekonomi_bulanan '
            '(assignment_id,__version_normalized,index1,tahun_mulai_operasi,pendapatan_utama_bln,__key_valid,__conflict) '
            'VALUES(?,?,?,?,?,?,?)',('DTD-0007',V1,'001','2026','100','1','0'))
    with Analytics(settings.census_db) as api:
        assert next(r for r in api._query('usaha.turnover_distribution')[1]
                    if r['dimensions']['turnover_group']=='MIKRO')['value']==7
        assert next(r for r in api.query('usaha.turnover_distribution')['rows']
                    if r['dimensions']['turnover_group']=='MIKRO')['suppressed']
        reported=api.query('usaha.turnover_distribution',filters={'turnover_basis':'REPORTED_ANNUAL'})
        assert reported['rows'][0]['value']==6
