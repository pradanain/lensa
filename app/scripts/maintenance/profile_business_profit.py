"""Read-only, aggregate feasibility study; does not install a dashboard metric."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP, localcontext
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'app/src'))
from se2026.analytics import Analytics
from se2026.analytics.numeric import parse_decimal
from se2026.common import dump, q, sha256, utcnow
from se2026.web.settings import Settings

SPECS = {
    'dtd_annual_2025': ('umkm_annual', 'ekonomi_tahunan', '2025',
        'total_pendapatan_2025', 'total_pengeluaran_2025',
        ['pendapatan_utama_2025', 'pendapatan_lainnya_2025'],
        ['pengeluaran_gaji_jaminan_sosial', 'biaya_produksi', 'biaya_pembelian_barang_terjual',
         'biaya_operasional', 'biaya_non_operasional'], 'usaha.annual_income_coverage'),
    'dtd_monthly_new_2026': ('umkm_monthly', 'ekonomi_bulanan', 'Bulan terakhir; kalender tidak tersedia',
        'total_pendapatan_bln', 'total_pengeluaran_bln',
        ['pendapatan_utama_bln', 'pendapatan_lainnya_bln'],
        ['pengeluaran_gaji_jaminan_sosial_bln', 'biaya_produksi_bln',
         'biaya_pembelian_barang_terjual_bln', 'biaya_operasional_bln', 'biaya_non_operasional_bln'],
        'usaha.monthly_income_coverage'),
    'ub_form_2025': ('ub_workers', 'ub_b', '2025 menurut PDF; versi digital historis tidak terverifikasi',
        'total_pendapatan', 'total_pengeluaran', ['pendapatan_utama', 'pendapatan_lainnya'],
        ['gaji_dan_jaminan_sosial', 'biaya_produksi', 'biaya_pembelian_barang',
         'biaya_operasional', 'biaya_non_operasional'], 'ub.reported_income_coverage'),
}
ANNUAL_EDGES = [0, 3_000_000, 12_000_000, 30_000_000, 60_000_000, 120_000_000]
MONTHLY_EDGES = [0, 1_000_000, 2_500_000, 5_000_000, 10_000_000,
                 25_000_000, 50_000_000, 100_000_000]
UB_EDGES = [0, 100_000_000, 1_000_000_000, 10_000_000_000, 100_000_000_000, 1_000_000_000_000]


def protected_counts(counts, minimum=5):
    """Suppress small cells and one companion, with no reconstructable percentages."""
    hidden = {k for k, v in counts.items() if 0 < v < minimum}
    if len(hidden) == 1:
        candidates = [k for k, v in counts.items() if k not in hidden and v > 0]
        if candidates:
            hidden.add(min(candidates, key=counts.get))
    return {k: None if k in hidden else v for k, v in counts.items()}


def pair(income, expense):
    values = [parse_decimal(v) for v in (income, expense)]
    if any(v.status == 'EMPTY' for v in values):
        return 'MISSING_TOTAL', None
    if any(v.status != 'VALID' for v in values):
        return 'INVALID_TOTAL', None
    if any(v.value < 0 for v in values):
        return 'NEGATIVE_INPUT_TOTAL', None
    with localcontext() as context:
        context.prec = 2048
        return 'VALID_PAIR', values[0].value - values[1].value


def component_status(total, components):
    """Blanks are zero only for this explicitly labelled source-formula audit."""
    parsed = [parse_decimal(v) for v in [total, *components]]
    if parsed[0].status != 'VALID':
        return 'TOTAL_UNAVAILABLE'
    if any(v.status not in ('VALID', 'EMPTY') or (v.value is not None and v.value < 0)
           for v in parsed[1:]):
        return 'INVALID_COMPONENT'
    with localcontext() as context:
        context.prec = 2048
        if sum((v.value or Decimal(0) for v in parsed[1:]), Decimal(0)) != parsed[0].value:
            return 'MISMATCH'
    return 'MATCH_WITH_BLANKS' if any(v.status == 'EMPTY' for v in parsed[1:]) else 'MATCH'


def distribution(values, edges, negative_label='RUGI', zero_label='IMPAS'):
    counts = {negative_label: 0, zero_label: 0}
    labels = [f'({edges[i]}, {edges[i+1]}]' for i in range(len(edges)-1)] + [f'> {edges[-1]}']
    counts.update(dict.fromkeys(labels, 0))
    for value in values:
        if value <= 0:
            counts[negative_label if value < 0 else zero_label] += 1
        else:
            index = next((i for i, bound in enumerate(edges[1:]) if value <= bound), len(labels)-1)
            counts[labels[index]] += 1
    assert sum(counts.values()) == len(values)
    return protected_counts(counts)


def rounded_quantiles(values):
    """No individual min/max; round aggregate quantiles to 100,000 source units."""
    ordered = sorted(values)
    if len(ordered) < 100:
        return {}
    result = {}
    for percent in [10, 25, 50, 75, 90, 95]:
        index = (len(ordered)-1)*percent//100
        result[f'p{percent}'] = str((ordered[index]/Decimal(100_000)).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP)*100_000)
    return result


def profile(database):
    before = sha256(database)
    output = dict(created_at=utcnow(), database_sha256_before=before, minimum_cell=5,
                  purpose='Internal aggregate feasibility; no feature/range installed', sources={})
    with Analytics(database=database, root=ROOT) as api:
        con = sqlite3.connect(database.as_uri()+'?mode=ro', uri=True)
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        try:
            for name, (query, table, period, income, expense, incparts, expparts, metric) in SPECS.items():
                print('Profiling '+name, flush=True)
                keys = ['assignment_id'] if name.startswith('ub_') else ['assignment_id', '__version_normalized', 'index1']
                columns = ','.join(map(q, keys))
                duplicates = con.execute('SELECT COUNT(*) FROM (SELECT '+columns+' FROM mart_'+table+
                    ' GROUP BY '+columns+' HAVING COUNT(*)>1)').fetchone()[0]
                if duplicates:
                    raise ValueError('SOURCE_GRAIN_NOT_UNIQUE')
                sql = (ROOT/'app/sql/analytics'/('dashboard_'+query+'.sql')).read_text(encoding='utf-8').strip().rstrip(';')
                # Reuse the registered completed-cohort predicate, projecting only financial fields.
                fields = [income, expense, *incparts, *expparts]
                tail = sql[sql.index(' FROM '):]
                cursor = con.execute('SELECT '+','.join('p.'+q(c) for c in fields)+tail)
                statuses, income_check, expense_check = Counter(), Counter(), Counter()
                profits, revenues, consistent_profits = [], [], []
                rows = 0
                for row in cursor:
                    rows += 1
                    status, profit = pair(row[0], row[1])
                    statuses[status] += 1
                    ic = component_status(row[0], row[2:2+len(incparts)])
                    ec = component_status(row[1], row[2+len(incparts):])
                    income_check[ic] += 1
                    expense_check[ec] += 1
                    if profit is not None:
                        profits.append(profit)
                        revenues.append(parse_decimal(row[0]).value)
                        if ic.startswith('MATCH') and ec.startswith('MATCH'):
                            consistent_profits.append(profit)
                public = api.query(metric)
                public_rows = public['rows'][0]['eligible_rows']
                if public_rows != rows:
                    raise ValueError('REGISTRY_COHORT_MISMATCH')
                assert sum(statuses.values()) == rows
                edges = UB_EDGES if name.startswith('ub_') else MONTHLY_EDGES if 'monthly' in name else ANNUAL_EDGES
                output['sources'][name] = dict(period=period, unit='IDR per reference form; no scaling applied',
                    source_view='mart_'+table, income_field=income, expense_field=expense,
                    source_rows=con.execute('SELECT COUNT(*) FROM mart_'+table).fetchone()[0],
                    module_completed_rows=rows, registry_cohort_reconciled=True, duplicate_keys=duplicates,
                    total_pair_status=protected_counts(dict(statuses)),
                    income_component_check=protected_counts(dict(income_check)),
                    expense_component_check=protected_counts(dict(expense_check)),
                    consistent_pairs=protected_counts({'consistent':len(consistent_profits),
                        'inconsistent_valid_pairs':len(profits)-len(consistent_profits)}),
                    profit_quantiles_rounded_100000=rounded_quantiles(profits),
                    revenue_quantiles_rounded_100000=rounded_quantiles(revenues),
                    profit_bands_all_valid=distribution(profits, edges),
                    # Comparing two distributions must not reveal a withheld mismatch count.
                    profit_bands_consistent=(distribution(consistent_profits, edges)
                        if len(profits) == len(consistent_profits) else None),
                    revenue_bands=distribution(revenues, edges, 'NEGATIVE_REVENUE', 'ZERO_REVENUE'))
            output['cohort_counts_public'] = {
                metric: api.query(metric)['rows'] for metric in ['usaha.enumerated_count','ub.enumerated_count']}
            overlap = con.execute('SELECT COUNT(*) FROM mart_ekonomi_tahunan a WHERE EXISTS '
                '(SELECT 1 FROM mart_ekonomi_bulanan b WHERE a.assignment_id=b.assignment_id '
                'AND a.__version_normalized=b.__version_normalized AND a.index1=b.index1)').fetchone()[0]
            output['annual_monthly_key_overlap'] = overlap
            output['quick_check'] = [r[0] for r in con.execute('PRAGMA quick_check')]
            output['foreign_key_violations'] = sum(1 for _ in con.execute('PRAGMA foreign_key_check'))
        finally:
            con.close()
    output['database_sha256_after'] = sha256(database)
    output['database_unchanged'] = before == output['database_sha256_after']
    if not output['database_unchanged']:
        raise ValueError('DATABASE_CHANGED_DURING_PROFILE')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=None)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = profile((args.database or Settings().census_db).resolve())
    dump(args.output, result)
    print(json.dumps({'report':str(args.output),'database_unchanged':result['database_unchanged']}))
