from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..directory import DirectoryQuery
from ..security import current_user, require_detail
from ..xlsx_export import directory_workbook

router = APIRouter(prefix="/api/v1", tags=["records"])


@router.post("/directories/{scope}/export")
def export_directory(scope: str, payload: DirectoryQuery, request: Request, user=Depends(require_detail)):
    if scope not in ("assignments", "businesses", "families", "members"):
        raise HTTPException(404, "SCOPE_NOT_FOUND")
    response = directory_workbook(request.app.state.directory, scope, payload, user["role"])
    request.app.state.app_db.audit(user["id"], "EXPORT_" + scope.upper())
    return response


@router.post("/directories/{scope}/search")
def search(scope: str, payload: DirectoryQuery, request: Request, user=Depends(require_detail)):
    request.app.state.app_db.audit(
        user["id"],
        "DIRECTORY_" + scope.upper()
        if scope in ("assignments", "businesses", "families", "members")
        else "DIRECTORY_UNKNOWN",
    )
    return request.app.state.directory.search(scope, payload, user["role"])


@router.get("/assignments/{system}")
def assignments(
    system: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    kecamatan: str = "",
    desa: str = "",
    sls: str = "",
    status: str = "",
    user=Depends(require_detail),
):
    if system not in ("dtd", "ub"):
        raise HTTPException(404, "SOURCE_NOT_FOUND")
    if "q" in request.query_params:
        raise HTTPException(422, "SEARCH_REQUIRES_POST_BODY")
    return request.app.state.directory.search(
        "assignments",
        DirectoryQuery(
            source=system,
            page=page,
            page_size=page_size,
            kecamatan=kecamatan,
            desa=desa,
            sls=sls,
            status=status,
        ),
        user["role"],
    )


@router.get("/questionnaires/{system}/{assignment_id}")
def questionnaire(
    system: str,
    assignment_id: str,
    request: Request,
    version: str | None = Query(default=None, max_length=100),
    business: str | None = Query(default=None, max_length=80),
    member: str | None = Query(default=None, max_length=80),
    meter: str | None = Query(default=None, max_length=80),
    office: str | None = Query(default=None, max_length=80),
    user=Depends(require_detail),
):
    result = request.app.state.questionnaires.get(
        system, assignment_id, user["role"], version, business, member, meter, office
    )
    request.app.state.app_db.audit(user["id"], "QUESTIONNAIRE_" + system.upper())
    return result


@router.get("/geography")
def geography(
    request: Request,
    source: str = "dtd",
    level: str = "kecamatan",
    parent: str = Query(default="", max_length=40),
    user=Depends(current_user),
):
    return dict(
        rows=request.app.state.directory.geography(source, level, parent),
        concept="assignment",
        codes_are_text=True,
    )


@router.get("/directory-statuses")
def statuses(request: Request, source: str = "dtd", scope: str = "assignments", user=Depends(require_detail)):
    if source not in ("dtd", "ub") or scope not in ("assignments", "businesses", "families", "members"):
        raise HTTPException(422, "SOURCE_NOT_ALLOWED")
    # Preserve existing code list; provide source-backed display labels separately.
    options = request.app.state.directory.status_options(scope, source)
    return dict(rows=[r["code"] for r in options], options=options)
