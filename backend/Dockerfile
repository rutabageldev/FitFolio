# backend/Dockerfile (dev)
# syntax=docker/dockerfile:1.4
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspaces/fitfolio/backend

# Base OS deps + Node.js (for pre-commit eslint/prettier hooks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash openssh-client curl ca-certificates gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt

COPY . .

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--reload"]
