"""Read-only annual gross-sales classification study, superseding the profit proposal."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import localcontext
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'app/src'))
from se2026.analytics import Analytics
from se2026.analytics.numeric import parse_decimal
from se2026.common import dump, q, sha256, utcnow
from se2026.web.settings import Settings
from profile_business_profit import SPECS, protected_counts

CLASSES = ['MIKRO', 'KECIL', 'MENENGAH', 'BESAR', 'BELUM_TERSEDIA',
           'NILAI_TIDAK_VALID', 'PERIODE_BULANAN']
LIMITS = [2_000_000_000, 15_000_000_000, 50_000_000_000]


def turnover_class(value, *, annual=True, estimate_monthly=False):
    parsed = parse_decimal(value)
    if parsed.status == 'EMPTY':
        return 'BELUM_TERSEDIA'
    if parsed.status != 'VALID' or parsed.value < 0:
        return 'NILAI_TIDAK_VALID'
    if not annual and not estimate_monthly:
        return 'PERIODE_BULANAN'
    with localcontext() as context:
        context.prec = 2048
        amount = parsed.value if annual else parsed.value * 12
    for label, limit in zip(CLASSES[:3], LIMITS):
        if amount <= limit:
            return label
    return 'BESAR'


def inspect_rows(rows, *, annual=True, estimate_monthly=False):
    """Only the gross goods/services amount drives classification, never expenses."""
    counts = Counter(dict.fromkeys(CLASSES, 0))
    comparison = Counter({'unchanged': 0, 'changed_or_missing': 0})
    zeros = Counter({'zero': 0, 'other': 0})
    for gross, total in rows:
        label = turnover_class(gross, annual=annual, estimate_monthly=estimate_monthly)
        counts[label] += 1
        comparison['unchanged' if label == turnover_class(total, annual=annual, estimate_monthly=estimate_monthly)
                   else 'changed_or_missing'] += 1
        parsed = parse_decimal(gross)
        zeros['zero' if parsed.value == 0 else 'other'] += 1
    return counts, comparison, zeros


def cohort_counts(counts, source_profiles):
    """A combined cohort must not expose a withheld source cell by subtraction."""
    published = protected_counts(dict(counts))
    for source in source_profiles:
        for label, count in source['classification'].items():
            if count is None:
                published[label] = None
    return published


def profile(database, *, annualize_new_2026=False):
    before = sha256(database)
    result = dict(created_at=utcnow(), measure='gross_goods_services_before_expenses',
        purpose='Corrected internal study; no UI or registry change',
        annual_upper_bounds_idr=LIMITS, minimum_cell=5,
        annualization=annualize_new_2026,
        annualization_rule='monthly gross x 12; user-authorized estimate' if annualize_new_2026 else None,
        database_sha256_before=before, sources={})
    with Analytics(database=database, root=ROOT) as api:
        con = sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        try:
            raw_dtd_counts = Counter(dict.fromkeys(CLASSES, 0))
            dtd_module_rows = 0
            for name, (query, table, period, total, _, incparts, _, metric) in SPECS.items():
                print('Profiling turnover '+name, flush=True)
                keys = ['assignment_id'] if name.startswith('ub_') else ['assignment_id','__version_normalized','index1']
                cols = ','.join(map(q, keys))
                duplicates = con.execute('SELECT COUNT(*) FROM (SELECT '+cols+' FROM mart_'+table+
                    ' GROUP BY '+cols+' HAVING COUNT(*)>1)').fetchone()[0]
                if duplicates:
                    raise ValueError('SOURCE_GRAIN_NOT_UNIQUE')
                sql = (ROOT/'app/sql/analytics'/('dashboard_'+query+'.sql')).read_text(encoding='utf-8').strip().rstrip(';')
                tail = sql[sql.index(' FROM '):]
                gross = incparts[0]
                rows = con.execute('SELECT p.'+q(gross)+',p.'+q(total)+tail)
                monthly = 'monthly' in name
                counts, comparison, zeros = inspect_rows(rows, annual=not monthly,
                    estimate_monthly=annualize_new_2026)
                count = sum(counts.values())
                if api.query(metric)['rows'][0]['eligible_rows'] != count:
                    raise ValueError('REGISTRY_COHORT_MISMATCH')
                if not name.startswith('ub_'):
                    # Keep the whole monthly module as a period exclusion in the cohort.
                    # A finer monthly missing split must not be reconstructed from totals.
                    if monthly and not annualize_new_2026:
                        raw_dtd_counts['PERIODE_BULANAN'] += count
                    else:
                        raw_dtd_counts.update(counts)
                    dtd_module_rows += count
                result['sources'][name] = dict(period=period, source_view='mart_'+table,
                    annual_value_basis='ESTIMATE_MONTHLY_X12' if monthly and annualize_new_2026
                        else 'MONTHLY_NOT_CLASSIFIED' if monthly else 'REPORTED_ANNUAL',
                    gross_field=gross, total_field_for_sensitivity_only=total,
                    completed_module_rows=count, duplicate_keys=duplicates,
                    registry_cohort_reconciled=True, classification=protected_counts(dict(counts)),
                    classification_if_using_total_comparison=protected_counts(dict(comparison)),
                    gross_zero_check=protected_counts(dict(zeros)))
            overlap = con.execute('SELECT COUNT(*) FROM mart_ekonomi_tahunan a WHERE EXISTS '
                '(SELECT 1 FROM mart_ekonomi_bulanan b WHERE a.assignment_id=b.assignment_id '
                'AND a.__version_normalized=b.__version_normalized AND a.index1=b.index1)').fetchone()[0]
            if overlap:
                raise ValueError('ANNUAL_MONTHLY_OVERLAP')
            dtd_total = api.query('usaha.enumerated_count')['rows'][0]['eligible_rows']
            ub_total = api.query('ub.enumerated_count')['rows'][0]['eligible_rows']
            absent = dtd_total-dtd_module_rows
            if absent < 0:
                raise ValueError('MODULE_ROWS_EXCEED_COHORT')
            raw_dtd_counts['BELUM_TERSEDIA'] += absent
            assert sum(raw_dtd_counts.values()) == dtd_total
            if result['sources']['ub_form_2025']['completed_module_rows'] != ub_total:
                raise ValueError('UB_MODULE_COHORT_MISMATCH')
            result['dtd_completed_cohort'] = dict(rows=dtd_total,
                classification=cohort_counts(raw_dtd_counts,
                    [p for name,p in result['sources'].items() if not name.startswith('ub_')]))
            result['ub_completed_cohort_rows'] = ub_total
            result['annual_monthly_key_overlap'] = overlap
            result['quick_check'] = [row[0] for row in con.execute('PRAGMA quick_check')]
            result['foreign_key_violations'] = sum(1 for _ in con.execute('PRAGMA foreign_key_check'))
        finally:
            con.close()
    result['database_sha256_after'] = sha256(database)
    result['database_unchanged'] = before == result['database_sha256_after']
    if not result['database_unchanged']:
        raise ValueError('DATABASE_CHANGED_DURING_STUDY')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--annualize-new-2026', action='store_true',
                        help='Estimate annual gross for businesses started in 2026 as monthly gross x 12')
    args = parser.parse_args()
    result = profile((args.database or Settings().census_db).resolve(),
                     annualize_new_2026=args.annualize_new_2026)
    dump(args.output, result)
    print(json.dumps({'report':str(args.output), 'database_unchanged':result['database_unchanged']}))
