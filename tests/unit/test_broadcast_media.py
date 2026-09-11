"""Tests for broadcast media upload + scheduling request models."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pydantic import ValidationError

from app.api.routes.media import detect_media_type
from app.api.routes.admin import (
    BroadcastRequest,
    CancelScheduledBroadcastRequest,
    UserCreateRequest,
    UserUpdateRequest,
)


class TestDetectMediaType:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("photo.jpg", "photo"),
            ("pic.JPEG", "photo"),
            ("img.png", "photo"),
            ("anim.gif", "photo"),
            ("shot.webp", "photo"),
            ("clip.mp4", "video"),
            ("movie.MOV", "video"),
            ("doc.pdf", "document"),
            ("archive.zip", "document"),
            ("track.mp3", "document"),
            ("notes.txt", "document"),
        ],
    )
    def test_known_types(self, filename: str, expected: str) -> None:
        assert detect_media_type(filename) == expected

    @pytest.mark.parametrize("filename", ["evil.exe", "script.sh", "page.html", "noext", ""])
    def test_rejected_types(self, filename: str) -> None:
        assert detect_media_type(filename) is None


class TestBroadcastRequest:
    def test_immediate_broadcast(self) -> None:
        req = BroadcastRequest(text="hello")
        assert req.scheduled_at is None
        assert req.media_url is None

    def test_scheduled_broadcast_with_media(self) -> None:
        req = BroadcastRequest(
            text="hello",
            archetype="head",
            media_url="https://example.com/media/abc.jpg",
            media_type="photo",
            scheduled_at=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
        )
        assert req.scheduled_at is not None
        assert req.media_type == "photo"

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BroadcastRequest(text="")

    def test_cancel_request(self) -> None:
        req = CancelScheduledBroadcastRequest(
            scheduled_at=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
            audience="head",
        )
        assert req.audience == "head"


class TestUserRequests:
    def test_create_minimal(self) -> None:
        req = UserCreateRequest(telegram_id=123, first_name="Ivan")
        assert req.role == "player"
        assert req.is_active is True

    def test_update_partial(self) -> None:
        req = UserUpdateRequest(xp=100, has_paid=True)
        assert req.first_name is None
        assert req.has_paid is True
