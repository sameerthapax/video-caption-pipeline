from fastapi import Request, Response, status
from sqlalchemy.orm import Session

from app.core.auth import ACCESS_TOKEN_COOKIE, AuthenticatedUser, clear_auth_cookies, issue_csrf_cookie, set_auth_cookies
from app.schemas.auth import AuthCredentialsRequest, AuthProfileResponse, AuthSessionResponse, AuthUserResponse
from app.services.job_service import summarize_jobs_for_user
from app.services.auth_service import sign_in_with_password, sign_out_session, sign_up_with_password


def sign_up(*, payload: AuthCredentialsRequest, response: Response) -> AuthSessionResponse:
    session = sign_up_with_password(email=payload.email, password=payload.password)
    set_auth_cookies(response, access_token=session.access_token, refresh_token=session.refresh_token)
    return AuthSessionResponse(user=AuthUserResponse(id=session.user.id, email=session.user.email))


def sign_in(*, payload: AuthCredentialsRequest, response: Response) -> AuthSessionResponse:
    session = sign_in_with_password(email=payload.email, password=payload.password)
    set_auth_cookies(response, access_token=session.access_token, refresh_token=session.refresh_token)
    return AuthSessionResponse(user=AuthUserResponse(id=session.user.id, email=session.user.email))


def sign_out(*, request: Request, response: Response) -> Response:
    access_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if access_token:
        sign_out_session(access_token=access_token)
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


def get_session(*, user: AuthenticatedUser, response: Response) -> AuthSessionResponse:
    issue_csrf_cookie(response)
    return AuthSessionResponse(user=AuthUserResponse(id=user.id, email=user.email))


def get_profile(*, user: AuthenticatedUser, response: Response, db: Session) -> AuthProfileResponse:
    issue_csrf_cookie(response)
    summary = summarize_jobs_for_user(db=db, user_id=user.id)
    return AuthProfileResponse(user=AuthUserResponse(id=user.id, email=user.email), **summary)
