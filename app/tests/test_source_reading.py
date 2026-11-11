from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

from se2026.common import records, sheets, timestamp, xlsx_rows
from se2026.scanner import profile_rows
from se2026.ingestion import clean_value
from se2026.common import is_identity


def workbook(path, rows):
    wb = Workbook()
    for row in rows:
        wb.active.append(row)
    wb.save(path)
    return path


def test_temporal_normalization():
    assert timestamp('2026-09-01 12:00:00.14') == timestamp('2026-09-01T12:00:00.140000')
    assert timestamp('2026-09-01T20:00:00+08:00') == timestamp('2026-09-01T12:00:00Z')
    assert timestamp('2026-09-01T12:00:00') != timestamp('2026-09-01T12:00:00Z')
    assert timestamp('invalid') is None
    assert timestamp('2026-09-01 12:00:00.1234567') is None
    assert timestamp('2026-09-01 12:00:00.1234560') == '2026-09-01T12:00:00.123456'


def test_exact_decimal_and_geographic_identifiers():
    assert clean_value('123456789012345.123456789','total_aset','DECIMAL_TEXT')=='123456789012345.123456789'
    assert clean_value('00100.5000','total_aset','DECIMAL_TEXT')=='100.5'
    assert clean_value('01','provinsi_domisili','TEXT')=='01'
    assert is_identity('provinsi_domisili')
    assert is_identity('negara_domisili_luar_negeri')


def test_streaming_cells_and_privacy(tmp_path):
    path = workbook(tmp_path / 'synthetic.xlsx', [
        ['assignment_id','assignment_date_modified','index1','nama_anggota','nilai'],
        ['synthetic-001','2026-09-01 12:00:00.14','01','PRIVATE_SYNTHETIC',10],
        ['synthetic-001','2026-09-01T12:00:00.140000','01','PRIVATE_SYNTHETIC',10],
        ['synthetic-001','2026-09-01 12:00:00.14','01','DIFFERENT_SYNTHETIC',None],
        ['synthetic-001','2026-09-02 12:00:00.14','01','VERSION_2',0],
        [None,'invalid','02',None,'=1+1'],
    ])
    sheet = sheets(path)[0][1]
    rows = list(xlsx_rows(path, sheet))
    assert rows[1][1][2] == '01'
    assert rows[1][1][4] == '10'
    assert rows[-1][2][-1] == 'formula'
    columns = rows[0][1]
    summary, dictionary, state = profile_rows(iter(rows[1:]), columns, 'synthetic', {'columns':columns,'key':columns[:3]})
    assert summary['rows'] == 5
    assert summary['candidates']['full']['distinct'] == 2
    assert summary['candidates']['full']['duplicate_excess'] == 2
    assert summary['conflicting_keys'] == 1
    assert summary['key_null_rows'] == 1
    assert summary['invalid_timestamps']['assignment_date_modified'] == 1
    assert 'PRIVATE_SYNTHETIC' not in str(summary) + str(dictionary)


def test_exact_duplicates_and_missing_cells(tmp_path):
    p = workbook(tmp_path/'duplicates.xlsx', [['id','value'],['0001',None],['0001',None]])
    xml = sheets(p)[0][1]
    rows = list(records(p, xml, 2))
    assert len(rows[0][1]) == 2
    summary, _, _ = profile_rows(rows, ['id','value'], 'synthetic')
    assert summary['identical_duplicate_rows'] == 1


def test_shared_string_reader(tmp_path):
    # Minimal OOXML sheet using shared strings, sparse cells, booleans and errors.
    p = tmp_path/'shared.xlsx'
    with ZipFile(p,'w') as z:
        z.writestr('xl/sharedStrings.xml','<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>000123</t></si></sst>')
        z.writestr('sheet.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1" t="b"><v>1</v></c><c r="D1" t="e"><v>#N/A</v></c></row></sheetData></worksheet>')
    row = next(xlsx_rows(p, 'sheet.xml'))
    assert row[1] == ['000123',None,'1','#N/A']
    assert row[2] == ['text','null','boolean','error']
