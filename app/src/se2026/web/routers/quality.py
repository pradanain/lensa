import csv
import json

from fastapi import APIRouter, Depends, Request

from ..security import current_user
from .references import suppress

router = APIRouter(prefix="/api/v1/data-quality", tags=["quality"])


@router.get("/summary")
def quality(request: Request, user=Depends(current_user)):
    settings = request.app.state.settings
    minimum = settings.minimum_contributors

    def mask_counts(values):
        masked = suppress([dict(code=k, units=v) for k, v in values.items()], ["units"], minimum)
        return {row["code"]: row["units"] for row in masked}

    def load(relative):
        path = settings.root / relative
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    foundation = load("docs/reports/analytics/foundation_validation.json")
    validation = load("docs/reports/database/database_validation.json")
    numeric = load("docs/reports/analytics/numeric_profiles.json")
    p1 = []
    path = settings.root / "docs/reports/p1/p1_unmatched_classification.csv"
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                # Only aggregate source/category/count columns are released.
                if row.get("layer") != "CLEAN":
                    continue
                keys = [
                    "total_rows",
                    "SAMA_ANGGOTA_SAMA_VERSI",
                    "SAMA_ANGGOTA_BEDA_VERSI",
                    "ASSIGNMENT_ADA_INDEKS_TIDAK_ADA",
                    "ASSIGNMENT_TIDAK_ADA",
                    "KUNCI_TIDAK_VALID",
                    "unmatched_rows",
                ]
                categories = {k: int(row[k]) for k in keys if k not in ("total_rows", "unmatched_rows")}
                filtered = {"dataset": row["dataset"], **mask_counts(categories)}
                p1.append(filtered)
    with request.app.state.app_db.connection() as con:
        grouped = con.execute(
            "SELECT scope,source,COUNT(*) AS records FROM directory_rows GROUP BY scope,source"
        ).fetchall()
    return dict(
        schema=request.app.state.questionnaires.schema_summary(),
        directory_counts=suppress([dict(r) for r in grouped], ["records"], minimum),
        recorded_validation={
            k: validation.get(k)
            for k in [
                "generated_utc",
                "integrity",
                "foreign_key_violations",
                "raw_rows",
                "clean_rows",
                "no_join_multiplication",
            ]
        },
        geographic_caveats=[
            {**row, "counts_by_code_status": mask_counts(row["counts_by_code_status"])}
            for row in foundation.get("geographic_code_status_counts", [])
        ],
        ub_geography=foundation.get("ub_geography_comparison", {}),
        numeric_profiles=[{**r, "status_counts": mask_counts(r["status_counts"])} for r in numeric]
        if isinstance(numeric, list)
        else [],
        p1_classification=p1,
        minimum_contributors=minimum,
        provenance="Angka audit historis diberi waktu/snapshot sendiri; selisih COUNT bukan kesalahan yang telah terbukti.",
        ub_policy="ASSIGNMENT_KEY_VERIFIED",
        ub_version="QUESTIONNAIRE_VERSION_NOT_VERIFIED — provenance non-blocking",
        source_access="SQL Lab ditutup permanen",
        census_read_only=True,
    )
