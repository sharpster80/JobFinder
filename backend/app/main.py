from fastapi import FastAPI

app = FastAPI(title="JobFinder API")

@app.get("/health")
def health_check():
    return {"status": "ok"}
