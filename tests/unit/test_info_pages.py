"""Tests for /menu info pages (privacy, agreement, contacts, pricing)."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services import settings_service as settings_mod


class TestInfoDefaults:
    @pytest.mark.asyncio
    async def test_privacy_default(self) -> None:
        with patch.object(
            settings_mod, "get_setting", new_callable=AsyncMock, return_value=""
        ):
            text = await settings_mod.get_privacy_policy()
            assert "152-ФЗ" in text
            assert "ulviateplovodskaya@yandex.ru" in text

    def test_privacy_chunks_fit_limit(self) -> None:
        from app.bot.handlers.registration import split_message
        from app.bot.services.settings_service import DEFAULT_PRIVACY_POLICY

        chunks = split_message(DEFAULT_PRIVACY_POLICY)
        assert len(chunks) >= 2
        assert all(len(c) <= 4000 for c in chunks)

    @pytest.mark.asyncio
    async def test_agreement_default(self) -> None:
        with patch.object(
            settings_mod, "get_setting", new_callable=AsyncMock, return_value=""
        ):
            text = await settings_mod.get_user_agreement()
            assert "соглашение" in text.lower()

    @pytest.mark.asyncio
    async def test_contacts_default(self) -> None:
        with patch.object(
            settings_mod, "get_setting", new_callable=AsyncMock, return_value=""
        ):
            text = await settings_mod.get_support_contacts()
            assert "@misticheskie_skazkii" in text
            assert "/help" in text

    @pytest.mark.asyncio
    async def test_pricing_uses_live_price(self) -> None:
        async def fake_get_setting(key: str, default: str = "") -> str:
            return ""

        with (
            patch.object(
                settings_mod, "get_setting", new_callable=AsyncMock, side_effect=fake_get_setting
            ),
            patch.object(
                settings_mod, "get_payment_amount", new_callable=AsyncMock, return_value=490000
            ),
        ):
            text = await settings_mod.get_pricing_text()
            assert "4900" in text
            assert "/pay" in text

    @pytest.mark.asyncio
    async def test_db_override_wins(self) -> None:
        with patch.object(
            settings_mod, "get_setting", new_callable=AsyncMock, return_value="CUSTOM"
        ):
            assert await settings_mod.get_privacy_policy() == "CUSTOM"

    @pytest.mark.asyncio
    async def test_schema_has_info_keys(self) -> None:
        with patch.object(
            settings_mod, "get_setting", new_callable=AsyncMock, return_value=""
        ):
            groups = await settings_mod.get_settings_schema()
            content = next(g for g in groups if g["group"] == "content")
            keys = {f["key"] for f in content["fields"]}
            assert {"privacy_policy", "user_agreement", "support_contacts", "pricing_text"} <= keys


def _callback():
    callback = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.mark.asyncio
async def test_info_handler_all_pages() -> None:
    """Each info button sends its text (chunked)."""
    from app.bot.handlers import help as help_mod
    from app.bot.callbacks.runner import InfoPage

    for page, marker in (
        ("privacy", "конфиденциальности"),
        ("agreement", "Соглашение"),
        ("contacts", "поддержки"),
        ("pricing", "Тарифы"),
    ):
        callback = _callback()
        with patch.object(
            settings_mod,
            {"privacy": "get_privacy_policy", "agreement": "get_user_agreement",
             "contacts": "get_support_contacts", "pricing": "get_pricing_text"}[page],
            new_callable=AsyncMock,
            return_value=f"TEXT-{marker}",
        ):
            data = MagicMock()
            data.page = page
            await help_mod.handle_info_page(callback, data)
        texts = [c[0][0] for c in callback.message.answer.call_args_list]
        assert any(marker in t for t in texts), page


@pytest.mark.asyncio
async def test_info_handler_unknown_page() -> None:
    from app.bot.handlers import help as help_mod

    callback = _callback()
    data = MagicMock()
    data.page = "nope"
    await help_mod.handle_info_page(callback, data)
    assert "/menu" in callback.message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_menu_has_info_buttons() -> None:
    """handle_menu keyboard includes the four info callbacks."""
    from app.bot.handlers import help as help_mod

    user = MagicMock()
    user.started_at = None
    user.role = "player"
    message = AsyncMock()
    message.from_user.id = 111
    message.answer = AsyncMock()
    with patch.object(
        help_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user
    ):
        await help_mod.handle_menu(message)

    kb = message.answer.call_args[1]["reply_markup"]
    callbacks = [b.callback_data for row in kb.inline_keyboard for b in row]
    for page in ("privacy", "agreement", "contacts", "pricing"):
        assert f"info:{page}" in callbacks, page
