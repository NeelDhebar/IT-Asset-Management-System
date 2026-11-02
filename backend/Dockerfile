# Multi-stage production-ready Dockerfile for FastAPI Backend
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    APP_ENV=prod \
    DB_TYPE=postgresql \
    DATABASE_URL="postgresql://neondb_owner:npg_GxM03pioWcOq@ep-young-bonus-aznnu60t-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

WORKDIR /app

# Install system dependencies for PostgreSQL client and build utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and sample data
COPY app/ /app/app/
COPY data/ /app/data/
COPY .env.example /app/.env.example

# Expose FastAPI server port
EXPOSE 8000

# Health check to ensure API readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn ASGI production server with dynamic PORT support
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
