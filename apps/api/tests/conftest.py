from pathlib import Path
import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_api.db"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173"
os.environ["SUPABASE_URL"] = "http://localhost:54321"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"

import pytest
from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import Base, engine
from app.main import app


def override_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(id="test-user-id", email="test@example.com")


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = override_current_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
