"""SE2026 local CLI. Errors never echo source row contents."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'app/src'))


def main():
    parser = argparse.ArgumentParser(description='Local SE2026 Bulungan audit and SQLite pipeline')
    parser.add_argument('command',choices=['scan','validate','sync','report','organize'])
    parser.add_argument('--apply',action='store_true',help='Apply sync or verified copies')
    parser.add_argument('--dry-run',action='store_true',help='Plan only; default for sync/organize')
    parser.add_argument('--activate',action='store_true',help='Activate declared full snapshots; never partial/delta')
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error('--apply and --dry-run are mutually exclusive')
    try:
        if args.command=='scan':
            from se2026.scanner import scan
            result = scan(ROOT)
            result = dict(status='AUDIT_COMPLETE',datasets=len(result['datasets']))
        elif args.command=='validate':
            from se2026.validation import validate
            result = validate(ROOT)
        elif args.command=='sync':
            from se2026.ingestion import sync
            result = sync(ROOT,apply=args.apply,activate=args.activate)
        elif args.command=='report':
            from se2026.reporting import report
            result = report(ROOT)
        else:
            from se2026.organization import reorganize
            result = reorganize(ROOT,apply=args.apply)
        print(json.dumps(result,ensure_ascii=True,indent=2))
        return 0
    except Exception as error:
        from se2026.ingestion import PipelineError
        code = str(error) if isinstance(error,PipelineError) else type(error).__name__
        print('FAILED: '+code+'; no respondent values logged.',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
