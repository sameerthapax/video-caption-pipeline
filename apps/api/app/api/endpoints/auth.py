from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.controllers.auth_controller import get_profile, get_session, sign_in, sign_out, sign_up
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.schemas.auth import AuthCredentialsRequest, AuthProfileResponse, AuthSessionResponse

router = APIRouter()


@router.post("/signup/", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def sign_up_endpoint(payload: AuthCredentialsRequest, response: Response) -> AuthSessionResponse:
    return sign_up(payload=payload, response=response)


@router.post("/login/", response_model=AuthSessionResponse)
def sign_in_endpoint(payload: AuthCredentialsRequest, response: Response) -> AuthSessionResponse:
    return sign_in(payload=payload, response=response)


@router.post("/logout/", status_code=status.HTTP_204_NO_CONTENT)
def sign_out_endpoint(request: Request, response: Response) -> Response:
    return sign_out(request=request, response=response)


@router.get("/session/", response_model=AuthSessionResponse)
def get_session_endpoint(
    response: Response,
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthSessionResponse:
    return get_session(user=user, response=response)


@router.get("/profile/", response_model=AuthProfileResponse)
def get_profile_endpoint(
    response: Response,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthProfileResponse:
    return get_profile(user=user, response=response, db=db)
