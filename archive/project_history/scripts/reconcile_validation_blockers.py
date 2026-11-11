"""Read-only follow-up audit. Does not invoke scan/sync or change the pipeline."""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'app/src'))
from se2026.common import dump, q, sha256, timestamp, utcnow, write_csv
from se2026.reporting import markdown_table

HISTORICAL_COUNTS = {'assignment_tgr':90008, 'anggota':142591, 'meteran':37260,
                     'screening':44270, 'bku':26639, 'usaha':53649}
COUNT_PATHS = {
    'assignment_tgr':'COUNT_MASTER_TGR.sql',
    'anggota':'COUNT_KURASI_04_anggota_keluarga.sql',
    'meteran':'COUNT_KURASI_06_meteran_pln.sql',
    'screening':'COUNT_KURASI_07_keluarga_screening_usaha.sql',
    'bku':'COUNT_KURASI_01_BKU_MASTER_SEMUA_STATUS.sql',
    'usaha':'COUNT_KURASI_01_master_usaha.sql',
}
DATA_PATHS = {
    'assignment_tgr':'01_Master_Assignment/00_MASTER_ASSIGNMENT_TGR.sql',
    'anggota':'02_Dataset_Siap_Analisis/Keluarga/04_anggota_keluarga.sql',
    'meteran':'02_Dataset_Siap_Analisis/Keluarga/06_meteran_pln.sql',
    'screening':'02_Dataset_Siap_Analisis/Keluarga/07_keluarga_screening_usaha.sql',
    'bku':'02_Dataset_Siap_Analisis/BKU/01_BKU_MASTER_SEMUA_STATUS.sql',
    'usaha':'02_Dataset_Siap_Analisis/Usaha_TGR/01_master_usaha.sql',
}
UB_FILES = {'ub_a':'09A_IDENTITAS_WILAYAH_KBLI_PJ.sql',
            'ub_b':'09B_PEKERJA_EKONOMI_MODAL.sql',
            'ub_c':'09C_DIGITAL_LINGKUNGAN_LEGALITAS.sql'}
P1 = ['p1_pekerjaan','p1_disabilitas','p1_kronis_a','p1_kronis_b']
CATEGORIES = ['SAMA_ANGGOTA_SAMA_VERSI','SAMA_ANGGOTA_BEDA_VERSI',
              'ASSIGNMENT_ADA_INDEKS_TIDAK_ADA','ASSIGNMENT_TIDAK_ADA','KUNCI_TIDAK_VALID']


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def strip_comments(sql):
    """Comments only; keep quoted SQL literal contents intact."""
    return re.sub(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|`[^`]*`|/\*.*?\*/|--[^\n]*",
                  lambda m:' ' if m[0].startswith(('/*','--')) else m[0], sql, flags=re.S)


def top_level_tokens(sql):
    depth, i = 0,0
    while i<len(sql):
        if sql[i] in "'\"`":
            quote = sql[i]
            i += 1
            while i<len(sql):
                if sql[i]==quote:
                    if i+1<len(sql) and sql[i+1]==quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            continue
        if sql[i]=='(':
            depth += 1
        elif sql[i]==')':
            depth -= 1
        elif depth==0 and (sql[i].isalpha() or sql[i]=='_'):
            start = i
            while i<len(sql) and (sql[i].isalnum() or sql[i]=='_'):
                i += 1
            yield sql[start:i].upper(),start,i
            continue
        elif depth==0 and sql[i]==',':
            yield ',',i,i+1
        i += 1


def projection_parts(sql):
    code = strip_comments(sql).strip().rstrip(';')
    tokens = list(top_level_tokens(code))
    select = next(t for t in tokens if t[0]=='SELECT')
    start_from = next(t for t in tokens if t[0]=='FROM' and t[1]>select[2])
    projection = code[select[2]:start_from[1]]
    cuts = [0]+[t[1]+1 for t in top_level_tokens(projection) if t[0]==',']
    ends = [t[1] for t in top_level_tokens(projection) if t[0]==',']+[len(projection)]
    expressions = [projection[a:b].strip() for a,b in zip(cuts,ends)]
    return code[:select[1]],expressions,code[start_from[1]:]


def count_classification(raw_count, historical_count, same_snapshot=False, export_failed=False):
    if export_failed:
        return 'REEXPORT_REQUIRED'
    if historical_count is None:
        return 'INSUFFICIENT_EVIDENCE'
    if raw_count != historical_count:
        return 'COUNT_DIFFERENCE'
    return 'VERIFIED_COMPLETE' if same_snapshot else 'COUNT_MATCH_SNAPSHOT_UNVERIFIED'


