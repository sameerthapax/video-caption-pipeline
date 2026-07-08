import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_worker.db"
os.environ["SUPABASE_URL"] = "http://localhost:54321"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"

import pytest

from core.database import Base, engine
from models.job import VideoJob


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
