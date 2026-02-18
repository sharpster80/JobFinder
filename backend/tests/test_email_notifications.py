import pytest
from unittest.mock import patch, MagicMock
from app.notifications.email import format_digest_html, should_send_immediate

def test_format_digest_html_contains_job_title():
    jobs = [{"title": "Staff Engineer", "company": "Acme", "match_score": 85,
             "salary_min": 130000, "salary_max": 160000, "url": "https://example.com"}]
    html = format_digest_html(jobs)
    assert "Staff Engineer" in html
    assert "Acme" in html

def test_format_digest_html_empty_returns_string():
    html = format_digest_html([])
    assert isinstance(html, str)

def test_should_send_immediate_above_threshold():
    assert should_send_immediate(95, threshold=90) is True

def test_should_send_immediate_below_threshold():
    assert should_send_immediate(85, threshold=90) is False
