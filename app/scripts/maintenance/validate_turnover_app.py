"""Validate live turnover grains and reconciliation without persisting private rows."""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'app/src'))
from se2026.analytics import Analytics
from se2026.analytics.turnover import GROUPS, BASES, register_turnover
from se2026.common import dump, sha256, utcnow
from se2026.web.database import census_connection
from se2026.web.directory import DirectoryIndex, DirectoryQuery
from se2026.web.settings import Settings


def validate():
    settings = Settings()
    before = sha256(settings.census_db)
    report = dict(created_at=utcnow(), database_sha256_before=before,
                  checks=[], public_results={}, elapsed_seconds={})
    # Use only a private in-memory projection of keys/status/geography. This
    # exercises the actual directory predicate without touching portal accounts,
    # the disk directory cache, or reading/exporting names and contact details.
    directory = sqlite3.connect(':memory:')
    directory.execute('CREATE TABLE directory_rows(scope TEXT,source TEXT,assignment_id TEXT,'
        'version TEXT,index1 TEXT,status TEXT,kecamatan TEXT,desa TEXT,sls TEXT,subsls TEXT)')
    directory.execute('CREATE INDEX directory_assignment ON directory_rows(assignment_id,scope)')
    directory.execute('CREATE INDEX directory_scope ON directory_rows(scope,source)')
    with census_connection(settings) as con:
        for system, master, business, status in [
            ('dtd','mart_assignment_tgr','mart_usaha','kode_keberadaan_usaha'),
            ('ub','mart_assignment_ub','mart_ub_a','status_keberadaan')]:
            geo = {}
            for row in con.execute('SELECT assignment_id,status_assignment,kode_kecamatan,kode_desa,'
                                   'kode_sls,kode_subsls FROM '+master):
                aid,workflow,*area = row
                geo[aid] = area
                directory.execute('INSERT INTO directory_rows VALUES(?,?,?,?,?,?,?,?,?,?)',
                    ('assignments',system,aid,None,None,workflow,*area))
            columns = 'assignment_id,__version_normalized,index1,'+status if system=='dtd' else 'assignment_id,NULL,NULL,'+status
            for aid,version,index,existence in con.execute('SELECT '+columns+' FROM '+business):
                directory.execute('INSERT INTO directory_rows VALUES(?,?,?,?,?,?,?,?,?,?)',
                    ('businesses',system,aid,version,index,existence,*geo.get(aid,[None]*4)))
        report['integrity_check'] = [row[0] for row in con.execute('PRAGMA integrity_check')]
        report['foreign_key_violations'] = sum(1 for _ in con.execute('PRAGMA foreign_key_check'))
    register_turnover(directory, settings.census_db)
    with Analytics(settings.census_db, settings.root) as api:
        report['validated_definitions'] = api.validate_definitions()
        for system,prefix in [('dtd','usaha'),('ub','ub')]:
            start=time.perf_counter()
            count=api._query(prefix+'.enumerated_count')[1][0]['value']
            raw=api._query(prefix+'.turnover_distribution')[1]
            if sum(row['value'] for row in raw)!=count:
                raise ValueError('TURNOVER_DENOMINATOR_MISMATCH')
            geography=api._query(prefix+'.turnover_distribution',group_by='kecamatan')[1]
            if sum(row['value'] for row in geography)!=count:
                raise ValueError('TURNOVER_GEOGRAPHY_RECONCILIATION_FAILED')
            for dimension,values in [('turnover_group',GROUPS),('turnover_basis',BASES)]:
                for value in values:
                    payload=DirectoryQuery(source=system,enumerated_only=True,**{dimension:value})
                    where,bindings=DirectoryIndex.where('businesses',payload,'admin')
                    actual=directory.execute('SELECT COUNT(*) FROM directory_rows d WHERE '+where,bindings).fetchone()[0]
                    expected=api._query(prefix+'.enumerated_count',filters={dimension:value})[1][0]['value']
                    if actual!=expected:
                        raise ValueError('TURNOVER_DIRECTORY_AGGREGATE_MISMATCH')
                    report['checks'].append(dict(source=system,dimension=dimension,value=value,passed=True))
            for name,groups in [('groups',None),('regions','kecamatan')]:
                report['public_results'][system+'_'+name]=api.query(prefix+'.turnover_distribution',group_by=groups)
            report['public_results'][system+'_basis']=api.query(prefix+'.turnover_basis_distribution')
            report['public_results'][system+'_cohort']=api.query(prefix+'.enumerated_count')
            report['elapsed_seconds'][system]=round(time.perf_counter()-start,3)
            print('Reconciled '+system+' cohort, grouping, geography and directory filters.',flush=True)
    directory.close()
    report['database_sha256_after']=sha256(settings.census_db)
    report['database_unchanged']=before==report['database_sha256_after']
    if not report['database_unchanged'] or report['integrity_check']!=['ok'] or report['foreign_key_violations']:
        raise ValueError('CENSUS_VALIDATION_FAILED')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=validate()
    dump(args.output,report)
    print('Validation passed; census unchanged; only protected aggregates saved.',flush=True)
