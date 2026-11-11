"""Transactional, immutable snapshot ingestion driven by audited schemas."""
from __future__ import annotations

import json
import sqlite3
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .common import digest, dump, identity, is_identity, q, records, sha256, sheets, timestamp, utcnow, xlsx_rows
from .scanner import load_config


class PipelineError(Exception):
    """Safe, non-respondent error codes suitable for logs."""


def local_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise PipelineError('PATH_OUTSIDE_WORKSPACE')
    return path


def type_mapping(root, source):
    import csv
    with (root/'data/metadata/column_dictionary.csv').open(encoding='utf-8-sig',newline='') as stream:
        observed = {r['column']:json.loads(r['observed_types']) for r in csv.DictReader(stream) if r['dataset']==source['id']}
    mapping = {}
    for col in source['columns']:
        kinds = set(observed.get(col,{}))
        if is_identity(col) or col in ('tanggal_dibuat','tanggal_diubah','versi_root_terbaru'):
            mapping[col] = 'TEXT'
        elif kinds and kinds <= {'integer_text','boolean'}:
            mapping[col] = 'INTEGER'
        elif kinds and kinds <= {'number','integer_text','decimal_text','boolean'}:
            # SQLite REAL cannot preserve every source decimal. Declared type
            # DECIMAL_TEXT deliberately has TEXT affinity and exact lexical value.
            mapping[col] = 'DECIMAL_TEXT'
        else:
            mapping[col] = 'TEXT'
    return mapping


def clean_value(value, column, sql_type):
    if value is None or str(value).strip() == '':
        return None
    if sql_type in ('INTEGER','DECIMAL_TEXT'):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            raise PipelineError('NUMERIC_SCHEMA_DRIFT') from None
        if not number.is_finite():
            raise PipelineError('NONFINITE_NUMERIC_VALUE')
        if sql_type=='INTEGER' and number == number.to_integral_value() and -(2**63) <= number <= 2**63-1:
            return int(number)
        if sql_type=='INTEGER':
            raise PipelineError('INTEGER_SCHEMA_DRIFT_OR_OVERFLOW')
        if abs(number.adjusted())>4000:
            raise PipelineError('NUMERIC_EXPONENT_OUT_OF_RANGE')
        text = format(number,'f')
        if '.' in text:
            text = text.rstrip('0').rstrip('.')
        return '0' if number==0 else text
    return identity(value) if is_identity(column) else str(value)


def incoming_entries(root):
    path = root/'app/config/incoming.json'
    return json.loads(path.read_text(encoding='utf-8')).get('files',[]) if path.exists() else []


