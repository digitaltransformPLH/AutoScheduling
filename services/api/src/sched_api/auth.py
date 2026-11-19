"""Login with the ASP.NET app's accounts (dbo.Users via sched.vw_auth_*) [DECISION 19-Nov-2026].

* Passwords: ASP.NET Core Identity `PasswordHasher` format (v3 = PBKDF2 with SHA1/256/512 + header; v2 = PBKDF2-SHA1, 1000 rounds).
* Session: our own HMAC-signed cookie `sched_session` (user id + expiry). Permissions and store scope are re-read from the DB
  (cached 30 s), so a role / store change made in the .NET app applies without logging in again; a deactivated user is out at once.
* Users, roles and store assignments are still managed in the .NET app.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass

from auto_scheduling.settings import get_settings
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import Connection, text

from .deps import get_conn

COOKIE = "sched_session"


class P:
    """Permission codes of the .NET app (dbo.Permissions.Code)."""
    PLANNING_INPUT_VIEW = "Action.Planning.Input.View"
    PLANNING_OVERVIEW_VIEW = "Action.Planning.Overview.View"
    PLANNING_ANALYSIS_VIEW = "Action.Planning.Analysis.View"
    PUBLISH_SCHEDULE = "Action.Publish.Schedule"
    STORE_MANAGE = "Action.Store.Manage"
    EMPLOYEE_VIEW = "Action.Employee.View"
    EMPLOYEE_MANAGE = "Action.Employee.Manage"
    AVAILABILITY_VIEW = "Action.EmployeeAvailability.View"
    AVAILABILITY_MANAGE = "Action.EmployeeAvailability.Manage"
    STORE_CONFIG_VIEW = "Action.StoreConfig.View"
    STORE_CONFIG_MANAGE = "Action.StoreConfig.Manage"


# what each platform action needs (any one of the codes)
SCHEDULE_VIEW = (P.PLANNING_OVERVIEW_VIEW, P.PLANNING_ANALYSIS_VIEW)
RUN_ENGINE = (P.PUBLISH_SCHEDULE,)
INPUT_VIEW = (P.PLANNING_INPUT_VIEW, P.EMPLOYEE_VIEW, P.AVAILABILITY_VIEW, P.STORE_CONFIG_VIEW)
EMPLOYEE_EDIT = (P.EMPLOYEE_MANAGE,)              # employees + secondments (lending is an employee assignment)
AVAILABILITY_EDIT = (P.AVAILABILITY_MANAGE,)
CONFIG_EDIT = (P.STORE_CONFIG_MANAGE,)            # TCPH target, staff minimums
HOURS_EDIT = (P.STORE_MANAGE,)                    # opening / closing time (dim_store_detail)


@dataclass(frozen=True)
class User:
    id: int
    email: str
    display_name: str
    role: str
    permissions: frozenset[str]
    all_stores: bool
    stores: frozenset[str]

    def can(self, codes: tuple[str, ...]) -> bool:
        return any(c in self.permissions for c in codes)

    def can_store(self, store: str | None) -> bool:
        return bool(store) and (self.all_stores or store in self.stores)


# ------------------------------------------------------------------ password (ASP.NET Core Identity PasswordHasher)
_PRF = {0: "sha1", 1: "sha256", 2: "sha512"}


def verify_aspnet_hash(hashed: str | None, password: str) -> bool:
    try:
        raw = base64.b64decode(hashed or "")
    except ValueError:
        return False
    if not raw:
        return False
    pw = password.encode("utf-8")
    if raw[0] == 0x00 and len(raw) == 49:                         # v2: salt 16 + subkey 32, PBKDF2-SHA1 1000
        salt, sub = raw[1:17], raw[17:]
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha1", pw, salt, 1000, len(sub)), sub)
    if raw[0] == 0x01 and len(raw) >= 13:                         # v3: prf | iter | salt_len | salt | subkey (uint32 big-endian)
        prf, iters, salt_len = (int.from_bytes(raw[i:i + 4], "big") for i in (1, 5, 9))
        salt, sub = raw[13:13 + salt_len], raw[13 + salt_len:]
        if prf not in _PRF or salt_len < 16 or len(sub) < 16 or iters < 1:
            return False
        return hmac.compare_digest(hashlib.pbkdf2_hmac(_PRF[prf], pw, salt, iters, len(sub)), sub)
    return False


# ------------------------------------------------------------------ signed session cookie
_RANDOM_SECRET = secrets.token_bytes(32)


def _secret() -> bytes:
    s = get_settings().session_secret
    return s.encode("utf-8") if s else _RANDOM_SECRET


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def sign_session(user_id: int, now: float | None = None) -> str:
    now = time.time() if now is None else now
    body = _b64(json.dumps({"uid": user_id, "iat": int(now), "exp": int(now + get_settings().session_hours * 3600)}).encode())
    return f"{body}.{_b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())}"


def read_session(token: str | None, now: float | None = None) -> dict | None:
    if not token or token.count(".") != 1:
        return None
    body, sig = token.split(".")
    try:
        if not hmac.compare_digest(_unb64(sig), hmac.new(_secret(), body.encode(), hashlib.sha256).digest()):
            return None
        data = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    return data if data.get("exp", 0) > (time.time() if now is None else now) else None


def set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(COOKIE, sign_session(user_id), max_age=get_settings().session_hours * 3600, httponly=True, samesite="lax",
                        secure=get_settings().cookie_secure, path="/")


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")


# ------------------------------------------------------------------ users from the DB
_CACHE: dict[int, tuple[float, User | None]] = {}
_LOCK = threading.Lock()
CACHE_SECONDS = 30


def load_user(conn: Connection, user_id: int) -> User | None:
    r = conn.execute(text("SELECT UserId, Email, DisplayName, IsActive, AllStores, RoleName FROM sched.vw_auth_user WHERE UserId = :u"),
                     {"u": user_id}).first()
    if r is None or not r.IsActive:
        return None
    perms = frozenset(x[0] for x in conn.execute(text("SELECT PermissionCode FROM sched.vw_auth_user_permission WHERE UserId = :u"),
                                                 {"u": user_id}))
    stores = frozenset(x[0] for x in conn.execute(text("SELECT StoreCode FROM sched.vw_auth_user_store WHERE UserId = :u"), {"u": user_id}))
    return User(r.UserId, r.Email, r.DisplayName, r.RoleName, perms, bool(r.AllStores), stores)


def cached_user(conn: Connection, user_id: int) -> User | None:
    now = time.monotonic()
    with _LOCK:
        hit = _CACHE.get(user_id)
    if hit and now - hit[0] < CACHE_SECONDS:
        return hit[1]
    user = load_user(conn, user_id)
    with _LOCK:
        _CACHE[user_id] = (now, user)
    return user


def forget_user(user_id: int) -> None:
    with _LOCK:
        _CACHE.pop(user_id, None)


# simple brute-force guard: 5 failures per email within 5 minutes -> wait
_FAILS: dict[str, list[float]] = {}
MAX_FAILS, FAIL_WINDOW = 5, 300


def check_password(conn: Connection, email: str, password: str) -> User:
    email = email.strip().lower()
    now = time.time()
    with _LOCK:
        recent = [t for t in _FAILS.get(email, []) if now - t < FAIL_WINDOW]
        _FAILS[email] = recent
    if len(recent) >= MAX_FAILS:
        raise HTTPException(429, "Đăng nhập sai quá nhiều lần, thử lại sau 5 phút")
    r = conn.execute(text("SELECT UserId, PasswordHash, IsActive FROM sched.vw_auth_user WHERE Email = :e"), {"e": email}).first()
    ok = r is not None and bool(r.IsActive) and verify_aspnet_hash(r.PasswordHash, password)
    if not ok:
        with _LOCK:
            _FAILS.setdefault(email, []).append(now)
        raise HTTPException(401, "Sai email hoặc mật khẩu")
    with _LOCK:
        _FAILS.pop(email, None)
    forget_user(r.UserId)
    user = cached_user(conn, r.UserId)
    if user is None:
        raise HTTPException(401, "Tài khoản đã bị khóa")
    return user


# ------------------------------------------------------------------ FastAPI dependencies
def current_user(request: Request, response: Response, conn: Connection = Depends(get_conn)) -> User:
    data = read_session(request.cookies.get(COOKIE))
    if data is None:
        raise HTTPException(401, "Chưa đăng nhập hoặc phiên đã hết hạn")
    user = cached_user(conn, int(data["uid"]))
    if user is None:
        raise HTTPException(401, "Tài khoản không còn hoạt động")
    if time.time() - data.get("iat", 0) > get_settings().session_hours * 1800:     # sliding: renew after half the lifetime
        set_session_cookie(response, user.id)
    return user


def require(*codes: str):
    """Dependency: logged in and holding any of `codes`."""
    def dep(user: User = Depends(current_user)) -> User:
        if not user.can(codes):
            raise HTTPException(403, "Bạn không có quyền thực hiện thao tác này")
        return user
    return dep


def ensure_store(user: User, store: str | None) -> None:
    if not user.can_store(store):
        raise HTTPException(403, f"Bạn không được phân quyền store {store}")
