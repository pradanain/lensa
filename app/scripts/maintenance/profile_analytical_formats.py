"""Classify formats and geographic caveats without logging respondent values."""
import json
import re
import sqlite3
import sys
from collections import Counter
from decimal import Decimal,InvalidOperation
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from se2026.common import dump,q,sha256,write_csv
from audit_analytical_readiness import variable_role


def format_class(value):
    if value is None or not str(value).strip():
        return 'EMPTY'
    text=str(value).strip()
    try:
        number=Decimal(text)
        if number.is_finite():
            return 'FINITE_DECIMAL_SCALAR'
        return 'NONFINITE_NUMERIC'
    except InvalidOperation:
        pass
    try:
        parsed=json.loads(text)
        if isinstance(parsed,dict):return 'JSON_OBJECT'
        if isinstance(parsed,list):return 'JSON_ARRAY'
        return 'JSON_OTHER'
    except (ValueError,TypeError):
        pass
    if re.fullmatch(r'[+-]?[\d.,\s]+',text):
        return 'NUMERIC_SEPARATORS_NOT_NORMALIZED'
    if '<' in text and '>' in text:
        return 'MARKUP_TEXT'
    return 'NON_NUMERIC_TEXT'


def audit(root=ROOT):
    path=root/'docs/reports/readiness/analytical_readiness_audit.json'
    result=json.loads(path.read_text(encoding='utf-8'))
    db=root/result['database']
    if sha256(db)!=result['database_sha256']:
        raise ValueError('BASELINE_CHANGED')
    con=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    con.execute('PRAGMA query_only=ON')
    try:
        formats=[]
        for sid,col in [('p1_pekerjaan','nilai_pend_pekerjaan'),('ekonomi_bulanan','total_aset_bln'),('kantor_unit','aset_unit_2025')]:
            counts=Counter(format_class(row[0]) for row in con.execute('SELECT '+q(col)+' FROM '+q('mart_'+sid)))
            for kind,count in sorted(counts.items()):
                formats.append(dict(dataset=sid,column=col,format_class=kind,rows=count))
        geo=[]
        for sid in ['assignment_tgr','assignment_ub']:
            source=q('mart_'+sid)
            for field in ['kode_kecamatan','kode_desa']:
                count=con.execute('SELECT COUNT(*) FROM '+source+' WHERE LENGTH('+q(field)+')>4 AND SUBSTR('+q(field)+",1,4)='6502' AND TRIM(SUBSTR("+q(field)+",5),'0')='' ").fetchone()[0]
                geo.append(dict(dataset=sid,column=field,rows_code_suffix_all_zero_below_kabupaten=count,
                                interpretation='Observed code shape only; not verified against an external official geography list'))
        result['text_measure_formats']=formats
        result['geographic_code_caveats']=geo
        for row in result['variables']:
            source=next(s for s in result['sources'] if s['dataset']==row['dataset'])
            row['role']=variable_role(row['column'],source['key'])
    finally:
        con.close()
    assert sha256(db)==result['database_sha256']
    dump(path,result)
    write_csv(root/'data/metadata/analytical_variable_catalog.csv',result['variables'])
    write_csv(root/'docs/reports/readiness/analytical_value_formats.csv',formats)
    write_csv(root/'docs/reports/readiness/analytical_geographic_code_caveats.csv',geo)
    print(json.dumps(dict(formats=formats,geographic_caveats=geo,database_unchanged=True),indent=2))


if __name__=='__main__':
    audit()
