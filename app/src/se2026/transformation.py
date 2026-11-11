"""Grain-preserving marts and FK-enforced links for actual matched rows."""
from .common import q
from .scanner import relation_specs


def join_condition(spec, parent='p', child='c'):
    return ' AND '.join(parent+'.'+q('__version_normalized' if a=='assignment_date_modified' else a)+'='+child+'.'+q('__version_normalized' if b=='assignment_date_modified' else b)
                        for a,b in zip(spec['parent_columns'],spec['child_columns']))


def safe_rows(name):
    return '(SELECT * FROM '+q('mart_'+name)+' WHERE __key_valid=1 AND __conflict=0)'


def same_batch(con, names):
    marks = ','.join('?' for _ in names)
    rows = con.execute(f'''SELECT f.source_id,f.batch_id FROM imported_files f
        JOIN active_imports a ON a.import_id=f.import_id WHERE f.source_id IN ({marks})''',names).fetchall()
    return len(rows)==len(names) and len({r[1] for r in rows})==1


def build_marts(con, sources):
    by_id = {s['id']:s for s in sources}
    # View recreation is part of the surrounding import transaction.
    for name, in con.execute("SELECT name FROM sqlite_master WHERE type='view' AND name LIKE 'mart_%'").fetchall():
        con.execute('DROP VIEW '+q(name))
    for s in sources:
        sid = s['id']
        con.execute(f'''CREATE VIEW {q('mart_'+sid)} AS SELECT c.*,f.batch_id AS __batch_id,f.sha256 AS __source_sha256
            FROM {q('clean_'+sid)} c JOIN active_imports a ON a.source_id='{sid}' AND a.import_id=c.__import_id
            JOIN imported_files f ON f.import_id=c.__import_id''')
        fields = ['__import_id'] + [c for c in s['key'] if c!='assignment_date_modified']
        if 'assignment_date_modified' in s['columns']:
            fields += ['__version_normalized']
        con.execute('CREATE INDEX IF NOT EXISTS '+q('ix_join_'+sid)+' ON '+q('clean_'+sid)+'('+','.join(map(q,fields))+')')
    for spec in relation_specs(sources):
        parent,child = spec['parent'],spec['child']
        # Recheck uniqueness after deduplication; never trust raw key claims.
        group = ','.join(q('__version_normalized' if c=='assignment_date_modified' else c) for c in spec['parent_columns'])
        duplicates = con.execute('SELECT COUNT(*) FROM (SELECT '+group+' FROM '+safe_rows(parent)+' GROUP BY '+group+' HAVING COUNT(*)>1)').fetchone()[0]
        if duplicates:
            continue
        name = q('link_'+child+'__'+parent)
        con.execute(f'''CREATE TABLE IF NOT EXISTS {name} (
            child_row_id INTEGER PRIMARY KEY REFERENCES {q('clean_'+child)}(__row_id),
            parent_row_id INTEGER NOT NULL REFERENCES {q('clean_'+parent)}(__row_id))''')
        con.execute(f'''INSERT OR IGNORE INTO {name} SELECT c.__row_id,p.__row_id
            FROM {safe_rows(child)} c JOIN {safe_rows(parent)} p ON {join_condition(spec)}''')
    # Family and business modules stay at their own parent grain; child rosters stay separate.
    for base, children, name in [
        ('keluarga',['perumahan','aset_keluarga','screening'],'mart_keluarga_integrated'),
        ('usaha',['legalitas_usaha','kegiatan_usaha','digital_usaha','program_usaha','ekonomi_tahunan','ekonomi_bulanan','jaringan_usaha'],'mart_usaha_integrated')]:
        if not same_batch(con,[base]+children):
            continue
        select = ['b.*']
        joins = []
        for i,child in enumerate(children):
            alias = 'm'+str(i)
            s = by_id[child]
            select += [alias+'.'+q(c)+' AS '+q(child+'__'+c) for c in s['columns'] if c not in s['key']]
            select += [alias+'.__source_sha256 AS '+q(child+'__source_sha256'), '('+alias+'.__row_id IS NOT NULL) AS '+q('has_'+child)]
            joins.append(' LEFT JOIN '+safe_rows(child)+' '+alias+' ON b.__key='+alias+'.__key')
        con.execute('CREATE VIEW '+q(name)+' AS SELECT '+','.join(select)+' FROM '+safe_rows(base)+' b'+''.join(joins))
    social = ['sosial_p0','p1_pekerjaan','p1_disabilitas','p1_kronis_a','p1_kronis_b']
    if same_batch(con,social):
        keys = ' UNION '.join('SELECT __key FROM '+safe_rows(s) for s in social)
        aliases = ['m'+str(i) for i in range(len(social))]
        select = ['k.__key AS integration_key']
        for column in ['assignment_id','__version_normalized','index1']:
            select.append('COALESCE('+','.join(a+'.'+q(column) for a in aliases)+') AS '+q(column))
        joins = []
        for s,a in zip(social,aliases):
            select += ['('+a+'.__row_id IS NOT NULL) AS '+q('has_'+s),a+'.__source_sha256 AS '+q(s+'__source_sha256'),a+'.__row_id AS '+q(s+'__row_id')]
            select += [a+'.'+q(c)+' AS '+q(s+'__'+c) for c in by_id[s]['columns'] if c not in ('assignment_id','index1')]
            joins.append(' LEFT JOIN '+safe_rows(s)+' '+a+' ON '+a+'.__key=k.__key')
        con.execute('CREATE VIEW mart_sosial_p0_p1 AS WITH keys AS ('+keys+') SELECT '+','.join(select)+' FROM keys k'+''.join(joins))
        con.execute('CREATE VIEW mart_sosial_p1_only AS SELECT * FROM mart_sosial_p0_p1 WHERE has_sosial_p0=0')
    from .ub_integration import build_ub_marts
    build_ub_marts(con,sources)
    for level,geo in [('kecamatan',['kode_kecamatan']),('desa',['kode_kecamatan','kode_desa']),('sls',['kode_kecamatan','kode_desa','kode_sls','kode_subsls'])]:
        unions = []
        for sid,assignment,system in [('assignment_tgr','assignment_tgr','TGR'),('keluarga','assignment_tgr','TGR'),('anggota','assignment_tgr','TGR'),('bku','assignment_tgr','TGR'),('usaha','assignment_tgr','TGR'),('assignment_ub','assignment_ub','TCZ'),('ub_a','assignment_ub','TCZ')]:
            field = 'id_penghubung' if sid=='ub_a' else 'assignment_id'
            cols = ','.join('a.'+q(c) for c in geo)
            unions.append(f"SELECT '{system}' AS source_system,'{sid}' AS entity,{cols},COUNT(*) AS jumlah_unit_versi FROM "+safe_rows(sid)+' e JOIN '+safe_rows(assignment)+' a ON e.'+q(field)+'=a.assignment_id GROUP BY '+cols)
        con.execute('CREATE VIEW '+q('mart_rekap_'+level)+' AS '+' UNION ALL '.join(unions))
    con.execute('CREATE VIEW mart_rekap_wilayah AS SELECT * FROM mart_rekap_sls')
