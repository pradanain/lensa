"""Optional stricter portal policy layered over the established k=5 semantic API."""

from copy import deepcopy
from decimal import Decimal
from ..analytics.client import complementary_kbli_geo


def protect_metric(result, minimum):
    output = deepcopy(result)
    rows = output["rows"]
    for row in rows:
        if row.get("suppressed"):
            continue
        small = 0 < row["eligible_rows"] < minimum
        if output["kind"] in ("decimal_sum", "decimal_mean"):
            small |= 0 < row["denominator"] < minimum
        if output["kind"] == "rate":
            num = Decimal(str(row["numerator"]))
            small |= 0 < num < minimum or 0 < Decimal(row["denominator"]) - num < minimum
        if small:
            row["suppressed"] = True
    suppressed = [i for i, row in enumerate(rows) if row.get("suppressed")]
    if len(suppressed) == 1 and len(rows) > 1:
        candidates = [i for i in range(len(rows)) if i not in suppressed and rows[i]["eligible_rows"]]
        if candidates:
            rows[min(candidates, key=lambda i: rows[i]["eligible_rows"])]["suppressed"] = True
    for index in complementary_kbli_geo(rows,[i for i,row in enumerate(rows) if row.get('suppressed')]):
        rows[index]['suppressed']=True
    for row in rows:
        if row.get("suppressed"):
            for key in ("eligible_rows", "numerator", "denominator", "excluded_rows", "value", "percentage"):
                row[key] = None
    if any(row.get("suppressed") for row in rows) and output["kind"] == "distribution":
        for row in rows:
            row["percentage"] = None
    output["suppression"]["minimum_contributors"] = minimum
    output["suppression"]["suppressed_rows"] = sum(bool(row.get("suppressed")) for row in rows)
    return output
