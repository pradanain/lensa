import sqlite3

import pytest

from se2026.analytics import Analytics
from se2026.analytics.business_audit import duplicate_groups
from se2026.analytics.business_location_audit import classify_location
from se2026.common import sha256


@pytest.mark.parametrize('family,building,expected',[
    (['3'],None,'RESIDENTIAL_PARENT'),
    (['2'],None,'MIXED_PARENT'),
    ([None],None,'FAMILY_BUILDING_UNCLASSIFIED'),
    (['9'],None,'FAMILY_BUILDING_UNCLASSIFIED'),
    (['2','3'],None,'FAMILY_BUILDING_UNCLASSIFIED'),
    (None,['1'],'SPECIAL_BUSINESS_BUILDING'),
    (None,['6'],'OTHER_BUILDING_USAGE'),
    (None,['2'],'OTHER_BUILDING_USAGE'),
    (None,[None],'OTHER_BUILDING_USAGE'),
    (['3'],['1'],'AMBIGUOUS_PARENTS'),
    (None,None,'NO_EXACT_PARENT'),
])
def test_only_observed_parent_codes_define_building_type(family,building,expected):
    assert classify_location(family,building)==expected


def test_family_population_needs_neither_scale_nor_building_type_to_count(portal):
    _,client,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute('DELETE FROM mart_bku')
        con.execute('UPDATE mart_usaha SET skala_usaha=NULL')
        con.execute('UPDATE mart_keluarga SET kode_penggunaan_bangunan=NULL')
        con.execute("UPDATE mart_keluarga SET kode_penggunaan_bangunan='3' WHERE assignment_id='DTD-0001'")
        con.execute("UPDATE mart_keluarga SET kode_penggunaan_bangunan='2' WHERE assignment_id='DTD-0002'")
        # A mobile/farming roster is still grouped by its parent; never relabel
        # its actual physical business location as inside the dwelling.
        con.execute("UPDATE mart_usaha SET jenis_usaha='6',is_prelist2='0' WHERE assignment_id='DTD-0001'")
    before=sha256(settings.census_db)
    with Analytics(settings.census_db) as api:
        def count(mid):return api._query(mid)[1][0]['value']
        assert count('usaha.enumerated_count')==13
        assert count('usaha.enumerated_family_count')==13
        assert count('usaha.enumerated_residential_count')==2
        assert count('usaha.enumerated_mixed_count')==1
        # Ten family businesses with missing code remain counted as family.
        assert count('usaha.enumerated_family_count')-count('usaha.enumerated_residential_count')-count('usaha.enumerated_mixed_count')==10
        assert api.query('usaha.enumerated_mixed_count')['rows'][0]['value'] is None
    summary=client.get('/api/v1/analytics/summary').json()
    assert summary['counts']['usaha.enumerated_family_count'][0]['value']==13
    assert sha256(settings.census_db)==before


def test_ambiguous_duplicate_candidates_are_preserved_without_scale_dependency():
    def entity(system,aid,roster,name='USAHA SINTETIS'):
        return dict(entity_id=system+aid+roster,system=system,assignment_id=aid,roster=roster,
                    name=name,kbli='01111',village='6502010001',address='ALAMAT SINTETIS',person=None,nib=None,code_identity=None)
    entities=[entity('TGR','FAMILY','001'),entity('TGR','BKU','001'),entity('TCZ','UB','')]
    groups,ids=duplicate_groups(entities)
    assert len(groups)==1 and len(ids)==3
    assert len(entities)==3 and len({e['entity_id'] for e in entities})==3
    # Same name and KBLI alone cannot identify a physical unit.
    for e in entities:e['address']=None
    assert duplicate_groups(entities)==([],set())
