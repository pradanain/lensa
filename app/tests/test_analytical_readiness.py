"""Synthetic checks for read-only analytical coverage, not respondent data."""
import importlib.util
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def load_script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'app/scripts/maintenance'/(name+'.py'))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_variable_coverage_keeps_zero_separate_from_missing():
    audit=load_script('audit_analytical_readiness')
    con=sqlite3.connect(':memory:')
    con.execute('CREATE TABLE synthetic(amount TEXT,label TEXT)')
    con.executemany('INSERT INTO synthetic VALUES (?,?)',[(None,'A'),('','B'),('  ',None),('0','C'),('100.5','')])
    rows,counts=audit.profile_columns(con,'synthetic',['amount','label'])
    assert rows==5 and counts=={'amount':2,'label':3}
    assert con.execute('SELECT COUNT(*) FROM synthetic').fetchone()[0]==5
    con.close()


def test_relationship_audit_detects_row_multiplication():
    audit=load_script('audit_analytical_readiness')
    con=sqlite3.connect(':memory:')
    con.execute('CREATE TABLE mart_parent(__row_id INTEGER,assignment_id TEXT,__version_normalized TEXT)')
    con.execute('CREATE TABLE mart_child(__row_id INTEGER,assignment_id TEXT,__version_normalized TEXT)')
    con.executemany('INSERT INTO mart_parent VALUES (?,?,?)',[(1,'synthetic-A','v1'),(2,'synthetic-A','v1')])
    con.executemany('INSERT INTO mart_child VALUES (?,?,?)',[(1,'synthetic-A','v1'),(2,'synthetic-A','v2')])
    result=audit.match_coverage(con,'parent','child',['assignment_id','__version_normalized'])
    assert result['child_rows']==2
    assert result['unmatched_child_rows']==1
    assert result['multiplication_excess']==1
    con.close()


def test_text_formats_do_not_silently_convert_locale_or_objects():
    formats=load_script('profile_analytical_formats')
    assert formats.format_class(None)=='EMPTY'
    assert formats.format_class('0')=='FINITE_DECIMAL_SCALAR'
    assert formats.format_class('100.50')=='FINITE_DECIMAL_SCALAR'
    assert formats.format_class('1.234.567')=='NUMERIC_SEPARATORS_NOT_NORMALIZED'
    assert formats.format_class('1.234,56')=='NUMERIC_SEPARATORS_NOT_NORMALIZED'
    assert formats.format_class('{"synthetic":100}')=='JSON_OBJECT'
    assert formats.format_class('synthetic-text')=='NON_NUMERIC_TEXT'


def test_geography_coverage_is_not_geographic_validity():
    audit=load_script('audit_analytical_readiness')
    con=sqlite3.connect(':memory:')
    con.execute('CREATE TABLE mart_assignment_tgr(__row_id INTEGER,assignment_id TEXT,kode_kecamatan TEXT,kode_desa TEXT,kode_sls TEXT,kode_subsls TEXT)')
    con.executemany('INSERT INTO mart_assignment_tgr VALUES (?,?,?,?,?,?)',[(1,'synthetic-A','6502000','6502000000','0','0')])
    con.execute('CREATE TABLE mart_family(assignment_id TEXT)')
    con.executemany('INSERT INTO mart_family VALUES (?)',[('synthetic-A',),('synthetic-unmatched',)])
    row=audit.geo_profile(con,{'id':'family','system':'TGR'})
    assert row['master_missing_rows']==1 and row['kecamatan_populated']==1
    assert row['multiplication_excess']==0
    con.close()


def test_variable_roles_keep_labels_out_of_numeric_measures():
    audit=load_script('audit_analytical_readiness')
    assert audit.variable_role('pendapatan_pekerjaan_label',[])=='KATEGORI_LABEL_ATAU_URAIAN'
    assert audit.variable_role('rentang_aset_2025',[])=='KATEGORI_LABEL_ATAU_URAIAN'
    assert audit.variable_role('total_pendapatan_2025',[])=='UKURAN_KUANTITATIF_PERLU_UNIT'
