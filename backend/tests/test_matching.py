import pytest
from app.matching import score_job

def make_criteria(
    titles=None, tech_stack=None, min_salary=0,
    exclude_keywords=None, company_blacklist=None, company_whitelist=None
):
    return {
        "titles": titles or ["Staff Software Engineer"],
        "tech_stack": tech_stack or ["Python"],
        "min_salary": min_salary,
        "exclude_keywords": exclude_keywords or [],
        "company_blacklist": company_blacklist or [],
        "company_whitelist": company_whitelist or [],
    }

def make_job(**kwargs):
    defaults = {
        "title": "Staff Software Engineer",
        "company": "Acme Corp",
        "description": "We use Python and Kubernetes",
        "salary_min": 130000,
        "salary_max": 160000,
        "is_remote": True,
        "tech_tags": ["Python", "Kubernetes"],
    }
    return {**defaults, **kwargs}

def test_perfect_match_scores_high():
    score = score_job(make_job(), make_criteria())
    assert score >= 80

def test_title_mismatch_lowers_score():
    score = score_job(make_job(title="Junior Developer"), make_criteria())
    assert score < 40

def test_salary_below_minimum_returns_zero():
    score = score_job(make_job(salary_max=100000), make_criteria(min_salary=125000))
    assert score == 0

def test_blacklisted_company_returns_zero():
    score = score_job(make_job(company="Bad Corp"), make_criteria(company_blacklist=["Bad Corp"]))
    assert score == 0

def test_excluded_keyword_in_description_returns_zero():
    score = score_job(
        make_job(description="This role requires relocation to NYC"),
        make_criteria(exclude_keywords=["relocation"])
    )
    assert score == 0

def test_tech_stack_match_boosts_score():
    score_with_match = score_job(make_job(), make_criteria(tech_stack=["Python"]))
    score_without = score_job(make_job(tech_tags=[]), make_criteria(tech_stack=["Python"]))
    assert score_with_match > score_without

def test_whitelisted_company_boosts_score():
    score_whitelist = score_job(make_job(company="Dream Co"), make_criteria(company_whitelist=["Dream Co"]))
    score_normal = score_job(make_job(company="Dream Co"), make_criteria())
    assert score_whitelist > score_normal

def test_no_salary_listed_does_not_disqualify():
    score = score_job(make_job(salary_min=None, salary_max=None), make_criteria(min_salary=125000))
    assert score > 0

def test_non_remote_job_scores_lower():
    score_remote = score_job(make_job(is_remote=True), make_criteria())
    score_onsite = score_job(make_job(is_remote=False), make_criteria())
    assert score_remote > score_onsite
