import os

# Set environment variables before importing app modules
# Use test database for tests
os.environ.setdefault("DATABASE_URL", "postgresql://jobfinder:jobfinder@localhost:5433/jobfinder")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app import models  # noqa

@pytest.fixture
def db_session():
    """Create a test database session."""
    # Use the test PostgreSQL database
    test_db_url = os.environ.get("DATABASE_URL", "postgresql://jobfinder:jobfinder@localhost:5433/jobfinder")
    engine = create_engine(test_db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
    # Clean up tables after test
    Base.metadata.drop_all(engine)
