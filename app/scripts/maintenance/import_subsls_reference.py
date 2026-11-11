"""Extract an allowlisted geographic reference from a local workbook.

Never exports chair names, contact persons, counts, or other workbook fields.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[3]
COMPONENTS = {"kdprov": 2, "kdkab": 2, "kdkec": 3, "kddesa": 3, "kdsls": 4, "kdsubsls": 2}


def extract(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        sheet.reset_dimensions()
        values = sheet.iter_rows(values_only=True)
        headers = next(values)
        required = [*COMPONENTS, "idsubsls", "semester", "nmsls", "jenis"]
        indexes = {key: headers.index(key) for key in required}
        rows, periods, seen = [], set(), set()
        numeric_ids = 0
        for raw in values:
            if raw[indexes["idsubsls"]] is None:
                continue
            row = {
                key: raw[indexes[key]].strip() if isinstance(raw[indexes[key]], str) else raw[indexes[key]]
                for key in required
            }
            if any(
                not isinstance(row[key], str) or not re.fullmatch(r"[0-9]{" + str(width) + r"}", row[key])
                for key, width in COMPONENTS.items()
            ):
                raise ValueError("REFERENCE_COMPONENT_MUST_BE_FIXED_WIDTH_TEXT")
            code = "".join(row[key] for key in COMPONENTS)
            numeric_ids += isinstance(row["idsubsls"], int)
            if str(row["idsubsls"]) != code or code in seen:
                raise ValueError("REFERENCE_ID_MISMATCH_OR_DUPLICATE")
            if not isinstance(row["nmsls"], str) or not row["nmsls"].strip():
                raise ValueError("REFERENCE_LABEL_MISSING")
            seen.add(code)
            periods.add(row["semester"])
            label = row["nmsls"].strip()
            rt = re.search(r"\bRT\s*\.?\s*([0-9]+)", label, re.IGNORECASE)
            rw = re.search(r"\bRW\s*\.?\s*([0-9]+)", label, re.IGNORECASE)
            rows.append(
                dict(
                    code=code,
                    sls=code[:14],
                    label=label,
                    rt=rt[1] if rt else None,
                    rw=rw[1] if rw else None,
                    kind=row["jenis"],
                )
            )
        if len(periods) != 1:
            raise ValueError("REFERENCE_REQUIRES_SINGLE_PERIOD")
        return dict(
            schema_version=1,
            period=next(iter(periods)),
            source_name=path.name,
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            normalization="Trim outer whitespace; retain fixed-width text components",
            numeric_ids_verified_against_components=numeric_ids,
            rows=sorted(rows, key=lambda row: row["code"]),
        )
    finally:
        workbook.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "app/config/references/subsls-2025-2-6502.json")
    args = parser.parse_args()
    document = extract(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError("REFERENCE_OUTPUT_ALREADY_EXISTS_REVIEW_BEFORE_REPLACING")
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reference_rows": len(document["rows"]), "period": document["period"]}))


if __name__ == "__main__":
    main()
