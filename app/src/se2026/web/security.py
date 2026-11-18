import secrets
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field

from .database import token_hash

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
hasher = PasswordHash.recommended()
dummy_hash = hasher.hash(secrets.token_urlsafe(24))
ROLES = {"admin", "analyst_detail", "aggregate_viewer"}
COMMITMENT_VERSION = "privacy_commitment_v1"


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9_.@+-]+$")
    password: str = Field(min_length=1, max_length=256)


class NewUser(Credentials):
    role: str


def cookie_options(request):
    return dict(secure=request.app.state.settings.secure_cookies, samesite="strict", path="/")


def csrf_guard(request: Request):
    origin = request.headers.get("origin")
    if origin and origin not in request.app.state.settings.allowed_origins:
        raise HTTPException(403, "ORIGIN_REJECTED")
    cookie = request.cookies.get("portal_csrf", "")
    header = request.headers.get("x-csrf-token", "")
    if len(cookie) < 32 or not secrets.compare_digest(cookie, header):
        raise HTTPException(403, "CSRF_REQUIRED")


def authenticated_user(request: Request):
    if not request.app.state.settings.auth_enabled:
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            csrf_guard(request)
        # Temporary local access. This identity is never inserted into users
        # or sessions; existing accounts remain available when login is enabled.
        return {
            "id": None,
            "username": "Lokal",
            "role": "admin",
            "csrf": request.cookies.get("portal_csrf", ""),
        }
    token = request.cookies.get("portal_session")
    if not token:
        raise HTTPException(401, "LOGIN_REQUIRED")
    with request.app.state.app_db.connection() as con:
        row = con.execute(
            "SELECT u.id,u.username,u.role,u.must_change_password,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1",
            (token_hash(token), int(time.time())),
        ).fetchone()
    if not row:
        raise HTTPException(401, "SESSION_EXPIRED")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf_guard(request)
        if not secrets.compare_digest(row["csrf"], request.headers.get("x-csrf-token", "")):
            raise HTTPException(403, "CSRF_REQUIRED")
    return dict(row)


def commitment_accepted(request: Request):
    with request.app.state.app_db.connection() as con:
        return con.execute(
            "SELECT 1 FROM session_commitments WHERE token_hash=? AND version=?",
            (token_hash(request.cookies.get("portal_session", "")), COMMITMENT_VERSION),
        ).fetchone() is not None


def password_ready_user(request: Request):
    user = authenticated_user(request)
    if user.get("must_change_password"):
        raise HTTPException(403, "PASSWORD_CHANGE_REQUIRED")
    return user


def current_user(request: Request):
    user = password_ready_user(request)
    if request.app.state.settings.auth_enabled and not commitment_accepted(request):
        raise HTTPException(403, "COMMITMENT_REQUIRED")
    return user


def require_detail(user=Depends(current_user)):
    if user["role"] not in ("admin", "analyst_detail"):
        raise HTTPException(403, "DETAIL_ACCESS_REQUIRED")
    return user


def require_admin(user=Depends(current_user)):
    if user["id"] is None:
        raise HTTPException(403, "AUTH_DISABLED")
    if user["role"] != "admin":
        raise HTTPException(403, "ADMIN_REQUIRED")
    return user


def public_user(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "can_detail": user["role"] != "aggregate_viewer",
        "can_sensitive": user["role"] == "admin",
        "must_change_password": bool(user.get("must_change_password")),
    }


@router.get("/session")
def session(request: Request, response: Response):
    csrf = request.cookies.get("portal_csrf") or secrets.token_urlsafe(32)
    if not request.app.state.settings.auth_enabled:
        response.set_cookie("portal_csrf", csrf, httponly=False, **cookie_options(request))
        return {
            "user": public_user(current_user(request)),
            "csrf_token": csrf,
            "setup_required": False,
            "auth_enabled": False,
            "password_change_required": False,
            "commitment_required": False,
            "commitment_version": COMMITMENT_VERSION,
            "business_focus_enabled": request.app.state.settings.business_focus_enabled,
        }
    user = None
    try:
        user = authenticated_user(request)
        csrf = user["csrf"]
    except HTTPException:
        pass
    response.set_cookie("portal_csrf", csrf, httponly=False, **cookie_options(request))
    return {
        "user": public_user(user) if user else None,
        "csrf_token": csrf,
        "setup_required": False,
        "password_change_required": bool(user and user.get("must_change_password")),
        "auth_enabled": True,
        "commitment_required": bool(user) and not commitment_accepted(request),
        "commitment_version": COMMITMENT_VERSION,
        "business_focus_enabled": request.app.state.settings.business_focus_enabled,
    }


