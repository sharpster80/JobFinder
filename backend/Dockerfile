FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir ".[dev]"
RUN python -m playwright install chromium --with-deps
