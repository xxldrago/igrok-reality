"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth import auth_router, tma_auth_router
from app.api.routes.health import router as health_router
from app.api.routes.admin import admin_router
from app.api.webhooks import router as webhook_router

ADMIN_DIST = Path("src/admin/dist")
TMA_DIST = Path("src/tma/dist")


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
app.include_router(webhook_router)
app.include_router(auth_router)
app.include_router(tma_auth_router)
app.include_router(admin_router)


# SPA catch-all — serve index.html for all /app/* routes (TMA)
@app.get("/app/{full_path:path}")
async def serve_tma(full_path: str) -> FileResponse:
    """Serve the TMA SPA for any route under /app/."""
    index = TMA_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return FileResponse(TMA_DIST / "index.html", status_code=404)


# Mount TMA static files AFTER the catch-all route
if TMA_DIST.exists():
    app.mount("/app/assets", StaticFiles(directory=str(TMA_DIST / "assets")), name="tma-assets")


# SPA catch-all — serve index.html for all /admin/* routes
@app.get("/admin/{full_path:path}")
async def serve_admin(full_path: str) -> FileResponse:
    """Serve the admin SPA for any route under /admin/."""
    index = ADMIN_DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return FileResponse(ADMIN_DIST / "index.html", status_code=404)


# Mount admin static files AFTER the catch-all route
if ADMIN_DIST.exists():
    app.mount("/admin/assets", StaticFiles(directory=str(ADMIN_DIST / "assets")), name="admin-assets")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000)
