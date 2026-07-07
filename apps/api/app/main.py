from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.database import initialize_database
from app.middleware.csrf import CSRFMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Video Caption Pipeline API",
    version="0.1.0",
    description="FastAPI backend scaffold for video upload and job/result APIs.",
    lifespan=lifespan,
)

if settings.app_force_https:
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-Id"],
)
app.include_router(api_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    raw_errors = exc.errors()
    logger.warning("Request validation failed for %s %s: %s", request.method, request.url.path, raw_errors)

    errors: list[dict[str, object]] = []
    for error in raw_errors:
        sanitized_error = {
            "type": error.get("type"),
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": error.get("msg"),
            "input": error.get("input"),
        }
        errors.append(sanitized_error)

    messages: list[str] = []
    for error in errors:
        path = ".".join(str(part) for part in error.get("loc", []) if part != "body")
        message = error.get("msg", "Invalid request.")
        messages.append(f"{path}: {message}" if path else message)

    detail = " ".join(messages) if messages else "Invalid request."
    return JSONResponse(status_code=422, content={"detail": detail, "errors": errors})
