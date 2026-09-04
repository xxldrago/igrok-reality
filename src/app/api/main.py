"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    print("API starting...")
    yield
    print("API stopping...")


app = FastAPI(
    title="Игрок.Реальность API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000)
