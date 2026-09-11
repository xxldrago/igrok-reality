# Stage 1: Build admin frontend
FROM node:20-alpine AS admin-builder
WORKDIR /build
COPY src/admin/package.json src/admin/package-lock.json* ./
RUN npm ci || npm install
COPY src/admin/ .
RUN npm run build

# Stage 2: Build TMA frontend
FROM node:20-alpine AS tma-builder
WORKDIR /build
COPY src/tma/package.json src/tma/package-lock.json* ./
RUN npm ci || npm install
COPY src/tma/ .
RUN npm run build

# Stage 3: Python application
FROM python:3.11-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY src/ src/
COPY scripts/ scripts/

# Copy built frontends into src/ where API expects them
COPY --from=admin-builder /build/dist/ src/admin/dist/
COPY --from=tma-builder /build/dist/ src/tma/dist/

ENV PYTHONPATH="/app/src:/app:$PYTHONPATH"