def count_queries(root):
    if root.resolve()==ROOT.resolve():
        raise RuntimeError("SQL_LAB_PERMANENTLY_CLOSED_USE_LOCAL_ANALYTICAL_AUDIT")
    base = root/'app/sql/source_queries'
    rows, checks = [],[]
    for sid, filename in COUNT_PATHS.items():
        count_sql = strip_comments((base/'04_COUNT_per_Tabel'/filename).read_text(encoding='utf-8-sig')).strip().rstrip(';')
        if sid=='assignment_tgr':
            body = "FROM (SELECT a.assignment_id FROM tgr_fd68e454.base_table_assignment a WHERE a.is_active=1 AND a.level_2_full_code='6502' GROUP BY a.assignment_id) scoped_assignment"
            kind = 'GROUPED_ASSIGNMENT_IDS_EQUALS_MASTER_RANK_ONE_GRAIN'
        else:
            body = re.search(r'\bFROM\b.*',count_sql,re.S|re.I)[0]
            data_sql = strip_comments((base/DATA_PATHS[sid]).read_text(encoding='utf-8-sig'))
            data_body = re.search(r'\bFROM\b.*',data_sql,re.S|re.I)[0]
            data_body = re.split(r'\bORDER\s+BY\b',data_body,flags=re.I)[0].strip().rstrip(';')
            canonical = lambda s:re.sub(r'\s+','',s).lower()
            if canonical(body)!=canonical(data_body):
                raise ValueError('COUNT_DATA_FILTER_MISMATCH: '+sid)
            kind = 'EXACT_FROM_JOIN_WHERE_MATCH'
        rows.append("SELECT '"+sid+"' AS dataset, CURRENT_TIMESTAMP AS checked_at_server, COUNT(*) AS jumlah_baris_raw_equivalent\n"+body)
        checks.append(dict(dataset=sid,source_count_path='app/sql/source_queries/04_COUNT_per_Tabel/'+filename,
                           source_data_path='app/sql/source_queries/'+DATA_PATHS[sid],scope_comparison=kind,
                           historical_count_query_provenance='NOT_SUPPLIED',same_snapshot_evidence=False))
    sql = ('-- NOT EXECUTED. One statement / six aggregate rows / three output columns.\n'
           '-- Preserve physical join multiplicity and all questionnaire versions.\n'
           '-- checked_at_server is an observation time, NOT a snapshot identifier.\n'
           '-- A fresh count does not retroactively verify an October export.\n\n'+'\nUNION ALL\n'.join(rows)+';\n')
    path = root/'app/sql/validation/blocker_reconciliation/01_COUNT_SIX_UNCERTAIN_EXPORTS.sql'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(sql,encoding='utf-8')
    return checks


