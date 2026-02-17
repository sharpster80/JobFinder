FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY app app

RUN pip install -e ".[dev]"
RUN python -m playwright install chromium --with-deps

COPY . .
