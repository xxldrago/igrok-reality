"""Re-export all SQLAlchemy models for Alembic autodiscovery."""

from __future__ import annotations

from app.shared.models.base import Base
from app.shared.models.user import User, Referral
from app.shared.models.scroll import Scroll
from app.shared.models.scroll_archetype_task import ScrollArchetypeTask
from app.shared.models.archetype import Archetype
from app.shared.models.payment import Payment
from app.shared.models.completion import UserCompletion
from app.shared.models.settings import Setting
from app.shared.models.audit import AuditLog
from app.shared.models.commission import CommissionBalance
from app.shared.models.group import Group
from app.shared.models.role_history import RoleHistory
from app.shared.models.clan import Clan, ClanMember
from app.shared.models.prize_fund import PrizeFund, PrizeFundPayout

__all__ = [
    "Base",
    "User",
    "Referral",
    "Scroll",
    "ScrollArchetypeTask",
    "Archetype",
    "Payment",
    "UserCompletion",
    "Setting",
    "AuditLog",
    "CommissionBalance",
    "Group",
    "RoleHistory",
    "Clan",
    "ClanMember",
    "PrizeFund",
    "PrizeFundPayout",
]
