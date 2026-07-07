from __future__ import annotations

from dataclasses import dataclass
from secrets import token_urlsafe

import httpx
from fastapi import HTTPException, Request, Response, status

from app.core.config import settings

ACCESS_TOKEN_COOKIE = "vp_access_token"
REFRESH_TOKEN_COOKIE = "vp_refresh_token"
CSRF_COOKIE = "vp_csrf_token"
CSRF_HEADER = "x-csrf-token"
SESSION_MAX_AGE_SECONDS = 30 * 60


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None


@dataclass(frozen=True)
class SupabaseSession:
    access_token: str
    refresh_token: str | None
    user: AuthenticatedUser


def _build_auth_url(path: str) -> str:
    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL must be configured before auth can be used.",
        )
    return f"{settings.supabase_url.rstrip('/')}/auth/v1/{path.lstrip('/')}"


def _require_anon_key() -> str:
    if not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_ANON_KEY must be configured before auth can be used.",
        )
    return settings.supabase_anon_key


def _base_headers() -> dict[str, str]:
    return {
        "apikey": _require_anon_key(),
        "Content-Type": "application/json",
    }


def _parse_user(payload: dict) -> AuthenticatedUser:
    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth payload.")
    return AuthenticatedUser(id=user_id, email=payload.get("email"))


def _fetch_user(access_token: str) -> AuthenticatedUser:
    try:
        response = httpx.get(
            _build_auth_url("user"),
            headers={
                **_base_headers(),
                "Authorization": f"Bearer {access_token}",
            },
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Supabase Auth.",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")

    return _parse_user(response.json())


def set_auth_cookies(response: Response, *, access_token: str, refresh_token: str | None) -> None:
    secure = settings.app_env != "development"
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        max_age=SESSION_MAX_AGE_SECONDS,
        samesite="lax",
        secure=secure,
    )
    if refresh_token:
        response.set_cookie(
            key=REFRESH_TOKEN_COOKIE,
            value=refresh_token,
            httponly=True,
            max_age=SESSION_MAX_AGE_SECONDS,
            samesite="lax",
            secure=secure,
        )
    issue_csrf_cookie(response)


def issue_csrf_cookie(response: Response) -> str:
    secure = settings.app_env != "development"
    csrf_token = token_urlsafe(32)
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        max_age=SESSION_MAX_AGE_SECONDS,
        samesite="lax",
        secure=secure,
    )
    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    secure = settings.app_env != "development"
    response.delete_cookie(ACCESS_TOKEN_COOKIE, httponly=True, samesite="lax", secure=secure)
    response.delete_cookie(REFRESH_TOKEN_COOKIE, httponly=True, samesite="lax", secure=secure)
    response.delete_cookie(CSRF_COOKIE, httponly=False, samesite="lax", secure=secure)


def refresh_supabase_session(refresh_token: str) -> SupabaseSession:
    try:
        response = httpx.post(
            f"{_build_auth_url('token')}?grant_type=refresh_token",
            headers=_base_headers(),
            json={"refresh_token": refresh_token},
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Supabase Auth.",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.")

    payload = response.json()
    user = payload.get("user")
    access_token = payload.get("access_token")
    if not user or not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth payload.")

    return SupabaseSession(
        access_token=access_token,
        refresh_token=payload.get("refresh_token"),
        user=_parse_user(user),
    )


def get_current_user(request: Request, response: Response) -> AuthenticatedUser:
    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if access_token:
        try:
            return _fetch_user(access_token)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_401_UNAUTHORIZED:
                raise

    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    session = refresh_supabase_session(refresh_token)
    set_auth_cookies(response, access_token=session.access_token, refresh_token=session.refresh_token)
    return session.user
