"""Reconcile totals without treating absent scale as an absent business."""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.common import sha256


def main():
    path=ROOT/'data/processed/se2026.sqlite'
    before=sha256(path)
    con=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA query_only=ON')
    con.execute('BEGIN')
    complete="u.kode_keberadaan_usaha IN ('1','2') AND EXISTS (SELECT 1 FROM mart_assignment_tgr a WHERE a.assignment_id=u.assignment_id AND a.status_assignment IN ('APPROVED BY Pengawas','COMPLETED BY Admin Kabupaten'))"
    results={
        'completed_by_status_scale':[dict(r) for r in con.execute("SELECT u.kode_keberadaan_usaha status,COALESCE(NULLIF(TRIM(u.skala_usaha),''),'MISSING') scale,COUNT(*) units FROM mart_usaha u WHERE "+complete+' GROUP BY 1,2')],
        'completed_by_prelist_scale':[dict(r) for r in con.execute("SELECT u.is_prelist2 prelist,COALESCE(NULLIF(TRIM(u.skala_usaha),''),'MISSING') scale,COUNT(*) units FROM mart_usaha u WHERE "+complete+' GROUP BY 1,2')],
        'completed_total':con.execute('SELECT COUNT(*) FROM mart_usaha u WHERE '+complete).fetchone()[0],
        'completed_assignments':con.execute('SELECT COUNT(DISTINCT u.assignment_id) FROM mart_usaha u WHERE '+complete).fetchone()[0],
        'found_new_all_workflows':con.execute("SELECT COUNT(*) FROM mart_usaha WHERE kode_keberadaan_usaha IN ('1','2')").fetchone()[0],
        'source_rosters':con.execute('SELECT COUNT(*) FROM mart_usaha').fetchone()[0],
        'ub_active_completed':con.execute("SELECT COUNT(*) FROM mart_ub_integrated u WHERE u.status_keberadaan='1. Ditemukan dan masih aktif' AND EXISTS(SELECT 1 FROM mart_assignment_ub a WHERE a.assignment_id=u.assignment_id AND a.status_assignment IN ('APPROVED BY Pengawas','COMPLETED BY Admin Kabupaten'))").fetchone()[0],
    }
    con.close()
    after=sha256(path)
    if before!=after:
        raise ValueError('CENSUS_DATABASE_CHANGED_DURING_READ')
    results.update(generated_utc=datetime.now(timezone.utc).isoformat(),census_sha256=after,census_unchanged=True,
                   total_interpretation='COMPLETED_TGR_ROSTER_UNITS_NOT_PHYSICALLY_DEDUPLICATED',
                   missing_scale_policy='INCLUDE_IN_OPERATIONAL_TOTAL_WITHOUT_INFERRING_UMKM_SCALE')
    (ROOT/'docs/reports/app/BUSINESS_TOTAL_RECHECK.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results))


if __name__=='__main__':
    main()
