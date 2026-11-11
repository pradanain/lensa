"""Local geographic labels only; no respondent or contact fields."""

import json
import re
from collections import defaultdict


class SlsReference:
    def __init__(self, root, path=None):
        path = path or root / "app/config/references/subsls-2025-2-6502.json"
        document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"rows": []}
        self.period = document.get("period")
        self.by_subsls = {}
        grouped = defaultdict(list)
        for row in document["rows"]:
            code, sls = row["code"], row["sls"]
            if not re.fullmatch(r"[0-9]{16}", code) or sls != code[:14] or code in self.by_subsls:
                raise ValueError("INVALID_SUBSLS_REFERENCE_KEY")
            self.by_subsls[code] = row
            grouped[sls].append(row)
        # An SLS label is used only when all its SUB-SLS records agree.
        self.by_sls = {
            code: rows[0]
            for code, rows in grouped.items()
            if len({(row["label"], row.get("rt"), row.get("rw")) for row in rows}) == 1
        }

    def describe(self, sls, subsls=None):
        result = dict(
            sls_label=None,
            subsls_label=None,
            rt=None,
            rw=None,
            geography_reference_status="NOT_IN_REFERENCE",
            geography_reference_period=self.period,
        )
        if sls and subsls and not str(subsls).startswith(str(sls)):
            result["geography_reference_status"] = "INCONSISTENT_CODES"
            return result
        row = self.by_subsls.get(subsls)
        exact = row is not None
        row = row or self.by_sls.get(sls)
        if row is None:
            return result
        result.update(
            sls_label=row["label"],
            rt=row.get("rt"),
            rw=row.get("rw"),
            geography_reference_status="SUBSLS_EXACT" if exact else "SLS_EXACT",
        )
        if exact:
            result["subsls_label"] = row["label"] + " · SUB-SLS " + row["code"][-2:]
        return result

    def choice_label(self, level, code):
        if not code:
            return "SLS belum tersedia" if level == "sls" else "SUB-SLS belum tersedia"
        row = self.by_subsls.get(code) if level == "subsls" else self.by_sls.get(code)
        if row:
            suffix = " · SUB-SLS " + code[-2:] if level == "subsls" else ""
            return row["label"] + suffix + " · " + code
        return ("SLS " if level == "sls" else "SUB-SLS ") + code + " (referensi belum tersedia)"
