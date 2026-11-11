import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from se2026.ub_integration import (ASSIGNMENT_STATUS, VERSION_PROVENANCE, UBIntegrationError,
                                   build_ub_marts, validate_ub_mart, verify_source_aliases)

ROOT = Path(__file__).resolve().parents[2]


def synthetic_database():
    sources = json.loads((ROOT/'app/config/sources.json').read_text(encoding='utf-8'))['sources']
    con = sqlite3.connect(':memory:')
    con.execute('CREATE TABLE active_imports(source_id TEXT,import_id INTEGER)')
    con.execute('CREATE TABLE imported_files(import_id INTEGER,batch_id TEXT,sha256 TEXT)')
    for i,sid in enumerate(['assignment_ub','ub_a','ub_b','ub_c'],1):
        source = next(s for s in sources if s['id']==sid)
        con.execute('INSERT INTO active_imports VALUES (?,?)',(sid,i))
        con.execute('INSERT INTO imported_files VALUES (?,?,?)',(i,'different-batch-'+str(i),'synthetic-sha-'+str(i)))
        columns = ['__row_id INTEGER','__import_id INTEGER','__conflict INTEGER','__key_valid INTEGER','__version_normalized TEXT']+[f'"{c}" TEXT' for c in source['columns']]
        con.execute('CREATE TABLE clean_'+sid+'('+','.join(columns)+')')
        for n in range(2):
            row = dict(__row_id=n+1,__import_id=i,__conflict=0,__key_valid=1,
                       __version_normalized='different-version-'+str(i),
                       **{col:'synthetic-payload-'+str(i)+'-'+str(n)+'-'+col for col in source['columns']})
            row['assignment_id' if sid=='assignment_ub' else 'id_penghubung']='synthetic-'+str(n)
            cols=list(row)
            con.execute('INSERT INTO clean_'+sid+'('+','.join('"'+c+'"' for c in cols)+') VALUES('+','.join('?' for _ in cols)+')',list(row.values()))
    con.execute('''CREATE VIEW mart_assignment_ub AS SELECT c.*,f.batch_id AS __batch_id,f.sha256 AS __source_sha256
        FROM clean_assignment_ub c JOIN active_imports a ON a.source_id='assignment_ub' AND a.import_id=c.__import_id
        JOIN imported_files f ON f.import_id=c.__import_id''')
    con.commit()
    return con,sources


def test_assignment_join_ignores_versions_and_batch_dates_and_keeps_payload():
    con,sources=synthetic_database()
    before={sid:con.execute('SELECT * FROM clean_'+sid).fetchall() for sid in ['assignment_ub','ub_a','ub_b','ub_c']}
    build_ub_marts(con,sources)
    proof=validate_ub_mart(con,sources,expected_rows=2)
    assert proof['complete_assignment_rows']==2
    assert proof['timestamp_join_required'] is False
    assert all(p['mismatched_rows']==0 for p in proof['payload_validation'])
    assert con.execute('SELECT DISTINCT integration_status,questionnaire_version_status FROM mart_ub_integrated').fetchall()==[(ASSIGNMENT_STATUS,VERSION_PROVENANCE)]
    for sid in ['ub_a','ub_b','ub_c']:
        assert con.execute('SELECT COUNT(*) FROM clean_'+sid+'_standardized WHERE assignment_id=id_penghubung').fetchone()[0]==2
        assert con.execute('SELECT * FROM clean_'+sid).fetchall()==before[sid]
    assert con.execute('SELECT * FROM clean_assignment_ub').fetchall()==before['assignment_ub']
    sql=con.execute("SELECT sql FROM sqlite_master WHERE name='mart_ub_integrated'").fetchone()[0]
    assert sql.count(' ON m.assignment_id=')==3
    assert 'same_batch' not in sql
    con.close()


@pytest.mark.parametrize('bad_change',[
    "UPDATE clean_ub_b SET id_penghubung=NULL WHERE __row_id=1",
    "UPDATE clean_ub_b SET id_penghubung='synthetic-0' WHERE __row_id=2",
    "UPDATE clean_ub_b SET id_penghubung='synthetic-orphan' WHERE __row_id=2",
    "UPDATE clean_ub_b SET __conflict=1 WHERE __row_id=1",
])
def test_invalid_assignment_sets_cannot_be_silently_joined(bad_change):
    con,sources=synthetic_database()
    build_ub_marts(con,sources)
    con.commit()
    original=con.execute("SELECT sql FROM sqlite_master WHERE name='mart_ub_integrated'").fetchone()[0]
    con.execute('BEGIN')
    con.execute(bad_change)
    with pytest.raises(UBIntegrationError):
        build_ub_marts(con,sources)
    con.rollback()
    assert con.execute("SELECT sql FROM sqlite_master WHERE name='mart_ub_integrated'").fetchone()[0]==original
    assert validate_ub_mart(con,sources,2)['mart_rows']==2
    con.close()


def test_ub_view_ddl_rolls_back_with_caller_transaction():
    con,sources=synthetic_database()
    con.execute('CREATE VIEW mart_ub_integrated AS SELECT 42 AS old_definition')
    con.commit()
    con.execute('BEGIN')
    build_ub_marts(con,sources)
    con.rollback()
    assert con.execute('SELECT old_definition FROM mart_ub_integrated').fetchall()==[(42,)]
    assert con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='clean_ub_a_standardized'").fetchone()[0]==0
    con.close()


def test_sql_source_alias_is_verified_and_changed_expression_is_rejected(tmp_path):
    source=ROOT/'app/sql/source_queries/02_Dataset_Siap_Analisis/UB'
    target=tmp_path/'app/sql/source_queries/02_Dataset_Siap_Analisis/UB'
    shutil.copytree(source,target)
    assert len(verify_source_aliases(tmp_path))==3
    path=target/'09A_IDENTITAS_WILAYAH_KBLI_PJ.sql'
    path.write_text(path.read_text(encoding='utf-8').replace('r.assignment_id AS id_penghubung','r.nib AS id_penghubung'),encoding='utf-8')
    with pytest.raises(UBIntegrationError,match='UB_ASSIGNMENT_ALIAS_NOT_PROVEN'):
        verify_source_aliases(tmp_path)


def test_migration_authorizer_allows_ub_view_ddl_and_denies_data_writes():
    import importlib.util
    spec=importlib.util.spec_from_file_location('ub_migration',ROOT/'archive/project_history/scripts/apply_ub_assignment_policy.py')
    migration=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    con,sources=synthetic_database()
    build_ub_marts(con,sources)
    con.commit()
    con.set_authorizer(migration.deny_table_writes)
    con.execute('BEGIN')
    build_ub_marts(con,sources)
    assert validate_ub_mart(con,sources,2)['mart_rows']==2
    with pytest.raises(sqlite3.DatabaseError,match='not authorized'):
        con.execute("UPDATE clean_ub_a SET id_penghubung='synthetic-changed'")
    con.rollback()
    con.close()
