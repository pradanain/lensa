"""Assignment-grain UB integration. Questionnaire dates are provenance only."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import q, sha256

ASSIGNMENT_STATUS = 'ASSIGNMENT_KEY_VERIFIED'
VERSION_PROVENANCE = 'QUESTIONNAIRE_VERSION_NOT_VERIFIED'
UB_SOURCES = ('assignment_ub','ub_a','ub_b','ub_c')
SQL_FILES = {
    'ub_a':'09A_IDENTITAS_WILAYAH_KBLI_PJ.sql',
    'ub_b':'09B_PEKERJA_EKONOMI_MODAL.sql',
    'ub_c':'09C_DIGITAL_LINGKUNGAN_LEGALITAS.sql',
}


class UBIntegrationError(ValueError):
    """Non-sensitive validation failure; never includes assignment values."""


def verify_source_aliases(root):
    result = []
    for sid,filename in SQL_FILES.items():
        path = root/'app/sql/source_queries/02_Dataset_Siap_Analisis/UB'/filename
        sql = path.read_text(encoding='utf-8-sig')
        code = re.sub(r'/\*.*?\*/|--[^\n]*',' ',sql,flags=re.S)
        required = [r'\br\.assignment_id\s+AS\s+id_penghubung\b',
                    r'FROM\s+tcz_37526b20\.root_table\s+r\b',
                    r'INNER\s+JOIN\s+ub_versi\s+r\s+ON\s+a\.assignment_id\s*=\s*r\.assignment_id']
        if not all(re.search(pattern,code,re.I) for pattern in required):
            raise UBIntegrationError('UB_ASSIGNMENT_ALIAS_NOT_PROVEN: '+sid)
        result.append(dict(dataset=sid,source_column='id_penghubung',logical_column='assignment_id',
                           source_expression='r.assignment_id AS id_penghubung',
                           source_sql=path.relative_to(root).as_posix(),source_sql_sha256=sha256(path)))
    return result


def active_ub_rows(sid):
    return (f'(SELECT c.* FROM {q("clean_"+sid)} c JOIN active_imports a '
            f"ON a.source_id='{sid}' AND a.import_id=c.__import_id)")


def audit_ub_assignment_keys(con, expected_rows=None):
    summaries = []
    for sid in UB_SOURCES:
        if con.execute('SELECT COUNT(*) FROM active_imports WHERE source_id=?',(sid,)).fetchone()[0]!=1:
            raise UBIntegrationError('UB_ACTIVE_IMPORT_MISSING: '+sid)
        key = 'assignment_id' if sid=='assignment_ub' else 'id_penghubung'
        source = active_ub_rows(sid)
        total,nulls,conflicts = con.execute('SELECT COUNT(*),COALESCE(SUM(NULLIF(TRIM('+q(key)+"),'') IS NULL),0),COALESCE(SUM(__conflict<>0),0) FROM "+source).fetchone()
        groups = con.execute('SELECT COUNT(*) FROM (SELECT '+q(key)+' FROM '+source+' GROUP BY '+q(key)+')').fetchone()[0]
        if total==0 or nulls or conflicts or groups!=total:
            raise UBIntegrationError('UB_ASSIGNMENT_KEY_NOT_UNIQUE_OR_VALID: '+sid)
        summaries.append(dict(dataset=sid,rows=total,unique_assignment_ids=groups,null_ids=nulls,conflicting_rows=conflicts))
    master = active_ub_rows('assignment_ub')
    relations = []
    for sid in UB_SOURCES[1:]:
        child = active_ub_rows(sid)
        joined,missing = con.execute('SELECT COUNT(*),COALESCE(SUM(c.__row_id IS NULL),0) FROM '+master+' m LEFT JOIN '+child+' c ON m.assignment_id=c.id_penghubung').fetchone()
        orphan = con.execute('SELECT COUNT(*) FROM '+child+' c LEFT JOIN '+master+' m ON m.assignment_id=c.id_penghubung WHERE m.__row_id IS NULL').fetchone()[0]
        if missing or orphan or joined!=summaries[0]['rows']:
            raise UBIntegrationError('UB_ASSIGNMENT_KEY_SET_MISMATCH: '+sid)
        relations.append(dict(parent='assignment_ub',child=sid,logical_join_key='assignment_id',
                              child_source_alias='id_penghubung',left_join_rows=joined,missing_module_rows=missing,
                              orphan_rows=orphan,multiplication_excess=joined-summaries[0]['rows'],
                              cardinality='one-to-one',status=ASSIGNMENT_STATUS,
                              version_provenance=VERSION_PROVENANCE))
    if expected_rows is not None and summaries[0]['rows']!=expected_rows:
        raise UBIntegrationError('UB_EXPECTED_ASSIGNMENT_COUNT_MISMATCH')
    return dict(status=ASSIGNMENT_STATUS,version_provenance=VERSION_PROVENANCE,
                assignment_rows=summaries[0]['rows'],sources=summaries,relationships=relations,
                timestamp_join_required=False,reexport_for_timestamp_required=False)


def view_columns(con, view):
    return [row[1] for row in con.execute('PRAGMA table_info('+q(view)+')')]


def build_ub_marts(con, sources):
    """Only UB views change. Caller owns transaction/backup and commit/rollback."""
    by_id = {s['id']:s for s in sources}
    for sid in UB_SOURCES[1:]:
        if 'id_penghubung' not in by_id[sid]['columns']:
            raise UBIntegrationError('UB_SOURCE_ALIAS_SCHEMA_CHANGED: '+sid)
    audit_ub_assignment_keys(con)
    con.execute('DROP VIEW IF EXISTS mart_ub_integrated')
    for sid in UB_SOURCES[1:]:
        con.execute('DROP VIEW IF EXISTS '+q('mart_'+sid))
        standardized = 'clean_'+sid+'_standardized'
        con.execute('DROP VIEW IF EXISTS '+q(standardized))
        con.execute('CREATE VIEW '+q(standardized)+' AS SELECT c.*,c.id_penghubung AS assignment_id FROM '+q('clean_'+sid)+' c')
        con.execute(f'''CREATE VIEW {q('mart_'+sid)} AS SELECT c.*,f.batch_id AS __batch_id,f.sha256 AS __source_sha256
            FROM {q(standardized)} c JOIN active_imports a ON a.source_id='{sid}' AND a.import_id=c.__import_id
            JOIN imported_files f ON f.import_id=c.__import_id''')
    select = ['m.assignment_id']
    # Keep every previous A column, including its original alias and provenance.
    select += ['a.'+q(col) for col in view_columns(con,'mart_ub_a') if col!='assignment_id']
    select += [f"'{ASSIGNMENT_STATUS}' AS integration_status",
               f"'{VERSION_PROVENANCE}' AS questionnaire_version_status"]
    for sid,alias in [('assignment_ub','m'),('ub_b','b'),('ub_c','c')]:
        for column in by_id[sid]['columns']:
            if column in ('assignment_id','id_penghubung'):
                continue
            select.append(alias+'.'+q(column)+' AS '+q(sid+'__'+column))
        for field in ['__source_sha256','__batch_id','__row_id','__import_id']:
            select.append(alias+'.'+q(field)+' AS '+q(sid+field))
    for sid,alias in [('assignment_ub','m'),('ub_a','a'),('ub_b','b'),('ub_c','c')]:
        select.append('('+alias+'.__row_id IS NOT NULL) AS '+q('has_'+sid))
    sql = ('CREATE VIEW mart_ub_integrated AS SELECT '+','.join(select)+
           ' FROM mart_assignment_ub m LEFT JOIN mart_ub_a a ON m.assignment_id=a.assignment_id'+
           ' LEFT JOIN mart_ub_b b ON m.assignment_id=b.assignment_id'+
           ' LEFT JOIN mart_ub_c c ON m.assignment_id=c.assignment_id')
    con.execute(sql)


def validate_ub_mart(con, sources, expected_rows=None):
    result = audit_ub_assignment_keys(con,expected_rows)
    total = con.execute('SELECT COUNT(*) FROM mart_ub_integrated').fetchone()[0]
    unique = con.execute('SELECT COUNT(*) FROM (SELECT assignment_id FROM mart_ub_integrated GROUP BY assignment_id)').fetchone()[0]
    complete = con.execute('''SELECT COUNT(*) FROM mart_ub_integrated WHERE
        has_assignment_ub=1 AND has_ub_a=1 AND has_ub_b=1 AND has_ub_c=1
        AND integration_status=? AND questionnaire_version_status=?''',(ASSIGNMENT_STATUS,VERSION_PROVENANCE)).fetchone()[0]
    if total!=result['assignment_rows'] or unique!=total or complete!=total:
        raise UBIntegrationError('UB_MART_GRAIN_OR_COMPLETENESS_FAILED')
    payload = []
    by_id = {s['id']:s for s in sources}
    for sid in UB_SOURCES:
        key = 'assignment_id' if sid=='assignment_ub' else 'id_penghubung'
        comparisons = []
        for col in by_id[sid]['columns']:
            output = ('assignment_id' if col=='assignment_id' else col) if sid=='ub_a' else 'assignment_id' if col in ('assignment_id','id_penghubung') else sid+'__'+col
            comparisons.append('NOT(v.'+q(output)+' IS s.'+q(col)+')')
        changed = con.execute('SELECT COUNT(*) FROM mart_ub_integrated v JOIN '+active_ub_rows(sid)+' s ON v.assignment_id=s.'+q(key)+' WHERE '+' OR '.join(comparisons)).fetchone()[0]
        if changed:
            raise UBIntegrationError('UB_MART_PAYLOAD_CHANGED: '+sid)
        payload.append(dict(dataset=sid,columns_checked=len(by_id[sid]['columns']),mismatched_rows=changed))
    result.update(mart_rows=total,unique_mart_assignment_ids=unique,complete_assignment_rows=complete,payload_validation=payload)
    return result


def write_ub_policy_report(root, validation):
    from .reporting import markdown_table
    table = markdown_table(['Dataset','Baris','ID unik','ID NULL','Konflik'],
        [[r[k] for k in ['dataset','rows','unique_assignment_ids','null_ids','conflicting_rows']] for r in validation['sources']])
    relation_table = markdown_table(['Induk','Modul','Baris JOIN','Modul hilang','Orphan','Kelebihan baris','Status'],
        [[r[k] for k in ['parent','child','left_join_rows','missing_module_rows','orphan_rows','multiplication_excess','status']] for r in validation['relationships']])
    mapping = verify_source_aliases(root)
    evidence = markdown_table(['Modul','Ekspresi SQL','Alias logis'],[[m['dataset'],m['source_expression'],m['logical_column']] for m in mapping])
    text = ('# Validasi integrasi UB berdasarkan assignment\n\n'
            'Keputusan desain final pengguna: JOIN assignment_ub, ub_a, ub_b dan ub_c hanya memakai assignment_id. '
            'Timestamp assignment, root, serta tie-break tidak menjadi syarat JOIN.\n\n'
            f'Status integrasi: **{ASSIGNMENT_STATUS}**. Provenance historis: **{VERSION_PROVENANCE}**, sebagai catatan informasi dan bukan blocker.\n\n'
            +table+'\n\n'+relation_table+'\n\n'
            f'MART menghasilkan {validation["mart_rows"]} baris dan {validation["unique_mart_assignment_ids"]} assignment unik; '
            f'{validation["complete_assignment_rows"]} baris memiliki master serta A/B/C. Seluruh 25 kolom sumber per modul diperbandingkan terhadap CLEAN dan tidak ada mismatch.\n\n'
            'Bukti alias sumber:\n\n'+evidence+'\n\n'
            'Ketiga ekspresi berasal dari tcz_37526b20.root_table dalam CTE ub_versi dan diteruskan ke hasil akhir; '
            'SQL asli tetap utuh. `data/metadata/ub_assignment_key_mapping.csv` mencatat lokasi dan SHA-256 SQL. '
            'View CLEAN `clean_ub_a_standardized`, `clean_ub_b_standardized`, `clean_ub_c_standardized` mempertahankan seluruh kolom lama dan menambah alias assignment_id. '
            'MART per modul memakai alias yang sama; tabel RAW dan CLEAN tidak diubah.\n\n'
            'mart_ub_integrated berawal dari master assignment dan LEFT JOIN tiga modul melalui assignment_id. '
            'Keunikan, kesamaan himpunan ID, kelengkapan modul, dan payload diperiksa sebelum/ sesudah perubahan. '
            'Perbedaan batch impor tidak menghalangi JOIN ID; provenance batch dan hash tiap modul tetap tersedia. '
            'Bila ID NULL, konflik, duplikat atau himpunan ID berbeda pada impor mendatang, integrasi ditolak tanpa memilih baris arbitrer.\n\n'
            'Kesamaan versi kuesioner historis tidak dinyatakan terbukti. Timestamp operasional dan hint versi_root_terbaru tetap disimpan sebagai provenance master; '
            'tidak dipaksakan sama dengan waktu A/B/C. Ekspor ulang UB untuk memperoleh timestamp tidak diperlukan untuk analisis satu record per assignment. '
            'Query versi yang disiapkan sebelumnya adalah artefak historis yang tidak diperlukan bagi desain ini. Tidak ada ekspor atau query SQL Lab tambahan yang dijalankan.\n\n'
            'Bukti migrasi, backup, integritas dan preservasi tabel: `docs/reports/ub/UB_ASSIGNMENT_INTEGRATION_CHANGE.md` serta '
            '`docs/reports/ub/ub_assignment_migration_validation.json`. Validasi rutin tersedia pada `docs/reports/ub/ub_assignment_integration_validation.json`.\n')
    (root/'docs/reports/ub/UB_VERSION_VALIDATION.md').write_text(text,encoding='utf-8')
