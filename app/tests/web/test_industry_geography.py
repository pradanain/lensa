from se2026.analytics import Analytics
from se2026.analytics.client import complementary_kbli_geo
from se2026.common import sha256
from se2026.web.disclosure import protect_metric


def test_each_kbli_has_complementary_geographic_suppression():
    rows=[{'dimensions':{'kbli':code,'kecamatan':{'geo_key':geo}},'eligible_rows':n} for code,geo,n in [('01111','a',1),('01111','b',8),('01222','a',2),('01222','b',9)]]
    assert complementary_kbli_geo(rows,[0,2])==[0,1,2,3]
    # A different group alone cannot serve as a complement for a published KBLI total.
    assert complementary_kbli_geo(rows,[0])==[0,1]


def test_stricter_portal_policy_applies_complements_per_kbli():
    counts=[6,20,7,30]
    rows=[dict(dimensions={'kbli':'01111' if i<2 else '01222','desa':{'geo_key':str(i)}},eligible_rows=n,numerator=n,denominator=n,excluded_rows=0,value=n,percentage=None,suppressed=False) for i,n in enumerate(counts)]
    output=protect_metric({'kind':'count','rows':rows,'suppression':{}},10)
    assert all(row['value'] is None for row in output['rows'])
    assert output['suppression']['suppressed_rows']==4


def test_existing_semantic_api_maps_kbli_and_preserves_directory_grain(portal):
    _,client,settings=portal
    before=sha256(settings.census_db)
    payload={'metric_id':'usaha.enumerated_count','filters':{'kbli':['01111']},'group_by':['kbli','kecamatan']}
    response=client.post('/api/v1/analytics/query',json=payload)
    assert response.status_code==200
    rows=response.json()['rows']
    assert len(rows)==1 and rows[0]['dimensions']['kbli']=='01111' and rows[0]['value']==10
    geo=rows[0]['dimensions']['kecamatan']
    assert geo['raw_codes']['kode_kecamatan']=='6502010'
    directory=client.post('/api/v1/directories/businesses/search',json={'source':'dtd','enumerated_only':True,'kbli_prefix':'01111','kecamatan':'6502010','page_size':100}).json()
    assert directory['total']==10
    assert len({r['record_key'] for r in directory['rows']})==10
    with Analytics(settings.census_db) as api:
        assert api._query('usaha.enumerated_count',filters={'kbli':'01111'})[1][0]['value']==10
    assert sha256(settings.census_db)==before
