import os


os.environ.setdefault("VITE_SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("VITE_SUPABASE_PUBLISHABLE_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.dependencies import get_db  # noqa: E402
from app.db.base import Base   # noqa: E402
from app.main import app    # noqa: E402


@pytest.fixture
def db_session():
    
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    
    @event.listens_for(engine, "connect")
    def _enable_constraints(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA ignore_check_constraints = OFF")
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session):
    
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
