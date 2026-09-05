"""Bot handler routers."""

from app.bot.handlers.leaderboard import leaderboard_router
from app.bot.handlers.payment import payment_router
from app.bot.handlers.progress import progress_router
from app.bot.handlers.referral import referral_router
from app.bot.handlers.registration import registration_router
from app.bot.handlers.scroll import scroll_router

__all__ = [
    "leaderboard_router",
    "payment_router",
    "progress_router",
    "referral_router",
    "registration_router",
    "scroll_router",
]
