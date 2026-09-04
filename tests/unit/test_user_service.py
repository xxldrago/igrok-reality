"""Tests for user service (referral code generation)."""

import re
import sys
from pathlib import Path

# Ensure src is on path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.bot.services.user_service import generate_referral_code


class TestGenerateReferralCode:
    """Tests for generate_referral_code pure function."""

    def test_unique(self) -> None:
        """Two calls should return different codes."""
        code1 = generate_referral_code()
        code2 = generate_referral_code()
        assert code1 != code2

    def test_length(self) -> None:
        """Code should be exactly 8 characters."""
        code = generate_referral_code()
        assert len(code) == 8

    def test_hex_format(self) -> None:
        """Code should contain only lowercase hexadecimal characters."""
        code = generate_referral_code()
        assert re.fullmatch(r"[0-9a-f]{8}", code) is not None
