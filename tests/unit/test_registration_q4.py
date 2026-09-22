"""Tests for quiz finalization (handle_q4) — no silent death on errors."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.handlers import registration as reg_mod


def _callback():
    callback = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.answer = AsyncMock()
    callback.answer = AsyncMock()
    callback.from_user.id = 111
    callback.bot = MagicMock()
    return callback


def _state():
    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "telegram_id": 111,
            "first_name": "Ivan",
            "last_name": None,
            "username": "ivan",
            "q1_answer": "a",
            "q2_answer": "a",
            "q3_answer": "b",
            "q4_answer": "a",
        }
    )
    return state


def _quiz():
    quiz = MagicMock()
    quiz.results = {"head": "ТВОЙ АРХЕТИП: ГОЛОВА"}
    return quiz


def _user():
    user = MagicMock()
    user.id = uuid4()
    user.referral_code = "abc123"
    return user


@pytest.mark.asyncio
async def test_q4_fresh_user_completes() -> None:
    """Fresh user: created, result + profile shown, pay prompt sent."""
    user = _user()
    with (
        patch.object(reg_mod, "_handle_quiz_answer", new_callable=AsyncMock, return_value=("head", "Голова")),
        patch.object(reg_mod, "load_quiz_config", new_callable=AsyncMock, return_value=_quiz()),
        patch.object(reg_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=None),
        patch.object(reg_mod, "create_user", new_callable=AsyncMock, return_value=user) as mock_create,
        patch.object(reg_mod, "generate_referral_code", return_value="abc123"),
        patch.object(reg_mod, "create_start_link", new_callable=AsyncMock, return_value="https://t.me/bot?start=abc123"),
        patch("app.bot.handlers.payment.send_pay_prompt", new_callable=AsyncMock) as mock_pay,
    ):
        await reg_mod.handle_q4(_callback(), _state())

    # create_user awaited tested via mock below — re-run with handle on mock
    assert mock_pay.await_count == 1
    assert mock_create.call_args[1]["quiz_answers"] == '["a", "a", "b", "a"]'
    assert mock_create.call_args[1]["started_at"] is None


@pytest.mark.asyncio
async def test_q4_reregistration_does_not_crash() -> None:
    """Existing telegram_id: no duplicate insert, flow still completes."""
    user = _user()
    callback = _callback()
    state = _state()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch.object(reg_mod, "_handle_quiz_answer", new_callable=AsyncMock, return_value=("head", "Голова")),
        patch.object(reg_mod, "load_quiz_config", new_callable=AsyncMock, return_value=_quiz()),
        patch.object(reg_mod, "get_user_by_telegram_id", new_callable=AsyncMock, return_value=user),
        patch.object(reg_mod, "create_user", new_callable=AsyncMock) as mock_create,
        patch.object(reg_mod, "generate_referral_code", return_value="abc123"),
        patch.object(reg_mod, "create_start_link", new_callable=AsyncMock, return_value="https://t.me/bot?start=abc123"),
        patch("app.shared.database.session_factory", return_value=cm),
        patch("app.bot.handlers.payment.send_pay_prompt", new_callable=AsyncMock),
    ):
        await reg_mod.handle_q4(callback, state)

    mock_create.assert_not_awaited()
    callback.message.edit_text.assert_awaited_once()
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_q4_error_is_visible_not_silent() -> None:
    """DB failure in finalization: user gets an error message, state cleared."""
    callback = _callback()
    state = _state()
    with (
        patch.object(reg_mod, "_handle_quiz_answer", new_callable=AsyncMock, return_value=("head", "Голова")),
        patch.object(reg_mod, "load_quiz_config", new_callable=AsyncMock, return_value=_quiz()),
        patch.object(
            reg_mod, "get_user_by_telegram_id", new_callable=AsyncMock, side_effect=Exception("db down")
        ),
    ):
        await reg_mod.handle_q4(callback, state)

    texts = [c[0][0] for c in callback.message.answer.call_args_list]
    assert any("Что-то пошло не так" in t for t in texts)
    state.clear.assert_awaited_once()
