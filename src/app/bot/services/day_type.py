"""Day type utilities — determines which scrolls are available for a given quest day."""

from __future__ import annotations

from dataclasses import dataclass


# Meditation days: 1, 8, 15, 22, 29, 36, 43, 50, 57, 64, 71, 78, 85
MEDITATION_DAYS = {1 + 7 * i for i in range(13)}  # {1, 8, 15, 22, 29, 36, 43, 50, 57, 64, 71, 78, 85}

# Breathing days: 7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84
BREATHING_DAYS = {7 + 7 * i for i in range(12)}  # {7, 14, 21, 28, 35, 42, 49, 56, 63, 70, 77, 84}

# Awareness days: 6, 13, 20, 27, 34, 41, 48, 55, 62, 69, 76, 83
AWARENESS_DAYS = {6 + 7 * i for i in range(12)}  # {6, 13, 20, 27, 34, 41, 48, 55, 62, 69, 76, 83}


@dataclass
class DayType:
    """Describes what type of day a quest day is."""

    day_number: int
    is_meditation: bool
    is_breathing: bool
    is_awareness: bool
    max_xp: int


def get_day_type(day_number: int) -> DayType:
    """Determine the day type and max XP for a given quest day (1-90)."""
    is_meditation = day_number in MEDITATION_DAYS
    is_breathing = day_number in BREATHING_DAYS
    is_awareness = day_number in AWARENESS_DAYS

    # Calculate max XP based on day type
    if is_breathing and is_awareness:
        # Both breathing and awareness (e.g., day 28 = 27+1, but 28 is breathing)
        # Actually day 28 is breathing, day 27 is awareness
        # No overlap in our definitions
        max_xp = 20 + 8 - 5  # breathing base + awareness otchet bonus - overlap
    elif is_breathing:
        max_xp = 20  # 5+5+5+3+2
    elif is_awareness:
        max_xp = 8  # 3+5
    elif is_meditation:
        max_xp = 36  # 5+5+5+5+3+3+3+5+2
    else:
        max_xp = 31  # 5+5+5+3+3+3+5+2

    return DayType(
        day_number=day_number,
        is_meditation=is_meditation,
        is_breathing=is_breathing,
        is_awareness=is_awareness,
        max_xp=max_xp,
    )


def get_available_scroll_codes(day_number: int) -> list[str]:
    """Return the list of scroll type codes available for a given quest day.

    Standard day: rassvet, ogne, vetr, sledy, zrya, pitaniye, integratsiya, otchet
    Meditation day (1,8,15...): + korni
    Breathing day (7,14,21...): + extra vetr slots (14:00, 21:00)
    Awareness day (6,13,20...): reduced set
    """
    day = get_day_type(day_number)

    # Base scrolls available every day
    codes = ["rassvet", "ogne", "vetr", "sledy", "zrya", "pitaniye", "integratsiya", "otchet"]

    if day.is_meditation:
        codes.insert(2, "korni")  # After ogne, before vetr

    if day.is_breathing:
        # Extra vetr scrolls at 14:00 and 21:00
        # These are handled by the scheduler using is_breathing_day_only flag
        pass

    if day.is_awareness:
        # Awareness days: only zrya + otchet
        codes = ["zrya", "otchet"]

    return codes


# Command -> scroll_type code mapping
COMMAND_TO_SCROLL_CODE = {
    "/wakeup": "rassvet",
    "/cold": "ogne",
    "/scan": "korni",
    "/scanreport": "korni",
    "/breath": "vetr",
    "/micro": "sledy",
    "/focus": "zrya",
    "/food": "pitaniye",
    "/sleep": "integratsiya",
    "/report": "otchet",
}

# Scroll code -> command mapping
SCROLL_CODE_TO_COMMAND = {v: k for k, v in COMMAND_TO_SCROLL_CODE.items()}

# Grace period: 5 hours after midnight (for night shift workers)
GRACE_PERIOD_HOURS = 5
