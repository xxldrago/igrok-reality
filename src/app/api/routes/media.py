"""Admin media upload — photos, videos, documents for scrolls and broadcasts.

Uploaded files are stored under ``media/`` (served at ``/media``) and
returned as absolute URLs that the Telegram Bot API can download when
sending (send_photo / send_video / send_document accept HTTP URLs).

Report attachments arrive as Telegram file_ids (not URLs), so this module
also proxies them: GET /api/admin/media/telegram/{file_id} downloads the
file from Telegram server-side (bot token never leaves the backend) and
streams it to the admin panel, where <img>/<video> can render it.
"""

from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path

from aiogram import Bot
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import require_role

media_router = APIRouter(prefix="/api/admin", tags=["admin-media"])

MEDIA_DIR = Path("media")

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
DOCUMENT_EXTS = {
    ".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".txt", ".csv", ".mp3", ".ogg", ".wav",
}

MAX_PHOTO_BYTES = 10 * 1024 * 1024  # Telegram photo limit
MAX_OTHER_BYTES = 50 * 1024 * 1024  # Telegram Bot API file limit


def detect_media_type(filename: str) -> str | None:
    """Return photo|video|document for a filename, None when rejected."""
    ext = Path(filename or "").suffix.lower()
    if ext in PHOTO_EXTS:
        return "photo"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in DOCUMENT_EXTS:
        return "document"
    return None


@media_router.post(
    "/upload",
    dependencies=[Depends(require_role("master", "leader"))],
)
async def upload_media(request: Request, file: UploadFile) -> dict:
    """Upload a photo/video/document, return its public URL + media type."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    media_type = detect_media_type(file.filename)
    if media_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: images (jpg/png/gif/webp), "
            "video (mp4/mov), documents (pdf/zip/doc/xls/mp3...)",
        )

    data = await file.read()
    limit = MAX_PHOTO_BYTES if media_type == "photo" else MAX_OTHER_BYTES
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )
    if len(data) > limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (max {limit // (1024 * 1024)} MB for {media_type})",
        )

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix.lower()
    stored_name = f"{uuid.uuid4().hex}{ext}"
    (MEDIA_DIR / stored_name).write_bytes(data)

    from app.bot.services.settings_service import _db_or_env

    base = await _db_or_env("media_base_url", "") or str(request.base_url).rstrip("/")
    return {
        "url": f"{base}/media/{stored_name}",
        "media_type": media_type,
        "filename": file.filename,
        "size": len(data),
    }


_FILE_ID_RE = re.compile(r"[A-Za-z0-9_-]{8,256}")


@media_router.get(
    "/media/telegram/{file_id}",
    dependencies=[Depends(require_role("master", "leader", "curator"))],
)
async def telegram_media(file_id: str):
    """Stream a Telegram file (report attachment) to the admin panel.

    Resolves file_id → file_path via getFile, downloads from Telegram
    server-side and streams bytes. The bot token never reaches the browser,
    and <img>/<video> tags can't carry the admin JWT — hence proxy, not URL.
    """
    if not _FILE_ID_RE.fullmatch(file_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_id",
        )

    from app.bot.services.settings_service import get_bot_token

    bot = Bot(token=await get_bot_token())
    try:
        try:
            tg_file = await bot.get_file(file_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Telegram getFile failed",
            )
        if not tg_file.file_path:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Telegram returned no file path",
            )
        url = f"https://api.telegram.org/file/bot{bot.token}/{tg_file.file_path}"
    finally:
        await bot.session.close()

    import httpx

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Telegram file download failed",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Telegram file download failed",
        )
    if len(resp.content) > MAX_OTHER_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large to preview",
        )

    media_type, _ = mimetypes.guess_type(tg_file.file_path)
    return StreamingResponse(
        iter([resp.content]),
        media_type=media_type or "application/octet-stream",
    )
