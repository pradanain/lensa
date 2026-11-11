"""Synthetic end-to-end tests: actual transactions and persisted view counts."""
import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
from openpyxl import Workbook

from se2026.common import dump, sha256
from se2026.ingestion import PipelineError, sync
from se2026.organization import reorganize
from se2026.scanner import scan
from se2026.validation import validate

PROJECT = Path(__file__).resolve().parents[2]


def write_workbook(path, columns, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    wb = Workbook()
    wb.active.title = 'Sheet1'
    wb.active.append(columns)
    for row in rows:
        wb.active.append([row.get(col) for col in columns])
    wb.save(path)


@pytest.fixture
def workspace(tmp_path):
    cfg = json.loads((PROJECT/'app/config/sources.json').read_text(encoding='utf-8'))
    cfg = deepcopy(cfg)
    for s in cfg['sources']:
        s['original'] = 'SE2026_BULUNGAN_WORKSPACE/'+s['id']+'.xlsx'
        s['path'] = 'data/raw/'+s['id']+'.xlsx'
        s['sheet_xml'] = 'xl/worksheets/sheet1.xml'
        s['reference_rows'] = None
        row = dict(assignment_id='synthetic-UB' if s['system']=='TCZ' else 'synthetic-A',
                   id_penghubung='synthetic-UB',assignment_date_modified='2026-09-01 12:00:00.14',
                   index1='001',index_usaha='001',index_meteran='001',index_kantor_unit='001',
                   kode_kabupaten='6502',kode_kecamatan='6502010',kode_desa='6502010001',
                   kode_sls='001',kode_subsls='00',total_pendapatan_pekerjaan='100.5')
        rows = [row]
        if s['id']=='keluarga':
            rows += [dict(row)]  # Duplicate parent formerly causes join multiplication.
        if s['id']=='p1_pekerjaan':
            rows[0] = dict(row,assignment_date_modified='2026-09-01T12:00:00.140000')
            rows += [dict(row,index1='003',assignment_date_modified='2026-09-02 12:00:00.14')]
        write_workbook(tmp_path/s['original'],s['columns'],rows)
    dump(tmp_path/'app/config/sources.json',cfg)
    dump(tmp_path/'app/config/incoming.json',{'files':[]})
    scan(tmp_path)
    reorganize(tmp_path,apply=True)
    return tmp_path


def read_database(root, sql):
    c = sqlite3.connect(root/'data/processed/se2026.sqlite')
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def test_report_generation_preserves_database_and_grouped_layout(workspace):
    from se2026.reporting import report

    sync(workspace, apply=True)
    validate(workspace)
    database = workspace/'data/processed/se2026.sqlite'
    before = sha256(database)
    result = report(workspace)

    assert result['datasets'] == 27
    assert sha256(database) == before
    for relative in (
        'docs/reference/DATA_ARCHITECTURE.md',
        'docs/reference/DATA_RELATIONSHIPS.md',
        'docs/reference/DATASET_CATALOG.md',
        'docs/history/WORKSPACE_REORGANIZATION_PLAN.md',
        'docs/history/WORKSPACE_INVENTORY.md',
        'docs/reports/database/DATA_QUALITY_REPORT.md',
        'docs/reports/integration/WORKSPACE_AND_INTEGRATION_FINAL_REPORT.md',
        'docs/reports/integration/PHASE_COMPLETION_LOG.md',
        'data/metadata/original_manifest.json',
    ):
        assert (workspace/relative).is_file(), relative
    for old_directory in ('src', 'scripts', 'tests', 'sql', 'config', 'metadata', 'reports'):
        assert not (workspace/old_directory).exists(), old_directory


def add_incoming(root, kind='partial', value='2026-09-03 12:00:00.14'):
    s = next(s for s in json.loads((root/'app/config/sources.json').read_text())['sources'] if s['id']=='p1_pekerjaan')
    p = root/'data/incoming/p1_pekerjaan/new.xlsx'
    write_workbook(p,s['columns'],[dict(assignment_id='synthetic-A',assignment_date_modified=value,index1='001')])
    dump(root/'app/config/incoming.json',{'files':[dict(source_id='p1_pekerjaan',path=p.relative_to(root).as_posix(),sha256=sha256(p),export_kind=kind,evidence='Synthetic declared export for transaction verification')]})
    scan(root)
    return p


def test_full_integration_dedup_and_idempotency(workspace):
    root = workspace
    plan = sync(root)
    assert plan['new']==27
    assert not (root/'data/processed/se2026.sqlite').exists()
    result = sync(root,apply=True)
    assert result['new']==27
    verified = validate(root)
    assert verified['no_join_multiplication']
    assert verified['deduplicated_rows']==1
    assert verified['social_union_rows']==2
    assert verified['p1_only_rows']==1
    assert read_database(root,'SELECT COUNT(*) FROM mart_keluarga_integrated')==[(1,)]
    assert read_database(root,'SELECT COUNT(*) FROM raw_keluarga')==[(2,)]
    assert read_database(root,'SELECT index1 FROM mart_sosial_p0')==[('001',)]
    assert read_database(root,'SELECT DISTINCT integration_status,questionnaire_version_status FROM mart_ub_integrated')==[('ASSIGNMENT_KEY_VERIFIED','QUESTIONNAIRE_VERSION_NOT_VERIFIED')]
    assert read_database(root,'SELECT total_pendapatan_pekerjaan FROM mart_sosial_p0')==[('100.5',)]
    before = read_database(root,'SELECT COUNT(*) FROM batches')
    assert sync(root,apply=True)['status']=='NO_CHANGES'
    assert read_database(root,'SELECT COUNT(*) FROM batches')==before


def test_rollback_partial_batch_and_activation_gate(workspace):
    root = workspace
    sync(root,apply=True)
    before = read_database(root,'SELECT COUNT(*) FROM imported_files')
    active = read_database(root,'SELECT * FROM active_imports ORDER BY source_id')
    add_incoming(root)
    with pytest.raises(PipelineError,match='SYNTHETIC_INJECTED_FAILURE'):
        sync(root,apply=True,fail_after=1)
    assert read_database(root,'SELECT COUNT(*) FROM imported_files')==before
    assert read_database(root,'SELECT * FROM active_imports ORDER BY source_id')==active
    assert read_database(root,'SELECT COUNT(*) FROM mart_sosial_p0_p1')==[(2,)]
    result = sync(root,apply=True)
    assert result['new']==1
    assert result['counts'][0]['keys_new_to_active']==1
    assert result['counts'][0]['keys_absent_from_new']==2
    assert read_database(root,'SELECT * FROM active_imports ORDER BY source_id')==active
    with pytest.raises(PipelineError,match='ACTIVATION_REQUIRES_DECLARED_FULL_SNAPSHOT'):
        sync(root,apply=True,activate=True)
    assert sync(root,apply=True)['status']=='NO_CHANGES'
    assert validate(root)['integrity']=='ok'


def test_new_full_snapshot_deactivates_mixed_batch_integration(workspace):
    root = workspace
    sync(root,apply=True)
    add_incoming(root,kind='full_snapshot')
    result = sync(root,apply=True,activate=True)
    assert result['new']==1
    assert read_database(root,"SELECT COUNT(*) FROM sqlite_master WHERE name='mart_sosial_p0_p1'")==[(0,)]
    assert read_database(root,'SELECT COUNT(*) FROM imported_files')==[(28,)]
    assert read_database(root,'SELECT COUNT(*) FROM raw_p1_pekerjaan')==[(3,)]
    assert read_database(root,'SELECT COUNT(*) FROM mart_p1_pekerjaan')==[(1,)]


def test_schema_and_unmapped_export_block_mutation(workspace):
    root = workspace
    sync(root,apply=True)
    p = root/'data/incoming/unmapped.xlsx'
    write_workbook(p,['assignment_id'],[dict(assignment_id='synthetic-A')])
    before = read_database(root,'SELECT COUNT(*) FROM imported_files')
    with pytest.raises(PipelineError,match='UNMAPPED_INCOMING_EXPORT'):
        sync(root,apply=True)
    assert read_database(root,'SELECT COUNT(*) FROM imported_files')==before
    source = next(s for s in json.loads((root/'app/config/sources.json').read_text())['sources'] if s['id']=='p1_pekerjaan')
    write_workbook(p,source['columns'][:-1],[dict(assignment_id='synthetic-A')])
    dump(root/'app/config/incoming.json',{'files':[dict(source_id='p1_pekerjaan',path=p.relative_to(root).as_posix(),sha256=sha256(p),export_kind='unknown',evidence='Synthetic schema drift')]})
    with pytest.raises(ValueError,match='SOURCE_SCHEMA_CHANGED'):
        scan(root)
    assert read_database(root,'SELECT COUNT(*) FROM imported_files')==before


def test_conflicting_payloads_are_preserved_and_marked(workspace):
    root = workspace
    sync(root,apply=True)
    source = next(s for s in json.loads((root/'app/config/sources.json').read_text())['sources'] if s['id']=='p1_pekerjaan')
    p = root/'data/incoming/conflict.xlsx'
    row = dict(assignment_id='synthetic-A',assignment_date_modified='2026-09-01 12:00:00.14',index1='001',profesi_lainnya='synthetic-one')
    write_workbook(p,source['columns'],[row,dict(row,profesi_lainnya='synthetic-two')])
    dump(root/'app/config/incoming.json',{'files':[dict(source_id='p1_pekerjaan',path=p.relative_to(root).as_posix(),sha256=sha256(p),export_kind='partial',evidence='Synthetic conflict')]})
    scan(root)
    sync(root,apply=True)
    assert read_database(root,'SELECT COUNT(*) FROM clean_p1_pekerjaan WHERE __conflict=1')==[(2,)]
    assert read_database(root,'SELECT COUNT(*) FROM raw_p1_pekerjaan')==[(4,)]
    assert read_database(root,'SELECT COUNT(*) FROM mart_sosial_p0_p1')==[(2,)]


def test_original_and_copy_checksum_guards(workspace):
    root = workspace
    p = root/'data/raw/keluarga.xlsx'
    with p.open('ab') as f:
        f.write(b'synthetic_changed_copy')
    with pytest.raises(PipelineError,match='SOURCE_CHANGED_OR_NOT_AUDITED'):
        sync(root,apply=True)
    assert not (root/'data/processed/se2026.sqlite').exists()
