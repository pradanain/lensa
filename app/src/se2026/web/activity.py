"""Private, bounded activity evidence. Never persist request bodies or respondent values."""
import hashlib
import hmac
import ipaddress
import json
import secrets
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from .database import token_hash
from .security import authenticated_user, require_admin, require_auth_enabled
from .xlsx_export import workbook_response

router = APIRouter(prefix="/api/v1/activity", tags=["activity"], dependencies=[Depends(require_auth_enabled)])
FIELDS = ("occurred_at", "user_id", "role", "session_ref", "request_id", "action", "evidence", "endpoint", "method", "status", "duration_ms", "response_bytes", "ip", "agent", "context", "previous_hash")
ACTIONS = {"LOGIN", "LOGOUT", "PASSWORD_CHANGE", "COMMITMENT", "USER_CREATE", "USER_UPDATE", "DIRECTORY_SEARCH", "DETAIL_VIEW", "EXPORT", "API_ACCESS", "PAGE_VIEW", "CONTROL_CLICK", "MONITOR_VIEW", "MONITOR_EXPORT", "INTEGRITY_CHECK"}
SCREENS = {"dashboard", "usaha", "keluarga", "data", "questionnaire", "pengaturan", "monitoring", "referensi", "kualitas", "login", "password", "commitment"}


