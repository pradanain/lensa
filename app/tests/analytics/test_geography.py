from se2026.analytics.geography import bucket


def codes():
    return dict(kode_kabupaten='6502',kode_kecamatan='6502010',kode_desa='6502010001',
                kode_sls='65020100010001',kode_subsls='6502010001000101')


def test_composite_keys_keep_source_concept_hierarchy_and_text():
    a=bucket('TGR','assignment','subsls',codes())
    b=bucket('TCZ','assignment','subsls',codes())
    assert a.key!=b.key and a.status=='OBSERVED_CODE_UNVERIFIED'
    assert a.as_dict()['raw_codes']['kode_subsls']=='6502010001000101'
    changed=codes();changed['kode_desa']='0000000001'
    assert bucket('TGR','assignment','desa',changed).as_dict()['raw_codes']['kode_desa']=='0000000001'


def test_special_missing_hierarchy_mismatch_and_unmatched_are_kept():
    special=codes();special['kode_kecamatan']='6502000'
    assert bucket('TGR','assignment','kecamatan',special).status=='SPECIAL_ZERO_SEGMENT'
    missing=codes();missing['kode_desa']=None
    assert bucket('TGR','assignment','desa',missing).status=='MISSING_CODE'
    mismatch=codes();mismatch['kode_desa']='6502020001'
    assert bucket('TGR','assignment','desa',mismatch).status=='HIERARCHY_MISMATCH'
    assert bucket('TGR','assignment','desa',{},False).status=='UNMATCHED_ASSIGNMENT'


def test_response_desa_does_not_invent_parent_or_sls_codes():
    item=bucket('TCZ','response','desa',{'kode_desa':'6502010001'}).as_dict()
    assert item['raw_codes']['kode_kecamatan'] is None
    assert item['raw_codes']['kode_sls'] is None
    assert item['raw_codes']['kode_desa']=='6502010001'


def test_administrative_fallback_labels_preserve_available_level_only():
    from se2026.analytics.geography import administrative_fallback
    labels={'6502050':{'TANJUNG SELOR'},'6502050009':{'TANJUNG SELOR HILIR'}}
    assert administrative_fallback({'kode_sls':'6502'},labels)==('Bulungan','kabupaten')
    assert administrative_fallback({'kode_sls':'65020000000000'},labels)==('Bulungan','kabupaten')
    assert administrative_fallback({'kode_sls':'65020500000000'},labels)==('TANJUNG SELOR','kecamatan')
    assert administrative_fallback({'kode_subsls':'6502050009000000'},labels)==('TANJUNG SELOR HILIR','desa')
    assert administrative_fallback({'kode_sls':'65020500090052'},labels) is None
    assert administrative_fallback({'kode_sls':'not-a-code'},labels) is None
