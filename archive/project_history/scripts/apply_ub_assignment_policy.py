"""Targeted UB view migration: locked backup, DDL transaction, no table writes."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.common import dump,q,sha256,utcnow,write_csv
from se2026.scanner import load_config
from se2026.ub_integration import (audit_ub_assignment_keys,build_ub_marts,validate_ub_mart,
                                  verify_source_aliases,write_ub_policy_report)


def table_fingerprints(con):
    result={}
    for name,sql in con.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        h=hashlib.sha256()
        count=0
        cursor=con.execute('SELECT * FROM '+q(name)+' ORDER BY rowid')
        for row in cursor:
            encoded=json.dumps(row,ensure_ascii=False,separators=(',',':'),default=lambda value:{'blob_hex':value.hex()}).encode('utf-8')
            h.update(len(encoded).to_bytes(8,'big'))
            h.update(encoded)
            count+=1
        result[name]=dict(rows=count,sha256=h.hexdigest(),schema_sha256=hashlib.sha256(sql.encode()).hexdigest())
    return result


def deny_table_writes(action,arg1,arg2,database,trigger):
    # SQLite emits SQLITE_DELETE(view_name) during DROP VIEW as well as
    # deleting the schema row. Permit those seven views, never a data table.
    if action==sqlite3.SQLITE_DELETE and arg1 in {
        'mart_ub_a','mart_ub_b','mart_ub_c','mart_ub_integrated',
        'clean_ub_a_standardized','clean_ub_b_standardized','clean_ub_c_standardized'}:
        return sqlite3.SQLITE_OK
    if action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE) and arg1 not in ('sqlite_master','sqlite_schema'):
        return sqlite3.SQLITE_DENY
    if action in (sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE,sqlite3.SQLITE_ALTER_TABLE,
                  sqlite3.SQLITE_CREATE_INDEX,sqlite3.SQLITE_DROP_INDEX):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def migrate(root=ROOT):
    sources=load_config(root)
    aliases=verify_source_aliases(root)
    path=root/'data/processed/se2026.sqlite'
    con=sqlite3.connect(path)
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=10000')
    backup=None
    try:
        # SQLite's backup API respects Windows byte-range locks. data_version
        # detects any intervening writer before the migration lock is acquired.
        if con.execute('PRAGMA journal_mode').fetchone()[0]!='delete':
            raise ValueError('BACKUP_REQUIRES_DELETE_JOURNAL_MODE')
        before_hash=sha256(path)
        version_before=con.execute('PRAGMA data_version').fetchone()[0]
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup=root/'archive/database_backups'/('se2026_before_ub_assignment_'+stamp+'.sqlite')
        backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():
            raise ValueError('BACKUP_TARGET_EXISTS')
        destination=sqlite3.connect(backup)
        try:
            con.backup(destination)
        finally:
            destination.close()
        backup_hash=sha256(backup)
        check=sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True)
        try:
            backup_integrity=check.execute('PRAGMA integrity_check').fetchone()[0]
        finally:
            check.close()
        if backup_integrity!='ok':
            raise ValueError('BACKUP_INTEGRITY_FAILED')
        con.execute('BEGIN IMMEDIATE')
        if con.execute('PRAGMA data_version').fetchone()[0]!=version_before:
            raise ValueError('DATABASE_CHANGED_DURING_BACKUP')
        before_keys=audit_ub_assignment_keys(con,expected_rows=226)
        print('BACKUP_VERIFIED; fingerprinting all physical tables',flush=True)
        before_tables=table_fingerprints(con)
        allowed={'mart_ub_a','mart_ub_b','mart_ub_c','mart_ub_integrated',
                 'clean_ub_a_standardized','clean_ub_b_standardized','clean_ub_c_standardized'}
        before_views={n:s for n,s in con.execute("SELECT name,sql FROM sqlite_master WHERE type='view'") if n not in allowed}
        old_sql=con.execute("SELECT sql FROM sqlite_master WHERE name='mart_ub_integrated'").fetchone()[0]
        con.set_authorizer(deny_table_writes)
        build_ub_marts(con,sources)
        proof=validate_ub_mart(con,sources,expected_rows=226)
        print('UB_MART_VERIFIED; checking table preservation',flush=True)
        after_tables=table_fingerprints(con)
        after_views={n:s for n,s in con.execute("SELECT name,sql FROM sqlite_master WHERE type='view'") if n not in allowed}
        if before_tables!=after_tables or before_views!=after_views:
            raise ValueError('NON_TARGET_DATA_OR_VIEW_CHANGED')
        integrity=con.execute('PRAGMA integrity_check').fetchone()[0]
        violations=len(con.execute('PRAGMA foreign_key_check').fetchall())
        if integrity!='ok' or violations:
            raise ValueError('DATABASE_INTEGRITY_FAILED')
        new_sql=con.execute("SELECT sql FROM sqlite_master WHERE name='mart_ub_integrated'").fetchone()[0]
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.set_authorizer(None)
        con.close()
    proof.update(generated_utc=utcnow(),backup_path=backup.relative_to(root).as_posix(),backup_sha256=backup_hash,
                 database_sha256_before=before_hash,backup_method='sqlite3.Connection.backup',backup_data_version_stable=True,
                 backup_integrity=backup_integrity,integrity=integrity,foreign_key_violations=violations,
                 physical_tables_unchanged=True,physical_tables_verified=len(before_tables),
                 raw_tables_verified=sum(n.startswith('raw_') for n in before_tables),
                 clean_tables_verified=sum(n.startswith('clean_') for n in before_tables),
                 non_ub_views_unchanged=True,non_ub_views_verified=len(before_views),
                 table_fingerprints=after_tables,old_ub_view_sql=old_sql,new_ub_view_sql=new_sql,
                 sql_lab_exports_executed=False)
    dump(root/'docs/reports/ub/ub_assignment_migration_validation.json',proof)
    dump(root/'docs/reports/ub/ub_assignment_integration_validation.json',{k:v for k,v in proof.items() if k not in ('table_fingerprints','old_ub_view_sql','new_ub_view_sql')})
    write_csv(root/'data/metadata/ub_assignment_key_mapping.csv',aliases)
    write_csv(root/'docs/reports/ub/ub_assignment_relationship_validation.csv',proof['relationships'])
    write_ub_policy_report(root,proof)
    (root/'app/sql/transformations/ub_assignment_views.sql').write_text(new_sql+';\n',encoding='utf-8')
    text=('# Perubahan integrasi UB berdasarkan assignment\n\n'
          f'Status: {proof["status"]}; baris MART={proof["mart_rows"]}; assignment unik={proof["unique_mart_assignment_ids"]}; '
          f'baris lengkap master+A/B/C={proof["complete_assignment_rows"]}.\n\n'
          'JOIN hanya assignment_id. Alias id_penghubung dibuktikan dari tiga SQL sumber, ditambahkan pada view CLEAN/MART, '
          'dan kolom lama dipertahankan. Seluruh 25 kolom setiap sumber diperbandingkan ke MART dengan nol mismatch. '
          'Tanggal serta batch tidak menjadi kondisi JOIN; metadata master dan provenance setiap modul tetap tersedia.\n\n'
          f'Backup SQLite konsisten dan integrity_check=ok: `{proof["backup_path"]}`; SHA-256 `{backup_hash}`. '
          'Backup memakai API SQLite sebelum DDL; PRAGMA data_version diverifikasi tidak berubah sampai BEGIN IMMEDIATE mengunci penulis. '
          'Pemulihan bila diperlukan: tutup koneksi database, simpan database aktif sebagai arsip, kemudian salin backup ke path database aktif dan periksa integritas; '
          'jangan menimpa file database yang sedang terbuka.\n\n'
          f'{len(before_tables)} tabel fisik memiliki schema, jumlah baris dan SHA-256 seluruh nilai yang identik sebelum/sesudah; '
          f'termasuk {proof["raw_tables_verified"]} RAW dan {proof["clean_tables_verified"]} CLEAN. '
          f'{len(before_views)} definisi view lain tidak berubah. Authorizer SQLite menolak DML tabel selama migrasi. '
          'Tidak ada ingestion, sync, aktivasi snapshot, ataupun rebuild dataset lain yang dijalankan.\n\n'
          f'integrity_check={integrity}; foreign_key_violations={violations}. '
          'Status QUESTIONNAIRE_VERSION_NOT_VERIFIED dipertahankan sebagai provenance historis yang tidak memblokir integrasi. '
          'Tidak ada ekspor SQL Lab untuk memperoleh timestamp. Bukti rinci: `docs/reports/ub/ub_assignment_migration_validation.json`.\n')
    (root/'docs/reports/ub/UB_ASSIGNMENT_INTEGRATION_CHANGE.md').write_text(text,encoding='utf-8')
    print(json.dumps({k:proof[k] for k in ['status','version_provenance','mart_rows','complete_assignment_rows','integrity','foreign_key_violations','physical_tables_verified','non_ub_views_verified','backup_path']},indent=2))


if __name__=='__main__':
    raise SystemExit('Skrip historis; tidak dijalankan. Gunakan README.md dan app/scripts/README.md untuk perintah aktif.')
