from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from ..security import current_user
from ..xlsx_export import workbook_response

router = APIRouter(prefix="/api/v1", tags=["references"])


class KbliExportQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    qualified_only: bool = False
    enumerated_only: bool = False
    level: int = Field(default=2, ge=1, le=5)
    prefix: str = Field(default="", pattern=r"^[0-9]{0,5}$")
    category: str = Field(default="", pattern=r"^[A-V]?$")
    q: str = Field(default="", max_length=120)


@router.post("/kbli/export")
def export_kbli(payload: KbliExportQuery, request: Request, user=Depends(current_user)):
    # Reuse the same complete-group suppression before omitting UI pagination.
    data = kbli_tree(request=request, user=user, page=1, page_size=100000, **payload.model_dump())
    return workbook_response(
        ["Kategori", "Kode", "Judul", "Definisi", "Rincian Kode", "UMKM", "Usaha Besar (UB)"],
        (
            [
                row.get("category"),
                row["code"],
                row["title"],
                row.get("description"),
                row.get("reference_codes"),
                row["dtd_units"],
                row["ub_units"],
            ]
            for row in data["rows"]
        ),
        "lensa-kbli-2025",
    )


def suppress(rows, fields, minimum=5):
    output = [dict(r) for r in rows]
    for name in fields:
        small = [i for i, r in enumerate(output) if isinstance(r.get(name), int) and 0 < r[name] < minimum]
        if len(small) == 1:
            candidates = [
                i
                for i, r in enumerate(output)
                if i not in small and isinstance(r.get(name), int) and r[name] > 0
            ]
            if candidates:
                small.append(min(candidates, key=lambda i: output[i][name]))
        for i in small:
            output[i][name] = None
            output[i]["suppressed"] = True
    return output


@router.get("/references/summary")
def reference_summary(request: Request, user=Depends(current_user)):
    return request.app.state.references.summary()


@router.get("/references/{kind}")
def reference_search(
    kind: str,
    request: Request,
    q: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=10, ge=1, le=100),
    user=Depends(current_user),
):
    if kind not in ("kbli", "professions", "countries"):
        raise HTTPException(404, "REFERENCE_NOT_FOUND")
    rows = request.app.state.references.search(kind, q, limit=None)
    return dict(
        rows=rows[(page - 1) * page_size : page * page_size],
        total=len(rows),
        page=page,
        page_size=page_size,
        pages=max(1, (len(rows) + page_size - 1) // page_size),
    )


@router.get("/kbli/tree")
def kbli_tree(
    request: Request,
    qualified_only: bool = False,
    enumerated_only: bool = False,
    level: int = Query(default=2, ge=1, le=5),
    prefix: str = Query(default="", pattern=r"^[0-9]{0,5}$"),
    category: str = Query(default="", pattern=r"^[A-V]?$"),
    q: str = Query(default="", max_length=120),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=10, ge=1, le=100),
    user=Depends(current_user),
):
    if prefix and len(prefix) > level:
        raise HTTPException(422, "PREFIX_LEVEL_CONFLICT")
    refs = request.app.state.references
    minimum = request.app.state.settings.minimum_contributors
    nodes = refs.tree(category or None, prefix, level, q)
    actual = {
        system: request.app.state.aggregate_cache.get(
            ("kbli-counts", system, qualified_only, enumerated_only),
            lambda system=system: request.app.state.directory.aggregate_counts(
                "businesses", system, "kbli", qualified_only, enumerated_only
            ),
        )
        for system in ["dtd", "ub"]
    }
    for node in nodes:
        for system in ["dtd", "ub"]:
            node[system + "_units"] = sum(
                row["units"]
                for row in actual[system]
                if row["code"]
                and str(row["code"]).startswith(node["prefix"])
                and row["code"] in refs.kbli
                and (not category or refs.kbli[row["code"]]["category"] == category)
            )
    protected = suppress(nodes, ["dtd_units", "ub_units"], minimum)
    return dict(
        rows=protected[(page - 1) * page_size : page * page_size],
        total=len(nodes),
        page=page,
        page_size=page_size,
        pages=max(1, (len(nodes) + page_size - 1) // page_size),
        selection=refs.hierarchy.selection(category, prefix),
        level=level,
        prefix=prefix,
        category=category,
        unit="record usaha DTD / assignment UB (terpisah)",
        population="LOCAL_AUDIT_QUALIFIED"
        if qualified_only
        else "ENUMERATED_SOURCE_RECORDS"
        if enumerated_only
        else "ALL_SOURCE_RECORDS",
        reference_unit="kode master, bukan unit usaha",
        suppression=f"k={minimum} with complementary suppression",
        unknown_buckets={
            system: suppress(
                request.app.state.aggregate_cache.get(
                    ("kbli-states", system, qualified_only, enumerated_only),
                    lambda system=system: request.app.state.directory.aggregate_counts(
                        "businesses", system, "kbli_state", qualified_only, enumerated_only
                    ),
                ),
                ["units"],
                minimum,
            )
            for system in ["dtd", "ub"]
        },
    )


@router.get("/kbli/catalog")
def kbli_catalog(request: Request, user=Depends(current_user)):
    refs = request.app.state.references
    return dict(
        rows=refs.hierarchy.catalog(),
        unit="kode referensi",
        version="KBLI 2025",
        single_digit_is_technical=True,
    )
