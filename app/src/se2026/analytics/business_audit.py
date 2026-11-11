"""Conservative local business-unit audit. Never mutates the census database.

Possible physical duplicates remain separate, with source links and review flags.
"""

import hashlib
import json
import re
import sqlite3
from functools import lru_cache
from collections import Counter, defaultdict
from pathlib import Path
from threading import Lock

from ..common import timestamp, sha256, sheets, xlsx_rows

COMPLETE = {'APPROVED BY Pengawas', 'COMPLETED BY Admin Kabupaten'}
SMALL_SCALES = {'UM', 'UMK', 'UMKM'}
NON_TARGET_BUILDINGS = {'4', '5', '6', '8'}
_population_lock = Lock()


def text(value):
    return str(value or '').strip()


def normalize(value):
    return ' '.join(re.findall(r'\w+', text(value).casefold()))


def classify(row, master, family=None, bku=None, version_count=1):
    """One input roster = one output; absence never becomes a fabricated unit."""
    flags = []
    status = text(row.get('kode_keberadaan_usaha'))
    scale = text(row.get('skala_usaha')).upper()
    lineage = 'BOTH' if family and bku else 'FAMILY' if family else 'BKU' if bku else 'UNRESOLVED'
    if not master:
        flags.append('ASSIGNMENT_NOT_FOUND')
    elif timestamp(master.get('versi_root_terbaru')) != row.get('__version_normalized'):
        flags.append('ROOT_VERSION_NOT_MATCHED')
    if version_count > 1:
        flags.append('MULTIPLE_ROSTER_VERSIONS')
    if str(row.get('__key_valid', 1)) != '1' or str(row.get('__conflict', 0)) != '0':
        flags.append('INVALID_OR_CONFLICTING_KEY')
    if lineage in ('BOTH', 'UNRESOLVED'):
        flags.append('PARENT_LINEAGE_' + lineage)
    if bku and text(bku.get('kode_penggunaan_bangunan')) in NON_TARGET_BUILDINGS:
        # A roster at a non-target building is a contradiction, not proof to delete it.
        flags.append('NON_TARGET_BUILDING_WITH_BUSINESS_ROSTER')
    if not text(row.get('nama_usaha')):
        flags.append('BUSINESS_NAME_MISSING')
    if scale == 'UB':
        flags.append('TGR_LARGE_BUSINESS')
    elif scale not in SMALL_SCALES:
        flags.append('SCALE_NOT_PROVEN')
    if master and text(master.get('kode_kabupaten')) != '6502':
        flags.append('OUTSIDE_BULUNGAN_OR_REGION_UNVERIFIED')
    found = status in ('1', '2')
    completed = bool(master and master.get('status_assignment') in COMPLETE)
    eligible = found and completed
    if not found:
        classification = {'00': 'NOT_FOUND', '0': 'NOT_FOUND', '3': 'CLOSED', '4': 'SOURCE_MARKED_DUPLICATE', '9': 'NON_RESPONSE'}.get(status, 'REVIEW_STATUS')
    elif not completed:
        classification = 'NOT_COMPLETED'
    elif flags:
        classification = 'REVIEW_REQUIRED'
    else:
        classification = 'LOCALLY_QUALIFIED'
    return dict(lineage=lineage, eligible=eligible, classification=classification, flags=flags,
                local_qualified=classification == 'LOCALLY_QUALIFIED')


def duplicate_groups(entities):
    """Multi-signal review candidates, never automatic physical identity merges."""
    signatures = defaultdict(list)
    for e in entities:
        name, code, village = normalize(e['name']), text(e['kbli']), text(e['village'])
        if not name or len(name)<4 or not code or not village:
            continue
        for evidence, value in [('NAME_KBLI_VILLAGE_ADDRESS', normalize(e['address'])),
                                ('NAME_KBLI_VILLAGE_PERSON', normalize(e['person']))]:
            if len(value)>=5:
                signatures[(evidence,name,code,village,value)].append(e)
        for evidence, value in [('NIB_NAME_KBLI',text(e['nib'])),('PRELIST_ID_NAME_KBLI',text(e['code_identity']))]:
            if value:
                signatures[(evidence,name,code,value)].append(e)
    groups = []
    candidate_ids = set()
    for signature, members in signatures.items():
        if len({(e['system'],e['assignment_id'],e['roster']) for e in members})<2:
            continue
        gid=hashlib.sha256(json.dumps(signature).encode()).hexdigest()
        groups.append((gid,signature[0],members))
        candidate_ids.update(e['entity_id'] for e in members)
    return groups, candidate_ids


