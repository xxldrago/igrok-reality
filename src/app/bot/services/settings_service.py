"""Settings service — typed accessors for platform configuration.

Editable platform values (price, tokens, channel IDs, Platega credentials,
admin profile) live in the ``settings`` DB table and are managed via the
admin panel. Every runtime helper below falls back to the environment
defaults when the DB is unreachable or the key is missing — the platform
keeps working and unit tests stay hermetic.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.shared.config import settings
from app.shared.database import session_factory
from app.shared.models.settings import Setting

logger = logging.getLogger(__name__)


@dataclass
class XPWeights:
    """XP weights for different scroll sections."""

    common: int = 10
    individual: int = 10
    ritual: int = 5
    habits: int = 5


@dataclass
class StreakBonusConfig:
    """Streak bonus configuration."""

    days: list[int] = None
    xp: list[int] = None

    def __post_init__(self):
        if self.days is None:
            self.days = [7, 30, 90]
        if self.xp is None:
            self.xp = [50, 250, 1000]


async def get_setting(key: str, default: str = "") -> str:
    """Get a single setting value by key."""
    async with session_factory() as session:
        result = await session.execute(select(Setting).where(Setting.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else default


async def get_xp_weights() -> XPWeights:
    """Get configured XP weights for scroll sections."""
    return XPWeights(
        common=int(await get_setting("xp_weight_common", "10")),
        individual=int(await get_setting("xp_weight_individual", "10")),
        ritual=int(await get_setting("xp_weight_ritual", "5")),
        habits=int(await get_setting("xp_weight_habits", "5")),
    )


async def get_streak_bonus_config() -> StreakBonusConfig:
    """Get configured streak bonus thresholds and XP rewards."""
    days_str = await get_setting("streak_bonus_days", "7,30,90")
    xp_str = await get_setting("streak_bonus_xp", "50,250,1000")

    try:
        days = [int(d.strip()) for d in days_str.split(",")]
    except ValueError:
        days = [7, 30, 90]

    try:
        xp = [int(x.strip()) for x in xp_str.split(",")]
    except ValueError:
        xp = [50, 250, 1000]

    return StreakBonusConfig(days=days, xp=xp)


async def get_prize_fund_percent() -> int:
    """Get configured prize fund percentage (basis points, e.g., 500 = 5%)."""
    val = await get_setting("prize_fund_percent", "500")
    try:
        return int(val)
    except ValueError:
        return 500  # default 5%


async def get_welcome_message() -> str:
    """Get the welcome message shown after /start."""
    return await get_setting("welcome_message", "Добро пожаловать в Игрок.Реальность!")


# ---------------------------------------------------------------------------
# Editable runtime configuration (admin panel → settings table → env fallback)
# ---------------------------------------------------------------------------

DEFAULT_PAYMENT_AMOUNT = 490000  # 4900 RUB in kopecks


async def _db_or_env(key: str, env_value: Any) -> str:
    """Return the DB setting value, or the env default when missing/empty.

    Never raises: on DB errors logs a warning and returns the env default.
    """
    try:
        value = await get_setting(key, "")
        if value:
            return value
    except Exception:
        logger.warning("settings: DB unreachable for key=%s, using env default", key)
    return str(env_value)


async def get_payment_amount() -> int:
    """Payment amount in kopecks (editable via admin panel, default 490000)."""
    raw = await _db_or_env("payment_amount", DEFAULT_PAYMENT_AMOUNT)
    try:
        amount = int(raw)
        if amount > 0:
            return amount
    except (TypeError, ValueError):
        pass
    return DEFAULT_PAYMENT_AMOUNT


async def get_bot_token() -> str:
    """Bot token — DB override or BOT_TOKEN env."""
    return await _db_or_env("bot_token", settings.BOT_TOKEN)


async def get_tma_bot_token() -> str:
    """TMA validation token — DB override, TMA_BOT_TOKEN env, then BOT_TOKEN."""
    override = await _db_or_env("tma_bot_token", settings.TMA_BOT_TOKEN)
    return override or await get_bot_token()


async def get_bot_username() -> str:
    """Bot username without @ — DB override or BOT_USERNAME env."""
    return await _db_or_env("bot_username", settings.BOT_USERNAME)


async def _get_channel_id(key: str, env_value: int) -> int:
    raw = await _db_or_env(key, env_value)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return int(env_value)


async def get_master_channel_id() -> int:
    """Master channel ID — DB override or MASTER_CHANNEL_ID env."""
    return await _get_channel_id("master_channel_id", settings.MASTER_CHANNEL_ID)


async def get_quest_channel_id() -> int:
    """Quest channel ID — DB override or QUEST_CHANNEL_ID env."""
    return await _get_channel_id("quest_channel_id", settings.QUEST_CHANNEL_ID)


async def get_payment_channel_id() -> int:
    """Payment channel ID — DB override or PAYMENT_CHANNEL_ID env."""
    return await _get_channel_id("payment_channel_id", settings.PAYMENT_CHANNEL_ID)


async def get_platega_credentials() -> tuple[str, str]:
    """Platega (merchant_id, secret) — DB overrides or env."""
    merchant = await _db_or_env("platega_merchant_id", settings.PLATEGA_MERCHANT_ID)
    secret = await _db_or_env("platega_secret", settings.PLATEGA_SECRET)
    return merchant, secret


async def get_platega_webhook_url() -> str:
    """Platega webhook URL — DB override or env."""
    return await _db_or_env("platega_webhook_url", settings.PLATEGA_WEBHOOK_URL)


async def get_grace_period_hours() -> int:
    """Night grace period in hours (commands after midnight count for prev day)."""
    raw = await _db_or_env("grace_period_hours", "5")
    try:
        value = int(raw)
        if 0 <= value <= 12:
            return value
    except (TypeError, ValueError):
        pass
    return 5


async def get_leaderboard_limit() -> int:
    """How many top users the /leaderboard shows."""
    raw = await _db_or_env("leaderboard_limit", "10")
    try:
        value = int(raw)
        if 1 <= value <= 50:
            return value
    except (TypeError, ValueError):
        pass
    return 10


DEFAULT_DELIVERY_SLOTS: list[tuple[int, int]] = [
    (5, 0), (8, 0), (12, 0), (14, 0), (16, 0), (21, 0)
]  # 14:00 — дневное дыхание в дни дыхания


async def get_delivery_slots() -> list[tuple[int, int]]:
    """Scroll delivery slots as [(hour, minute)] — editable, scheduler restart applies.

    Stored as "05:00, 08:00, 12:00, 16:00, 21:00" (server time).
    """
    raw = await _db_or_env("delivery_slots", "")
    if raw:
        try:
            slots: list[tuple[int, int]] = []
            for part in raw.replace(";", ",").split(","):
                part = part.strip()
                if not part:
                    continue
                h, _, m = part.partition(":")
                hour, minute = int(h), int(m or 0)
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    slots.append((hour, minute))
            if slots:
                return sorted(set(slots))
        except (TypeError, ValueError):
            pass
    return DEFAULT_DELIVERY_SLOTS


async def get_streak_warning_time() -> tuple[int, int]:
    """(hour, minute) of the streak-loss warning — editable, scheduler restart applies."""
    try:
        hour = int(await _db_or_env("streak_warning_hour", "23"))
        minute = int(await _db_or_env("streak_warning_minute", "0"))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (TypeError, ValueError):
        pass
    return 23, 0


async def get_consent_text() -> str:
    """152-ФЗ consent text shown at /start (editable via admin panel)."""
    try:
        value = await get_setting("consent_text", "")
        if value:
            return value
    except Exception:
        logger.warning("settings: DB unreachable for consent_text, using default")
    return DEFAULT_CONSENT_TEXT


DEFAULT_CONSENT_TEXT = (
    "Добро пожаловать в Игрок.Реальность!\n"
    "\n"
    "Для участия в квесте нам нужны ваши данные:\n"
    "• Имя и фамилия из Telegram\n"
    "• Username (если есть)\n"
    "\n"
    "Мы обрабатываем ваши данные для:\n"
    "• Управления вашим прогрессом в квесте\n"
    "• Связи с вами по вопросам квеста\n"
    "• Отправки ежедневных заданий\n"
    "\n"
    "Нажимая «Я согласен», вы подтверждаете обработку персональных данных."
)


# ---------------------------------------------------------------------------
# Admin profile (login credentials editable via admin panel)
# ---------------------------------------------------------------------------


def hash_admin_password(password: str) -> str:
    """SHA-256 hash for the admin panel password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_admin_password(password: str, stored_hash: str) -> bool:
    """Constant-time comparison of password against stored hash."""
    return hmac.compare_digest(hash_admin_password(password), stored_hash)


