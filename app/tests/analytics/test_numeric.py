from decimal import Decimal
import pytest

from se2026.analytics.numeric import ExactSum,Quantity,parse_decimal,read_field,sum_quantities,worker_valid


@pytest.mark.parametrize('value,status',[(None,'EMPTY'),('','EMPTY'),('  ','EMPTY'),('0','VALID'),
    ('NaN','INVALID'),('Infinity','INVALID'),(True,'INVALID_TYPE'),(0.1,'INVALID_TYPE'),('Rp 1.000','INVALID')])
def test_missing_invalid_and_float_do_not_become_money(value,status):
    assert parse_decimal(value).status==status


def test_locale_requires_explicit_rule_for_ambiguous_separators():
    assert parse_decimal('1.234','auto_strict').status=='AMBIGUOUS_SEPARATOR'
    assert parse_decimal('1,234','auto_strict').status=='AMBIGUOUS_SEPARATOR'
    assert parse_decimal('1.234','id_ID').value==Decimal('1234')
    assert parse_decimal('1.234','canonical').value==Decimal('1.234')
    assert parse_decimal('1.234,56','id_ID').value==Decimal('1234.56')
    assert parse_decimal('1,234.56','en_US').value==Decimal('1234.56')
    assert parse_decimal('1.234.567','auto_strict').value==Decimal('1234567')


def test_exact_sum_does_not_round_at_default_decimal_precision():
    result=ExactSum();result.add('123456789012345678901234567890.123456789');result.add('0.000000001')
    assert result.result()=='123456789012345678901234567890.123456790'
    empty=ExactSum();empty.add(None)
    assert empty.result() is None
    empty.add('0');assert Decimal(empty.result())==0


def test_unit_and_period_cannot_be_silently_mixed():
    annual=Quantity(Decimal('1.5'),'source_currency','ANNUAL_2025')
    monthly=Quantity(Decimal('1.5'),'source_currency','MONTHLY_2026')
    with pytest.raises(ValueError,match='MEASURE_UNIT_OR_PERIOD_MISMATCH'):sum_quantities([annual,monthly])
    assert sum_quantities([annual,Quantity(None,'source_currency','ANNUAL_2025')]).value==Decimal('1.5')


def test_p1_opaque_field_is_never_reinterpreted_even_if_text_looks_numeric():
    assert read_field('1000',{'numeric_policy':'OPAQUE_NON_NUMERIC'}).status=='NON_NUMERIC_FIELD_EXCLUDED'


@pytest.mark.parametrize('values,valid',[(('2','3','5'),1),(('0','0','0'),1),((None,'0','0'),0),
    (('-1','3','2'),0),(('1.5','3','4.5'),0),(('2','3','6'),0)])
def test_worker_cohort_is_explicit_and_consistent(values,valid):
    assert worker_valid(*values)==valid
