from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import jobs, criteria, scrapes, notifications

app = FastAPI(title="JobFinder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(criteria.router, prefix="/api/criteria", tags=["criteria"])
app.include_router(scrapes.router, prefix="/api/scrapes", tags=["scrapes"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

@app.get("/health")
def health():
    return {"status": "ok"}
