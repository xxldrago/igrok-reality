"""Archetype scoring logic for the 4-question quiz.

Maps quiz answers to one of four archetypes: Head, Shell, Whirlwind, Ghost.
Each answer awards +2 points to its corresponding archetype.
The archetype with the highest total score wins (ties broken by first encountered).
"""

from __future__ import annotations

# Mapping: question -> answer -> {archetype: score_increment}
ARCHETYPE_SCORES: dict[int, dict[str, dict[str, int]]] = {
    1: {
        "a": {"head": 2},
        "b": {"whirlwind": 2},
        "c": {"shell": 2},
        "d": {"ghost": 2},
    },
    2: {
        "a": {"head": 2},
        "b": {"whirlwind": 2},
        "c": {"shell": 2},
        "d": {"ghost": 2},
    },
    3: {
        "a": {"head": 2},
        "b": {"whirlwind": 2},
        "c": {"shell": 2},
        "d": {"ghost": 2},
    },
    4: {
        "a": {"head": 2},
        "b": {"whirlwind": 2},
        "c": {"shell": 2},
        "d": {"ghost": 2},
    },
}

ARCHETYPE_NAMES: dict[str, str] = {
    "head": "Голова",
    "shell": "Панцирь",
    "whirlwind": "Вихрь",
    "ghost": "Призрак",
}


def calculate_archetype(data: dict) -> str:
    """Calculate the user's archetype from their quiz answers.

    Args:
        data: FSM context data dict containing q1_answer through q4_answer.

    Returns:
        Internal archetype name ("head", "shell", "whirlwind", or "ghost").
    """
    scores: dict[str, int] = {"head": 0, "shell": 0, "whirlwind": 0, "ghost": 0}

    for q_num in range(1, 5):
        answer = data.get(f"q{q_num}_answer")
        if answer and q_num in ARCHETYPE_SCORES:
            for archetype, points in ARCHETYPE_SCORES[q_num].get(answer, {}).items():
                scores[archetype] += points

    # Return highest-scoring archetype (ties broken by first encountered)
    return max(scores, key=scores.get)  # type: ignore[arg-type]
