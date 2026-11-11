"""Local read-only audit of residential/mixed/special-business parent buildings."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.analytics.business_location_audit import location_report
from se2026.common import sha256


def main():
    database=ROOT/'data/processed/se2026.sqlite'
    before=sha256(database)
    result=location_report(database,ROOT)
    after=sha256(database)
    if before!=after:raise ValueError('CENSUS_DATABASE_CHANGED_DURING_READ')
    template=ROOT/'codex_app_brief/referensi/DTD/SE2026.html'
    result.update(generated_utc=datetime.now(timezone.utc).isoformat(),census_sha256=after,census_unchanged=True,
                  local_template_path=str(template.relative_to(ROOT)),local_template_sha256=sha256(template),
                  mapping={'1':'Bangunan Khusus Usaha','2':'Bangunan Campuran','3':'Bangunan Tempat Tinggal'},
                  mapping_evidence='Local DTD pilihan_kode_bang expression and kode_bang sourceOption; SQL r.kode_bang_value. Template read as text, never executed.')
    (ROOT/'docs/reports/app/BUSINESS_LOCATION_AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('roster_prelist_attribute_by_category','roster_business_kind_by_category')},ensure_ascii=True))


if __name__=='__main__':main()
