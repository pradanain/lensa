"""Synthetic checks: units, versions, workflow, review and shared API population."""
import sqlite3

import pytest

from se2026.analytics import Analytics
from se2026.analytics.business_audit import audit, classify
from se2026.common import sha256

VERSION = '2026-09-01T00:00:00.000000'


def business(**changes):
    return dict(nama_usaha='USAHA SINTETIS', skala_usaha='UMKM',
                kode_keberadaan_usaha='2', __version_normalized=VERSION,
                __key_valid=1, __conflict=0, **changes)


def master(status='APPROVED BY Pengawas'):
    return dict(versi_root_terbaru=VERSION, kode_kabupaten='6502', status_assignment=status)


@pytest.mark.parametrize('status,expected', [('3','CLOSED'), ('00','NOT_FOUND'), ('4','SOURCE_MARKED_DUPLICATE'), ('9','NON_RESPONSE')])
def test_existence_does_not_become_completed_unit(status, expected):
    row=business(); row['kode_keberadaan_usaha']=status
    assert classify(row, master(), family={'present':True})['classification']==expected


@pytest.mark.parametrize('workflow', ['SUBMITTED BY Petugas','REJECTED','DRAFT','REVOKED BY Pengawas'])
def test_unapproved_or_returned_status_is_not_completed(workflow):
    assert classify(business(), master(workflow), family={'present':True})['classification']=='NOT_COMPLETED'


def test_new_building_is_not_a_business_without_roster():
    # Classifier receives roster units only: a parent cannot create an output unit.
    building={'kode_penggunaan_bangunan':'6'}
    assert [classify(row,master(),bku=building) for row in []]==[]
    state=classify(business(),master(),bku=building)
    assert not state['local_qualified']
    assert 'NON_TARGET_BUILDING_WITH_BUSINESS_ROSTER' in state['flags']


@pytest.mark.parametrize('parent', ['FAMILY','BKU'])
def test_multiple_businesses_count_units_not_parent(parent):
    kwargs={'family':{'present':True}} if parent=='FAMILY' else {'bku':{'kode_penggunaan_bangunan':'1'}}
    states=[classify(business(), master(), **kwargs) for _ in range(3)]
    assert sum(s['local_qualified'] for s in states)==3


def test_cross_parent_and_historical_versions_remain_review():
    state=classify(business(),master(),family={'present':True},bku={'kode_penggunaan_bangunan':'1'})
    assert state['lineage']=='BOTH' and not state['local_qualified']
    assert not classify(business(),master(),family={'present':True},version_count=2)['local_qualified']
    old=master(); old['versi_root_terbaru']='2026-09-02T00:00:00.000000'
    assert 'ROOT_VERSION_NOT_MATCHED' in classify(business(),old,family={'present':True})['flags']


def test_missing_kbli_does_not_invent_or_remove_a_real_unit():
    assert classify(business(kbli=None),master(),family={'present':True})['local_qualified']


def test_incomplete_identity_unknown_scale_and_large_tgr_remain_review():
    for column,value in [('nama_usaha',None),('skala_usaha',None),('skala_usaha','UB'),('__key_valid','0'),('__conflict','1')]:
        row=business();row[column]=value
        assert not classify(row,master(),family={'present':True})['local_qualified']


def test_shared_registry_directory_kbli_and_no_name_only_merge(portal):
    _,client,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        # Synthetic default has both kinds of parents; choose a family lineage.
        con.execute('DELETE FROM mart_bku')
        con.execute("UPDATE mart_usaha SET skala_usaha='UMKM',nama_pengusaha_pj=NULL,alamat_usaha=NULL,code_identity=NULL")
        con.execute('UPDATE mart_legalitas_usaha SET nib=NULL')
        # Name alone is not evidence of a duplicate, including repeated roster names.
        con.execute("UPDATE mart_usaha SET nama_usaha='NAMA SAMA SINTETIS'")
    before=sha256(settings.census_db)
    states=audit(settings.census_db,None,settings.root)
    dtd=[e for e in states if e['system']=='TGR']
    assert len(dtd)==13
    assert all(e['local_qualified'] for e in dtd)
    assert all(e['duplicate_status']=='NO_MULTI_SIGNAL_CANDIDATE' for e in dtd)
    with Analytics(settings.census_db) as api:
        count=api._query('usaha.qualified_count')[1][0]['value']
        assert count==13
        assert api._query('usaha.qualified_family_count')[1][0]['value']==13
        assert api._query('usaha.qualified_bku_count')[1][0]['value']==0
    directory=client.post('/api/v1/directories/businesses/search',json={'source':'dtd','qualified_only':True,'page_size':100}).json()
    assert directory['total']==count
    tree=client.get('/api/v1/kbli/tree?level=2&prefix=01&qualified_only=true').json()
    assert tree['population']=='LOCAL_AUDIT_QUALIFIED'
    assert tree['rows'][0]['dtd_units']==10  # three missing/invalid/unknown codes stay in model
    assert sha256(settings.census_db)==before


def test_cross_system_prelist_requires_more_than_id_and_keeps_both(portal):
    _,_,settings=portal
    with sqlite3.connect(settings.census_db) as con:
        con.execute("UPDATE mart_assignment_tgr SET code_identity='PRELIST-SYNTHETIC'")
        con.execute("UPDATE mart_assignment_ub SET code_identity='PRELIST-SYNTHETIC' WHERE assignment_id='UB-0001'")
        con.execute("UPDATE mart_usaha SET code_identity='PRELIST-SYNTHETIC',nama_usaha='CROSS SYSTEM SYNTHETIC',kbli='01111' WHERE assignment_id='DTD-0001' AND index1='001'")
        con.execute("UPDATE mart_ub_a SET nama_usaha='CROSS SYSTEM SYNTHETIC',kbli_akhir='01111' WHERE assignment_id='UB-0001'")
    entities=audit(settings.census_db,None,settings.root)
    matches=[e for e in entities if e['name']=='CROSS SYSTEM SYNTHETIC']
    assert len(matches)==2 and {e['system'] for e in matches}=={'TCZ','TGR'}
    assert all(e['duplicate_status']=='POSSIBLE_DUPLICATE' for e in matches)
    assert all(not e['local_qualified'] for e in matches)
