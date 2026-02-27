# tests/conftest.py
import os
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from app.db.base import Base
from app.main import app
from app.api.deps import get_db
from app.db.models.org import Org
from app.db.models.project import Project
from app.db.models.device import Device
from app.db.models.rule import Rule
from app.db.models.api_key import ApiKey
from app.core.security import generate_api_key

# ========== PostgreSQL Test Container ==========

@pytest.fixture(scope="session")
def postgres_container():
    """
    Start a PostgreSQL container for the entire test session.
    This container will be reused across all tests for better performance.
    
    Can be skipped if TEST_DATABASE_URL environment variable is set,
    allowing you to use a local PostgreSQL instance for faster iteration.
    """
    # Check if user provided their own PostgreSQL instance
    if os.getenv("TEST_DATABASE_URL"):
        # Skip container creation, user is providing their own DB
        yield None
    else:
        # Use testcontainers
        with PostgresContainer("postgres:15-alpine") as postgres:
            yield postgres


@pytest.fixture(scope="function")
def db_engine(postgres_container):
    """
    Create a test database engine using PostgreSQL.
    
    Priority:
    1. If TEST_DATABASE_URL env var is set, use that
    2. Otherwise, use the testcontainer
    
    Each test gets a fresh database with all tables created.
    """
    # Check for user-provided database URL
    test_db_url = os.getenv("TEST_DATABASE_URL")
    
    if test_db_url:
        # Use provided PostgreSQL instance
        print(f"\nUsing provided PostgreSQL: {test_db_url.split('@')[1] if '@' in test_db_url else 'custom'}")
        engine = create_engine(test_db_url)
    elif postgres_container:
        # Use testcontainer
        connection_url = postgres_container.get_connection_url()
        print(f"\nUsing PostgreSQL testcontainer")
        engine = create_engine(connection_url)
    else:
        raise RuntimeError("No PostgreSQL database available for testing!")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup: drop all tables and dispose engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a test database session.
    Each test gets a fresh session that's rolled back after the test.
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with overridden DB dependency"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# ========== Test Data Fixtures ==========

@pytest.fixture
def test_org(db_session: Session):
    """Create a test organization"""
    org = Org(name="Test Org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org

@pytest.fixture
def test_project(db_session: Session, test_org):
    """Create a test project"""
    project = Project(org_id=test_org.id, name="Test Project")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project

@pytest.fixture
def test_api_key(db_session: Session, test_project):
    """Create a test API key"""
    raw_key, prefix, hashed = generate_api_key()
    api_key = ApiKey(
        project_id=test_project.id,
        prefix=prefix,
        hashed_secret=hashed
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    
    # Return both the key and the raw secret for testing
    api_key.raw_key = raw_key
    return api_key

@pytest.fixture
def test_device(db_session: Session, test_project):
    """Create a test device"""
    device = Device(
        project_id=test_project.id,
        external_id="test-device-001",
        name="Test Device",
        tags=["test", "temperature"]
    )
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device

@pytest.fixture
def test_rule(db_session: Session, test_project):
    """Create a test rule"""
    rule = Rule(
        project_id=test_project.id,
        name="High Temperature Alert",
        metric="temperature",
        operator=">",
        threshold=80.0,
        window_n=5,
        required_k=3,
        cooldown_seconds=300,
        enabled=True,
        scope="ALL"
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule

@pytest.fixture
def test_tag_rule(db_session: Session, test_project):
    """Create a tag-scoped rule"""
    rule = Rule(
        project_id=test_project.id,
        name="Tag-based Alert",
        metric="cpu",
        operator=">",
        threshold=90.0,
        window_n=3,
        required_k=2,
        cooldown_seconds=60,
        enabled=True,
        scope="TAG",
        tag="temperature"
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule

# ========== Helper Functions ==========

@pytest.fixture
def create_telemetry_event(db_session: Session):
    """Factory function to create telemetry events"""
    from app.db.models.telemetry_event import TelemetryEvent
    
    def _create_event(device_id: int, payload: dict, ts: datetime = None):
        if ts is None:
            ts = datetime.now(timezone.utc)
        
        event = TelemetryEvent(
            device_id=device_id,
            ts=ts,
            payload=payload
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        return event
    
    return _create_event