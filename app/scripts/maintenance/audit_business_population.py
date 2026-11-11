"""Audit local census read-only, writing a separate private model and aggregate report."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.analytics.business_audit import audit


def main():
    source=ROOT/'data/processed/se2026.sqlite'
    before=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
    result=audit(source,ROOT/'data/app/business_audit.sqlite',ROOT)
    after=hashlib.file_digest(source.open('rb'),'sha256').hexdigest()
    if before!=after:
        raise ValueError('CENSUS_DATABASE_CHANGED_DURING_AUDIT')
    result.update(generated_utc=datetime.now(timezone.utc).isoformat(),census_sha256=after,census_unchanged=True)
    target=ROOT/'docs/reports/app/BUSINESS_DATA_AUDIT.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('inventory','imports')},ensure_ascii=True))


if __name__=='__main__':
    main()
