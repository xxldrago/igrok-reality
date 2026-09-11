"""Tests for editable runtime settings — price, tokens, channels, admin creds."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services import settings_service
from app.bot.services.settings_service import (
    DEFAULT_PAYMENT_AMOUNT,
    get_admin_credentials,
    get_bot_token,
    get_consent_text,
    get_delivery_slots,
    get_grace_period_hours,
    get_leaderboard_limit,
    get_payment_amount,
    get_platega_credentials,
    get_quest_channel_id,
    get_settings_schema,
    get_streak_warning_time,
    hash_admin_password,
    verify_admin_password,
)
from app.shared.config import settings


def _patch_get_setting(return_value="", side_effect=None):
    """Patch get_setting inside settings_service."""
    return patch.object(
        settings_service,
        "get_setting",
        new_callable=AsyncMock,
        **({"side_effect": side_effect} if side_effect else {"return_value": return_value}),
    )


class TestPaymentAmount:
    @pytest.mark.asyncio
    async def test_empty_setting_gives_default(self) -> None:
        with _patch_get_setting(""):
            assert await get_payment_amount() == DEFAULT_PAYMENT_AMOUNT == 490000

    @pytest.mark.asyncio
    async def test_custom_amount(self) -> None:
        with _patch_get_setting("100000"):
            assert await get_payment_amount() == 100000

    @pytest.mark.asyncio
    async def test_invalid_amount_gives_default(self) -> None:
        with _patch_get_setting("not-a-number"):
            assert await get_payment_amount() == DEFAULT_PAYMENT_AMOUNT

    @pytest.mark.asyncio
    async def test_non_positive_amount_gives_default(self) -> None:
        with _patch_get_setting("0"):
            assert await get_payment_amount() == DEFAULT_PAYMENT_AMOUNT

    @pytest.mark.asyncio
    async def test_db_error_gives_default(self) -> None:
        with _patch_get_setting(side_effect=Exception("db down")):
            assert await get_payment_amount() == DEFAULT_PAYMENT_AMOUNT


class TestRuntimeTokens:
    @pytest.mark.asyncio
    async def test_bot_token_db_override(self) -> None:
        with _patch_get_setting("db-token-123"):
            assert await get_bot_token() == "db-token-123"

    @pytest.mark.asyncio
    async def test_bot_token_env_fallback(self) -> None:
        with _patch_get_setting(""):
            assert await get_bot_token() == settings.BOT_TOKEN

    @pytest.mark.asyncio
    async def test_quest_channel_db_override(self) -> None:
        with _patch_get_setting("-100123"):
            assert await get_quest_channel_id() == -100123

    @pytest.mark.asyncio
    async def test_quest_channel_env_fallback(self) -> None:
        with _patch_get_setting(""):
            assert await get_quest_channel_id() == settings.QUEST_CHANNEL_ID

    @pytest.mark.asyncio
    async def test_platega_credentials_db_override(self) -> None:
        async def _fake(key: str, default: str = "") -> str:
            return {"platega_merchant_id": "mid-1", "platega_secret": "sec-1"}.get(key, "")

        with patch.object(settings_service, "get_setting", new_callable=AsyncMock) as m:
            m.side_effect = _fake
            assert await get_platega_credentials() == ("mid-1", "sec-1")


class TestAdminCredentials:
    def test_hash_verify_roundtrip(self) -> None:
        hashed = hash_admin_password("supersecret")
        assert verify_admin_password("supersecret", hashed) is True
        assert verify_admin_password("wrong", hashed) is False

    @pytest.mark.asyncio
    async def test_db_override_credentials(self) -> None:
        async def _fake(key: str, default: str = "") -> str:
            return {
                "admin_username": "boss",
                "admin_password_hash": hash_admin_password("pw12345"),
            }.get(key, "")

        with patch.object(settings_service, "get_setting", new_callable=AsyncMock) as m:
            m.side_effect = _fake
            username, pwd_hash = await get_admin_credentials()
            assert username == "boss"
            assert pwd_hash is not None
            assert verify_admin_password("pw12345", pwd_hash) is True

    @pytest.mark.asyncio
    async def test_env_fallback_credentials(self) -> None:
        with _patch_get_setting(""):
            username, pwd_hash = await get_admin_credentials()
            assert username == settings.ADMIN_USERNAME
            assert pwd_hash is None


class TestQuestMechanics:
    @pytest.mark.asyncio
    async def test_grace_default(self) -> None:
        with _patch_get_setting(""):
            assert await get_grace_period_hours() == 5

    @pytest.mark.asyncio
    async def test_grace_custom(self) -> None:
        with _patch_get_setting("3"):
            assert await get_grace_period_hours() == 3

    @pytest.mark.asyncio
    async def test_grace_invalid(self) -> None:
        with _patch_get_setting("99"):
            assert await get_grace_period_hours() == 5

    @pytest.mark.asyncio
    async def test_leaderboard_default_and_custom(self) -> None:
        with _patch_get_setting(""):
            assert await get_leaderboard_limit() == 10
        with _patch_get_setting("25"):
            assert await get_leaderboard_limit() == 25

    @pytest.mark.asyncio
    async def test_delivery_slots_default(self) -> None:
        with _patch_get_setting(""):
            assert await get_delivery_slots() == [(5, 0), (8, 0), (12, 0), (14, 0), (16, 0), (21, 0)]

    @pytest.mark.asyncio
    async def test_delivery_slots_custom(self) -> None:
        with _patch_get_setting("06:30, 21:15"):
            assert await get_delivery_slots() == [(6, 30), (21, 15)]

    @pytest.mark.asyncio
    async def test_delivery_slots_invalid(self) -> None:
        with _patch_get_setting("nonsense"):
            assert await get_delivery_slots() == [(5, 0), (8, 0), (12, 0), (14, 0), (16, 0), (21, 0)]

    @pytest.mark.asyncio
    async def test_streak_warning_default(self) -> None:
        with _patch_get_setting(""):
            assert await get_streak_warning_time() == (23, 0)

    @pytest.mark.asyncio
    async def test_consent_db_and_fallback(self) -> None:
        with _patch_get_setting("Custom consent"):
            assert await get_consent_text() == "Custom consent"
        with _patch_get_setting(""):
            assert "персональных данных" in await get_consent_text()


class TestSettingsSchema:
    @pytest.mark.asyncio
    async def test_schema_groups_and_fields(self) -> None:
        with _patch_get_setting(""):
            groups = await get_settings_schema()
            names = [g["group"] for g in groups]
            assert names == ["telegram", "platega", "payments", "quest", "media", "content"]
            payments = next(g for g in groups if g["group"] == "payments")
            price = next(f for f in payments["fields"] if f["key"] == "payment_amount")
            assert price["type"] == "price_rub"
            assert price["is_default"] is True
            content = next(g for g in groups if g["group"] == "content")
            assert any(f["key"] == "welcome_message" for f in content["fields"])
