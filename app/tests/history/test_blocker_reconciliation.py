"""Synthetic checks for the separate read-only blocker audit."""
import importlib.util
import shutil
import sqlite3
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('blocker_audit', PROJECT/'archive/project_history/scripts/reconcile_validation_blockers.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def copy_source_queries(root):
    shutil.copytree(PROJECT/'app/sql/source_queries',root/'app/sql/source_queries')


def test_historical_count_never_implies_same_snapshot():
    assert audit.count_classification(100,100)=='COUNT_MATCH_SNAPSHOT_UNVERIFIED'
    assert audit.count_classification(102,100)=='COUNT_DIFFERENCE'
    assert audit.count_classification(98,100)=='COUNT_DIFFERENCE'
    assert audit.count_classification(100,None)=='INSUFFICIENT_EVIDENCE'
    assert audit.count_classification(100,100,same_snapshot=True)=='VERIFIED_COMPLETE'
    assert audit.count_classification(100,100,export_failed=True)=='REEXPORT_REQUIRED'


def test_count_query_keeps_physical_join_multiplicity(tmp_path):
    copy_source_queries(tmp_path)
    checks = audit.count_queries(tmp_path)
    assert len(checks)==6
    query = (tmp_path/'app/sql/validation/blocker_reconciliation/01_COUNT_SIX_UNCERTAIN_EXPORTS.sql').read_text()
    con = sqlite3.connect(':memory:')
    con.execute("ATTACH DATABASE ':memory:' AS tgr_fd68e454")
    con.executescript('''
        CREATE TABLE tgr_fd68e454.base_table_assignment(assignment_id TEXT,is_active INTEGER,level_2_full_code TEXT);
        INSERT INTO tgr_fd68e454.base_table_assignment VALUES ('synthetic-A',1,'6502'),('synthetic-A',1,'6502'),('synthetic-B',0,'6502'),('synthetic-C',1,'6503');
        CREATE TABLE tgr_fd68e454.root_table(assignment_id TEXT,assignment_date_modified TEXT,ada_keluarga_value TEXT,ada_bang_usaha_value TEXT);
        INSERT INTO tgr_fd68e454.root_table VALUES ('synthetic-A','v1','1','7'),('synthetic-A','v1','1','7'),('synthetic-B','v1','1','7'),('synthetic-C','v1','1','7');
        CREATE TABLE tgr_fd68e454.nested_dtsen(assignment_id TEXT,assignment_date_modified TEXT);
        INSERT INTO tgr_fd68e454.nested_dtsen VALUES ('synthetic-A','v1'),('synthetic-A','v9'),('synthetic-B','v1'),('synthetic-C','v1');
        CREATE TABLE tgr_fd68e454.nested_meteran(assignment_id TEXT,assignment_date_modified TEXT);
        INSERT INTO tgr_fd68e454.nested_meteran VALUES ('synthetic-A','v1');
        CREATE TABLE tgr_fd68e454.se2026_nested(assignment_id TEXT,assignment_date_modified TEXT,keberadaan_usaha_value TEXT);
        INSERT INTO tgr_fd68e454.se2026_nested VALUES ('synthetic-A','v1','7'),('synthetic-A','v2','1'),('synthetic-A','v1',NULL);
    ''')
    rows = con.execute(query).fetchall()
    assert {r[0]:r[2] for r in rows}==dict(assignment_tgr=1,anggota=4,meteran=4,screening=4,bku=4,usaha=6)
    assert all(len(r)==3 for r in rows)
    con.close()


def test_ub_exports_preserve_payload_and_result_column_limit(tmp_path):
    copy_source_queries(tmp_path)
    generated = audit.ub_queries(tmp_path)
    assert len(generated)==6
    for module,filename in audit.UB_FILES.items():
        original = (tmp_path/'app/sql/source_queries/02_Dataset_Siap_Analisis/UB'/filename).read_text(encoding='utf-8-sig')
        _,original_columns,original_suffix = audit.projection_parts(original)
        recovered = []
        for part in (1,2):
            record = next(r for r in generated if r['module']==module and r['part']==part)
            text = (tmp_path/record['path']).read_text(encoding='utf-8')
            prefix,columns,suffix = audit.projection_parts(text)
            assert len(columns)==(25 if part==1 else 5)
            assert columns[0]==original_columns[0]
            assert 'assignment_date_modified AS questionnaire_modified_at' in columns[1]
            assert 'assignment_id_timestamp AS questionnaire_id_timestamp' in columns[2]
            assert suffix==original_suffix
            assert 'r.assignment_date_modified,' in prefix
            assert 'r.assignment_id_timestamp,' in prefix
            recovered.extend(columns[3:])
        assert recovered==original_columns[1:]


def test_all_five_p1_categories_and_raw_duplicates():
    con = sqlite3.connect(':memory:')
    con.executescript('''
        CREATE TABLE active_imports(source_id TEXT,import_id INTEGER);
        CREATE TABLE imported_files(import_id INTEGER,raw_rows INTEGER,clean_rows INTEGER);
        INSERT INTO active_imports VALUES ('sosial_p0',1),('assignment_tgr',2);
        CREATE TABLE clean_assignment_tgr(__import_id INTEGER,assignment_id TEXT);
        INSERT INTO clean_assignment_tgr VALUES (2,'synthetic-A'),(2,'synthetic-B');
        CREATE TABLE clean_sosial_p0(__import_id INTEGER,__key_valid INTEGER,__conflict INTEGER,assignment_id TEXT,index1 TEXT,__version_normalized TEXT);
        INSERT INTO clean_sosial_p0 VALUES (1,1,0,'synthetic-A','001','v1');
    ''')
    for i,sid in enumerate(audit.P1,start=3):
        con.execute('INSERT INTO active_imports VALUES (?,?)',(sid,i))
        con.execute('INSERT INTO imported_files VALUES (?,6,5)',(i,))
        con.execute('CREATE TABLE clean_'+sid+' (__import_id INTEGER,__clean_hash INTEGER,__key_valid INTEGER,__conflict INTEGER,assignment_id TEXT,index1 TEXT,__version_normalized TEXT)')
        con.execute('CREATE TABLE raw_'+sid+' (__import_id INTEGER,__clean_hash INTEGER)')
        rows = [(i,1,1,0,'synthetic-A','001','v1'),(i,2,1,0,'synthetic-A','001','v2'),
                (i,3,1,0,'synthetic-A','002','v1'),(i,4,1,0,'synthetic-B','001','v1'),(i,5,0,0,'','001',None)]
        con.executemany('INSERT INTO clean_'+sid+' VALUES (?,?,?,?,?,?,?)',rows)
        con.executemany('INSERT INTO raw_'+sid+' VALUES (?,?)',[(i,n) for n in [1,1,2,3,4,5]])
    result = audit.p1_classification(con)
    for row in result:
        assert row['unmatched_rows']==4
        assert row['p0_absent_but_master_present']==1
        assert row['total_rows']==(6 if row['layer']=='RAW' else 5)
        assert [row[c] for c in audit.CATEGORIES]==([2,1,1,1,1] if row['layer']=='RAW' else [1,1,1,1,1])
    con.close()


def test_ub_diagnostic_rejects_ambiguous_or_null_version_keys(tmp_path):
    copy_source_queries(tmp_path)
    audit.ub_queries(tmp_path)
    query = (tmp_path/'app/sql/validation/blocker_reconciliation/02_UB_CURRENT_VERSION_KEY_DIAGNOSTIC.sql').read_text()
    con = sqlite3.connect(':memory:')
    con.execute("ATTACH DATABASE ':memory:' AS tcz_37526b20")
    con.executescript('''
        CREATE TABLE tcz_37526b20.base_table_assignment(assignment_id TEXT,is_active INTEGER,level_2_full_code TEXT);
        INSERT INTO tcz_37526b20.base_table_assignment VALUES ('synthetic-A',1,'6502'),('synthetic-B',1,'6502'),('synthetic-B',1,'6502'),('synthetic-C',1,'6502'),('synthetic-D',1,'6502');
        CREATE TABLE tcz_37526b20.root_table(assignment_id TEXT,assignment_date_modified TEXT,assignment_id_timestamp TEXT);
        INSERT INTO tcz_37526b20.root_table VALUES ('synthetic-A','v1','t1'),('synthetic-A','v1','t1'),('synthetic-B','v1','t1'),('synthetic-C',NULL,'t1'),('synthetic-D','v1','t1'),('synthetic-D','v2','t2');
    ''')
    rows = con.execute(query).fetchall()
    status = {r[0]:r[5] for r in rows}
    assert status=={'synthetic-A':'AMBIGUOUS_KEY','synthetic-B':'AMBIGUOUS_KEY','synthetic-C':'INVALID_VERSION_KEY','synthetic-D':'CANDIDATE_UNIQUE_AT_OBSERVATION'}
    assert all(len(row)==8 for row in rows)
    assert next(r for r in rows if r[0]=='synthetic-D')[1:3]==('v2','t2')
    con.close()
