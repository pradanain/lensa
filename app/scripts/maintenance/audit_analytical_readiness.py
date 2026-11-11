"""Profile local analytical coverage only; never changes SQLite or requests data."""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.common import dump,q,sha256,utcnow,write_csv


def populated(column):
    return 'NULLIF(TRIM(CAST('+column+" AS TEXT)),'') IS NOT NULL"


def profile_columns(con,table,columns,where='',parameters=()):
    expressions=['COUNT(*)']+['COALESCE(SUM('+populated(q(col))+'),0)' for col in columns]
    row=con.execute('SELECT '+','.join(expressions)+' FROM '+q(table)+where,parameters).fetchone()
    return row[0],dict(zip(columns,row[1:]))


def sensitivity(column):
    if re.search(r'(^|__)(nama|nik|no_kk|alamat|nomor_hp|nomor_telepon|email|id_pelanggan|nomor_meteran|link_google)',column) or re.search(r'latitude|longitude|tanggal_lahir',column):
        return 'IDENTITAS_ATAU_LOKASI_TERBATAS'
    if re.search(r'dis_|sakit_|disabilitas|penyakit|pendapatan|pend_|gaji|pengeluaran|biaya|aset|modal|rekening',column):
        return 'SOSIAL_EKONOMI_KESEHATAN_TERBATAS'
    return 'AGREGAT_INTERNAL'


def variable_role(column,key):
    if column in key:
        return 'KUNCI_UNIT_VERSI'
    if column.startswith('__') or column in ('assignment_id_timestamp','assignment_date_modified'):
        return 'PROVENANCE'
    if column.endswith('_label') or column.startswith('rentang_') or column=='biaya_perlindungan_lingkungan':
        return 'KATEGORI_LABEL_ATAU_URAIAN'
    if re.search(r'^kode_|_value$|^status_|^has_|^ada_|^mempunyai_|^menggunakan_|^punya_|^memiliki_',column):
        return 'KATEGORI_FLAG'
    if re.search(r'kecamatan|desa|sls|provinsi|kabupaten|negara',column):
        return 'WILAYAH'
    if sensitivity(column)=='IDENTITAS_ATAU_LOKASI_TERBATAS':
        return 'IDENTITAS_LOKASI_BUKAN_DIMENSI_PUBLIK'
    if re.search(r'jumlah|total|nilai|pendapatan|pend_|pengeluaran|biaya|aset|modal|persen|pekerja|umur|luas|tahun|gaji',column):
        return 'UKURAN_KUANTITATIF_PERLU_UNIT'
    return 'KATEGORI_LABEL_ATAU_URAIAN'


def source_profile(con,source):
    sid=source['id']
    iid=con.execute('SELECT import_id FROM active_imports WHERE source_id=?',(sid,)).fetchone()[0]
    schema={r[1]:r[2] for r in con.execute('PRAGMA table_info('+q('clean_'+sid)+')')}
    rows,nonempty=profile_columns(con,'clean_'+sid,source['columns'],' WHERE __import_id=?',(iid,))
    raw=con.execute('SELECT COUNT(*) FROM '+q('raw_'+sid)+' WHERE __import_id=?',(iid,)).fetchone()[0]
    key_column='id_penghubung' if sid.startswith('ub_') else 'assignment_id'
    assignments=con.execute('SELECT COUNT(*) FROM (SELECT '+q(key_column)+' FROM '+q('clean_'+sid)+' WHERE __import_id=? GROUP BY '+q(key_column)+')',(iid,)).fetchone()[0]
    identity_fields=[c for c in source['key'] if c!='assignment_date_modified']
    units=con.execute('SELECT COUNT(*) FROM (SELECT '+','.join(map(q,identity_fields))+' FROM '+q('clean_'+sid)+' WHERE __import_id=? GROUP BY '+','.join(map(q,identity_fields))+')',(iid,)).fetchone()[0]
    invalid,conflicts=con.execute('SELECT COALESCE(SUM(__key_valid=0),0),COALESCE(SUM(__conflict),0) FROM '+q('clean_'+sid)+' WHERE __import_id=?',(iid,)).fetchone()
    columns=[]
    for col in source['columns']:
        columns.append(dict(dataset=sid,mart='mart_'+sid,column=col,sqlite_type=schema[col],grain=source['grain'],
                            source_rows=rows,nonempty_rows=nonempty[col],nonempty_percent=round(100*nonempty[col]/rows,3) if rows else 0,
                            role=variable_role(col,source['key']),sensitivity=sensitivity(col),
                            availability='ALL_EMPTY_LOCAL' if nonempty[col]==0 else 'PARTIAL_LOCAL' if nonempty[col]<rows else 'POPULATED_LOCAL'))
    summary=dict(dataset=sid,raw_rows=raw,clean_rows=rows,distinct_assignments=assignments,distinct_units_without_version=units,
                 extra_version_rows=rows-units,grain=source['grain'],key=source['key'],source_columns=len(columns),
                 all_empty_columns=sum(v==0 for v in nonempty.values()),invalid_key_rows=invalid,conflict_rows=conflicts)
    return summary,columns


