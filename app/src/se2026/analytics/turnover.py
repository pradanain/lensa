"""Shared read-only turnover semantics for analytics, directories and forms."""
from collections import defaultdict
from dataclasses import dataclass
from decimal import localcontext
from functools import lru_cache
from pathlib import Path
import sqlite3
from threading import Lock

from .numeric import parse_decimal
from .registry import AnalyticsError

GROUPS = ('MIKRO', 'KECIL', 'MENENGAH', 'BESAR', 'UNAVAILABLE', 'REVIEW')
BASES = ('REPORTED_ANNUAL', 'ESTIMATE_MONTHLY_X12', 'UNAVAILABLE')
GROUP_LABELS = dict(zip(GROUPS, ('Mikro','Kecil','Menengah','Besar','Belum tersedia','Perlu diperiksa')))
BASIS_LABELS = dict(zip(BASES, ('Tahunan dilaporkan (2025)','Estimasi bulanan × 12','Belum tersedia')))
LIMITS = (2_000_000_000, 15_000_000_000, 50_000_000_000)
_lock = Lock()


@dataclass(frozen=True)
class Turnover:
    group: str = 'UNAVAILABLE'
    basis: str = 'UNAVAILABLE'
    annual: str | None = None
    monthly: str | None = None
    period: str | None = None
    reason: str = 'MISSING_MODULE'

    def public(self, sensitive=False):
        result = dict(group=self.group, basis=self.basis, period=self.period, reason=self.reason,
                      amount_status='AVAILABLE' if sensitive else 'RESTRICTED')
        if sensitive:
            result.update(annual=self.annual, monthly=self.monthly)
        return result


def classify(value, *, monthly=False):
    parsed = parse_decimal(value)
    basis = 'ESTIMATE_MONTHLY_X12' if monthly else 'REPORTED_ANNUAL'
    period = 'ESTIMATE_12_MONTHS_FROM_2026' if monthly else '2025'
    if parsed.status == 'EMPTY':
        return Turnover(basis=basis, period=period, reason='MISSING_AMOUNT')
    if parsed.status != 'VALID' or parsed.value < 0:
        return Turnover(group='REVIEW', basis=basis, period=period, reason='INVALID_AMOUNT')
    with localcontext() as context:
        context.prec = 2048
        annual = parsed.value * 12 if monthly else parsed.value
    group = next((label for label, bound in zip(GROUPS, LIMITS) if annual <= bound), 'BESAR')
    return Turnover(group, basis, format(annual, 'f'), format(parsed.value, 'f') if monthly else None,
                    period, 'AVAILABLE')


def _rows(connection, table, columns):
    schema = {r[1] for r in connection.execute('PRAGMA table_info("'+table+'")')}
    if not schema:
        return []
    if not set(columns).issubset(schema):
        raise AnalyticsError('TURNOVER_SOURCE_SCHEMA_MISMATCH')
    return connection.execute('SELECT '+','.join('"'+c+'"' for c in columns)+' FROM "'+table+'"')


@lru_cache(maxsize=2)
def _load(database, size, modified):
    connection = sqlite3.connect(Path(database).as_uri()+'?mode=ro', uri=True)
    connection.execute('PRAGMA query_only=ON')
    connection.execute('BEGIN')
    states = {}
    try:
        eligible = set()
        for aid, version, index in connection.execute("SELECT u.assignment_id,u.__version_normalized,u.index1 "
                "FROM mart_usaha u WHERE u.kode_keberadaan_usaha IN ('1','2') AND EXISTS "
                "(SELECT 1 FROM mart_assignment_tgr a WHERE a.assignment_id=u.assignment_id "
                "AND a.status_assignment IN ('APPROVED BY Pengawas','COMPLETED BY Admin Kabupaten'))"):
            eligible.add(('dtd', aid, version, index))
        for (aid,) in connection.execute("SELECT u.assignment_id FROM mart_ub_a u "
                "WHERE u.status_keberadaan='1. Ditemukan dan masih aktif' AND EXISTS "
                "(SELECT 1 FROM mart_assignment_ub a WHERE a.assignment_id=u.assignment_id "
                "AND a.status_assignment IN ('APPROVED BY Pengawas','COMPLETED BY Admin Kabupaten'))"):
            eligible.add(('ub', aid, None, None))
        modules = defaultdict(list)
        for table, amount, monthly in [('mart_ekonomi_tahunan','pendapatan_utama_2025',False),
                                        ('mart_ekonomi_bulanan','pendapatan_utama_bln',True)]:
            columns = ['assignment_id','__version_normalized','index1',amount,
                       'tahun_mulai_operasi','__key_valid','__conflict']
            for aid, version, index, value, year, valid, conflict in _rows(connection, table, columns):
                key = ('dtd', aid, version, index)
                if key not in eligible:
                    continue
                number = parse_decimal(year).value
                year_ok = number is not None and number == number.to_integral_value() and (
                    number == 2026 if monthly else 0 < number < 2026)
                if str(valid) != '1' or str(conflict) != '0' or not year_ok:
                    item = Turnover(group='REVIEW', reason='SOURCE_CONFLICT_OR_PERIOD')
                else:
                    item = classify(value, monthly=monthly)
                modules[key].append(item)
        for aid, amount, valid, conflict in _rows(connection, 'mart_ub_b',
                ['assignment_id','pendapatan_utama','__key_valid','__conflict']):
            key = ('ub', aid, None, None)
            if key in eligible:
                modules[key].append(classify(amount) if str(valid) == '1' and str(conflict) == '0'
                                    else Turnover(group='REVIEW', reason='SOURCE_CONFLICT'))
        for key in eligible:
            matches = modules[key]
            states[key] = (matches[0] if len(matches) == 1 else
                           Turnover(group='REVIEW', reason='AMBIGUOUS_MODULES') if matches else Turnover())
    finally:
        connection.close()
    stamp = Path(database).stat()
    if (stamp.st_size, stamp.st_mtime_ns) != (size, modified):
        raise AnalyticsError('TURNOVER_SNAPSHOT_CHANGED')
    return states


def lookup(database):
    path = Path(database).resolve()
    stat = path.stat()
    with _lock:
        return _load(str(path), stat.st_size, stat.st_mtime_ns)


def record(states, system, assignment, version=None, index=None):
    key = ('ub', assignment, None, None) if system in ('ub','TCZ') else ('dtd', assignment, version, index)
    return states.get(key, Turnover(reason='OUTSIDE_COMPLETED_COHORT'))


def register_turnover(connection, database):
    states = None

    def item(*key):
        nonlocal states
        if states is None:
            states = lookup(database)
        return record(states, *key)

    connection.create_function('TURNOVER_GROUP', 4, lambda *key: item(*key).group, deterministic=True)
    connection.create_function('TURNOVER_BASIS', 4, lambda *key: item(*key).basis, deterministic=True)
