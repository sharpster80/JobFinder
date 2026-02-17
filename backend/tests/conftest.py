import os

# Set environment variables before importing app modules
# Use test database for tests
os.environ.setdefault("DATABASE_URL", "postgresql://jobfinder:jobfinder@localhost:5433/jobfinder")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