def geo_profile(con,source):
    sid=source['id']
    system=source['system']
    master='mart_assignment_ub' if system=='TCZ' else 'mart_assignment_tgr'
    unit='mart_'+sid
    key='assignment_id' if not sid.startswith('ub_') else 'assignment_id'
    select=['COUNT(*)','COALESCE(SUM(m.__row_id IS NULL),0)']
    fields={'kecamatan':'m.kode_kecamatan','desa':'m.kode_desa',
            'sls':'m.kode_sls','subsls':'m.kode_subsls'}
    select+=['COALESCE(SUM('+populated(v)+'),0)' for v in fields.values()]
    select+=['COALESCE(SUM(('+populated('m.kode_sls')+') OR ('+populated('m.kode_subsls')+')),0)']
    row=con.execute('SELECT '+','.join(select)+' FROM '+q(unit)+' e LEFT JOIN '+q(master)+' m ON e.'+q(key)+'=m.assignment_id').fetchone()
    total=con.execute('SELECT COUNT(*) FROM '+q(unit)).fetchone()[0]
    return dict(dataset=sid,system=system,rows=total,left_join_rows=row[0],master_missing_rows=row[1],kecamatan_populated=row[2],
                desa_populated=row[3],sls_populated=row[4],subsls_populated=row[5],sls_or_subsls_populated=row[6],
                multiplication_excess=row[0]-total)


def match_coverage(con,parent,child,fields,parent_aliases=None):
    parent_aliases=parent_aliases or fields
    on=' AND '.join('p.'+q(a)+'=c.'+q(b) for a,b in zip(parent_aliases,fields))
    row=con.execute('SELECT COUNT(*),COALESCE(SUM(p.__row_id IS NULL),0) FROM '+q('mart_'+child)+' c LEFT JOIN '+q('mart_'+parent)+' p ON '+on).fetchone()
    total=con.execute('SELECT COUNT(*) FROM '+q('mart_'+child)).fetchone()[0]
    return dict(parent=parent,child=child,child_rows=total,matched_child_rows=row[0]-row[1],unmatched_child_rows=row[1],
                left_join_rows=row[0],multiplication_excess=row[0]-total,join_columns=fields,parent_columns=parent_aliases)


def table_inventory(con):
    result=[]
    for name,sql in con.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        rows=con.execute('SELECT COUNT(*) FROM '+q(name)).fetchone()[0]
        result.append(dict(table=name,rows=rows,columns=len(con.execute('PRAGMA table_info('+q(name)+')').fetchall()),
                           purpose='raw' if name.startswith('raw_') else 'clean' if name.startswith('clean_') else 'matched_links' if name.startswith('link_') else 'provenance_and_control'))
    return result


