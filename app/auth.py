import secrets
import bcrypt
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from itsdangerous import URLSafeTimedSerializer, BadSignature
from app.config import AUTH_ENABLED, AUTH_USERNAME, AUTH_PASSWORD_HASH, SECRET_KEY

# Session duration: 365 days
SESSION_MAX_AGE = 365 * 24 * 60 * 60

_serializer = URLSafeTimedSerializer(SECRET_KEY) if SECRET_KEY else None


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify bcrypt password hash."""
    return bcrypt.checkpw(plain_password.encode(), password_hash.encode())


def create_session_token(username: str) -> str:
    """Create signed session token."""
    if not _serializer:
        raise ValueError("SECRET_KEY not configured")
    return _serializer.dumps({"username": username, "created": datetime.utcnow().isoformat()})


def verify_session_token(token: str) -> str | None:
    """Verify session token and return username, or None if invalid."""
    if not _serializer:
        return None
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("username")
    except (BadSignature, Exception):
        return None


def get_current_user(request: Request) -> str | None:
    """Get username from session cookie."""
    if not AUTH_ENABLED:
        return "anonymous"
    token = request.cookies.get("session")
    if not token:
        return None
    return verify_session_token(token)


async def auth_middleware(request: Request, call_next):
    """Middleware to check authentication."""
    # Skip auth check for login endpoint and static files
    if request.url.path in ["/login", "/api/login"] or request.url.path.startswith("/static/"):
        return await call_next(request)

    if AUTH_ENABLED:
        user = get_current_user(request)
        if not user:
            # Return 401 for API endpoints, redirect for pages
            if request.url.path.startswith("/api/"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
            # For page requests, serve login page instead of redirect
            return await call_next(request)

    return await call_next(request)


def set_session_cookie(response: Response, username: str):
    """Set session cookie on response."""
    token = create_session_token(username)
    response.set_cookie(
        key="session",
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response):
    """Clear session cookie."""
    response.delete_cookie(key="session")
