from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from app.auth import (
    AUTH_ENABLED,
    AUTH_USERNAME,
    AUTH_PASSWORD_HASH,
    verify_password,
    set_session_cookie,
    clear_session_cookie,
    get_current_user,
)

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/api/login")
def login(body: LoginRequest):
    """API login endpoint."""
    if not AUTH_ENABLED:
        raise HTTPException(status_code=400, detail="Authentication not enabled")

    if body.username != AUTH_USERNAME or not verify_password(body.password, AUTH_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response = JSONResponse({"ok": True})
    set_session_cookie(response, body.username)
    return response


@router.post("/api/logout")
def logout():
    """API logout endpoint."""
    response = JSONResponse({"ok": True})
    clear_session_cookie(response)
    return response


@router.get("/api/auth/status")
def auth_status(request: Request):
    """Check if user is authenticated."""
    user = get_current_user(request)
    return {
        "authenticated": user is not None,
        "username": user,
        "auth_enabled": AUTH_ENABLED,
    }
