"""Bot handler routers."""

from app.bot.handlers.progress import progress_router
from app.bot.handlers.registration import registration_router
from app.bot.handlers.scroll import scroll_router

__all__ = ["progress_router", "registration_router", "scroll_router"]
