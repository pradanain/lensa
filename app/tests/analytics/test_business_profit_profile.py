"""Synthetic checks for the feasibility study's risky money/missing boundaries."""
import importlib.util
from decimal import Decimal
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2]/'scripts/maintenance/profile_business_profit.py'
SPEC = importlib.util.spec_from_file_location('profit_profile', SCRIPT)
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


def test_missing_invalid_and_negative_inputs_cannot_become_profit():
    assert profile.pair(None, '1') == ('MISSING_TOTAL', None)
    assert profile.pair('10', '') == ('MISSING_TOTAL', None)
    assert profile.pair('1,000', '1') == ('INVALID_TOTAL', None)
    assert profile.pair('-1', '0') == ('NEGATIVE_INPUT_TOTAL', None)
    assert profile.pair('0', '0') == ('VALID_PAIR', Decimal('0'))
    assert profile.pair('0', '100') == ('VALID_PAIR', Decimal('-100'))
    assert profile.pair('123456789012345678901234567890.01', '.01')[1] == Decimal('123456789012345678901234567890')


def test_component_audit_distinguishes_blank_from_explicit_zero_and_mismatch():
    assert profile.component_status('10', ['10', None]) == 'MATCH_WITH_BLANKS'
    assert profile.component_status('10', ['10', '0']) == 'MATCH'
    assert profile.component_status('10', ['11', '0']) == 'MISMATCH'
    assert profile.component_status('10', ['10', 'Rp 0']) == 'INVALID_COMPONENT'
    assert profile.component_status(None, ['0', '0']) == 'TOTAL_UNAVAILABLE'


def test_bands_keep_loss_zero_and_adjacent_boundaries_disjoint():
    values = [Decimal(v) for v in ['-1','0','1','10','10.1','20','21'] for _ in range(5)]
    counts = profile.distribution(values, [0,10,20])
    assert counts == {'RUGI':5,'IMPAS':5,'(0, 10]':10,'(10, 20]':10,'> 20':5}
    assert sum(counts.values()) == len(values)


def test_small_cells_have_complementary_suppression_and_no_extrema_export():
    assert profile.protected_counts({'missing':1,'valid':100,'zero':0}) == {
        'missing':None,'valid':None,'zero':0}
    assert profile.rounded_quantiles([Decimal(5)]*99) == {}
    quantiles = profile.rounded_quantiles([Decimal(1234567)]*100)
    assert set(quantiles) == {'p10','p25','p50','p75','p90','p95'}
    assert set(quantiles.values()) == {'1200000'}