def audit(root=ROOT):
    db=root/'data/processed/se2026.sqlite'
    before=sha256(db)
    protected=[root/'main.py',*sorted((root/'app/src').rglob('*.py')),root/'app/config/sources.json',root/'app/config/incoming.json']
    code_hashes={p.relative_to(root).as_posix():sha256(p) for p in protected}
    sources=json.loads((root/'app/config/sources.json').read_text(encoding='utf-8'))['sources']
    c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    c.execute('PRAGMA query_only=ON')
    c.execute('BEGIN')
    summaries,variables,geography,marts,mart_columns=[],[],[],[],[]
    try:
        tables=table_inventory(c)
        for source in sources:
            print('ANALYTICAL_PROFILE',source['id'],flush=True)
            summary,columns=source_profile(c,source)
            summaries.append(summary)
            variables.extend(columns)
            geography.append(geo_profile(c,source))
        definitions=c.execute("SELECT name,sql FROM sqlite_master WHERE type='view' ORDER BY name").fetchall()
        for name,sql in definitions:
            schema=c.execute('PRAGMA table_info('+q(name)+')').fetchall()
            if name.startswith('mart_'):
                rows=c.execute('SELECT COUNT(*) FROM '+q(name)).fetchone()[0]
                marts.append(dict(mart=name,rows=rows,columns=len(schema),sql=sql))
            else:
                rows=None
            for entry in schema:
                mart_columns.append(dict(view=name,column=entry[1],sqlite_type=entry[2],sensitivity=sensitivity(entry[1])))
        matches=[]
        version=['assignment_id','__version_normalized']
        member=version+['index1']
        for parent,child,keys,parent_keys in [
            ('keluarga','perumahan',version,None),('keluarga','aset_keluarga',version,None),
            ('keluarga','screening',version,None),('keluarga','anggota',version,None),
            ('anggota','sosial_p0',member,None),('keluarga','meteran',version,None),
            ('usaha','legalitas_usaha',member,None),('usaha','kegiatan_usaha',member,None),
            ('usaha','digital_usaha',member,None),('usaha','program_usaha',member,None),
            ('usaha','ekonomi_tahunan',member,None),('usaha','ekonomi_bulanan',member,None),
            ('usaha','jaringan_usaha',version+['index_usaha'],member),
            ('usaha','kantor_unit',version+['index_usaha'],member),
            ('keluarga','usaha',version,None),('bku','usaha',version,None),
            ('bku','kantor_pusat',version,None)]:
            matches.append(match_coverage(c,parent,child,keys,parent_keys))
        for sid in ['p1_pekerjaan','p1_disabilitas','p1_kronis_a','p1_kronis_b']:
            matches.append(match_coverage(c,'sosial_p0',sid,member))
        integrated=[]
        for view in ['mart_keluarga_integrated','mart_usaha_integrated','mart_sosial_p0_p1','mart_ub_integrated']:
            flags=[r[1] for r in c.execute('PRAGMA table_info('+q(view)+')') if r[1].startswith('has_')]
            expr=['COUNT(*)']+['COALESCE(SUM('+q(flag)+'=1),0)' for flag in flags]
            row=c.execute('SELECT '+','.join(expr)+' FROM '+q(view)).fetchone()
            integrated.append(dict(mart=view,rows=row[0],module_presence=dict(zip(flags,row[1:]))))
        administrative=[]
        for system,view in [('TGR','mart_assignment_tgr'),('TCZ','mart_assignment_ub')]:
            for level,cols in [('kecamatan',['kode_kecamatan']),('desa',['kode_kecamatan','kode_desa']),('sls',['kode_kecamatan','kode_desa','kode_sls']),('sls_subsls',['kode_kecamatan','kode_desa','kode_sls','kode_subsls'])]:
                if level=='sls_subsls':
                    valid=' AND '.join(populated(q(col)) for col in cols[:2])+' AND ('+populated(q('kode_sls'))+' OR '+populated(q('kode_subsls'))+')'
                else:
                    valid=' AND '.join(populated(q(col)) for col in cols)
                count=c.execute('SELECT COUNT(*) FROM (SELECT '+','.join(map(q,cols))+' FROM '+q(view)+' WHERE '+valid+' GROUP BY '+','.join(map(q,cols))+')').fetchone()[0]
                administrative.append(dict(system=system,level=level,observed_populated_code_groups=count,definition='composite stored keys; no official boundary universe assumed'))
        rekap=[]
        for view in ['mart_rekap_kecamatan','mart_rekap_desa','mart_rekap_sls','mart_rekap_wilayah']:
            for system,entity,n in c.execute('SELECT source_system,entity,SUM(jumlah_unit_versi) FROM '+q(view)+' GROUP BY source_system,entity'):
                sid=entity
                expected=c.execute('SELECT COUNT(*) FROM '+q('mart_'+sid)).fetchone()[0]
                rekap.append(dict(mart=view,system=system,entity=entity,sum_unit_versions=n,source_mart_rows=expected,counts_agree=n==expected))
        business_links=dict(zip(['family_only','bku_only','both','neither'],c.execute('''
            WITH presence AS (
                SELECT EXISTS(SELECT 1 FROM mart_keluarga f WHERE f.assignment_id=u.assignment_id AND f.__version_normalized=u.__version_normalized) AS family,
                       EXISTS(SELECT 1 FROM mart_bku b WHERE b.assignment_id=u.assignment_id AND b.__version_normalized=u.__version_normalized) AS bku
                FROM mart_usaha u
            ) SELECT SUM(family=1 AND bku=0),SUM(family=0 AND bku=1),SUM(family=1 AND bku=1),SUM(family=0 AND bku=0) FROM presence
        ''').fetchone()))
        ub_geo=c.execute('''SELECT COUNT(*),COALESCE(SUM(NULLIF(TRIM(a.kode_desa),'') IS NOT NULL AND NULLIF(TRIM(m.kode_desa),'') IS NOT NULL AND a.kode_desa<>m.kode_desa),0)
            FROM mart_ub_a a JOIN mart_assignment_ub m ON a.assignment_id=m.assignment_id''').fetchone()
        financial_overlap=c.execute('SELECT COUNT(*) FROM mart_ekonomi_tahunan a JOIN mart_ekonomi_bulanan b ON a.__key=b.__key').fetchone()[0]
        # Availability of fields on the same record supports a specific cross-tab denominator.
        combos=[]
        for sid,fields in [
            ('sosial_p0',['kode_ijazah_tertinggi','kode_profesi_utama']),
            ('sosial_p0',['kode_profesi_utama','total_pendapatan_pekerjaan']),
            ('usaha',['kbli','kategori','skala_usaha']),
            ('program_usaha',['pekerja_laki_laki','pekerja_perempuan']),
            ('ekonomi_tahunan',['total_pendapatan_2025','total_pengeluaran_2025']),
            ('ekonomi_bulanan',['total_pendapatan_bln','total_pengeluaran_bln']),
            ('ub_b',['total_pendapatan','total_pengeluaran'])]:
            joint=c.execute('SELECT COUNT(*) FROM '+q('mart_'+sid)+' WHERE '+' AND '.join(populated(q(col)) for col in fields)).fetchone()[0]
            combos.append(dict(dataset=sid,columns=fields,joint_nonempty_rows=joint))
        c.rollback()
    finally:
        c.close()
    if sha256(db)!=before:
        raise RuntimeError('DATABASE_CHANGED_DURING_READ_ONLY_AUDIT')
    if any(sha256(root/p)!=checksum for p,checksum in code_hashes.items()):
        raise RuntimeError('PIPELINE_OR_SOURCE_CONFIGURATION_CHANGED')
    result=dict(generated_utc=utcnow(),database='data/processed/se2026.sqlite',database_sha256=before,
                database_unchanged=True,pipeline_and_source_configuration_unchanged=True,access='mode=ro; PRAGMA query_only=ON',
                data_policy='PERMANENT_LOCAL_BASELINE_NO_SQL_LAB',tables=tables,sources=summaries,variables=variables,
                views=definitions,marts=marts,view_columns=mart_columns,geography=geography,administrative_groups=administrative,
                relationship_coverage=matches,integrated_module_coverage=integrated,rekap_count_validation=rekap,
                business_assignment_links=business_links,ub_desa_code_comparison=dict(joined_rows=ub_geo[0],different_nonempty_desa_codes=ub_geo[1]),
                annual_monthly_same_unit_version_overlap=financial_overlap,joint_field_availability=combos)
    dump(root/'docs/reports/readiness/analytical_readiness_audit.json',result)
    write_csv(root/'data/metadata/analytical_variable_catalog.csv',variables)
    write_csv(root/'data/metadata/analytical_view_columns.csv',mart_columns)
    write_csv(root/'docs/reports/readiness/analytical_geographic_coverage.csv',geography)
    write_csv(root/'docs/reports/readiness/analytical_relationship_coverage.csv',matches)
    print(json.dumps(dict(sources=len(summaries),source_variables=len(variables),marts=len(marts),
                         physical_tables=len(tables),all_empty_fields=sum(r['availability']=='ALL_EMPTY_LOCAL' for r in variables),
                         business_assignment_links=business_links,database_unchanged=True),indent=2),flush=True)
    return result


if __name__=='__main__':
    audit()
