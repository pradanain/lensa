"""Synthetic coverage of annual thresholds and monthly/missing exclusions."""
import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[2]/'scripts/maintenance/profile_business_turnover.py'
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location('turnover_profile', SCRIPT)
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


@pytest.mark.parametrize('value,expected', [
    ('0', 'MIKRO'), ('2000000000', 'MIKRO'), ('2000000000.01', 'KECIL'),
    ('15000000000', 'KECIL'), ('15000000000.01', 'MENENGAH'),
    ('50000000000', 'MENENGAH'), ('50000000000.01', 'BESAR'),
    (None, 'BELUM_TERSEDIA'), ('', 'BELUM_TERSEDIA'), ('-1', 'NILAI_TIDAK_VALID'),
    ('NaN', 'NILAI_TIDAK_VALID'), ('2.000.000.000', 'NILAI_TIDAK_VALID'),
])
def test_exact_upper_bounds_zero_and_missing(value, expected):
    assert profile.turnover_class(value) == expected


def test_monthly_values_are_never_classified_by_annual_thresholds():
    assert profile.turnover_class('3000000000', annual=False) == 'PERIODE_BULANAN'
    assert profile.turnover_class(None, annual=False) == 'BELUM_TERSEDIA'


def test_primary_gross_is_independent_of_other_income_and_never_filled_from_total():
    counts, comparison, zeros = profile.inspect_rows([
        ('2000000000','3000000000'), (None,'100'), ('0','0')])
    assert counts['MIKRO'] == 2
    assert counts['BELUM_TERSEDIA'] == 1
    assert comparison == {'unchanged':1,'changed_or_missing':2}
    assert zeros['zero'] == 1
    assert sum(counts.values()) == 3


@pytest.mark.parametrize('monthly,expected', [
    ('0', 'MIKRO'), ('166666666.66', 'MIKRO'), ('166666666.67', 'KECIL'),
    ('1250000000', 'KECIL'), ('1250000000.01', 'MENENGAH'),
    ('4166666666.66', 'MENENGAH'), ('4166666666.67', 'BESAR'),
    (None, 'BELUM_TERSEDIA'), ('-1', 'NILAI_TIDAK_VALID')])
def test_explicit_monthly_estimate_multiplies_before_classifying(monthly, expected):
    assert profile.turnover_class(monthly, annual=False, estimate_monthly=True) == expected


def test_estimation_does_not_multiply_reported_annual_amount_or_fill_missing():
    assert profile.turnover_class('2000000000', estimate_monthly=True) == 'MIKRO'
    counts, _, _ = profile.inspect_rows([(None,'100'),('2000000000','2000000000')],
                                       annual=False, estimate_monthly=True)
    assert counts['BELUM_TERSEDIA'] == 1 and counts['MENENGAH'] == 1


def test_combined_cohort_preserves_suppression_across_source_slices():
    assert profile.cohort_counts({'MIKRO':1000,'KECIL':10,'BELUM_TERSEDIA':100},
        [{'classification':{'MIKRO':None,'KECIL':10,'BELUM_TERSEDIA':None}}]) == {
            'MIKRO':None,'KECIL':10,'BELUM_TERSEDIA':None}
