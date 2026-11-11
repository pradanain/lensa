"""Location provenance and source-path audit, without a scale/prelist eligibility gate."""
from collections import Counter, defaultdict
import sqlite3

from ..common import timestamp
from .business_audit import COMPLETE, audit, duplicate_groups


def value(raw):
    return None if raw is None or str(raw).strip()=='' else str(raw).strip()


def classify_location(family_codes, building_codes):
    """Parent existence defines the path; only observed codes define building type.

    None means no parent. [None] means a parent with an unknown building code.
    A missing family building code must never discard its business roster.
    """
    if family_codes is not None and building_codes is not None:
        return 'AMBIGUOUS_PARENTS'
    if family_codes is not None:
        codes={value(code) for code in family_codes}
        if codes=={'3'}:
            return 'RESIDENTIAL_PARENT'
        if codes=={'2'}:
            return 'MIXED_PARENT'
        return 'FAMILY_BUILDING_UNCLASSIFIED'
    if building_codes is not None:
        codes={value(code) for code in building_codes}
        if codes=={'1'}:
            return 'SPECIAL_BUSINESS_BUILDING'
        return 'OTHER_BUILDING_USAGE'
    return 'NO_EXACT_PARENT'


def location_report(database, root):
    con=sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA query_only=ON'); con.execute('BEGIN')
    def raw(source):
        return [dict(r) for r in con.execute('SELECT r.* FROM raw_'+source+' r WHERE r.__import_id=(SELECT import_id FROM active_imports WHERE source_id=?)',(source,))]
    families,buildings=defaultdict(list),defaultdict(list)
    for r in raw('keluarga'):
        families[(value(r['assignment_id']),timestamp(r['assignment_date_modified']))].append(r)
    for r in raw('bku'):
        buildings[(value(r['assignment_id']),timestamp(r['assignment_date_modified']))].append(r)
    masters={value(r['assignment_id']):r for r in raw('assignment_tgr')}
    rows=raw('usaha');counts=Counter();flags=Counter();keys=Counter();prelist=Counter();actual_kind=Counter()
    categories={};workflow_existence=Counter();eligible_total=0
    for r in rows:
        aid=value(r['assignment_id']);version=timestamp(r['assignment_date_modified']);index=value(r['index1'])
        keys[(aid,version,index)]+=1
        master=masters.get(aid,{})
        found=value(r['kode_keberadaan_usaha']) in ('1','2')
        completed=master.get('status_assignment') in COMPLETE
        workflow_existence['FOUND_NEW_COMPLETED' if found and completed else 'FOUND_NEW_NOT_COMPLETED' if found else 'OTHER_EXISTENCE']+=1
        if not (found and completed):continue
        eligible_total+=1
        f=families.get((aid,version));b=buildings.get((aid,version))
        category=classify_location([x['kode_penggunaan_bangunan'] for x in f] if f else None,
                                   [x['kode_penggunaan_bangunan'] for x in b] if b else None)
        counts[category]+=1;categories[('TGR',aid,version,index)]=category
        prelist[(category,value(r['is_prelist2']) or 'MISSING')]+=1
        actual_kind[(category,value(r['jenis_usaha']) or 'MISSING')]+=1
        if not all((aid,version,index)):flags['INVALID_ID_VERSION_OR_INDEX']+=1
        if timestamp(master.get('versi_root_terbaru'))!=version:flags['MASTER_ROOT_VERSION_MISMATCH']+=1
        if value(master.get('kode_kabupaten'))!='6502':flags['REGION_NOT_PROVEN']+=1
        if category=='OTHER_BUILDING_USAGE':flags['NON_SPECIAL_BUILDING_WITH_ROSTER']+=1
    # Candidate matching is shared with the earlier audit. Scale-related diagnostic
    # labels are deliberately not used to select or reject these populations.
    entities=audit(database,None,root)
    eligible=[e for e in entities if e['eligible']]
    groups,_=duplicate_groups(eligible)
    overlap=Counter()
    for _,_,members in groups:
        labels={categories.get((e['system'],e['assignment_id'],e['version'],e['roster']),'UB') for e in members}
        family=bool(labels & {'RESIDENTIAL_PARENT','MIXED_PARENT','FAMILY_BUILDING_UNCLASSIFIED'})
        if family and 'SPECIAL_BUSINESS_BUILDING' in labels:overlap['FAMILY_VS_BKU_SIGNATURE_GROUPS']+=1
        if 'UB' in labels and len(labels)>1:overlap['TGR_VS_UB_SIGNATURE_GROUPS']+=1
        if 'RESIDENTIAL_PARENT' in labels and 'MIXED_PARENT' in labels:overlap['RESIDENTIAL_VS_MIXED_SIGNATURE_GROUPS']+=1
    candidate=Counter();candidate_categories=Counter()
    for e in eligible:
        if e['duplicate_status']=='POSSIBLE_DUPLICATE':
            candidate[e['system']]+=1
            candidate_categories[categories.get((e['system'],e['assignment_id'],e['version'],e['roster']),'UB')]+=1
    selected_groups={'RESIDENTIAL_PARENT','MIXED_PARENT','SPECIAL_BUSINESS_BUILDING'}
    result={
        'count_basis':'ROSTER_UNITS_WITH_CURRENT_EXPORTED_WORKFLOW_NOT_FINAL_PHYSICAL_UNIQUENESS',
        'scale_used_as_eligibility':False,
        'raw_business_records':len(rows),'raw_unit_version_keys':len(keys),
        'repeated_unit_version_keys':sum(n>1 for n in keys.values()),
        'repeated_key_excess_records':sum(n-1 for n in keys.values() if n>1),
        'completed_tgr':eligible_total,'operational_counts_by_parent_building':dict(counts),
        'three_categories_before_physical_deduplication':sum(counts[g] for g in selected_groups),
        'outside_three_categories':sum(n for g,n in counts.items() if g not in selected_groups),
        'existence_workflow':dict(workflow_existence),'review_flags_overlapping':dict(flags),
        'roster_prelist_attribute_by_category':[dict(category=g,is_prelist2=p,units=n) for (g,p),n in sorted(prelist.items())],
        'roster_business_kind_by_category':[dict(category=g,jenis_usaha=k,units=n) for (g,k),n in sorted(actual_kind.items())],
        'duplicate_candidate_completed_records_by_system':dict(candidate),
        'duplicate_candidate_completed_records_by_category':dict(candidate_categories),
        'completed_candidate_signature_groups':len(groups),
        'completed_cross_path_candidate_groups_overlapping':dict(overlap),
        'physical_duplicates_resolved':0,'physical_unique_umkm':None,'physical_unique_ub':None,
        'physical_uniqueness_status':'UNVERIFIED_POSSIBLE_DUPLICATES_PRESERVED',
        'confirmed_same_roster_in_two_parent_paths':counts['AMBIGUOUS_PARENTS'],
        'source_activity_status':'FILTERED_ACTIVE_AT_HISTORICAL_EXPORT_NOT_CURRENTLY_RECHECKABLE',
        'ub_active_completed':sum(e['system']=='TCZ' for e in eligible),
        'parent_building_type_is_not_exact_business_location':True,
        'census_integrity':con.execute('PRAGMA integrity_check').fetchone()[0],
        'census_foreign_key_violations':len(con.execute('PRAGMA foreign_key_check').fetchall()),
    }
    con.close()
    return result
