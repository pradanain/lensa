import json
import sqlite3

from .common import dump, q, sha256, utcnow, write_csv
from .ingestion import PipelineError, plan_sync
from .scanner import load_config, relation_specs
from .transformation import join_condition, safe_rows


def diagnose_unmatched(con, sources, root):
    rows = []
    for spec in relation_specs(sources):
        if spec['temporal_evidence']!='EXACT_NORMALIZED_VERSION':
            continue
        parent,child = safe_rows(spec['parent']),safe_rows(spec['child'])
        fields = [(a,b) for a,b in zip(spec['parent_columns'],spec['child_columns']) if a!='assignment_date_modified']
        unit_condition = ' AND '.join('v.'+q(a)+'=c.'+q(b) for a,b in fields)
        id_condition = 'v.'+q(fields[0][0])+'=c.'+q(fields[0][1])
        sql = ('SELECT COUNT(*), COALESCE(SUM(NOT EXISTS(SELECT 1 FROM '+parent+' v WHERE '+id_condition+')),0), '
               'COALESCE(SUM(EXISTS(SELECT 1 FROM '+parent+' v WHERE '+id_condition+') AND NOT EXISTS(SELECT 1 FROM '+parent+' v WHERE '+unit_condition+')),0), '
               'COALESCE(SUM(EXISTS(SELECT 1 FROM '+parent+' v WHERE '+unit_condition+')),0) '
               'FROM '+child+' c LEFT JOIN '+parent+' p ON '+join_condition(spec)+' WHERE p.__row_id IS NULL')
        total,no_id,no_unit,different_time = con.execute(sql).fetchone()
        rows.append(dict(parent=spec['parent'],child=spec['child'],unmatched_rows=total,assignment_id_not_found=no_id,
                         roster_unit_not_found=no_unit,same_unit_different_timestamp=different_time,
                         classification_exhaustive=total==no_id+no_unit+different_time))
    write_csv(root/'docs/reports/database/unmatched_diagnosis.csv',rows)
    return rows


