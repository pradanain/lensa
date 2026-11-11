"""Aggregate-only CLI for the local semantic layer. No ingestion or dashboard."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'app/src'))
from se2026.analytics import Analytics
from se2026.analytics.registry import AnalyticsError


def main():
    parser=argparse.ArgumentParser(description='Read-only SE2026 local aggregate query')
    parser.add_argument('--list',action='store_true')
    parser.add_argument('--metric')
    parser.add_argument('--group-by',nargs='*')
    parser.add_argument('--filter',action='append',default=[],help='Whitelisted_dimension=value; repeat as needed')
    parser.add_argument('--location',choices=['assignment','response'],default='assignment')
    args=parser.parse_args()
    try:
        filters={}
        for item in args.filter:
            if '=' not in item:raise AnalyticsError('FILTER_REQUIRES_KEY_VALUE')
            key,value=item.split('=',1)
            filters.setdefault(key,[]).append(value)
        with Analytics() as api:
            if args.list:
                result=[dict(metric_id=m['metric_id'],name=m['name'],kind=m['kind'],domain=m['domain']) for m in api.registry.metrics.values()]
            elif args.metric:
                result=api.query(args.metric,filters,args.group_by,args.location)
            else:
                raise AnalyticsError('METRIC_OR_LIST_REQUIRED')
        print(json.dumps(result,ensure_ascii=True,indent=2))
        return 0
    except Exception as error:
        print('FAILED: '+(str(error) if isinstance(error,AnalyticsError) else type(error).__name__)+'; no source row values logged.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