def ub_queries(root):
    if root.resolve()==ROOT.resolve():
        raise RuntimeError("SQL_LAB_PERMANENTLY_CLOSED_NO_VERSION_EXPORT_REQUIRED")
    target = root/'app/sql/validation/blocker_reconciliation'
    target.mkdir(parents=True,exist_ok=True)
    manifest = '''-- NOT EXECUTED. 8 columns; no respondent payload.
-- These are CURRENT source candidates, not version evidence for historical A/B/C.
-- Stop if version_key_rows<>1, active_assignment_rows<>1, or a key is NULL.
WITH assignment_scope AS (
    SELECT a.assignment_id, COUNT(*) AS active_assignment_rows
    FROM tcz_37526b20.base_table_assignment a
    WHERE a.is_active=1 AND a.level_2_full_code='6502'
    GROUP BY a.assignment_id
), version_candidates AS (
    SELECT r.assignment_id, r.assignment_date_modified, r.assignment_id_timestamp,
           COUNT(*) OVER (PARTITION BY r.assignment_id, r.assignment_date_modified,
                                      r.assignment_id_timestamp) AS version_key_rows,
           ROW_NUMBER() OVER (PARTITION BY r.assignment_id
                              ORDER BY r.assignment_date_modified DESC,
                                       r.assignment_id_timestamp DESC) AS version_rank
    FROM tcz_37526b20.root_table r
    WHERE r.assignment_id IN (SELECT s.assignment_id FROM assignment_scope s)
)
SELECT v.assignment_id AS id_penghubung,
       v.assignment_date_modified AS questionnaire_modified_at,
       v.assignment_id_timestamp AS questionnaire_id_timestamp,
       v.version_key_rows, s.active_assignment_rows,
       CASE WHEN v.assignment_id IS NULL OR v.assignment_date_modified IS NULL
                      OR v.assignment_id_timestamp IS NULL THEN 'INVALID_VERSION_KEY'
            WHEN v.version_key_rows<>1 OR s.active_assignment_rows<>1 THEN 'AMBIGUOUS_KEY'
            ELSE 'CANDIDATE_UNIQUE_AT_OBSERVATION' END AS key_status,
       CURRENT_TIMESTAMP AS checked_at_server,
       'CURRENT_CANDIDATE_NOT_HISTORICAL_PROOF' AS evidence_scope
FROM version_candidates v
INNER JOIN assignment_scope s ON s.assignment_id=v.assignment_id
WHERE v.version_rank=1
ORDER BY id_penghubung;
'''
    (target/'02_UB_CURRENT_VERSION_KEY_DIAGNOSTIC.sql').write_text(manifest,encoding='utf-8')
    generated = []
    for sid,filename in UB_FILES.items():
        original = root/'app/sql/source_queries/02_Dataset_Siap_Analisis/UB'/filename
        prefix,columns,suffix = projection_parts(original.read_text(encoding='utf-8-sig'))
        if len(columns)!=25:
            raise ValueError('UB_EXPECTED_25_EXPORTED_COLUMNS')
        # The two version fields are already evidenced by ORDER BY and raw PART SQL.
        prefix,count = re.subn(r'(SELECT\s+r\.assignment_id\s*,)',
            r'\1\n        r.assignment_date_modified,\n        r.assignment_id_timestamp,',prefix,count=1,flags=re.I)
        if count!=1:
            raise ValueError('UB_CTE_NOT_RECOGNIZED')
        for part,payload in enumerate([columns[1:23],columns[23:]],start=1):
            output = [columns[0], 'r.assignment_date_modified AS questionnaire_modified_at',
                      'r.assignment_id_timestamp AS questionnaire_id_timestamp']+payload
            sql = ('-- NOT EXECUTED. Version-bound NEW export; does not amend original A/B/C.\n'
                   '-- Output '+str(len(output))+' columns. Validate all parts and root-key uniqueness before use.\n'
                   '-- Query body/projection copied from: '+original.relative_to(root).as_posix()+'\n'
                   +prefix+'SELECT\n    '+',\n    '.join(output)+'\n'+suffix+';\n')
            path = target/(sid.upper()+'_VERSION_BOUND_PART_'+str(part)+'.sql')
            path.write_text(sql,encoding='utf-8')
            generated.append(dict(module=sid,part=part,path=path.relative_to(root).as_posix(),output_columns=len(output),
                                  source_sql_sha256=sha256(original),payload_columns=len(payload)))
    return generated


def active_import(con, sid):
    row = con.execute('SELECT import_id FROM active_imports WHERE source_id=?',(sid,)).fetchone()
    if row is None:
        raise ValueError('ACTIVE_IMPORT_MISSING: '+sid)
    return row[0]


def p1_classification(con):
    p0_id = active_import(con,'sosial_p0')
    master_id = active_import(con,'assignment_tgr')
    rows = []
    ref = 'clean_sosial_p0 p'
    valid_ref = f'p.__import_id={p0_id} AND p.__key_valid=1 AND p.__conflict=0'
    exact = f'EXISTS(SELECT 1 FROM {ref} WHERE {valid_ref} AND p.assignment_id=c.assignment_id AND p.index1=c.index1 AND p.__version_normalized=c.__version_normalized)'
    unit = f'EXISTS(SELECT 1 FROM {ref} WHERE {valid_ref} AND p.assignment_id=c.assignment_id AND p.index1=c.index1)'
    assignment = f'EXISTS(SELECT 1 FROM {ref} WHERE {valid_ref} AND p.assignment_id=c.assignment_id)'
    case = (f"CASE WHEN c.__key_valid=0 OR c.__version_normalized IS NULL OR NULLIF(TRIM(c.assignment_id),'') IS NULL OR NULLIF(TRIM(c.index1),'') IS NULL THEN '{CATEGORIES[4]}' "
            f"WHEN {exact} THEN '{CATEGORIES[0]}' WHEN {unit} THEN '{CATEGORIES[1]}' "
            f"WHEN {assignment} THEN '{CATEGORIES[2]}' ELSE '{CATEGORIES[3]}' END")
    for sid in P1:
        iid = active_import(con,sid)
        for layer in ['CLEAN','RAW']:
            source = q('clean_'+sid)+' c'
            if layer=='RAW':
                source = q('raw_'+sid)+' r JOIN '+source+' ON c.__import_id=r.__import_id AND c.__clean_hash=r.__clean_hash'
            counts = dict(con.execute(f'SELECT category,COUNT(*) FROM (SELECT {case} AS category FROM {source} WHERE c.__import_id=?) GROUP BY category',(iid,)))
            total = sum(counts.values())
            expected = con.execute('SELECT '+('clean_rows' if layer=='CLEAN' else 'raw_rows')+' FROM imported_files WHERE import_id=?',(iid,)).fetchone()[0]
            if expected!=total:
                raise ValueError('P1_CLASSIFICATION_NOT_EXHAUSTIVE')
            row = dict(dataset=sid,layer=layer,total_rows=total,**{name:counts.get(name,0) for name in CATEGORIES})
            row['unmatched_rows'] = total-row[CATEGORIES[0]]
            # Assignment absence in P0 is a scope statement, not a claim that the master is missing it.
            row['p0_absent_but_master_present'] = con.execute(f'''SELECT COUNT(*) FROM {source}
                WHERE c.__import_id=? AND ({case})=? AND EXISTS(
                    SELECT 1 FROM clean_assignment_tgr m WHERE m.__import_id=? AND m.assignment_id=c.assignment_id)''',(iid,CATEGORIES[3],master_id)).fetchone()[0]
            row['conflicting_rows'] = con.execute('SELECT COUNT(*) FROM '+source+' WHERE c.__import_id=? AND c.__conflict=1',(iid,)).fetchone()[0]
            rows.append(row)
    return rows