def validate(root):
    plan = plan_sync(root)
    baseline = json.loads((root/'data/metadata/original_manifest.json').read_text(encoding='utf-8'))
    original = []
    for e in baseline['files']:
        p = root/e['path']
        original.append(dict(path=e['path'],status='UNCHANGED' if p.is_file() and sha256(p)==e['sha256'] else 'CHANGED_OR_MISSING'))
    write_csv(root/'docs/reports/integration/original_preservation_validation.csv',original)
    if any(e['status']!='UNCHANGED' for e in original):
        raise PipelineError('ORIGINAL_WORKSPACE_CHANGED')
    result = dict(generated_utc=utcnow(),original_files_verified=len(original),planned_new=sum(e['status']!='DUPLICATE' for e in plan['entries']),database_exists=False)
    path = root/'data/processed/se2026.sqlite'
    if path.exists():
        con = sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
        try:
            result.update(database_exists=True,integrity=con.execute('PRAGMA integrity_check').fetchone()[0],foreign_key_violations=len(con.execute('PRAGMA foreign_key_check').fetchall()))
            counts = []
            for s in load_config(root):
                sid = s['id']
                for import_id,expected_raw,expected_clean in con.execute('SELECT import_id,raw_rows,clean_rows FROM imported_files WHERE source_id=?',(sid,)).fetchall():
                    raw = con.execute('SELECT COUNT(*) FROM '+q('raw_'+sid)+' WHERE __import_id=?',(import_id,)).fetchone()[0]
                    clean = con.execute('SELECT COUNT(*) FROM '+q('clean_'+sid)+' WHERE __import_id=?',(import_id,)).fetchone()[0]
                    invalid,conflicts = con.execute('SELECT COALESCE(SUM(__key_valid=0),0),COALESCE(SUM(__conflict),0) FROM '+q('clean_'+sid)+' WHERE __import_id=?',(import_id,)).fetchone()
                    untraced = con.execute('SELECT COUNT(*) FROM '+q('raw_'+sid)+' r LEFT JOIN '+q('clean_'+sid)+' c ON r.__import_id=c.__import_id AND r.__clean_hash=c.__clean_hash WHERE r.__import_id=? AND c.__row_id IS NULL',(import_id,)).fetchone()[0]
                    counts.append(dict(dataset=sid,import_id=import_id,raw_rows=raw,clean_rows=clean,deduplicated=raw-clean,invalid_key_rows=invalid,conflicting_rows=conflicts,raw_without_clean_provenance=untraced,status='PASS' if raw==expected_raw and clean==expected_clean and untraced==0 else 'FAIL'))
            write_csv(root/'docs/reports/database/database_row_validation.csv',counts)
            result['raw_rows'] = sum(r['raw_rows'] for r in counts)
            result['clean_rows'] = sum(r['clean_rows'] for r in counts)
            result['row_checks_pass'] = all(r['status']=='PASS' for r in counts)
            result['deduplicated_rows'] = result['raw_rows']-result['clean_rows']
            relations = []
            for spec in relation_specs(load_config(root)):
                parent,child = spec['parent'],spec['child']
                total = con.execute('SELECT COUNT(*) FROM '+safe_rows(child)).fetchone()[0]
                joined,unmatched = con.execute('SELECT COUNT(*),COALESCE(SUM(p.__row_id IS NULL),0) FROM '+safe_rows(child)+' c LEFT JOIN '+safe_rows(parent)+' p ON '+join_condition(spec)).fetchone()
                relations.append(dict(parent=parent,child=child,child_rows=total,left_join_rows=joined,unmatched_child_rows=unmatched,multiplication_excess=joined-total,
                                      temporal_evidence=spec['temporal_evidence'],status='PASS_NO_MULTIPLICATION' if joined==total else 'FAIL_MULTIPLICATION'))
            result['no_join_multiplication'] = all(r['multiplication_excess']==0 for r in relations)
            from .ub_integration import validate_ub_mart
            ub_validation = validate_ub_mart(con,load_config(root))
            for relation in relations:
                if relation['child'] in ('ub_a','ub_b','ub_c'):
                    relation['status']=ub_validation['status']
            write_csv(root/'docs/reports/database/database_relationship_validation.csv',relations)
            dump(root/'docs/reports/ub/ub_assignment_integration_validation.json',ub_validation)
            result['ub_assignment_integration'] = ub_validation
            diagnoses = diagnose_unmatched(con,load_config(root),root)
            if not all(r['classification_exhaustive'] for r in diagnoses):
                raise PipelineError('UNMATCHED_CLASSIFICATION_COUNT_MISMATCH')
            marts = dict(con.execute("SELECT name,sql FROM sqlite_master WHERE type='view' AND name LIKE 'mart_%'"))
            mart_counts = {name:con.execute('SELECT COUNT(*) FROM '+q(name)).fetchone()[0] for name in marts}
            write_csv(root/'docs/reports/database/mart_row_counts.csv',[dict(mart=n,rows=v) for n,v in mart_counts.items()])
            for integrated,base in [('mart_keluarga_integrated','mart_keluarga'),('mart_usaha_integrated','mart_usaha'),('mart_ub_integrated','mart_ub_a')]:
                if integrated in mart_counts and mart_counts[integrated]!=mart_counts[base]:
                    raise PipelineError('MART_GRAIN_CHANGED')
            if 'mart_sosial_p0_p1' in mart_counts:
                expected = con.execute('SELECT COUNT(*) FROM ('+' UNION '.join('SELECT __key FROM '+safe_rows(s) for s in ['sosial_p0','p1_pekerjaan','p1_disabilitas','p1_kronis_a','p1_kronis_b'])+')').fetchone()[0]
                if expected!=mart_counts['mart_sosial_p0_p1']:
                    raise PipelineError('SOCIAL_UNION_GRAIN_CHANGED')
                result.update(social_union_rows=expected,p1_only_rows=mart_counts['mart_sosial_p1_only'])
            if result['integrity']!='ok' or result['foreign_key_violations'] or not result['row_checks_pass'] or not result['no_join_multiplication']:
                raise PipelineError('DATABASE_VALIDATION_FAILED')
            result['mart_counts'] = mart_counts
        finally:
            con.close()
    dump(root/'docs/reports/database/database_validation.json',result)
    return result