class ActivityLog:
    def __init__(self, db):
        self.db = db
        with db.connection() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS activity_key(id INTEGER PRIMARY KEY CHECK(id=1), secret TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS activity_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at INTEGER NOT NULL, user_id INTEGER,
                    role TEXT NOT NULL, session_ref TEXT NOT NULL, request_id TEXT NOT NULL,
                    action TEXT NOT NULL, evidence TEXT NOT NULL, endpoint TEXT NOT NULL, method TEXT NOT NULL,
                    status INTEGER NOT NULL, duration_ms INTEGER NOT NULL, response_bytes INTEGER NOT NULL,
                    ip TEXT NOT NULL, agent TEXT NOT NULL, context TEXT NOT NULL,
                    previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS activity_time ON activity_events(occurred_at DESC,id DESC);
                CREATE INDEX IF NOT EXISTS activity_user ON activity_events(user_id,occurred_at DESC);
                CREATE INDEX IF NOT EXISTS activity_session ON activity_events(session_ref,id);
                CREATE INDEX IF NOT EXISTS activity_action ON activity_events(action,occurred_at DESC);
                CREATE INDEX IF NOT EXISTS activity_resource ON activity_events(json_extract(context,'$.resource_ref'),occurred_at DESC);
                CREATE TRIGGER IF NOT EXISTS activity_no_update BEFORE UPDATE ON activity_events BEGIN SELECT RAISE(ABORT,'ACTIVITY_APPEND_ONLY'); END;
                CREATE TRIGGER IF NOT EXISTS activity_no_delete BEFORE DELETE ON activity_events BEGIN SELECT RAISE(ABORT,'ACTIVITY_APPEND_ONLY'); END;
            """)
            if con.execute("SELECT 1 FROM activity_events LIMIT 1").fetchone() and not con.execute("SELECT 1 FROM activity_key WHERE id=1").fetchone():
                raise RuntimeError("ACTIVITY_KEY_MISSING")
            con.execute("INSERT OR IGNORE INTO activity_key VALUES(1,?)", (secrets.token_hex(32),))
            self.key = bytes.fromhex(con.execute("SELECT secret FROM activity_key WHERE id=1").fetchone()[0])

    def fingerprint(self, kind, value):
        return hmac.new(self.key, (kind + ":" + value).encode(), hashlib.sha256).hexdigest()[:32] if value else ""

    def identity(self, request):
        token = request.cookies.get("portal_session", "")
        if not token:
            return {}
        with self.db.connection() as con:
            row = con.execute("SELECT u.id,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1", (token_hash(token), int(time.time()))).fetchone()
        return {"id": row["id"], "role": row["role"], "session_ref": self.fingerprint("session", token_hash(token))} if row else {}

    def append(self, **values):
        with self.db.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            previous = con.execute("SELECT event_hash FROM activity_events ORDER BY id DESC LIMIT 1").fetchone()
            values["previous_hash"] = previous[0] if previous else ""
            raw = json.dumps([values[key] for key in FIELDS], ensure_ascii=True, separators=(",", ":"))
            digest = hmac.new(self.key, raw.encode(), hashlib.sha256).hexdigest()
            con.execute("INSERT INTO activity_events(" + ",".join(FIELDS) + ",event_hash) VALUES(" + ",".join("?" for _ in range(len(FIELDS) + 1)) + ")", [values[key] for key in FIELDS] + [digest])

    def record(self, request, response, identity, started):
        route = request.scope.get("route")
        endpoint = getattr(route, "path", "UNKNOWN_ENDPOINT")
        if endpoint == "/{path:path}":
            endpoint = "SPA"
        action = "API_ACCESS"
        for suffix, name in [("/auth/login", "LOGIN"), ("/auth/logout", "LOGOUT"), ("/auth/change-password", "PASSWORD_CHANGE"), ("/auth/commitment", "COMMITMENT")]:
            if endpoint.endswith(suffix):
                action = name
        if endpoint.endswith("/auth/users") and request.method == "POST":
            action = "USER_CREATE"
        elif endpoint.endswith("/auth/users/{user_id}"):
            action = "USER_UPDATE"
        elif "/directories/" in endpoint and endpoint.endswith("/search"):
            action = "DIRECTORY_SEARCH"
        elif "/questionnaires/" in endpoint:
            action = "DETAIL_VIEW"
        elif endpoint.endswith("/export"):
            action = "EXPORT"
        if endpoint.startswith("/api/v1/activity"):
            action = "MONITOR_EXPORT" if endpoint.endswith("/export") else "INTEGRITY_CHECK" if endpoint.endswith("/integrity") else "MONITOR_VIEW"
        user = getattr(request.state, "activity_user", None) or identity
        context = dict(getattr(request.state, "activity_context", {}))
        params = request.path_params
        for key, allowed in [("system", {"dtd", "ub"}), ("scope", {"assignments", "businesses", "families", "members"})]:
            if params.get(key) in allowed:
                context[key] = params[key]
        if "assignment_id" in params:
            context["resource_ref"] = self.fingerprint("resource", json.dumps([params.get("system"), params["assignment_id"], *[request.query_params.get(k, "") for k in ("version", "business", "member", "meter", "office")]], separators=(",", ":")))
        if "user_id" in params and str(params["user_id"]).isdigit():
            context["target_user_id"] = int(params["user_id"])
        attempt = getattr(request.state, "activity_attempt", None)
        if attempt:
            context["attempted_account_ref"] = self.fingerprint("account", attempt)
        browser = getattr(request.state, "activity_browser", None)
        if browser and response.status_code < 400:
            action = browser.pop("event")
            resource = browser.pop("assignment", "")
            source = browser.pop("system", "")
            parts = [browser.pop(k, "") for k in ("version", "business", "member", "meter", "office")]
            if resource:
                browser["resource_ref"] = self.fingerprint("resource", json.dumps([source, resource, *parts], separators=(",", ":")))
            context.update(browser)
        address = request.client.host if request.client else ""
        try:
            address = str(ipaddress.ip_address(address))
        except ValueError:
            address = "unavailable"
        # Uses ASGI's resolved peer only. Never trust arbitrary forwarding headers here.
        agent = "".join(c for c in request.headers.get("user-agent", "")[:300] if c.isprintable())
        self.append(occurred_at=int(time.time() * 1000), user_id=user.get("id"), role=user.get("role", "anonymous"), session_ref=user.get("session_ref", ""), request_id=request.state.activity_request_id, action=action, evidence="browser" if browser and response.status_code < 400 else "server", endpoint=endpoint, method=request.method, status=response.status_code, duration_ms=max(0, int((time.perf_counter() - started) * 1000)), response_bytes=int(response.headers.get("content-length", "0")), ip=address, agent=agent, context=json.dumps(context, separators=(",", ":"), sort_keys=True))


class BrowserEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event: Literal["PAGE_VIEW", "CONTROL_CLICK"]
    screen: Literal["dashboard", "usaha", "keluarga", "data", "questionnaire", "pengaturan", "monitoring", "referensi", "kualitas", "login", "password", "commitment"]
    control: Literal["navigation", "tab", "select", "button", "map", "search", "pagination", "export", "detail", "other"] = "navigation"
    tab: Literal["", "ringkasan", "direktori", "anggota", "kbli", "rincian", "komposisi"] = ""
    block: Literal["", "b0", "b1_p", "b5", "b_ak", "blokl", "b_ak_lanjutan", "b_perumahan", "ket_jawaban", "cat", "ub_i_1", "ub_i_2", "ub_i_3", "ub_ii", "ub_iii"] = ""
    assignment: str = Field(default="", max_length=128)
    system: Literal["", "dtd", "ub"] = ""
    version: str = Field(default="", max_length=100)
    business: str = Field(default="", max_length=80)
    member: str = Field(default="", max_length=80)
    meter: str = Field(default="", max_length=80)
    office: str = Field(default="", max_length=80)


@router.post("/events")
def browser_event(payload: BrowserEvent, request: Request, user=Depends(authenticated_user)):
    # Only fixed classifications, never DOM text, input values or URLs.
    request.state.activity_browser = payload.model_dump()
    return {"status": "RECORDED"}


def filters(user_id, action, outcome, since, until, session_ref, resource_ref=""):
    terms, args = [], []
    if user_id is not None:
        terms.append("(e.user_id=? OR (e.action='LOGIN' AND json_extract(e.context,'$.attempted_user_id')=?))")
        args.extend([user_id, user_id])
    for clause, value in [("e.action=?", action), ("e.occurred_at>=?", since), ("e.occurred_at<=?", until), ("e.session_ref=?", session_ref)]:
        if value not in (None, ""):
            terms.append(clause)
            args.append(value)
    if action and action not in ACTIONS:
        raise HTTPException(422, "INVALID_REQUEST")
    if resource_ref:
        terms.append("json_extract(e.context,'$.resource_ref')=?")
        args.append(resource_ref)
    if since is not None and until is not None and since > until:
        raise HTTPException(422, "INVALID_REQUEST")
    if outcome:
        terms.append("e.status<400" if outcome == "success" else "e.status>=400")
    return (" WHERE " + " AND ".join(terms)) if terms else "", args


@router.get("")
def events(request: Request, user_id: int | None = Query(default=None, ge=1), action: str = Query(default="", max_length=40), outcome: Literal["", "success", "failure"] = "", since: int | None = Query(default=None, ge=0), until: int | None = Query(default=None, ge=0), session_ref: str = Query(default="", max_length=32, pattern=r"^[a-f0-9]*$"), resource_ref: str = Query(default="", max_length=32, pattern=r"^[a-f0-9]*$"), page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100), user=Depends(require_admin)):
    where, args = filters(user_id, action, outcome, since, until, session_ref, resource_ref)
    with request.app.state.app_db.connection() as con:
        total = con.execute("SELECT count(*) FROM activity_events e" + where, args).fetchone()[0]
        rows = con.execute("SELECT e.*,u.username FROM activity_events e LEFT JOIN users u ON u.id=e.user_id" + where + " ORDER BY e.occurred_at DESC,e.id DESC LIMIT ? OFFSET ?", [*args, page_size, (page - 1) * page_size]).fetchall()
        summary = dict(con.execute("SELECT count(*) total,count(DISTINCT user_id) accounts,sum(CASE WHEN action='LOGIN' AND status<400 THEN 1 ELSE 0 END) logins,sum(CASE WHEN action='EXPORT' AND status<400 THEN 1 ELSE 0 END) exports,sum(CASE WHEN status>=400 THEN 1 ELSE 0 END) failures FROM activity_events e" + where, args).fetchone())
        legacy = con.execute("SELECT count(*) FROM audit").fetchone()[0]
    return {"rows": [dict(row, context=json.loads(row["context"])) for row in rows], "total": total, "summary": summary, "actions": sorted(ACTIONS), "legacy_events": legacy, "timezone": "UTC"}


@router.get("/sessions")
def sessions(request: Request, user=Depends(require_admin)):
    log = request.app.state.activity
    with log.db.connection() as con:
        active = {log.fingerprint("session", r[0]) for r in con.execute("SELECT token_hash FROM sessions WHERE expires_at>?", (int(time.time()),))}
        rows = con.execute("SELECT e.user_id,u.username,e.session_ref,min(e.occurred_at) first_seen,max(e.occurred_at) last_seen,count(*) events,sum(CASE WHEN e.action='EXPORT' AND e.status<400 THEN 1 ELSE 0 END) exports FROM activity_events e LEFT JOIN users u ON u.id=e.user_id WHERE e.session_ref<>'' GROUP BY e.user_id,e.session_ref ORDER BY last_seen DESC LIMIT 100").fetchall()
    return {"rows": [dict(row, active=row["session_ref"] in active) for row in rows], "limit": 100}


@router.get("/integrity")
def integrity(request: Request, user=Depends(require_admin)):
    log = request.app.state.activity
    # A read transaction gives a stable prefix while requests continue appending.
    with log.db.connection() as con:
        con.execute("BEGIN")
        checked, previous, last_id = 0, "", 0
        for row in con.execute("SELECT * FROM activity_events ORDER BY id"):
            raw = json.dumps([row[key] for key in FIELDS], ensure_ascii=True, separators=(",", ":"))
            digest = hmac.new(log.key, raw.encode(), hashlib.sha256).hexdigest()
            if row["previous_hash"] != previous or not hmac.compare_digest(row["event_hash"], digest):
                return {"valid": False, "checked": checked, "failed_id": row["id"], "last_id": last_id, "head": previous}
            checked, previous, last_id = checked + 1, row["event_hash"], row["id"]
    return {"valid": True, "checked": checked, "last_id": last_id, "head": previous}


class ExportFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int | None = Field(default=None, ge=1)
    action: str = Field(default="", max_length=40)
    outcome: Literal["", "success", "failure"] = ""
    since: int | None = Field(default=None, ge=0)
    until: int | None = Field(default=None, ge=0)
    session_ref: str = Field(default="", max_length=32, pattern=r"^[a-f0-9]*$")
    resource_ref: str = Field(default="", max_length=32, pattern=r"^[a-f0-9]*$")


@router.post("/export")
def export(payload: ExportFilter, request: Request, user=Depends(require_admin)):
    where, args = filters(**payload.model_dump())
    with request.app.state.app_db.connection() as con:
        count = con.execute("SELECT count(*) FROM activity_events e" + where, args).fetchone()[0]
        if count > 10000:
            raise HTTPException(422, "ACTIVITY_EXPORT_TOO_LARGE")
        rows = con.execute("SELECT e.*,u.username FROM activity_events e LEFT JOIN users u ON u.id=e.user_id" + where + " ORDER BY e.id", args).fetchall()
    request.state.activity_context = {"exported_events": count}
    columns = ["id", "username", *FIELDS, "event_hash"]
    return workbook_response(columns, ([row[col] for col in columns] for row in rows), "lensa-aktivitas-utc")


async def activity_middleware(request, call_next):
    if not request.url.path.startswith("/api/v1/") or request.url.path == "/api/v1/auth/session":
        return await call_next(request)
    request.state.activity_request_id = secrets.token_hex(16)
    log = request.app.state.activity
    started = time.perf_counter()
    try:
        identity = await run_in_threadpool(log.identity, request)
        try:
            response = await call_next(request)
        except Exception:
            from fastapi.responses import JSONResponse
            response = JSONResponse(status_code=500, content={"detail": "INTERNAL_ERROR_NO_SOURCE_VALUES_LOGGED"})
        await run_in_threadpool(log.record, request, response, identity, started)
    except Exception:
        from fastapi.responses import JSONResponse
        # Fail closed: never deliver data if its activity record cannot be persisted.
        response = JSONResponse(status_code=503, content={"detail": "ACTIVITY_RECORD_UNAVAILABLE"})
    response.headers["X-Request-ID"] = request.state.activity_request_id
    return response
