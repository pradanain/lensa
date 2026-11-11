"""Read-only source audit. Reports contain counts and format classes only."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

from .common import digest, dump, identity, q, records, sha256, sheets, timestamp, utcnow, write_csv, xlsx_rows


def load_config(root):
    return json.loads((root / 'app/config/sources.json').read_text(encoding='utf-8'))['sources']


def value_type(value, kind):
    if value is None or value == '':
        return 'empty'
    if kind in ('number', 'boolean', 'date', 'formula', 'error'):
        return kind
    text = str(value)
    if re.fullmatch(r'[+-]?\d+', text):
        return 'integer_text'
    if re.fullmatch(r'[+-]?(?:\d+\.\d*|\d*\.\d+)(?:[eE][+-]?\d+)?', text):
        return 'decimal_text'
    if re.fullmatch(r'[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', text):
        return 'uuid_text'
    if re.match(r'^\d{4}-\d\d-\d\d[ T]', text):
        return 'timestamp_text' if timestamp(text) else 'invalid_timestamp_text'
    return 'text'


def canonical_key(values, columns, fields):
    result = []
    for name in fields:
        value = values[columns.index(name)]
        value = timestamp(value) if name == 'assignment_date_modified' else identity(value)
        if value is None:
            return None
        result.append(value)
    return digest(result)


def projections(source):
    columns = source['columns']
    base = ['id_penghubung'] if 'id_penghubung' in columns else ['assignment_id']
    result = {'assignment':base}
    if 'assignment_date_modified' in columns:
        result['version'] = base + ['assignment_date_modified']
    unit = next((x for x in ['index1','index_usaha','index_meteran'] if x in columns), None)
    if unit:
        result['unit'] = result['version'] + [unit]
    result['full'] = source['key']
    return result


def profile_rows(rows, columns, dataset_id, source=None):
    width, count = len(columns), 0
    nulls = [0] * width
    kinds = [Counter() for _ in columns]
    lengths = [set() for _ in columns]
    invalid_time = Counter()
    row_hashes, first_keys, conflicts = set(), {}, set()
    raw_duplicates = 0
    states = {name:Counter() for name in projections(source)} if source else {}
    fields = projections(source) if source else {}
    missing_keys = Counter()
    outside = 0
    formula_count = error_count = 0
    for _, values, types in rows:
        values = (list(values) + [None] * width)[:width]
        types = (list(types) + ['null'] * width)[:width]
        count += 1
        row_hash = digest([values, types])
        if row_hash in row_hashes:
            raw_duplicates += 1
        row_hashes.add(row_hash)
        for i, value in enumerate(values):
            kind = value_type(value, types[i])
            kinds[i][kind] += 1
            if value is None or str(value).strip() == '':
                nulls[i] += 1
            else:
                lengths[i].add(min(len(str(value)), 1000))
                if columns[i] in ('assignment_date_modified','tanggal_dibuat','tanggal_diubah','versi_root_terbaru') and timestamp(value) is None:
                    invalid_time[columns[i]] += 1
            formula_count += kind == 'formula'
            error_count += kind == 'error'
        if 'kode_kabupaten' in columns:
            scope = identity(values[columns.index('kode_kabupaten')])
            outside += scope is not None and scope != '6502'
        for projection, key_fields in fields.items():
            key = canonical_key(values, columns, key_fields)
            if key is None:
                missing_keys[projection] += 1
            else:
                states[projection][key] += 1
                if projection == 'full':
                    if key in first_keys and first_keys[key] != row_hash:
                        conflicts.add(key)
                    first_keys.setdefault(key, row_hash)
    dictionary = []
    for i, col in enumerate(columns):
        types_nonempty = {t:n for t,n in kinds[i].items() if t != 'empty'}
        dictionary.append(dict(dataset=dataset_id, position=i+1, column=col,
                               observed_types=json.dumps(types_nonempty, sort_keys=True),
                               null_count=nulls[i], null_percent=round(100*nulls[i]/count, 4) if count else 0,
                               format_example=';'.join(sorted(types_nonempty)) + (';length=' + str(min(lengths[i])) + '..' + str(max(lengths[i])) if lengths[i] else ''),
                               sensitive='yes' if re.search(r'nama|nik|no_kk|alamat|telepon|hp|email|latitude|longitude|pendapatan|pend_|sakit_|dis_', col) else 'potentially',
                               role='candidate_key' if source and col in source['key'] else 'attribute'))
    candidates = {name:dict(columns=fields[name], distinct=len(counter), null_rows=missing_keys[name],
                            duplicate_excess=sum(n-1 for n in counter.values()),
                            unique=not missing_keys[name] and all(n == 1 for n in counter.values())) for name,counter in states.items()}
    summary = dict(dataset=dataset_id, rows=count, columns=len(columns), identical_duplicate_rows=raw_duplicates,
                   conflicting_keys=len(conflicts), conflict_rows=sum(states['full'][k] for k in conflicts) if source else 0,
                   key_null_rows=missing_keys['full'] if source else None, candidates=candidates,
                   invalid_timestamps=dict(invalid_time), out_of_scope_rows=outside,
                   formula_cells=formula_count, error_cells=error_count)
    return summary, dictionary, states


def original_files(root):
    legacy = root / 'SE2026_BULUNGAN_WORKSPACE'
    files = list(legacy.rglob('*')) if legacy.exists() else []
    files += list(root.glob('SE2026_Bulungan_*'))
    # Future exports are deliberately isolated; they cannot silently replace curated marts.
    files += list((root / 'data/incoming').rglob('*')) if (root / 'data/incoming').exists() else []
    return sorted(p for p in files if p.is_file())


def manifest(root):
    files, by_hash = [], defaultdict(list)
    for path in original_files(root):
        entry = dict(path=path.relative_to(root).as_posix(), bytes=path.stat().st_size,
                     modified_utc=__import__('datetime').datetime.fromtimestamp(path.stat().st_mtime, __import__('datetime').timezone.utc).isoformat(),
                     sha256=sha256(path), extension=path.suffix.lower())
        by_hash[entry['sha256']].append(entry['path'])
        files.append(entry)
    zips = []
    for entry in files:
        if entry['extension'] != '.zip':
            continue
        with ZipFile(root / entry['path']) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                with archive.open(member) as stream:
                    checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
                zips.append(dict(archive=entry['path'], member=member.filename, bytes=member.file_size,
                                 sha256=checksum, identical_extracted_paths=by_hash.get(checksum, [])))
    dirs = sorted(p.relative_to(root).as_posix() for p in (root / 'SE2026_BULUNGAN_WORKSPACE').rglob('*') if p.is_dir())
    result = dict(generated_utc=utcnow(), scope='original workspace plus data/incoming; generated outputs excluded',
                  files=files, directories=dirs, zip_members=zips,
                  exact_duplicate_groups=[dict(sha256=h, paths=paths) for h,paths in by_hash.items() if len(paths)>1])
    prior_path = root / 'data/metadata/file_manifest.json'
    old = json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.exists() else None
    if old:
        before = {e['path']:e['sha256'] for e in old['files']}
        after = {e['path']:e['sha256'] for e in files}
        result['changes_since_scan'] = dict(new=[p for p in after if p not in before], changed=[p for p in after if p in before and after[p]!=before[p]], missing=[p for p in before if p not in after])
    dump(prior_path, result)
    if not (root / 'data/metadata/original_manifest.json').exists():
        dump(root / 'data/metadata/original_manifest.json', result)
    return result


def relation_specs(sources):
    by_id = {s['id']:s for s in sources}
    result = []
    for source in sources:
        if not source['parent']:
            continue
        parent = by_id[source['parent']]
        projection = 'assignment' if parent['grain'] in ('assignment','ub') else 'full'
        child_projection = ('unit' if source['grain'] == 'kantor_unit' else 'version' if parent['grain'] in ('keluarga','bku') else 'full') if projection == 'full' else 'assignment'
        result.append(dict(parent=parent['id'], child=source['id'], parent_projection=projection, child_projection=child_projection,
                           parent_columns=projections(parent)[projection], child_columns=projections(source)[child_projection],
                           temporal_evidence='QUESTIONNAIRE_VERSION_NOT_VERIFIED' if source['grain']=='ub' else 'OPERATIONAL_ID_ONLY' if projection=='assignment' else 'EXACT_NORMALIZED_VERSION'))
    return result


def validate_relations(sources, states):
    result = []
    for spec in relation_specs(sources):
        parent = states[spec['parent']][spec['parent_projection']]
        child = states[spec['child']][spec['child_projection']]
        unmatched = sum(n for k,n in child.items() if k not in parent)
        joined = sum(n * parent.get(k, 0) for k,n in child.items())
        parent_unique = all(n == 1 for n in parent.values())
        child_unique = all(n == 1 for n in child.values())
        result.append(dict(**spec, parent_unique=parent_unique, child_unique=child_unique,
                           cardinality='one-to-one' if parent_unique and child_unique else 'one-to-many' if parent_unique else 'many-to-one' if child_unique else 'many-to-many',
                           parent_keys=len(parent), child_keys=len(child), child_rows=sum(child.values()),
                           unmatched_child_rows=unmatched, unmatched_parent_keys=sum(k not in child for k in parent),
                           inner_join_rows=joined, left_join_rows=joined+unmatched,
                           multiplication_excess=joined+unmatched-sum(child.values()),
                           status='BLOCKED_MULTIPLICATION' if not parent_unique else 'PARTIAL_UNMATCHED' if unmatched else 'STRUCTURAL_ONLY' if spec['temporal_evidence'].startswith('UNVERIFIED') else 'VALIDATED'))
    return result


def scan(root):
    sources = load_config(root)
    found = manifest(root)
    by_path = {s['original']:s for s in sources}
    incoming_config = root / 'app/config/incoming.json'
    if incoming_config.exists():
        by_id = {s['id']:s for s in sources}
        for e in json.loads(incoming_config.read_text(encoding='utf-8')).get('files',[]):
            if e.get('source_id') in by_id:
                by_path[e['path']] = by_id[e['source_id']]
    inventory, dictionary, states, summaries, sqlite_audit = [], [], {}, [], []
    for entry in found['files']:
        path = root / entry['path']
        if path.suffix.lower() == '.xlsx':
            available = sheets(path)
            for sheet_name, xml in available:
                raw = xlsx_rows(path, xml)
                _, columns, _ = next(raw)
                # Administrative layout is not a respondent table. Give blanks stable names.
                columns = [str(c) if c is not None else f'column_{i+1}' for i,c in enumerate(columns)]
                source = by_path.get(entry['path'])
                is_initial = source and entry['path']==source['original']
                dataset_id = (source['id'] if is_initial else source['id']+'@'+entry['sha256'][:12]) if source else path.stem + '/' + sheet_name
                print('AUDIT', dataset_id, flush=True)
                summary, cols, state = profile_rows(raw, columns, dataset_id, source)
                summary.update(path=entry['path'], sha256=entry['sha256'], sheet=sheet_name, sheet_count=len(available),
                               source_system=source['system'] if source else 'ADMIN', phase=source['phase'] if source else 'ADMIN',
                               grain=source['grain'] if source else 'administrative_layout',
                               key=json.dumps(source['key']) if source else '', reference_rows=source['reference_rows'] if source else None,
                               reference_difference=summary['rows']-source['reference_rows'] if source and source['reference_rows'] is not None else None)
                summaries.append(summary)
                inventory.append({k:v for k,v in summary.items() if k not in ('candidates','invalid_timestamps')})
                dictionary.extend(cols)
                if source:
                    if columns != source['columns']:
                        raise ValueError('SOURCE_SCHEMA_CHANGED: ' + dataset_id)
                    if is_initial:
                        states[dataset_id] = state
                    sidecar = path.with_suffix(path.suffix + '.manifest.json')
                    if sidecar.exists():
                        export = json.loads(sidecar.read_text(encoding='utf-8-sig'))
                        summary['export_metadata'] = {k:export.get(k) for k in ['status','fetched_rows','target_max_rows','unique_key','unique_key_count','duplicate_key_rows','end_of_data_detected','started_at_utc','finished_at_utc','failed_offsets']}
                        summary['export_row_count_matches'] = export.get('fetched_rows') == summary['rows']
        elif path.suffix.lower() == '.csv':
            with path.open(encoding='utf-8-sig', newline='') as stream:
                sample = stream.read(8192)
                stream.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
                except csv.Error:
                    dialect = csv.excel
                reader = csv.reader(stream, dialect)
                columns = next(reader)
                summary, cols, _ = profile_rows(((i+2,row,['text']*len(row)) for i,row in enumerate(reader)), columns, path.stem)
                summary.update(path=entry['path'], sheet='', sheet_count=0, source_system='ADMIN', phase='ADMIN',grain='administrative_table',key='',sha256=entry['sha256'])
                summaries.append(summary)
                inventory.append({k:v for k,v in summary.items() if k not in ('candidates','invalid_timestamps')})
                dictionary.extend(cols)
        elif path.suffix.lower() in ('.sqlite','.sqlite3','.db'):
            con = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
            try:
                info = dict(path=entry['path'], integrity=con.execute('PRAGMA integrity_check').fetchone()[0], tables=[])
                for name, sql in con.execute("SELECT name,sql FROM sqlite_master WHERE type='table'").fetchall():
                    cursor = con.execute('SELECT * FROM ' + q(name))
                    columns = [d[0] for d in cursor.description]
                    summary, cols, _ = profile_rows(((i+1,list(row),['null' if v is None else 'number' if isinstance(v,(int,float)) else 'text' for v in row]) for i,row in enumerate(cursor)), columns, 'existing_sqlite/' + name)
                    summary.update(path=entry['path'],sheet=name,sheet_count=0,source_system='TGR_CHECKPOINT',phase='partial',grain='export_checkpoint',key='',sha256=entry['sha256'])
                    inventory.append({k:v for k,v in summary.items() if k not in ('candidates','invalid_timestamps')})
                    dictionary.extend(cols)
                    info['tables'].append(dict(name=name,schema=sql,rows=summary['rows']))
                sqlite_audit.append(info)
            finally:
                con.close()
    relations = validate_relations(sources, states)
    # P1 modules should match each other independently of P0 coverage.
    p1 = [s for s in sources if s['id'].startswith('p1_')]
    p1_sets = {s['id']:set(states[s['id']]['full']) for s in p1}
    cross = [dict(left=p1[0]['id'], right=s['id'],left_only=len(p1_sets[p1[0]['id']]-p1_sets[s['id']]),right_only=len(p1_sets[s['id']]-p1_sets[p1[0]['id']])) for s in p1[1:]]
    write_csv(root / 'data/metadata/dataset_inventory.csv', inventory, list(dict.fromkeys(k for row in inventory for k in row)))
    write_csv(root / 'data/metadata/column_dictionary.csv', dictionary)
    write_csv(root / 'data/metadata/relationship_mapping.csv', relations)
    write_csv(root / 'docs/reports/database/relationship_validation.csv', relations)
    result = dict(generated_utc=utcnow(), datasets=summaries, sqlite=sqlite_audit, relationships=relations,p1_cross_validation=cross,
                  key_comparison='SHA-256 of positional normalized key tuple; raw values never reported')
    dump(root / 'data/metadata/audit_results.json', result)
    print('AUDIT_COMPLETE', len(sources), 'source datasets;', sum(s['rows'] for s in summaries if s['source_system'] in ('TGR','TCZ')), 'rows', flush=True)
    return result
