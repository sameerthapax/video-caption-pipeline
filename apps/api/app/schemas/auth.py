from pydantic import BaseModel


class AuthCredentialsRequest(BaseModel):
    email: str
    password: str


class AuthUserResponse(BaseModel):
    id: str
    email: str | None


class AuthSessionResponse(BaseModel):
    user: AuthUserResponse