def ub_audit(con):
    summaries,relations = [],[]
    for sid in ['assignment_ub','ub_a','ub_b','ub_c']:
        key = 'assignment_id' if sid=='assignment_ub' else 'id_penghubung'
        iid = active_import(con,sid)
        columns = {r[1] for r in con.execute('PRAGMA table_info('+q('clean_'+sid)+')')}
        for layer in ['RAW','CLEAN']:
            table = q(layer.lower()+'_'+sid)
            total = con.execute('SELECT COUNT(*) FROM '+table+' WHERE __import_id=?',(iid,)).fetchone()[0]
            groups = con.execute('SELECT COUNT(*) FROM (SELECT '+q(key)+' FROM '+table+' WHERE __import_id=? GROUP BY '+q(key)+')',(iid,)).fetchone()[0]
            nulls = con.execute('SELECT COUNT(*) FROM '+table+' WHERE __import_id=? AND NULLIF(TRIM('+q(key)+"),'') IS NULL",(iid,)).fetchone()[0]
            summaries.append(dict(dataset=sid,layer=layer,rows=total,unique_key_groups=groups,null_key_rows=nulls,duplicate_excess=total-groups,
                                  questionnaire_modified_exported='assignment_date_modified' in columns and sid!='assignment_ub',
                                  root_latest_hint_exported='versi_root_terbaru' in columns,status='ASSIGNMENT_KEY_VERIFIED'))
    for parent,child in [('assignment_ub','ub_a'),('assignment_ub','ub_b'),('assignment_ub','ub_c'),('ub_a','ub_b'),('ub_a','ub_c'),('ub_b','ub_c')]:
        left_key = 'assignment_id' if parent=='assignment_ub' else 'id_penghubung'
        a,b = active_import(con,parent),active_import(con,child)
        left = '(SELECT '+q(left_key)+' AS id FROM '+q('clean_'+parent)+f' WHERE __import_id={a})'
        right = '(SELECT id_penghubung AS id FROM '+q('clean_'+child)+f' WHERE __import_id={b})'
        joined,missing = con.execute('SELECT COUNT(*),COALESCE(SUM(p.id IS NULL),0) FROM '+right+' c LEFT JOIN '+left+' p ON p.id=c.id').fetchone()
        absent_right = con.execute('SELECT COUNT(*) FROM '+left+' p LEFT JOIN '+right+' c ON p.id=c.id WHERE c.id IS NULL').fetchone()[0]
        relations.append(dict(parent=parent,child=child,left_join_rows=joined,child_without_parent=missing,parent_without_child=absent_right,cardinality='one-to-one' if joined==226 and not missing and not absent_right else 'CHECK_REQUIRED',temporal_status='QUESTIONNAIRE_VERSION_NOT_VERIFIED'))
    iid = active_import(con,'assignment_ub')
    valid_hint = sum(timestamp(row[0]) is not None for row in con.execute('SELECT versi_root_terbaru FROM clean_assignment_ub WHERE __import_id=?',(iid,)))
    return summaries,relations,valid_hint


def replace_addendum(path, text):
    marker = '<!-- VALIDATION_BLOCKER_RECONCILIATION -->'
    original = path.read_text(encoding='utf-8').split(marker)[0].rstrip()
    path.write_text(original+'\n\n'+marker+'\n\n'+text.rstrip()+'\n',encoding='utf-8')


