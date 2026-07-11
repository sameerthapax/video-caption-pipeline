from datetime import datetime

from pydantic import BaseModel


class AuthCredentialsRequest(BaseModel):
    email: str
    password: str


class AuthUserResponse(BaseModel):
    id: str
    email: str | None


class AuthSessionResponse(BaseModel):
    user: AuthUserResponse


class AuthProfileResponse(BaseModel):
    user: AuthUserResponse
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    active_jobs: int
    latest_job_at: datetime | None