def plan_sync(root):
    sources = load_config(root)
    by_id = {s['id']:s for s in sources}
    audit_path = root/'data/metadata/audit_results.json'
    if not audit_path.exists():
        raise PipelineError('SCAN_REQUIRED')
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    audited = {(d['path'],d['sha256']):d for d in audit['datasets'] if d['source_system'] in ('TGR','TCZ')}
    entries = [dict(source_id=s['id'],path=s['path'],audit_path=s['original'],export_kind='audited_initial_export',evidence='Initial audited export; not assumed a complete snapshot',sha256=None) for s in sources]
    incoming = incoming_entries(root)
    declared = set()
    for e in incoming:
        if e.get('source_id') not in by_id or e.get('export_kind') not in ('unknown','partial','delta','full_snapshot'):
            raise PipelineError('INVALID_INCOMING_DECLARATION')
        path = local_path(root,e['path'])
        if not path.is_relative_to((root/'data/incoming').resolve()):
            raise PipelineError('INCOMING_PATH_REQUIRED')
        if not e.get('evidence') or len(e.get('sha256','')) != 64:
            raise PipelineError('INCOMING_EVIDENCE_AND_SHA_REQUIRED')
        if e['path'] in declared:
            raise PipelineError('DUPLICATE_INCOMING_PATH')
        declared.add(e['path'])
        entries.append(dict(**e,audit_path=e['path']))
    incoming_paths = {p.relative_to(root).as_posix() for p in (root/'data/incoming').rglob('*.xlsx')} if (root/'data/incoming').exists() else set()
    if incoming_paths-declared:
        raise PipelineError('UNMAPPED_INCOMING_EXPORT')
    db = root/'data/processed/se2026.sqlite'
    known = set()
    active = {}
    if db.exists():
        c = sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
        try:
            known = set(c.execute('SELECT source_id,sha256 FROM imported_files'))
            active = dict(c.execute('SELECT source_id,import_id FROM active_imports'))
        finally:
            c.close()
    seen = set()
    for e in entries:
        source = by_id[e['source_id']]
        path = local_path(root,e['path'])
        if not path.is_file():
            raise PipelineError('SOURCE_FILE_MISSING: '+source['id'])
        checksum = sha256(path)
        if e['sha256'] and checksum != e['sha256']:
            raise PipelineError('DECLARED_SHA_MISMATCH: '+source['id'])
        e['sha256'] = checksum
        audited_dataset = audited.get((e['audit_path'],checksum))
        if not audited_dataset:
            raise PipelineError('SOURCE_CHANGED_OR_NOT_AUDITED: '+source['id'])
        if e['export_kind']=='audited_initial_export' and sha256(root/source['original']) != checksum:
            raise PipelineError('RAW_COPY_AND_ORIGINAL_DIVERGED: '+source['id'])
        if audited_dataset.get('export_row_count_matches') is False:
            raise PipelineError('AUDIT_EXPORT_COUNT_MISMATCH: '+source['id'])
        e.update(expected_rows=audited_dataset['rows'],status='DUPLICATE' if (source['id'],checksum) in known or (source['id'],checksum) in seen else 'NEW_SNAPSHOT' if source['id'] in active else 'INITIAL_IMPORT')
        seen.add((source['id'],checksum))
    return dict(generated_utc=utcnow(),database=db.relative_to(root).as_posix(),entries=entries)


def schema(con, sources, mappings):
    con.executescript('''
        CREATE TABLE IF NOT EXISTS batches (
            batch_id TEXT PRIMARY KEY, started_utc TEXT NOT NULL, completed_utc TEXT,
            pipeline_version TEXT NOT NULL, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS imported_files (
            import_id INTEGER PRIMARY KEY, source_id TEXT NOT NULL, sha256 TEXT NOT NULL,
            batch_id TEXT NOT NULL REFERENCES batches(batch_id), source_path TEXT NOT NULL,
            export_kind TEXT NOT NULL, evidence TEXT NOT NULL, raw_rows INTEGER NOT NULL DEFAULT 0,
            clean_rows INTEGER NOT NULL DEFAULT 0, imported_utc TEXT NOT NULL,
            UNIQUE(source_id,sha256));
        CREATE TABLE IF NOT EXISTS active_imports (
            source_id TEXT PRIMARY KEY, import_id INTEGER NOT NULL UNIQUE REFERENCES imported_files(import_id));
        CREATE TABLE IF NOT EXISTS activation_history (
            activation_id INTEGER PRIMARY KEY, source_id TEXT NOT NULL,
            old_import_id INTEGER REFERENCES imported_files(import_id), new_import_id INTEGER NOT NULL REFERENCES imported_files(import_id),
            activated_utc TEXT NOT NULL, batch_id TEXT NOT NULL REFERENCES batches(batch_id));
    ''')
    for s in sources:
        sid, cols = s['id'],s['columns']
        raw_cols = ','.join(q(col)+' TEXT' for col in cols)
        clean_cols = ','.join(q(col)+' '+mappings[sid][col] for col in cols)
        con.execute(f'''CREATE TABLE IF NOT EXISTS {q('raw_'+sid)} (
            __import_id INTEGER NOT NULL REFERENCES imported_files(import_id),
            __row_number INTEGER NOT NULL, __row_hash BLOB NOT NULL,
            __clean_hash BLOB NOT NULL, __cell_types TEXT NOT NULL,
            {raw_cols}, PRIMARY KEY(__import_id,__row_number))''')
        con.execute(f'''CREATE TABLE IF NOT EXISTS {q('clean_'+sid)} (
            __row_id INTEGER PRIMARY KEY, __import_id INTEGER NOT NULL REFERENCES imported_files(import_id),
            __clean_hash BLOB NOT NULL, __key BLOB, __version_normalized TEXT,
            __key_valid INTEGER NOT NULL, __conflict INTEGER NOT NULL DEFAULT 0,
            {clean_cols}, UNIQUE(__import_id,__clean_hash))''')
        con.execute(f'CREATE INDEX IF NOT EXISTS {q("ix_key_"+sid)} ON {q("clean_"+sid)}(__import_id,__key)')