def audit(database, output, root):
    database, root = Path(database).resolve(), Path(root).resolve()
    output = Path(output).resolve() if output is not None else None
    if output is not None and (output == database or not output.is_relative_to(root / 'data/app')):
        raise ValueError('AUDIT_OUTPUT_MUST_BE_SEPARATE_PRIVATE_APP_DATABASE')
    if output is not None and output.exists() and output.samefile(database):
        raise ValueError('AUDIT_OUTPUT_ALIAS_IS_PROTECTED')
    con = sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA query_only=ON')
    con.execute('BEGIN')
    def rows(table, columns='*'):
        return [dict(r) for r in con.execute('SELECT '+columns+' FROM "'+table+'"')]
    master_fields='assignment_id,versi_root_terbaru,kode_kabupaten,kode_kecamatan,kode_desa,kode_sls,kode_subsls,status_assignment,code_identity'
    masters = {r['assignment_id']: r for r in rows('mart_assignment_tgr',master_fields)}
    ub_masters = {r['assignment_id']: r for r in rows('mart_assignment_ub',master_fields)}
    businesses = rows('mart_usaha')
    family_rows = rows('mart_keluarga','assignment_id,__version_normalized')
    bku_rows = rows('mart_bku','assignment_id,__version_normalized,kode_penggunaan_bangunan,kode_keberadaan_bku')
    ub_rows = rows('mart_ub_a')
    families = {(r['assignment_id'], r['__version_normalized']): r for r in family_rows}
    buildings = {(r['assignment_id'], r['__version_normalized']): r for r in bku_rows}
    legal = {(r['assignment_id'], r['__version_normalized'], r['index1']): r for r in rows('mart_legalitas_usaha','assignment_id,__version_normalized,index1,nib')}
    versions = defaultdict(set)
    for r in businesses:
        versions[(r['assignment_id'], r['index1'])].add(r['__version_normalized'])
    entities = []
    for r in businesses:
        aid, version, index = r['assignment_id'], r['__version_normalized'], r['index1']
        key = (aid, version)
        master = masters.get(aid)
        state = classify(r, master, families.get(key), buildings.get(key), len(versions[(aid, index)]))
        entity_id = hashlib.sha256(json.dumps(['TGR', aid, version, index]).encode()).hexdigest()
        entities.append(dict(entity_id=entity_id, system='TGR', assignment_id=aid, version=version, roster=index,
                             name=r.get('nama_usaha'), kbli=r.get('kbli'), scale=r.get('skala_usaha'),
                             region=(master or {}).get('kode_subsls'), village=(master or {}).get('kode_desa'),
                             existence=r.get('kode_keberadaan_usaha'), workflow=(master or {}).get('status_assignment'),
                             nib=legal.get((aid, version, index), {}).get('nib'), code_identity=r.get('code_identity'),
                             address=r.get('alamat_usaha'), person=r.get('nama_pengusaha_pj'),
                             source_object='mart_usaha', source_row_id=r['__row_id'], source_hash=r.get('__source_sha256'),
                             import_id=r['__import_id'], **state))
    for r in ub_rows:
        aid = r['assignment_id']; master = ub_masters.get(aid, {})
        eligible = r.get('status_keberadaan') == '1. Ditemukan dan masih aktif' and master.get('status_assignment') in COMPLETE
        ub_flags = []
        if not master:
            ub_flags.append('ASSIGNMENT_NOT_FOUND')
        if not text(r.get('nama_usaha')):
            ub_flags.append('BUSINESS_NAME_MISSING')
        if text(master.get('kode_kabupaten')) != '6502':
            ub_flags.append('OUTSIDE_BULUNGAN_OR_REGION_UNVERIFIED')
        if str(r.get('__key_valid', 1)) != '1' or str(r.get('__conflict', 0)) != '0':
            ub_flags.append('INVALID_OR_CONFLICTING_KEY')
        entities.append(dict(entity_id=hashlib.sha256(json.dumps(['TCZ',aid]).encode()).hexdigest(), system='TCZ',
                             assignment_id=aid, version=None, roster=None, name=r.get('nama_usaha'), kbli=r.get('kbli_akhir'),
                             scale='UB', region=master.get('kode_subsls'), village=master.get('kode_desa'),
                             existence=r.get('status_keberadaan'), workflow=master.get('status_assignment'),
                             nib=r.get('nib'), code_identity=master.get('code_identity'), address=r.get('alamat_usaha'),
                             person=r.get('nama_penanggung_jawab'), lineage='UB', eligible=eligible,
                             classification=('REVIEW_REQUIRED' if ub_flags else 'LOCALLY_QUALIFIED') if eligible else 'NOT_ELIGIBLE',
                             flags=ub_flags, local_qualified=eligible and not ub_flags,
                             source_object='mart_ub_a', source_row_id=r['__row_id'], source_hash=r.get('__source_sha256'),
                             import_id=r['__import_id']))
    groups, candidate_ids = duplicate_groups(entities)
    for e in entities:
        e['duplicate_status']='POSSIBLE_DUPLICATE' if e['entity_id'] in candidate_ids else 'NO_MULTI_SIGNAL_CANDIDATE'
        if e['entity_id'] in candidate_ids:
            e['flags'].append('POSSIBLE_DUPLICATE')
            if e['local_qualified']:
                e['classification']='REVIEW_DUPLICATE'
                e['local_qualified']=False
    if output is None:
        con.close()
        return entities
    output.parent.mkdir(parents=True, exist_ok=True)
    target=sqlite3.connect(output)
    try:
        target.execute('PRAGMA foreign_keys=ON')
        target.execute('BEGIN IMMEDIATE')
        target.execute('CREATE TABLE IF NOT EXISTS audit_entities(entity_id TEXT PRIMARY KEY,system TEXT,assignment_id TEXT,version TEXT,roster TEXT,name TEXT,kbli TEXT,scale TEXT,region TEXT,village TEXT,existence TEXT,workflow TEXT,lineage TEXT,eligible INTEGER,classification TEXT,flags TEXT,local_qualified INTEGER,duplicate_status TEXT,source_object TEXT,source_row_id INTEGER,source_hash TEXT,import_id INTEGER)')
        target.execute('CREATE TABLE IF NOT EXISTS duplicate_members(group_id TEXT,evidence TEXT,entity_id TEXT REFERENCES audit_entities(entity_id),PRIMARY KEY(group_id,entity_id))')
        target.execute('CREATE TABLE IF NOT EXISTS audit_geography(entity_id TEXT PRIMARY KEY REFERENCES audit_entities(entity_id),kecamatan TEXT,desa TEXT,sls TEXT,subsls TEXT)')
        target.execute('DELETE FROM duplicate_members'); target.execute('DELETE FROM audit_geography'); target.execute('DELETE FROM audit_entities')
        columns=[r[1] for r in target.execute('PRAGMA table_info(audit_entities)')]
        target.executemany('INSERT INTO audit_entities VALUES('+','.join('?' for _ in columns)+')',
                           [[json.dumps(e[col]) if col=='flags' else e[col] for col in columns] for e in entities])
        target.executemany('INSERT INTO duplicate_members VALUES(?,?,?)',[(gid,evidence,e['entity_id']) for gid,evidence,members in groups for e in members])
        target.executemany('INSERT INTO audit_geography VALUES(?,?,?,?,?)',[
            (e['entity_id'],*((ub_masters if e['system']=='TCZ' else masters).get(e['assignment_id'],{}).get(col) for col in ['kode_kecamatan','kode_desa','kode_sls','kode_subsls']))
            for e in entities])
        target.execute('CREATE VIEW IF NOT EXISTS consolidated_business_units AS SELECT e.*,g.kecamatan,g.desa,g.sls,g.subsls FROM audit_entities e LEFT JOIN audit_geography g ON g.entity_id=e.entity_id')
        target.commit()
        integrity=target.execute('PRAGMA integrity_check').fetchone()[0]
    finally:
        target.close()
    inventory=[]
    for definition in json.loads((root/'app/config/sources.json').read_text(encoding='utf-8'))['sources']:
        sid=definition['id']
        inventory.append(dict(source=sid,path=definition['path'],columns=definition['columns'],
                              raw=con.execute('SELECT COUNT(*) FROM "raw_'+sid+'"').fetchone()[0],
                              clean=con.execute('SELECT COUNT(*) FROM "clean_'+sid+'"').fetchone()[0]))
    summary=dict(inventory=inventory,private_model=str(output.relative_to(root)),integrity=integrity,
                 raw_dtd=next(r['raw'] for r in inventory if r['source']=='usaha'),dtd_records=len(businesses),ub_records=len(ub_rows),
                 logical_roster_keys=len(versions),multiple_version_keys=sum(len(v)>1 for v in versions.values()),
                 lineage=dict(Counter(e['lineage'] for e in entities if e['system']=='TGR')),
                 eligible_by_lineage=dict(Counter(e['lineage'] for e in entities if e['system']=='TGR' and e['eligible'])),
                 classifications=dict(Counter(e['classification'] for e in entities)),
                 eligible_dtd=sum(e['eligible'] for e in entities if e['system']=='TGR'),
                 local_qualified_dtd=sum(e['local_qualified'] for e in entities if e['system']=='TGR'),
                 local_qualified_by_lineage=dict(Counter(e['lineage'] for e in entities if e['system']=='TGR' and e['local_qualified'])),
                 local_qualified_ub=sum(e['local_qualified'] for e in entities if e['system']=='TCZ'),
                 flags_eligible_dtd=dict(Counter(flag for e in entities if e['system']=='TGR' and e['eligible'] for flag in e['flags'])),
                 duplicate_candidate_records=len(candidate_ids),duplicate_candidate_groups=len(groups),
                 duplicate_groups_by_evidence=dict(Counter(evidence for _,evidence,_ in groups)),
                 cross_system_groups=sum(len({e['system'] for e in members})>1 for _,_,members in groups),
                 definite_physical_duplicates=0,physical_uniqueness_status='NOT_PROVEN',
                 source_activity_status='FILTERED_ACTIVE_AT_HISTORICAL_EXPORT_NOT_LOCALLY_RECHECKABLE',
                 building_usage=dict(Counter(text(r['kode_penggunaan_bangunan']) or 'MISSING' for r in bku_rows)),
                 building_existence=dict(Counter(text(r['kode_keberadaan_bku']) for r in bku_rows)),
                 imports=[dict(r) for r in con.execute('SELECT source_id,sha256,raw_rows,clean_rows,imported_utc,export_kind FROM imported_files')])
    summary['eligible_ub'] = sum(e['eligible'] for e in entities if e['system']=='TCZ')
    summary['eligible_scale'] = dict(Counter(text(e['scale']) or 'MISSING' for e in entities if e['system']=='TGR' and e['eligible']))
    summary['existence_tgr'] = dict(Counter(text(e['existence']) for e in entities if e['system']=='TGR'))
    summary['workflow_tgr'] = dict(Counter(text(e['workflow']) for e in entities if e['system']=='TGR'))
    summary['existence_ub'] = dict(Counter(text(e['existence']) for e in entities if e['system']=='TCZ'))
    summary['workflow_ub'] = dict(Counter(text(e['workflow']) for e in entities if e['system']=='TCZ'))
    summary['census_integrity'] = con.execute('PRAGMA integrity_check').fetchone()[0]
    summary['census_foreign_key_violations'] = len(con.execute('PRAGMA foreign_key_check').fetchall())
    summary['candidate_records_by_lineage'] = dict(Counter(e['lineage'] for e in entities if e['entity_id'] in candidate_ids))
    summary['candidate_groups_by_lineage'] = dict(Counter('+'.join(sorted({e['lineage'] for e in members})) for _,_,members in groups))
    summary['eligible_review_dtd'] = summary['eligible_dtd']-summary['local_qualified_dtd']
    summary['raw_file_validation'] = []
    for item in inventory:
        if item['source'] not in ('assignment_tgr','assignment_ub','usaha','keluarga','bku','ub_a','ub_b','ub_c'):
            continue
        file = root/item['path']
        sheet = sheets(file)[0][1]
        row_count = sum(1 for number, values, _ in xlsx_rows(file, sheet) if number>1 and any(v is not None for v in values))
        imported_hashes = {r[0] for r in con.execute('SELECT sha256 FROM imported_files WHERE source_id=?',(item['source'],))}
        summary['raw_file_validation'].append(dict(source=item['source'],file_rows=row_count,raw_rows=item['raw'],clean_rows=item['clean'],checksum_matches_import=sha256(file) in imported_hashes))
    con.close()
    return summary


@lru_cache(maxsize=2)
def _population(database, root, size, modified):
    # Cache is private process memory and is invalidated by the census file stamp.
    # Runtime uses the same classifier as the persisted audit, never an old report.
    return {(e['system'], e['assignment_id'], e['version'], e['roster']):
            (int(e['local_qualified']), e['lineage'], int(e['eligible']))
            for e in audit(database, None, root)}


def register_population(connection, database, root):
    """One shared population predicate for registry, directory and KBLI queries."""
    path = Path(database).resolve()
    stamp = path.stat()
    states = None

    def state(system, assignment, version, roster):
        nonlocal states
        if states is None:
            with _population_lock:
                states = _population(str(path), str(Path(root).resolve()), stamp.st_size, stamp.st_mtime_ns)
        if system in ('ub', 'TCZ'):
            return states.get(('TCZ', assignment, None, None), (0, 'UNRESOLVED', 0))
        return states.get(('TGR', assignment, version, roster), (0, 'UNRESOLVED', 0))

    connection.create_function('AUDIT_QUALIFIED', 4, lambda *key: state(*key)[0], deterministic=True)
    connection.create_function('AUDIT_LINEAGE', 4, lambda *key: state(*key)[1], deterministic=True)
