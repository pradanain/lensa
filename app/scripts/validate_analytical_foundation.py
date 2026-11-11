"""Execute every registered metric against the actual read-only baseline."""
import json
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.common import dump,sha256,utcnow,write_csv
from se2026.analytics import Analytics
from se2026.analytics.numeric import ExactSum,ratio


def totals(metric,rows):
    eligible=sum(r['eligible_rows'] for r in rows)
    denominator=sum(r['denominator'] for r in rows)
    if metric['kind'].startswith('decimal_'):
        accumulator=ExactSum()
        for row in rows:accumulator.add(row['numerator'])
        numerator=accumulator.result()
    else:numerator=sum(r['numerator'] for r in rows)
    return eligible,None if numerator is None else Decimal(str(numerator)),denominator


def validate(root=ROOT):
    db=root/'data/processed/se2026.sqlite'
    before=sha256(db)
    metrics_checks=[];regional_checks=[];unknowns=[]
    with Analytics(db,root) as api:
        definition_count=api.validate_definitions(lambda source:print('SOURCE_SCHEMA_GRAIN',source,flush=True))
        for metric_id in sorted(api.registry.metrics):
            print('METRIC_VALIDATION',metric_id,flush=True)
            metric,rows=api._query(metric_id)
            global_values=totals(metric,rows)
            assert all(0<=r['denominator']<=r['eligible_rows'] for r in rows)
            if metric['kind'] in ('rate','distribution','count'):
                assert all(0<=r['numerator']<=r['denominator'] for r in rows)
            if metric['kind']=='rate':
                assert all(r['percentage']==ratio(r['numerator'],r['denominator'],100) for r in rows)
            if metric['kind']=='distribution':
                denominator=sum(r['denominator'] for r in rows)
                assert all(r['percentage']==ratio(r['numerator'],denominator,100) for r in rows)
            # Every metric is checked by district; count anchors also by all lower levels.
            levels=['kecamatan']+(['desa','sls','subsls'] if metric['kind']=='count' else [])
            for level in levels:
                _,groups=api._query(metric_id,group_by=level)
                regional_values=totals(metric,groups)
                assert regional_values==global_values,'GRAIN_OR_DENOMINATOR_CHANGED'
                regional_checks.append(dict(metric_id=metric_id,location='assignment',level=level,groups=len(groups),components_reconcile=True))
                if metric_id in ('assignment_tgr.count','assignment_ub.count'):
                    status_counts=Counter()
                    for row in groups:status_counts[row['dimensions'][level]['geo_status']]+=row['eligible_rows']
                    unknowns.append(dict(metric_id=metric_id,level=level,counts_by_code_status=dict(status_counts)))
            if api.registry.sources[metric['source']].get('response_desa'):
                _,groups=api._query(metric_id,group_by='desa',location='response')
                assert totals(metric,groups)==global_values
                regional_checks.append(dict(metric_id=metric_id,location='response',level='desa',groups=len(groups),components_reconcile=True))
            contributors=global_values[2] if metric['kind'].startswith('decimal_') else global_values[0]
            safe_cohort=contributors>=5 or contributors==0
            metrics_checks.append(dict(metric_id=metric_id,source=metric['source'],kind=metric['kind'],
                eligible_rows=global_values[0] if safe_cohort else None,
                numerator=str(global_values[1]) if safe_cohort and global_values[1] is not None else None,
                denominator=global_values[2] if safe_cohort else None,
                validation_status='VALIDATED_LOCAL',schema_references_valid=True,source_grain_unique=True,
                components_reconcile=True,small_cells_not_exported=True))
        geographic_catalog=api.geography()
        comparison=api.ub_geography_comparison()
        reference=json.loads((root/'docs/reports/readiness/analytical_readiness_audit.json').read_text(encoding='utf-8'))
        same_reference_hash=before==reference['database_sha256']
        if same_reference_hash:
            assert comparison['ub_assignments']==226 and comparison['different_nonempty_desa_codes']==136
            for metric_id,expected in [('assignment_tgr.count',234),('assignment_ub.count',103)]:
                record=next(r for r in unknowns if r['metric_id']==metric_id and r['level']=='kecamatan')
                assert record['counts_by_code_status']['SPECIAL_ZERO_SEGMENT']==expected
        numeric=json.loads((root/'app/config/analytics/numeric_fields.json').read_text(encoding='utf-8'))
        profiles=[]
        for field_id,definition in numeric.items():
            # Explicit schema reference check; profiling exposes counts only, never values.
            api._connection.execute('EXPLAIN SELECT n."'+definition['column']+'" FROM "'+definition['view']+'" n').fetchall()
            profiles.append(api.numeric_profile(field_id))
        provenance=api._provenance
    after=sha256(db)
    assert before==after,'DATABASE_CHANGED'
    folder=root/'docs/reports/analytics'
    folder.mkdir(parents=True,exist_ok=True)
    dump(root/'app/config/analytics/dimensions/local_geography.json',dict(generated_utc=utcnow(),database_sha256=before,
         records=geographic_catalog,assignment_ids_included=False,respondent_counts_included=False,
         label_source='Local administrative labels only; original alternatives and conflicts retained'))
    write_csv(folder/'metric_validation.csv',metrics_checks)
    write_csv(folder/'regional_component_validation.csv',regional_checks)
    dump(folder/'numeric_profiles.json',profiles)
    tests_path=folder/'synthetic_tests.xml'
    test_suite=ET.parse(tests_path).getroot().find('testsuite') if tests_path.exists() else None
    result=dict(generated_utc=utcnow(),metric_count=definition_count,metrics=metrics_checks,
                geographic_catalog_records=len(geographic_catalog),geographic_code_status_counts=unknowns,
                ub_geography_comparison=comparison,regional_checks=len(regional_checks),all_components_reconcile=True,
                source_grains_unique=True,all_references_valid=True,numeric_fields_profiled=len(profiles),
                database_sha256_before=before,database_sha256_after=after,database_unchanged=before==after,
                baseline_reference_hash_matches=same_reference_hash,source_provenance=provenance,
                tests=dict(test_suite.attrib) if test_suite is not None else {},sql_lab_access=False,
                raw_clean_changes=False,etl_rebuilt=False,dashboard_built=False,
                disclosure_control='Only whole-source aggregate components saved; no individual values or small regional cells exported')
    dump(folder/'foundation_validation.json',result)
    for path in (root/'app/config/analytics/metrics').glob('*.json'):
        definitions=json.loads(path.read_text(encoding='utf-8'))
        for metric in definitions:
            metric['validation_status']='VALIDATED_LOCAL'
            metric['validation_evidence']='docs/reports/analytics/foundation_validation.json'
            metric['validated_database_sha256']=before
        dump(path,definitions)
    print(json.dumps({k:result[k] for k in ['metric_count','regional_checks','geographic_catalog_records','numeric_fields_profiled','database_unchanged']},indent=2))
    return result


if __name__=='__main__':validate()
