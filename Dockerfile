FROM python:3.11-slim AS base

# System dependencies for asyncpg and compilation
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application source
COPY src/ src/

# Make app module importable
ENV PYTHONPATH="/app/src:/app:$PYTHONPATH"
