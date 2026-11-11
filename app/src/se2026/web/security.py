import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field

from .database import token_hash

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
hasher = PasswordHash.recommended()
dummy_hash = hasher.hash(secrets.token_urlsafe(24))
ROLES = {"admin", "analyst_detail", "aggregate_viewer"}


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
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


def current_user(request: Request):
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
            "SELECT u.id,u.username,u.role,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1",
            (token_hash(token), int(time.time())),
        ).fetchone()
    if not row:
        raise HTTPException(401, "SESSION_EXPIRED")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        csrf_guard(request)
        if not secrets.compare_digest(row["csrf"], request.headers.get("x-csrf-token", "")):
            raise HTTPException(403, "CSRF_REQUIRED")
    return dict(row)


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
            "business_focus_enabled": request.app.state.settings.business_focus_enabled,
        }
    user = None
    try:
        user = current_user(request)
        csrf = user["csrf"]
    except HTTPException:
        pass
    response.set_cookie("portal_csrf", csrf, httponly=False, **cookie_options(request))
    with request.app.state.app_db.connection() as con:
        setup = con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    return {
        "user": public_user(user) if user else None,
        "csrf_token": csrf,
        "setup_required": setup,
        "auth_enabled": True,
        "business_focus_enabled": request.app.state.settings.business_focus_enabled,
    }


def require_auth_enabled(request: Request):
    if not request.app.state.settings.auth_enabled:
        raise HTTPException(403, "AUTH_DISABLED")


def strong_password(value):
    if len(value) < 12:
        raise HTTPException(422, "PASSWORD_MINIMUM_12_CHARACTERS")


@router.post("/setup", dependencies=[Depends(require_auth_enabled), Depends(csrf_guard)])
def setup(payload: Credentials, request: Request):
    if not request.app.state.settings.allow_web_setup:
        raise HTTPException(403, "WEB_SETUP_DISABLED")
    strong_password(payload.password)
    with request.app.state.app_db.connection() as con:
        con.execute("BEGIN IMMEDIATE")
        if con.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
            raise HTTPException(409, "SETUP_ALREADY_COMPLETE")
        con.execute(
            "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
            (payload.username, hasher.hash(payload.password), "admin", int(time.time())),
        )
    request.app.state.app_db.audit(None, "ADMIN_SETUP")
    return {"status": "ADMIN_CREATED"}


@router.post("/login", dependencies=[Depends(require_auth_enabled), Depends(csrf_guard)])
def login(payload: Credentials, request: Request, response: Response):
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
            "SELECT id,username,password_hash,role,active FROM users WHERE username=?", (payload.username,)
        ).fetchone()
    valid = hasher.verify(payload.password, user["password_hash"] if user else dummy_hash)
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
    return {"user": public_user(user), "csrf_token": csrf}


@router.post("/logout", dependencies=[Depends(require_auth_enabled)])
def logout(request: Request, response: Response, user=Depends(current_user)):
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
                dict(row) for row in con.execute("SELECT id,username,role,active FROM users ORDER BY id")
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