def require_auth_enabled(request: Request):
    if not request.app.state.settings.auth_enabled:
        raise HTTPException(403, "AUTH_DISABLED")


def strong_password(value):
    if (len(value) < 8 or len(value) > 256 or not re.search(r"[A-Z]", value)
            or not re.search(r"[0-9]", value)
            or not any(not c.isalnum() and not c.isspace() for c in value)):
        raise HTTPException(422, "PASSWORD_POLICY_REQUIRED")


@router.post("/setup", dependencies=[Depends(require_auth_enabled), Depends(csrf_guard)])
def setup(payload: Credentials, request: Request):
    raise HTTPException(403, "WEB_SETUP_DISABLED")


@router.post("/login", dependencies=[Depends(require_auth_enabled), Depends(csrf_guard)])
def login(payload: Credentials, request: Request, response: Response):
    request.state.activity_attempt = payload.username
    now = int(time.time())
    client = token_hash(request.client.host if request.client else "local")
    db = request.app.state.app_db
    with db.connection() as con:
        attempt = con.execute(
            "SELECT failures,window_start FROM login_attempts WHERE client_hash=?", (client,)
        ).fetchone()
        if attempt and attempt["failures"] >= 5 and now - attempt["window_start"] < 300:
            raise HTTPException(429, "LOGIN_RATE_LIMIT")
        user = con.execute(
            "SELECT id,username,password_hash,role,active,must_change_password FROM users WHERE username=?", (payload.username,)
        ).fetchone()
    valid = hasher.verify(payload.password, user["password_hash"] if user else dummy_hash)
    if user:
        request.state.activity_context = {"attempted_user_id": user["id"]}
    if not user or not valid or not user["active"]:
        with db.connection() as con:
            old = attempt["failures"] if attempt and now - attempt["window_start"] < 300 else 0
            start = attempt["window_start"] if old else now
            con.execute(
                "INSERT INTO login_attempts VALUES(?,?,?) ON CONFLICT(client_hash) DO UPDATE SET failures=excluded.failures,window_start=excluded.window_start",
                (client, old + 1, start),
            )
        db.audit(None, "LOGIN", "DENIED")
        raise HTTPException(401, "LOGIN_FAILED")
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    with db.connection() as con:
        con.execute("BEGIN IMMEDIATE")
        if not con.execute("SELECT 1 FROM users WHERE id=? AND password_hash=? AND active=1", (user["id"], user["password_hash"])).fetchone():
            raise HTTPException(401, "LOGIN_FAILED")
        con.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        con.execute("DELETE FROM login_attempts WHERE client_hash=?", (client,))
        con.execute(
            "INSERT INTO sessions VALUES(?,?,?,?)",
            (token_hash(token), user["id"], csrf, now + request.app.state.settings.session_hours * 3600),
        )
    response.set_cookie(
        "portal_session",
        token,
        httponly=True,
        max_age=request.app.state.settings.session_hours * 3600,
        **cookie_options(request),
    )
    response.set_cookie("portal_csrf", csrf, httponly=False, **cookie_options(request))
    db.audit(user["id"], "LOGIN")
    request.state.activity_user = {"id": user["id"], "role": user["role"], "session_ref": request.app.state.activity.fingerprint("session", token_hash(token))}
    return {"user": public_user(dict(user)), "csrf_token": csrf,
            "password_change_required": bool(user["must_change_password"]),
            "commitment_required": True, "commitment_version": COMMITMENT_VERSION}


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)
    confirm_password: str = Field(min_length=1, max_length=256)


@router.post("/change-password", dependencies=[Depends(require_auth_enabled)])
def change_password(payload: PasswordChange, request: Request, response: Response, user=Depends(authenticated_user)):
    strong_password(payload.new_password)
    if payload.new_password != payload.confirm_password:
        raise HTTPException(422, "PASSWORD_CONFIRMATION_MISMATCH")
    now = int(time.time())
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    with request.app.state.app_db.connection() as con:
        con.execute("BEGIN IMMEDIATE")
        current = con.execute("SELECT password_hash FROM users WHERE id=? AND active=1", (user["id"],)).fetchone()
        if not current or not con.execute("SELECT 1 FROM sessions WHERE token_hash=? AND user_id=? AND expires_at>?",
                                         (token_hash(request.cookies.get("portal_session", "")), user["id"], now)).fetchone():
            raise HTTPException(401, "SESSION_EXPIRED")
        if not hasher.verify(payload.current_password, current["password_hash"]):
            raise HTTPException(400, "CURRENT_PASSWORD_INVALID")
        if hasher.verify(payload.new_password, current["password_hash"]):
            raise HTTPException(422, "PASSWORD_MUST_DIFFER")
        con.execute("UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?",
                    (hasher.hash(payload.new_password), user["id"]))
        # Revoke every session issued under the old password, including its pact.
        con.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        con.execute("INSERT INTO sessions VALUES(?,?,?,?)",
                    (token_hash(token), user["id"], csrf, now + request.app.state.settings.session_hours * 3600))
        con.execute("INSERT INTO audit(occurred_at,user_id,action,outcome) VALUES(?,?,?,?)",
                    (now, user["id"], "PASSWORD_CHANGED", "OK"))
    response.set_cookie("portal_session", token, httponly=True,
                        max_age=request.app.state.settings.session_hours * 3600, **cookie_options(request))
    response.set_cookie("portal_csrf", csrf, httponly=False, **cookie_options(request))
    request.state.activity_context = {"new_session_ref": request.app.state.activity.fingerprint("session", token_hash(token))}
    return {"status": "PASSWORD_CHANGED", "csrf_token": csrf, "password_change_required": False,
            "commitment_required": True, "commitment_version": COMMITMENT_VERSION}


class CommitmentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=80)
    accepted: bool


@router.post("/commitment", dependencies=[Depends(require_auth_enabled)])
def accept_commitment(payload: CommitmentDecision, request: Request, user=Depends(password_ready_user)):
    if payload.version != COMMITMENT_VERSION:
        raise HTTPException(409, "COMMITMENT_VERSION_CHANGED")
    if not payload.accepted:
        raise HTTPException(422, "COMMITMENT_ACCEPTANCE_REQUIRED")
    key = token_hash(request.cookies.get("portal_session", ""))
    now = int(time.time())
    with request.app.state.app_db.connection() as con:
        con.execute("BEGIN IMMEDIATE")
        if not con.execute("SELECT 1 FROM sessions WHERE token_hash=? AND expires_at>?", (key, now)).fetchone():
            raise HTTPException(401, "SESSION_EXPIRED")
        previous = con.execute("SELECT version FROM session_commitments WHERE token_hash=?", (key,)).fetchone()
        if not previous or previous["version"] != COMMITMENT_VERSION:
            con.execute(
                "INSERT INTO session_commitments VALUES(?,?,?) ON CONFLICT(token_hash) DO UPDATE SET version=excluded.version,accepted_at=excluded.accepted_at",
                (key, COMMITMENT_VERSION, now),
            )
            con.execute("INSERT INTO audit(occurred_at,user_id,action,outcome) VALUES(?,?,?,?)",
                        (now, user["id"], "COMMITMENT_ACCEPTED:" + COMMITMENT_VERSION, "OK"))
    return {"status": "COMMITMENT_ACCEPTED", "version": COMMITMENT_VERSION}


@router.post("/logout", dependencies=[Depends(require_auth_enabled)])
def logout(request: Request, response: Response, user=Depends(authenticated_user)):
    with request.app.state.app_db.connection() as con:
        con.execute(
            "DELETE FROM sessions WHERE token_hash=?", (token_hash(request.cookies["portal_session"]),)
        )
    response.delete_cookie("portal_session", path="/")
    request.app.state.app_db.audit(user["id"], "LOGOUT")
    return {"status": "SIGNED_OUT"}


@router.get("/users")
def users(request: Request, user=Depends(require_admin)):
    with request.app.state.app_db.connection() as con:
        return {
            "rows": [
                dict(row) for row in con.execute("SELECT id,username,role,active,must_change_password FROM users ORDER BY id")
            ]
        }


@router.post("/users")
def add_user(payload: NewUser, request: Request, user=Depends(require_admin)):
    strong_password(payload.password)
    if payload.role not in ROLES:
        raise HTTPException(422, "ROLE_NOT_ALLOWED")
    import sqlite3

    try:
        with request.app.state.app_db.connection() as con:
            con.execute(
                "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
                (payload.username, hasher.hash(payload.password), payload.role, int(time.time())),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "USERNAME_ALREADY_EXISTS") from None
    request.app.state.app_db.audit(user["id"], "USER_CREATED")
    return {"status": "USER_CREATED"}


class UserUpdate(BaseModel):
    role: str
    active: bool


@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, request: Request, user=Depends(require_admin)):
    if payload.role not in ROLES or user_id == user["id"]:
        raise HTTPException(422, "ROLE_CHANGE_NOT_ALLOWED")
    with request.app.state.app_db.connection() as con:
        changed = con.execute(
            "UPDATE users SET role=?,active=? WHERE id=?", (payload.role, int(payload.active), user_id)
        ).rowcount
        if not changed:
            raise HTTPException(404, "USER_NOT_FOUND")
        con.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    request.app.state.app_db.audit(user["id"], "USER_UPDATED")
    return {"status": "USER_UPDATED"}