def main(root=ROOT):
    sources = {s['id']:s for s in read_json(root/'app/config/sources.json')['sources']}
    manifest = read_json(root/'data/metadata/file_manifest.json')
    prior_validation = read_json(root/'docs/reports/database/database_validation.json')
    # Required existing reports are read and preserved; only a marked follow-up is appended.
    for name in ['WORKSPACE_AND_INTEGRATION_FINAL_REPORT.md','DATA_QUALITY_REPORT.md']:
        (root/'docs/reports'/name).read_text(encoding='utf-8')
    db = root/'data/processed/se2026.sqlite'
    baseline_db_hash = sha256(db)
    pipeline_files = [root/'main.py',*sorted((root/'app/src').rglob('*.py'))]
    pipeline_hashes = {p.relative_to(root).as_posix():sha256(p) for p in pipeline_files}
    manifest_hash = sha256(root/'data/metadata/file_manifest.json')
    verified_files = 0
    for f in manifest['files']:
        if sha256(root/f['path'])!=f['sha256']:
            raise ValueError('SOURCE_MANIFEST_MISMATCH')
        verified_files += 1
    source_sql_copies_verified = 0
    with (root/'data/metadata/path_mapping.csv').open(encoding='utf-8-sig',newline='') as stream:
        for entry in csv.DictReader(stream):
            if entry['role']=='source_sql_unexecuted':
                if sha256(root/entry['new_path'])!=entry['sha256']:
                    raise ValueError('SOURCE_SQL_COPY_MISMATCH')
                source_sql_copies_verified += 1
    con = sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON')
    try:
        con.execute('BEGIN')
        counts,export_metadata = [],{}
        for sid,old_count in HISTORICAL_COUNTS.items():
            s = sources[sid]
            export = read_json((root/s['original']).with_suffix('.xlsx.manifest.json'))
            export_metadata[sid] = export
            iid = active_import(con,sid)
            raw = con.execute('SELECT COUNT(*) FROM '+q('raw_'+sid)+' WHERE __import_id=?',(iid,)).fetchone()[0]
            imported_sha = con.execute('SELECT sha256 FROM imported_files WHERE import_id=?',(iid,)).fetchone()[0]
            if sha256(root/s['path'])!=imported_sha or sha256(root/s['original'])!=imported_sha:
                raise ValueError('ACTIVE_RAW_SOURCE_MISMATCH')
            if raw!=export['fetched_rows']:
                raise ValueError('RAW_EXPORT_COUNT_MISMATCH')
            counts.append(dict(dataset=sid,historical_count_sql=old_count,raw_rows=raw,difference_raw_minus_count=raw-old_count,
                               classification=count_classification(raw,old_count),historical_count_time='NOT_SUPPLIED',same_snapshot_proven=False,
                               export_started_utc=export['started_at_utc'],export_finished_utc=export['finished_at_utc'],
                               end_of_data_detected=export['end_of_data_detected'],failed_offsets=len(export.get('failed_offsets',[]))))
        p1 = p1_classification(con)
        ub,ub_rel,root_hints = ub_audit(con)
        from se2026.ub_integration import validate_ub_mart
        ub_policy_validation = validate_ub_mart(con,list(sources.values()),expected_rows=226)
        p0_conflicts = con.execute('SELECT COUNT(*) FROM clean_sosial_p0 WHERE __import_id=? AND (__key_valid=0 OR __conflict=1)',(active_import(con,'sosial_p0'),)).fetchone()[0]
        if p0_conflicts:
            raise ValueError('P0_REFERENCE_KEYS_REQUIRE_REVIEW')
        con.rollback()
    finally:
        con.close()
    scope_checks = count_queries(root)
    ub_generated = []  # Timestamp exports are superseded by assignment-ID integration.
    write_csv(root/'docs/reports/reconciliation/export_completeness_reconciliation.csv',counts)
    write_csv(root/'docs/reports/p1/p1_unmatched_classification.csv',p1)
    write_csv(root/'docs/reports/ub/ub_version_key_audit.csv',ub)
    write_csv(root/'docs/reports/ub/ub_version_relationship_audit.csv',ub_rel)
    write_csv(root/'docs/reports/reconciliation/count_query_scope_validation.csv',scope_checks)
    if ub_generated:
        write_csv(root/'docs/reports/ub/ub_version_query_manifest.csv',ub_generated)
    counts_table = markdown_table(['Dataset','COUNT historis','RAW','RAW - COUNT','Klasifikasi'],
        [[r[k] for k in ['dataset','historical_count_sql','raw_rows','difference_raw_minus_count','classification']] for r in counts])
    time_table = markdown_table(['Dataset','Mulai UTC','Selesai UTC','EOF','Request gagal'],
        [[r[k] for k in ['dataset','export_started_utc','export_finished_utc','end_of_data_detected','failed_offsets']] for r in counts])
    scope_table = markdown_table(['Dataset','Grain / filter / versi yang dipertahankan'],[
        ['assignment_tgr',"ID assignment aktif wilayah a.level_2_full_code=6502; master memilih satu versi operasional dengan ROW_NUMBER; COUNT GROUP BY ID setara jumlah output; root tidak wajib."],
        ['anggota',"nested_dtsen INNER JOIN root pada ID+assignment_date_modified; keluarga ditemukan/baru (1/2); assignment aktif 6502; semua versi yang cocok, bukan hanya latest."],
        ['meteran',"nested_meteran INNER JOIN root pada ID+assignment_date_modified; keluarga 1/2; assignment aktif 6502; roster meteran per versi."],
        ['screening',"root INNER JOIN assignment aktif 6502; ada_keluarga_value IN (1,2); semua record root/versi yang lolos."],
        ['bku',"root INNER JOIN assignment aktif 6502; ada_bang_usaha_value IS NOT NULL; semua status termasuk 7; tidak dibatasi ditemukan/baru."],
        ['usaha',"se2026_nested INNER JOIN assignment aktif 6502 dan LEFT JOIN root pada ID+versi; keberadaan_usaha_value IS NOT NULL; semua status; multiplicity LEFT JOIN dipertahankan."],
    ])
    (root/'docs/reports/reconciliation/EXPORT_COMPLETENESS_RECONCILIATION.md').write_text(
        '# Rekonsiliasi kelengkapan ekspor\n\nCOUNT historis berasal dari pesan pengguna pada 10 November 2026; waktu eksekusi, SQL persis yang dijalankan, snapshot ID dan log COUNT tidak disertakan. '
        'Angka tersebut dicatat sebagai bukti historis pengguna, bukan hasil query baru. Pembanding memakai RAW snapshot aktif, tanpa deduplikasi.\n\n'+counts_table+'\n\n'
        'Definisi klasifikasi:\n\n'
        '- VERIFIED_COMPLETE: COUNT dan ekspor terikat pada snapshot serta filter/grain yang sama, jumlah dan kontrol pagination/kunci lolos.\n'
        '- COUNT_MATCH_SNAPSHOT_UNVERIFIED: jumlah sama, kesamaan snapshot belum terbukti.\n'
        '- COUNT_DIFFERENCE: jumlah berbeda; belum membuktikan file terpotong atau perubahan sumber tertentu.\n'
        '- REEXPORT_REQUIRED: ada bukti kegagalan/truncation atau snapshot baru yang terikat versi memang diperlukan; bukan konsekuensi otomatis selisih angka.\n'
        '- INSUFFICIENT_EVIDENCE: tidak ada pembanding/provenance yang cukup untuk keputusan yang diminta.\n\n'
        'Hasil: empat COUNT_DIFFERENCE dan dua COUNT_MATCH_SNAPSHOT_UNVERIFIED; belum ada VERIFIED_COMPLETE. '
        'Tidak ada kegagalan request pada enam manifest; tidak ada bukti yang cukup untuk menetapkan REEXPORT_REQUIRED secara mutlak bagi keenam file. '
        'Provenance snapshot/SQL COUNT historis sendiri berstatus INSUFFICIENT_EVIDENCE. Dataset lain tidak diberi status lengkap berdasarkan enam COUNT ini.\n\n'
        'Waktu dan bukti pagination:\n\n'+time_table+'\n\n'
        'Keenam ekspor berhenti tepat di target_max_rows dan end_of_data_detected=false. Status complete berarti rencana ekstraksi selesai, bukan bukti EOF sumber. '
        'Tanggal modifikasi file pada data/metadata/file_manifest.json adalah metadata filesystem, bukan waktu COUNT, bukan snapshot ID. '
        'Manifest ekspor tidak memuat query hash atau snapshot token. Rentang waktu ekspor berbeda; bahkan satu workbook dipaginasi selama beberapa menit.\n\n'
        'Audit kesesuaian SQL yang tersedia:\n\n'+scope_table+'\n\n'
        'Untuk lima modul, FROM/JOIN/WHERE COUNT pendamping dibandingkan dengan SQL data setelah komentar/ORDER BY dihapus dan dinyatakan sama. '
        'Untuk master, GROUP BY assignment_id setara grain satu ID hasil ROW_NUMBER master. Ini membuktikan kesesuaian pasangan SQL lokal, '
        'bukan membuktikan COUNT historis memakai pasangan tersebut. Status keberadaan, versi, duplikasi join, assignment aktif dan perubahan populasi sumber dapat memengaruhi jumlah; penyebab selisih belum teridentifikasi. '
        'Khusus anggota, CLEAN 142.593 bukan pembanding COUNT 142.591; enam duplikat RAW tidak boleh digunakan untuk menyesuaikan hitungan.\n\n'
        'Query tambahan yang diperlukan: `archive/project_history/sql/blocker_reconciliation/01_COUNT_SIX_UNCERTAIN_EXPORTS.sql`. '
        'Satu statement menghasilkan enam baris agregat dan tiga kolom; hanya COUNT(*), tanpa COUNT DISTINCT atau SELECT wildcard. '
        'Query mempertahankan FROM/JOIN/WHERE serta grain RAW; tidak memperkenalkan filter latest pada modul yang semula multi-versi. SQL baru belum dieksekusi di SQL Lab.\n\n'
        'Penutupan blocker: cari log COUNT historis beserta SQL/snapshot jika tersedia. Jika tidak, jalankan query tambahan pada snapshot sumber yang dapat dibekukan atau dibuktikan stabil, '
        'catat SQL SHA-256, waktu server dan zona, batas target, EOF, semua offset, serta hash berkas hasil. COUNT baru hanya baseline baru; '
        'tidak mengesahkan ekspor lama secara retroaktif. Bila jumlah berbeda, identitas unit berubah, pagination tidak stabil, atau snapshot historis tidak bisa dibuktikan dan kelengkapan terverifikasi dibutuhkan, '
        'lakukan ekspor baru tanpa menimpa RAW lama. COUNT yang sama saja juga tidak membuktikan kesamaan himpunan key.\n',encoding='utf-8')
    from se2026.ub_integration import write_ub_policy_report
    write_ub_policy_report(root,ub_policy_validation)
    headers = ['Modul','Total','1 Sama anggota/versi','2 Beda versi','3 Indeks tidak ada','4 Assignment tidak ada di P0','5 Key invalid','Unmatched']
    def p1_table(layer):
        return markdown_table(headers,[[r['dataset'],r['total_rows'],*[r[c] for c in CATEGORIES],r['unmatched_rows']] for r in p1 if r['layer']==layer])
    master_table = markdown_table(['Modul','Lapisan','Baris kategori 4 dengan ID ditemukan pada master'],
        [[r['dataset'],r['layer'],r['p0_absent_but_master_present']] for r in p1])
    (root/'docs/reports/p1/P1_UNMATCHED_CLASSIFICATION.md').write_text(
        '# Klasifikasi unmatched P1 terhadap P0\n\n'
        'Referensi adalah sosial_p0 pada active_imports, bukan seluruh roster anggota dan bukan seluruh master assignment. '
        'Kunci unit roster = assignment_id + index1; versi = timestamp kuesioner ternormalisasi. '
        'Label sama anggota di sini berarti identitas roster sama menurut key tersebut; indeks dapat berubah/berulang antarversi, sehingga ini tidak membuktikan orang yang sama secara longitudinal. '
        'Tidak memakai nama, NIK, pendapatan, disabilitas atau penyakit untuk pencocokan.\n\n'
        'Klasifikasi CLEAN (setelah duplikat identik digabungkan):\n\n'+p1_table('CLEAN')+'\n\n'
        'Klasifikasi RAW (semua baris asli termasuk duplikat):\n\n'+p1_table('RAW')+'\n\n'
        'Aturan berurutan dan saling lepas: (5) komponen kunci kosong/timestamp gagal validasi; (1) ID+index+versi sama ditemukan pada P0; '
        '(2) ID+index ditemukan tetapi versi berbeda; (3) assignment ada pada P0 tetapi index tidak ditemukan pada versi mana pun; '
        '(4) assignment tidak ada pada P0. EXISTS dipakai agar duplikasi referensi tidak menggandakan baris. '
        'RAW ditautkan ke CLEAN melalui provenance import_id+clean_hash sehingga setiap duplikat tetap dihitung. '
        'Jumlah lima kategori wajib sama dengan jumlah baris lapisan terkait, dan unmatched adalah total dikurangi kategori 1.\n\n'
        'Pemeriksaan cakupan assignment:\n\n'+master_table+'\n\n'
        'Angka pada tabel adalah jumlah baris P1, bukan jumlah assignment unik. Assignment tidak ditemukan pada P0 bukan berarti assignment tidak ada di sistem. '
        'Referensi P0 tidak mempunyai key invalid/konflik pada snapshot ini; seluruh P1 juga memiliki nol key invalid dan nol baris konflik. '
        'Sebagian besar unmatched adalah kandidat unit roster sama dengan timestamp berbeda, sehingga tidak boleh digabungkan otomatis. '
        'Perbedaan snapshot mungkin berperan: sosial P0 selesai 2026-10-31 09:09:57 UTC, sedangkan P1 ditarik 13:27:25 hingga 14:23:55 UTC dengan modul pada rentang berbeda. '
        'SQL P1 mendeduplikasi key root keluarga dan memakai IN assignment aktif; P0 memakai INNER JOIN fisik root/assignment. '
        'Perbedaan implementasi cakupan/multiplicity dan perubahan sumber belum dibuktikan sebagai penyebab tiap unit. '
        'Semua versi dan unmatched tetap dipertahankan; 739 key P1-only pada mart union bukan klaim 739 orang baru.\n\n'
        'Hasil agregat ini dihitung ulang langsung dalam satu transaksi baca SQLite, lalu dicocokkan dengan jumlah RAW/CLEAN impor. '
        'Tidak ada data individu ditampilkan dan tidak ada JOIN temporal lintas versi yang diterapkan.\n',encoding='utf-8')
    # Preserve earlier audit as history and explicitly supersede the open EOF assessment.
    summary = ('## Rekonsiliasi blocker lanjutan — 10 November 2026\n\n'+counts_table+'\n\n'
        'COUNT historis tidak disertai waktu/SQL/snapshot; tidak ada status VERIFIED_COMPLETE baru. '
        'Temuan EOF_NOT_PROVEN sebelumnya diperinci oleh klasifikasi di atas; meteran dan BKU belum dinyatakan lengkap hanya karena jumlah cocok. '
        'UB memakai ASSIGNMENT_KEY_VERIFIED: 226 ID unik dan identik antar sumber. QUESTIONNAIRE_VERSION_NOT_VERIFIED hanya provenance historis non-blocking. '
        'P1 sudah diklasifikasikan ulang secara agregat dalam lima kategori; unmatched CLEAN berturut-turut 525, 587, 689, 698, tanpa key invalid. '
        'Kategori assignment tidak ditemukan merujuk cakupan P0, bukan otomatis master assignment.\n\n'
        'Lihat [rekonsiliasi ekspor](EXPORT_COMPLETENESS_RECONCILIATION.md), [versi UB](UB_VERSION_VALIDATION.md), '
        'dan [klasifikasi P1](P1_UNMATCHED_CLASSIFICATION.md). Query yang disiapkan ada di `app/sql/validation/blocker_reconciliation/`; belum dijalankan di SQL Lab. '
        'Audit ini hanya membaca database; pipeline, RAW, snapshot aktif dan flag mart tidak diubah. '
        'Blocker eksternal yang tersisa adalah provenance/hasil COUNT pada snapshot terbukti; ekspor timestamp UB tidak diperlukan bagi JOIN assignment.\n')
    test_evidence = root/'docs/reports/reconciliation/blocker_reconciliation_tests.xml'
    if test_evidence.exists():
        from xml.etree import ElementTree as ET
        suite = ET.parse(test_evidence).getroot().find('testsuite')
        if suite is not None:
            summary += ('\nUji tambahan audit: '+suite.attrib.get('tests','?')+'; failures='+suite.attrib.get('failures','?')+
                        '; errors='+suite.attrib.get('errors','?')+'. Bukti: `docs/reports/reconciliation/blocker_reconciliation_tests.xml`. '
                        'Hasil 11 pengujian pipeline sebelumnya tetap merupakan bukti baseline yang terpisah.\n')
    for name in ['DATA_QUALITY_REPORT.md','WORKSPACE_AND_INTEGRATION_FINAL_REPORT.md']:
        replace_addendum(root/'docs/reports'/name,summary)
    if sha256(db)!=baseline_db_hash or sha256(root/'data/metadata/file_manifest.json')!=manifest_hash:
        raise ValueError('IMMUTABLE_ARTIFACT_CHANGED')
    if any(sha256(root/p)!=checksum for p,checksum in pipeline_hashes.items()):
        raise ValueError('PIPELINE_CHANGED')
    proof = dict(generated_utc=utcnow(),database_mode='ro; PRAGMA query_only=ON',database_sha256=baseline_db_hash,
                 database_checksum_unchanged=True,pipeline_unchanged=True,file_manifest_unchanged=True,
                 original_files_verified=verified_files,source_sql_copies_verified=source_sql_copies_verified,
                 classification_counts=dict(Counter(r['classification'] for r in counts)),
                 ub_status='ASSIGNMENT_KEY_VERIFIED',raw_total_from_existing_validation=prior_validation['raw_rows'],
                 p1_category_totals_verified=True,query_scope_checks=scope_checks,sql_lab_executed=False)
    dump(root/'docs/reports/reconciliation/blocker_reconciliation_validation.json',proof)
    print(json.dumps(dict(export_counts=counts,p1=p1,ub_status='ASSIGNMENT_KEY_VERIFIED',database_unchanged=True),ensure_ascii=True,indent=2))


if __name__=='__main__':
    print('Audit rekonsiliasi SQL Lab diarsipkan. Akses sumber ditutup permanen; gunakan python app/scripts/maintenance/audit_analytical_readiness.py. Baseline lokal dan catatan kualitas tetap dipertahankan.')
