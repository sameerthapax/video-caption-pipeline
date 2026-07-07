from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.core.auth import SupabaseSession, _base_headers, _build_auth_url, _parse_user


def _extract_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or "Authentication request failed."

    return (
        payload.get("msg")
        or payload.get("error_description")
        or payload.get("error")
        or payload.get("message")
        or "Authentication request failed."
    )


def _raise_auth_error(response: httpx.Response) -> None:
    detail = _extract_error_message(response)
    if response.status_code in {
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
    }:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)


def _build_session(payload: dict) -> SupabaseSession:
    user = payload.get("user")
    access_token = payload.get("access_token")
    if not user or not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth payload.")
    return SupabaseSession(
        access_token=access_token,
        refresh_token=payload.get("refresh_token"),
        user=_parse_user(user),
    )


def sign_in_with_password(*, email: str, password: str) -> SupabaseSession:
    try:
        response = httpx.post(
            f"{_build_auth_url('token')}?grant_type=password",
            headers=_base_headers(),
            json={"email": email, "password": password},
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Supabase Auth.",
        ) from exc

    if response.status_code != status.HTTP_200_OK:
        _raise_auth_error(response)

    return _build_session(response.json())


def sign_up_with_password(*, email: str, password: str) -> SupabaseSession:
    try:
        response = httpx.post(
            _build_auth_url("signup"),
            headers=_base_headers(),
            json={"email": email, "password": password},
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Supabase Auth.",
        ) from exc

    if response.status_code not in {status.HTTP_200_OK, status.HTTP_201_CREATED}:
        _raise_auth_error(response)

    return _build_session(response.json())


def sign_out_session(*, access_token: str) -> None:
    try:
        httpx.post(
            _build_auth_url("logout"),
            headers={**_base_headers(), "Authorization": f"Bearer {access_token}"},
            timeout=5.0,
        )
    except httpx.HTTPError:
        return