def connect(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    con = sqlite3.connect(path)
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=10000')
    con.execute('PRAGMA journal_mode=DELETE')
    con.execute('PRAGMA synchronous=FULL')
    return con


def import_file(con, root, entry, source, mapping, batch_id, fail_after=None):
    path = local_path(root,entry['path'])
    if sha256(path) != entry['sha256']:
        raise PipelineError('SOURCE_CHANGED_BEFORE_READ')
    available = sheets(path)
    if len(available)!=1 or available[0][0]!=source['sheet']:
        raise PipelineError('SHEET_SCHEMA_DRIFT')
    first = next(xlsx_rows(path,available[0][1]))[1]
    columns = source['columns']
    if first != columns:
        raise PipelineError('COLUMN_SCHEMA_DRIFT')
    import_id = con.execute('''INSERT INTO imported_files(source_id,sha256,batch_id,source_path,export_kind,evidence,imported_utc)
        VALUES(?,?,?,?,?,?,?)''',(source['id'],entry['sha256'],batch_id,entry['path'],entry['export_kind'],entry['evidence'],utcnow())).lastrowid
    raw_fields = ['__import_id','__row_number','__row_hash','__clean_hash','__cell_types']+columns
    clean_fields = ['__import_id','__clean_hash','__key','__version_normalized','__key_valid']+columns
    raw_sql = 'INSERT INTO '+q('raw_'+source['id'])+' ('+','.join(map(q,raw_fields))+') VALUES('+','.join('?' for _ in raw_fields)+')'
    clean_sql = 'INSERT OR IGNORE INTO '+q('clean_'+source['id'])+' ('+','.join(map(q,clean_fields))+') VALUES('+','.join('?' for _ in clean_fields)+')'
    raws,cleans,count = [],[],0
    for number,values,types in records(path,available[0][1],len(columns)):
        cleaned = [clean_value(v,col,mapping[col]) for col,v in zip(columns,values)]
        version = timestamp(values[columns.index('assignment_date_modified')]) if 'assignment_date_modified' in columns else None
        normalized = list(cleaned)
        if 'assignment_date_modified' in columns:
            normalized[columns.index('assignment_date_modified')] = version
        key_values = [normalized[columns.index(col)] for col in source['key']]
        valid = all(v is not None for v in key_values)
        key = digest(key_values) if valid else None
        # Invalid timestamps must not collapse distinct original invalid values.
        if 'assignment_date_modified' in columns and version is None:
            normalized[columns.index('assignment_date_modified')] = values[columns.index('assignment_date_modified')]
        clean_hash = digest(normalized)
        raws.append((import_id,number,digest([values,types]),clean_hash,json.dumps(types,separators=(',',':')),*values))
        cleans.append((import_id,clean_hash,key,version,int(valid),*cleaned))
        count += 1
        if len(raws)>=1000:
            con.executemany(raw_sql,raws)
            con.executemany(clean_sql,cleans)
            raws.clear()
            cleans.clear()
        if fail_after is not None and count>=fail_after:
            raise PipelineError('SYNTHETIC_INJECTED_FAILURE')
    con.executemany(raw_sql,raws)
    con.executemany(clean_sql,cleans)
    if count != entry['expected_rows'] or sha256(path)!=entry['sha256']:
        raise PipelineError('SOURCE_CHANGED_DURING_IMPORT_OR_ROW_COUNT_MISMATCH')
    table = q('clean_'+source['id'])
    con.execute(f'''UPDATE {table} SET __conflict=1 WHERE __import_id=? AND __key IN
        (SELECT __key FROM {table} WHERE __import_id=? AND __key IS NOT NULL GROUP BY __key HAVING COUNT(*)>1)''',(import_id,import_id))
    clean_count = con.execute(f'SELECT COUNT(*) FROM {table} WHERE __import_id=?',(import_id,)).fetchone()[0]
    con.execute('UPDATE imported_files SET raw_rows=?,clean_rows=? WHERE import_id=?',(count,clean_count,import_id))
    return import_id,count,clean_count


def snapshot_change(con, source_id, new_id, old_id):
    table = q('clean_'+source_id)
    if old_id is None:
        count = con.execute('SELECT COUNT(*) FROM '+table+' WHERE __import_id=?',(new_id,)).fetchone()[0]
        return dict(keys_new_to_active=count,keys_absent_from_new=0,changed_payload_keys=0,comparison='initial baseline')
    added = con.execute(f'''SELECT COUNT(*) FROM {table} n WHERE n.__import_id=? AND n.__key_valid=1 AND n.__conflict=0
        AND NOT EXISTS(SELECT 1 FROM {table} p WHERE p.__import_id=? AND p.__key=n.__key AND p.__conflict=0)''',(new_id,old_id)).fetchone()[0]
    absent = con.execute(f'''SELECT COUNT(*) FROM {table} p WHERE p.__import_id=? AND p.__key_valid=1 AND p.__conflict=0
        AND NOT EXISTS(SELECT 1 FROM {table} n WHERE n.__import_id=? AND n.__key=p.__key AND n.__conflict=0)''',(old_id,new_id)).fetchone()[0]
    changed = con.execute(f'''SELECT COUNT(*) FROM {table} n JOIN {table} p ON n.__key=p.__key
        WHERE n.__import_id=? AND p.__import_id=? AND n.__conflict=0 AND p.__conflict=0 AND n.__clean_hash<>p.__clean_hash''',(new_id,old_id)).fetchone()[0]
    return dict(keys_new_to_active=added,keys_absent_from_new=absent,changed_payload_keys=changed,comparison='snapshot difference only; absent does not mean deleted')


def sync(root, apply=False, activate=False, fail_after=None):
    plan = plan_sync(root)
    dump(root/'docs/reports/sync/sync_dry_run.json',plan)
    if not apply:
        return dict(mode='dry-run',new=sum(e['status']!='DUPLICATE' for e in plan['entries']),duplicate=sum(e['status']=='DUPLICATE' for e in plan['entries']))
    if activate:
        proposals = [e for e in plan['entries'] if e['export_kind']!='audited_initial_export']
        if any(e['export_kind']!='full_snapshot' for e in proposals):
            raise PipelineError('ACTIVATION_REQUIRES_DECLARED_FULL_SNAPSHOT')
        if len({e['source_id'] for e in proposals})!=len(proposals):
            raise PipelineError('AMBIGUOUS_MULTIPLE_SNAPSHOTS_FOR_ACTIVATION')
    new = [e for e in plan['entries'] if e['status']!='DUPLICATE']
    # Re-running an unchanged sync has no database writes or empty batch.
    if not new and not activate:
        result = dict(mode='apply',new=0,duplicate=len(plan['entries']),status='NO_CHANGES',generated_utc=utcnow())
        dump(root/'docs/reports/sync/last_sync.json',result)
        return result
    sources = load_config(root)
    by_id = {s['id']:s for s in sources}
    mappings = {s['id']:type_mapping(root,s) for s in sources}
    db = root/plan['database']
    con = connect(db)
    batch_id = str(uuid.uuid4())
    counts = []
    try:
        # Schema setup is idempotent. Respondent rows, activation and mart DDL share one transaction.
        schema(con,sources,mappings)
        con.execute('BEGIN IMMEDIATE')
        con.execute('INSERT INTO batches VALUES(?,?,?,?,?)',(batch_id,utcnow(),None,'0.1.0','IMPORTING'))
        for entry in plan['entries']:
            old = con.execute('SELECT import_id FROM active_imports WHERE source_id=?',(entry['source_id'],)).fetchone()
            if entry['status']=='DUPLICATE':
                import_id = con.execute('SELECT import_id FROM imported_files WHERE source_id=? AND sha256=?',(entry['source_id'],entry['sha256'])).fetchone()[0]
            else:
                print('IMPORT',entry['source_id'],entry['expected_rows'],flush=True)
                import_id,raw_count,clean_count = import_file(con,root,entry,by_id[entry['source_id']],mappings[entry['source_id']],batch_id,fail_after=fail_after)
                previous = con.execute('SELECT raw_rows,clean_rows FROM imported_files WHERE import_id=?',(old[0],)).fetchone() if old else (0,0)
                counts.append(dict(source=entry['source_id'],raw_rows=raw_count,clean_rows=clean_count,deduplicated=raw_count-clean_count,
                                   previous_raw_rows=previous[0],previous_clean_rows=previous[1],raw_row_difference=raw_count-previous[0],clean_row_difference=clean_count-previous[1],
                                   **snapshot_change(con,entry['source_id'],import_id,old[0] if old else None)))
            activate_this = old is None and entry['export_kind']=='audited_initial_export' or activate and entry['export_kind']=='full_snapshot'
            if activate_this and (not old or old[0]!=import_id):
                con.execute('INSERT OR REPLACE INTO active_imports VALUES(?,?)',(entry['source_id'],import_id))
                con.execute('INSERT INTO activation_history(source_id,old_import_id,new_import_id,activated_utc,batch_id) VALUES(?,?,?,?,?)',
                            (entry['source_id'],old[0] if old else None,import_id,utcnow(),batch_id))
        from .transformation import build_marts
        build_marts(con,sources)
        if con.execute('PRAGMA foreign_key_check').fetchone():
            raise PipelineError('FOREIGN_KEY_CHECK_FAILED')
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise PipelineError('INTEGRITY_CHECK_FAILED')
        con.execute('UPDATE batches SET completed_utc=?,status=? WHERE batch_id=?',(utcnow(),'COMPLETE',batch_id))
        con.commit()
    except BaseException:
        con.rollback()
        dump(root/'docs/reports/sync/sync_failure.json',dict(batch_id=batch_id,status='ROLLED_BACK',generated_utc=utcnow(),error='IMPORT_TRANSACTION_FAILED_NO_RESPONDENT_VALUES_LOGGED'))
        raise
    finally:
        con.close()
    result = dict(mode='apply',batch_id=batch_id,new=len(new),duplicate=len(plan['entries'])-len(new),counts=counts,status='COMPLETE',generated_utc=utcnow())
    # Preserve successful history, including the initial baseline summary.
    dump(root/f'docs/reports/sync/sync_batches/{batch_id}.json',result)
    dump(root/'docs/reports/sync/last_sync.json',result)
    from .common import write_csv
    write_csv(root/f'docs/reports/sync/sync_batches/{batch_id}_changes.csv',counts)
    write_csv(root/'data/metadata/type_mapping.csv',[dict(dataset=s['id'],column=col,clean_type=mappings[s['id']][col],policy='identifiers kept TEXT; exact numeric conversion; RAW unchanged') for s in sources for col in s['columns']])
    return result
