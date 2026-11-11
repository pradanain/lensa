import json
import sqlite3
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[3]


@pytest.fixture
def analytical_db(tmp_path):
    sources=json.loads((ROOT/'app/config/analytics/sources.json').read_text(encoding='utf-8'))
    path=tmp_path/'synthetic.sqlite'
    con=sqlite3.connect(path)
    for sid,source in sources.items():
        if source.get('query') and not source['query'].startswith('dashboard_'):continue
        if con.execute("SELECT 1 FROM sqlite_master WHERE name=?",(source['view'],)).fetchone():continue
        cols=source['columns']
        con.execute('CREATE TABLE "'+source['view']+'"('+','.join('"'+col+'" TEXT' for col in cols)+')')
        for n in range(12):
            code='6502010' if n<10 else '6502000'
            desa=code+'001' if n<10 else '6502000000'
            values={col:None for col in cols}
            values.update({col:'1' for col in cols if col.startswith('has_')})
            values.update(assignment_id=('UB-' if source['system']=='TCZ' else 'TGR-')+str(n),
                          __version_normalized='v1',index1='001',index_meteran='001',index_usaha='001',index_kantor_unit='001',
                          __row_id=str(n+1),kode_kabupaten='6502',kode_kecamatan=code,kode_desa=desa,
                          kode_sls=desa+'0001',kode_subsls=desa+'0001'+'01',kecamatan='AREA TEST',desa_kelurahan='DESA TEST',
                          sls='SLS TEST',subsls='SUBSLS TEST',
                          kode_keberadaan_keluarga='1',kode_keberadaan_bku='1',kode_keberadaan_usaha='1',
                          status_keberadaan='1. Ditemukan dan masih aktif',
                          kbli='04710',kategori='G',kbli_akhir='04710',kategori_kbli='G',
                          status_kepemilikan='1',status_kuesioner='ADA_KUESIONER',
                          kode_menggunakan_internet='1' if n<5 else '2' if n<10 else None,
                          menggunakan_internet='1. Ya' if n<5 else '2. Tidak' if n<10 else None,
                          pekerja_laki_laki='2',pekerja_perempuan='3',total_pekerja_jenis_kelamin='5',jumlah_pekerja='5',
                          status_konsistensi_pekerja='SESUAI')
            con.execute('INSERT INTO "'+source['view']+'"('+','.join('"'+col+'"' for col in cols)+') VALUES('+','.join('?' for _ in cols)+')',[values.get(col) for col in cols])
    con.execute('CREATE TABLE mart_ub_a AS SELECT * FROM mart_ub_integrated')
    con.execute("UPDATE mart_ub_a SET kode_desa='6502020002',desa_kelurahan='RESPONSE DESA TEST'")
    con.execute('CREATE TABLE IF NOT EXISTS mart_legalitas_usaha(assignment_id TEXT,__version_normalized TEXT,index1 TEXT,nib TEXT)')
    if 'nib' not in {r[1] for r in con.execute('PRAGMA table_info(mart_legalitas_usaha)')}:
        con.execute('ALTER TABLE mart_legalitas_usaha ADD COLUMN nib TEXT')
    con.execute('CREATE TABLE active_imports(source_id TEXT PRIMARY KEY,import_id INTEGER)')
    con.execute('CREATE TABLE imported_files(import_id INTEGER,source_id TEXT,sha256 TEXT,batch_id TEXT)')
    for i,sid in enumerate(['sosial_p0','p1_pekerjaan','p1_disabilitas','p1_kronis_a','p1_kronis_b'],1):
        con.execute('INSERT INTO active_imports VALUES (?,?)',(sid,i))
        con.execute('INSERT INTO imported_files VALUES (?,?,?,?)',(i,sid,'synthetic-sha','synthetic-batch'))
        con.execute('CREATE TABLE clean_'+sid+'(__row_id INTEGER,__import_id INTEGER,__key BLOB,__key_valid INTEGER,__conflict INTEGER,assignment_id TEXT,__version_normalized TEXT,index1 TEXT)')
        con.execute('CREATE INDEX ix_key_'+sid+' ON clean_'+sid+'(__import_id,__key)')
        con.execute('CREATE INDEX ix_join_'+sid+' ON clean_'+sid+'(__import_id,assignment_id,index1,__version_normalized)')
        con.executemany('INSERT INTO clean_'+sid+' VALUES (?,?,?,?,?,?,?,?)',[(n+1,i,str(n).encode(),1,0,'TGR-'+str(n),'v1','001') for n in range(12)])
    for i,sid in enumerate(['assignment_tgr','assignment_ub'],100):
        con.execute('INSERT INTO active_imports VALUES (?,?)',(sid,i))
        con.execute('INSERT INTO imported_files VALUES (?,?,?,?)',(i,sid,'synthetic-sha','synthetic-batch'))
        con.execute('CREATE TABLE clean_'+sid+' AS SELECT * FROM mart_'+sid)
        con.execute('UPDATE clean_'+sid+' SET __import_id=?',(i,))
        con.execute('CREATE INDEX ix_join_'+sid+' ON clean_'+sid+'(__import_id,assignment_id)')
    con.execute("INSERT INTO active_imports VALUES ('ub_a',102)")
    con.execute("INSERT INTO imported_files VALUES (102,'ub_a','synthetic-sha','synthetic-batch')")
    con.execute('CREATE TABLE clean_ub_a AS SELECT assignment_id AS id_penghubung,kode_desa,desa_kelurahan,rowid AS __row_id,102 AS __import_id FROM mart_ub_a')
    con.execute('CREATE INDEX ix_join_ub_a ON clean_ub_a(__import_id,id_penghubung)')
    # Independently repeated child rosters would multiply the first family 3*2*2.
    for view,key,extra in [('mart_anggota','index1',2),('mart_meteran','index_meteran',1),('mart_usaha','index1',1)]:
        cols=[r[1] for r in con.execute('PRAGMA table_info("'+view+'")')]
        original=list(con.execute('SELECT * FROM "'+view+'" LIMIT 1').fetchone())
        for n in range(extra):
            row=list(original);row[cols.index(key)]=str(n+2);row[cols.index('__row_id')]=str(13+n)
            con.execute('INSERT INTO "'+view+'" VALUES('+','.join('?' for _ in cols)+')',row)
    con.commit();con.close()
    return path
