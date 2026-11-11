"""Explicit numeric formats, no float coercion and no implicit missing=zero."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
import re


@dataclass(frozen=True)
class ParsedNumber:
    value: Decimal | None
    status: str
    format: str


def _parse(text, style):
    if style=='canonical':
        if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',text):
            return None
    elif style=='id_ID':
        if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?',text):
            return None
        text=text.replace('.','').replace(',','.')
    elif style=='en_US':
        if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?',text):
            return None
        text=text.replace(',','')
    else:
        raise ValueError('NUMERIC_FORMAT_NOT_ALLOWED')
    try:
        value=Decimal(text)
    except InvalidOperation:
        return None
    if not value.is_finite() or len(value.as_tuple().digits)>256 or abs(value.as_tuple().exponent)>1000:
        return None
    return value


def parse_decimal(value, style='canonical'):
    if value is None or isinstance(value,str) and not value.strip():
        return ParsedNumber(None,'EMPTY',style)
    if isinstance(value,(float,bool)):
        return ParsedNumber(None,'INVALID_TYPE',style)
    text=str(value).strip()
    if style=='auto_strict':
        candidates={v for fmt in ('canonical','id_ID','en_US') if (v:=_parse(text,fmt)) is not None}
        if len(candidates)>1:
            return ParsedNumber(None,'AMBIGUOUS_SEPARATOR',style)
        number=next(iter(candidates),None)
    else:
        number=_parse(text,style)
    return ParsedNumber(number,'VALID' if number is not None else 'INVALID',style)


class ExactSum:
    """Integer coefficient accumulator, independent of Decimal context precision."""
    def __init__(self):
        self.coefficient=0
        self.exponent=0
        self.count=0

    def add(self, value):
        number=parse_decimal(value)
        if number.status!='VALID':
            return
        sign,digits,exponent=number.value.as_tuple()
        coefficient=int(''.join(map(str,digits)) or '0') * (-1 if sign else 1)
        if self.count==0:
            self.exponent=exponent
        target=min(self.exponent,exponent)
        self.coefficient=self.coefficient*10**(self.exponent-target)+coefficient*10**(exponent-target)
        self.exponent=target
        self.count+=1

    def result(self):
        if not self.count:
            return None
        number=Decimal((int(self.coefficient<0),tuple(map(int,str(abs(self.coefficient)))),self.exponent))
        return format(number,'f')

    def step(self,value):
        self.add(value)

    def finalize(self):
        return self.result()


def ratio(numerator,denominator,multiplier=1):
    if numerator is None or not denominator:
        return None
    with localcontext() as context:
        number=Decimal(str(numerator))
        context.prec=max(80,len(number.as_tuple().digits)+max(number.as_tuple().exponent,0)+len(str(denominator))+20)
        return format((Decimal(str(numerator))*Decimal(multiplier)/Decimal(denominator)).quantize(Decimal('0.000001')),'f')


def worker_valid(male,female,total):
    values=[parse_decimal(v).value for v in (male,female,total)]
    if any(v is None or v<0 or v!=v.to_integral_value() for v in values):
        return 0
    accumulator=ExactSum()
    accumulator.add(values[0]);accumulator.add(values[1])
    return int(Decimal(accumulator.result())==values[2])


@dataclass(frozen=True)
class Quantity:
    value: Decimal | None
    unit: str
    period: str


def sum_quantities(quantities):
    items=list(quantities)
    if not items:raise ValueError('MEASURE_CONTEXT_REQUIRED')
    if any((item.unit,item.period)!=(items[0].unit,items[0].period) for item in items):
        raise ValueError('MEASURE_UNIT_OR_PERIOD_MISMATCH')
    total=ExactSum()
    for item in items:total.add(item.value)
    result=total.result()
    return Quantity(None if result is None else Decimal(result),items[0].unit,items[0].period)


def read_field(value,definition,style=None):
    if value is None or isinstance(value,str) and not value.strip():
        return ParsedNumber(None,'EMPTY',style or definition.get('default_format','not_applicable'))
    if definition.get('numeric_policy')=='OPAQUE_NON_NUMERIC':
        return ParsedNumber(None,'NON_NUMERIC_FIELD_EXCLUDED','not_applicable')
    return parse_decimal(value,style or definition['default_format'])


def worker_band(male, female, total, consistency):
    """Descriptive worker-count intervals; never an official business scale."""
    if consistency not in (None, 'SESUAI') or not worker_valid(male, female, total):
        return 'UNAVAILABLE'
    count=parse_decimal(total).value
    if count==0:return 'ZERO'
    if count<=4:return 'ONE_FOUR'
    if count<=19:return 'FIVE_NINETEEN'
    if count<=99:return 'TWENTY_NINETYNINE'
    return 'HUNDRED_PLUS'
