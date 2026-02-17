from rapidfuzz import fuzz

WEIGHTS = {
    "title": 40,
    "tech_stack": 25,
    "remote": 15,
    "salary": 10,
    "whitelist": 10,
}

def score_job(job: dict, criteria: dict) -> int:
    """Score a job against criteria. Returns 0-100. Returns 0 if hard disqualifiers hit."""

    # Hard disqualifiers
    company = (job.get("company") or "").lower()
    description = (job.get("description") or "").lower()

    if criteria["company_blacklist"]:
        if any(b.lower() == company for b in criteria["company_blacklist"]):
            return 0

    if criteria["exclude_keywords"]:
        if any(kw.lower() in description for kw in criteria["exclude_keywords"]):
            return 0

    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    if criteria["min_salary"] and salary_max is not None:
        if salary_max < criteria["min_salary"]:
            return 0

    score = 0

    # Title match (fuzzy)
    title = job.get("title") or ""
    title_scores = [fuzz.partial_ratio(t.lower(), title.lower()) for t in criteria["titles"]]
    best_title = max(title_scores) if title_scores else 0
    score += int((best_title / 100) * WEIGHTS["title"])

    # Only award other bonuses if title match is reasonable (>= 50%)
    if best_title >= 50:
        # Tech stack match
        job_tags = {t.lower() for t in (job.get("tech_tags") or [])}
        if criteria["tech_stack"] and job_tags:
            matched = sum(1 for t in criteria["tech_stack"] if t.lower() in job_tags)
            ratio = matched / len(criteria["tech_stack"])
            score += int(ratio * WEIGHTS["tech_stack"])

        # Remote bonus
        if job.get("is_remote"):
            score += WEIGHTS["remote"]

        # Salary bonus (salary listed and above threshold)
        if salary_min and criteria["min_salary"] and salary_min >= criteria["min_salary"]:
            score += WEIGHTS["salary"]

        # Company whitelist bonus
        if criteria["company_whitelist"]:
            if any(w.lower() == company for w in criteria["company_whitelist"]):
                score += WEIGHTS["whitelist"]

    return min(score, 100)
