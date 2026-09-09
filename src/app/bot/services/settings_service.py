"""Settings service — typed accessors for platform configuration."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.settings import Setting


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