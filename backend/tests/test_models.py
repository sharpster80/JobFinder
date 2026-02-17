import uuid
from datetime import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Job, JobMatch, SearchCriteria, ScrapeRun, Notification, PushSubscription


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_job_creation(db_session):
    """Test creating a Job instance."""
    job = Job(
        source="remoteok",
        external_id="test123",
        url="https://example.com/job/123",
        title="Senior Python Developer",
        company="Test Corp",
        location="Remote",
        is_remote=True,
        salary_min=100000,
        salary_max=150000,
        description="Great job opportunity",
        tech_tags=["python", "fastapi", "postgresql"],
        posted_at=datetime.utcnow(),
    )
    db_session.add(job)
    db_session.commit()

    assert job.id is not None
    assert isinstance(job.id, uuid.UUID)
    assert job.source == "remoteok"
    assert job.title == "Senior Python Developer"
    assert job.is_active is True
    assert len(job.tech_tags) == 3


def test_search_criteria_creation(db_session):
    """Test creating a SearchCriteria instance."""
    criteria = SearchCriteria(
        name="My Search",
        titles=["Python Developer", "Backend Engineer"],
        tech_stack=["python", "fastapi"],
        min_salary=90000,
        exclude_keywords=["senior", "lead"],
        company_blacklist=["BadCorp"],
        company_whitelist=["GoodCorp"],
    )
    db_session.add(criteria)
    db_session.commit()

    assert criteria.id is not None
    assert criteria.name == "My Search"
    assert len(criteria.titles) == 2
    assert criteria.is_active is True


def test_job_match_relationship(db_session):
    """Test JobMatch relationship between Job and SearchCriteria."""
    job = Job(
        source="remoteok",
        external_id="test123",
        url="https://example.com/job/123",
        title="Python Developer",
        company="Test Corp",
    )
    criteria = SearchCriteria(
        name="My Search",
        titles=["Python Developer"],
    )
    db_session.add(job)
    db_session.add(criteria)
    db_session.commit()

    match = JobMatch(
        job_id=job.id,
        criteria_id=criteria.id,
        match_score=85,
        status="new",
    )
    db_session.add(match)
    db_session.commit()

    assert match.id is not None
    assert match.match_score == 85
    assert match.job.title == "Python Developer"
    assert match.criteria.name == "My Search"
    assert len(job.matches) == 1
    assert len(criteria.matches) == 1


def test_scrape_run_creation(db_session):
    """Test creating a ScrapeRun instance."""
    run = ScrapeRun(
        source="linkedin",
        jobs_found=50,
        jobs_new=10,
    )
    db_session.add(run)
    db_session.commit()

    assert run.id is not None
    assert run.source == "linkedin"
    assert run.jobs_found == 50
    assert run.jobs_new == 10
    assert run.finished_at is None
    assert run.error is None


def test_notification_creation(db_session):
    """Test creating a Notification instance."""
    job = Job(
        source="remoteok",
        external_id="test123",
        url="https://example.com/job/123",
        title="Python Developer",
        company="Test Corp",
    )
    db_session.add(job)
    db_session.commit()

    notification = Notification(
        job_id=job.id,
        channel="email",
    )
    db_session.add(notification)
    db_session.commit()

    assert notification.id is not None
    assert notification.channel == "email"
    assert notification.sent_at is not None


def test_push_subscription_creation(db_session):
    """Test creating a PushSubscription instance."""
    subscription = PushSubscription(
        endpoint="https://push.example.com/endpoint",
        subscription_json={
            "endpoint": "https://push.example.com/endpoint",
            "keys": {"auth": "test", "p256dh": "test"},
        },
    )
    db_session.add(subscription)
    db_session.commit()

    assert subscription.id is not None
    assert subscription.endpoint == "https://push.example.com/endpoint"
    assert "keys" in subscription.subscription_json
