"""Re-export all SQLAlchemy models for Alembic autodiscovery."""

from __future__ import annotations

from app.shared.models.base import Base
from app.shared.models.user import User, Referral
from app.shared.models.scroll import Scroll
from app.shared.models.payment import Payment
from app.shared.models.completion import UserCompletion
from app.shared.models.settings import Setting
from app.shared.models.audit import AuditLog
from app.shared.models.commission import CommissionBalance

__all__ = [
    "Base",
    "User",
    "Referral",
    "Scroll",
    "Payment",
    "UserCompletion",
    "Setting",
    "AuditLog",
    "CommissionBalance",
]
