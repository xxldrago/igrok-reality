"""Channel access service — grant/revoke Telegram channel access.

This is a stub module. Full implementation will be in plan 05-03.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


async def grant_channel_access(telegram_id: int, bot: object) -> None:
    """Grant access to the quest channel for a user.

    Stub — to be implemented in 05-03 (channel_access service).
    """
    logger.info("grant_channel_access stub called for telegram_id=%s", telegram_id)


async def revoke_channel_access(telegram_id: int, bot: object) -> None:
    """Revoke access to the quest channel for a user.

    Stub — to be implemented in 05-03 (channel_access service).
    """
    logger.info("revoke_channel_access stub called for telegram_id=%s", telegram_id)
