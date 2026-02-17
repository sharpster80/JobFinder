"""Smoke test to ensure models can be imported and have correct structure."""
import uuid
from datetime import datetime


def test_import_models():
    """Test that all models can be imported."""
    from app.models import Job, JobMatch, SearchCriteria, ScrapeRun, Notification, PushSubscription

    assert Job is not None
    assert JobMatch is not None
    assert SearchCriteria is not None
    assert ScrapeRun is not None
    assert Notification is not None
    assert PushSubscription is not None


def test_job_model_structure():
    """Test Job model has expected fields."""
    from app.models import Job

    # Verify the model has the expected table name
    assert Job.__tablename__ == "jobs"

    # Verify key annotations exist
    assert "id" in Job.__annotations__
    assert "source" in Job.__annotations__
    assert "title" in Job.__annotations__
    assert "company" in Job.__annotations__
    assert "tech_tags" in Job.__annotations__


def test_search_criteria_model_structure():
    """Test SearchCriteria model has expected fields."""
    from app.models import SearchCriteria

    assert SearchCriteria.__tablename__ == "search_criteria"
    assert "id" in SearchCriteria.__annotations__
    assert "name" in SearchCriteria.__annotations__
    assert "titles" in SearchCriteria.__annotations__
    assert "tech_stack" in SearchCriteria.__annotations__


def test_job_match_model_structure():
    """Test JobMatch model has expected fields."""
    from app.models import JobMatch

    assert JobMatch.__tablename__ == "job_matches"
    assert "id" in JobMatch.__annotations__
    assert "job_id" in JobMatch.__annotations__
    assert "criteria_id" in JobMatch.__annotations__
    assert "match_score" in JobMatch.__annotations__