async def get_admin_credentials() -> tuple[str, str | None]:
    """Return (username, password_hash).

    password_hash is None when no DB override is set — callers must then
    validate against the ADMIN_PASSWORD env variable.
    """
    try:
        username = await get_setting("admin_username", "")
        pwd_hash = await get_setting("admin_password_hash", "")
    except Exception:
        logger.warning("settings: DB unreachable for admin credentials, using env")
        return settings.ADMIN_USERNAME, None
    return username or settings.ADMIN_USERNAME, pwd_hash or None


async def get_admin_telegram() -> str:
    """Admin contact telegram (@login) — DB setting, empty when not set."""
    try:
        return await get_setting("admin_telegram", "")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Settings schema for the admin panel (grouped editor)
# ---------------------------------------------------------------------------


@dataclass
class SettingsField:
    """One editable setting: key, label, input type, env default source."""

    key: str
    label: str
    type: str = "text"  # text | password | number | textarea | price_rub
    env_attr: str = ""  # settings.<env_attr> used as default when DB is empty
    hint: str = ""


@dataclass
class SettingsGroup:
    """A group of settings shown as one card in the admin panel."""

    group: str
    title: str
    fields: list[SettingsField] = field(default_factory=list)


SETTINGS_SCHEMA: list[SettingsGroup] = [
    SettingsGroup(
        group="telegram",
        title="Telegram — бот и каналы",
        fields=[
            SettingsField("bot_token", "Токен бота", "password", "BOT_TOKEN",
                          "Применяется сразу. Храните в тайне!"),
            SettingsField("bot_username", "Username бота (без @)", "text", "BOT_USERNAME"),
            SettingsField("tma_bot_token", "Токен для Mini App (пусто = токен бота)", "password", "TMA_BOT_TOKEN"),
            SettingsField("master_channel_id", "ID канала мастера", "number", "MASTER_CHANNEL_ID"),
            SettingsField("quest_channel_id", "ID канала квеста", "number", "QUEST_CHANNEL_ID"),
            SettingsField("payment_channel_id", "ID канала оплат", "number", "PAYMENT_CHANNEL_ID"),
        ],
    ),
    SettingsGroup(
        group="platega",
        title="Platega.io — приём платежей",
        fields=[
            SettingsField("platega_merchant_id", "Merchant ID", "text", "PLATEGA_MERCHANT_ID"),
            SettingsField("platega_secret", "Секретный ключ", "password", "PLATEGA_SECRET"),
            SettingsField("platega_webhook_url", "Webhook URL", "text", "PLATEGA_WEBHOOK_URL",
                          "Должен совпадать с URL в кабинете Platega"),
        ],
    ),
SettingsGroup(
        group="payments",
        title="Оплата участия",
        fields=[
            SettingsField("payment_amount", "Цена участия", "price_rub", "",
                          "В рублях. Применяется к новым платежам (/pay) сразу"),
            SettingsField(
                "payments_enabled", "Приём платежей", "bool", "true",
                "Выключить для тестов (появляется кнопка тестовой оплаты)",
            ),
        ],
    ),
    SettingsGroup(
        group="quest",
        title="Квест — механики",
        fields=[
            SettingsField("commission_rate", "Ставка реферальной комиссии (0–1)", "text", "COMMISSION_RATE",
                          "Например 0.10 = 10%"),
            SettingsField("prize_fund_percent", "Процент в призовой фонд (базисные пункты)", "text", "",
                          "Например 500 = 5%"),
            SettingsField("xp_weight_common", "XP за общее задание", "number", ""),
            SettingsField("xp_weight_individual", "XP за индивидуальное задание", "number", ""),
            SettingsField("xp_weight_ritual", "XP за ритуал", "number", ""),
            SettingsField("xp_weight_habits", "XP за привычки", "number", ""),
            SettingsField("streak_bonus_days", "Пороги стрика (дни, через запятую)", "text", ""),
            SettingsField("streak_bonus_xp", "Бонусы стрика (XP, через запятую)", "text", ""),
            SettingsField(
                "grace_period_hours", "Ночной зачёт команд (часов после полуночи)", "number", "",
                "Команды в это время относятся к предыдущему дню. 0–12",
            ),
            SettingsField("leaderboard_limit", "Размер таблицы лидеров", "number", "",
                          "Сколько игроков показывает /leaderboard. 1–50"),
            SettingsField("reminder_hour", "Час вечернего напоминания", "number", "",
                          "Время сервера. Применяется сразу"),
            SettingsField("reminder_minute", "Минута вечернего напоминания", "number", ""),
            SettingsField("delivery_slots", "Слоты доставки свитков (ЧЧ:ММ через запятую)", "text", "",
                          "Время сервера. Применяется после рестарта scheduler"),
            SettingsField("streak_warning_hour", "Час предупреждения о стрике", "number", "",
                          "Применяется после рестарта scheduler"),
            SettingsField("streak_warning_minute", "Минута предупреждения о стрике", "number", ""),
        ],
    ),
    SettingsGroup(
        group="media",
        title="Файлы и медиа",
        fields=[
            SettingsField("media_base_url", "Базовый URL для медиафайлов", "text", "",
                          "Например https://api.ваш-домен. Пусто = текущий адрес API"),
        ],
    ),
    SettingsGroup(
        group="content",
        title="Контент — приветствие и согласие",
        fields=[
            SettingsField("welcome_message", "Приветствие после /start", "textarea", "",
                          "Показывается вместе с кнопкой согласия на обработку данных"),
            SettingsField("consent_text", "Текст согласия (152-ФЗ)", "textarea", "",
                          "Показывается после приветствия, перед тестом"),
        ],
    ),
]


async def get_payments_enabled() -> bool:
    """Whether real payments are currently accepted."""
    val = await get_setting("payments_enabled", "true")
    return val.lower() not in ("false", "0", "no")


def _setting_value_to_bool(value: str | bool | int | None) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value in (True, "true", "True", 1, "1"):
        return "true"
    return "false"


async def get_settings_schema() -> list[dict[str, Any]]:
    """Return schema groups with effective values for the admin panel.

    Each field dict: {key, label, type, hint, value, is_default}.
    """
    result: list[dict[str, Any]] = []
    for group in SETTINGS_SCHEMA:
        fields: list[dict[str, Any]] = []
        for f in group.fields:
            env_default = str(getattr(settings, f.env_attr, "")) if f.env_attr else ""
            try:
                db_value = await get_setting(f.key, "")
            except Exception:
                db_value = ""
            is_default = not db_value
            fields.append(
                {
                    "key": f.key,
                    "label": f.label,
                    "type": f.type,
                    "hint": f.hint,
                    "value": db_value or env_default,
                    "is_default": is_default,
                }
            )
        result.append({"group": group.group, "title": group.title, "fields": fields})
    return result