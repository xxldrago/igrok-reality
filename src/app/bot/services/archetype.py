"""Archetype scoring logic for the 4-question quiz.

Maps quiz answers to one of four archetypes: Head, Shell, Whirlwind, Ghost.
Each answer awards +2 points to its corresponding archetype.
The archetype with the highest total score wins (ties broken by first encountered).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.bot.services.settings_service import get_setting

# Default fallback scoring (used if settings not configured)
DEFAULT_ARCHETYPE_SCORES: dict[int, dict[str, dict[str, int]]] = {
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

# Canonical descriptions, kept in sync with the add_archetypes migration and
# the seed_scrolls ensure step.
ARCHETYPE_DESCRIPTIONS: dict[str, str] = {
    "head": (
        "Архетип Голова — рациональный стратег. Основан на логике, планировании "
        "и интеллектуальном поиске решений. Сильная сторона — анализ и "
        "систематизация."
    ),
    "shell": (
        "Архетип Панцирь — надёжный защитник и опора. Ценит стабильность, "
        "порядок и последовательность. Сильная сторона — выносливость и "
        "устойчивость к трудностям."
    ),
    "whirlwind": (
        "Архетип Вихрь — энергичный исследователь. Движется быстро, берётся "
        "за многое, вдохновляется новизной. Сильная сторона — инициативность "
        "и способность к быстрой адаптации."
    ),
    "ghost": (
        "Архетип Призрак — интуитивный наблюдатель. Чувствует тонкие энергии "
        "и скрытые закономерности. Сильная сторона — интуиция и способность "
        "видеть неочевидное."
    ),
}


@dataclass
class QuizQuestion:
    """Single quiz question with options."""
    text: str
    options: list[dict[str, str]]  # [{"text": "...", "key": "a"}, ...]


@dataclass
class QuizConfig:
    """Complete quiz configuration loaded from settings."""
    intro: str
    questions: list[QuizQuestion]
    results: dict[str, str]  # archetype -> result text


async def load_quiz_config() -> QuizConfig:
    """Load quiz configuration from settings, fallback to defaults."""
    import json
    
    # Load intro
    intro = await get_setting("quiz_intro", DEFAULT_INTRO)
    
    # Load questions
    questions_json = await get_setting("quiz_questions", "[]")
    try:
        questions_data = json.loads(questions_json)
        questions = [QuizOption(**q) for q in questions_data]
    except Exception:
        questions = DEFAULT_QUESTIONS
    
    # Load results
    results_json = await get_setting("quiz_results", "{}")
    try:
        results = json.loads(results_json)
    except Exception:
        results = DEFAULT_RESULTS
    
    return QuizConfig(intro=intro, questions=questions, results=results)


async def load_archetype_scores() -> dict[int, dict[str, dict[str, int]]]:
    """Load archetype scoring from settings."""
    import json
    scores_json = await get_setting("archetype_scores", "{}")
    try:
        data = json.loads(scores_json)
        # Convert string keys to int
        return {int(k): v for k, v in data.items()}
    except Exception:
        return DEFAULT_ARCHETYPE_SCORES


DEFAULT_INTRO = """⚔️ ПРЕЖДЕ ЧЕМ ТЫ ПОЛУЧИШЬ СВОЙ ПЕРВЫЙ СВИТОК, ОТВЕТЬ НА 4 ВОПРОСА.

Это не экзамен. Это способ понять, какая часть тебя потеряла связь с телом. Ответь честно — и ты получишь ключ к своей ТРОПЕ.

Не думай. Не анализируй. Просто почувствуй. Твоё тело знает ответы, даже если ум сомневается.

Начинаем..."""

DEFAULT_QUESTIONS = [
    QuizQuestion(
        text="Сядь удобно. Закрой глаза на 10 секунд. Просто почувствуй себя.\n\nЧто ты чувствуешь в теле прямо сейчас?",
        options=[
            {"text": "Мысли крутятся, а тело — пустое. Я не чувствую его", "key": "a"},
            {"text": "Тело тяжёлое, сжатое, будто я в корсете или броне", "key": "b"},
            {"text": "Энергия размазана. Я везде и нигде. Не могу собраться", "key": "c"},
            {"text": "Я будто парю. Нет опоры. Не чувствую земли под ногами", "key": "d"},
        ]
    ),
    QuizQuestion(
        text="Представь, что ты стоишь на пороге долгого пути. Что ты чувствуешь?",
        options=[
            {"text": "Мне нужно понять, куда идти. Я ищу логику, смысл, карту", "key": "a"},
            {"text": "Я хочу быть готовым ко всему. Я собираю силы, чтобы не сдаться", "key": "b"},
            {"text": "Мне хочется бежать. Вперёд! Я не могу стоять на месте", "key": "c"},
            {"text": "Я не чувствую, что могу идти. Нет опоры. Нет почвы под ногами", "key": "d"},
        ]
    ),
    QuizQuestion(
        text="Если бы ты мог услышать свой внутренний голос (Компас), что бы он сказал?",
        options=[
            {"text": "Остановись. Хватит думать. Начни чувствовать", "key": "a"},
            {"text": "Раскройся. Сбрось броню. Ты в безопасности", "key": "b"},
            {"text": "Соберись. Найди центр. Не распыляйся", "key": "c"},
            {"text": "Оприся на землю. Ты существуешь. Ты весишь", "key": "d"},
        ]
    ),
    QuizQuestion(
        text="Что из перечисленного тебе ближе всего? Что звучит как правда?",
        options=[
            {"text": "Я устал жить в голове. Я хочу чувствовать тело", "key": "a"},
            {"text": "Я устал быть сильным. Я хочу быть живым", "key": "b"},
            {"text": "Я устал разрываться. Я хочу быть целым", "key": "c"},
            {"text": "Я устал быть невидимым. Я хочу чувствовать опору", "key": "d"},
        ]
    ),
]

DEFAULT_RESULTS = {
    "head": """🔹 АРХЕТИП «ГОЛОВА»

Ты потерял связь с телом. Ты живёшь в мыслях, анализируешь, ищешь ответы, но не чувствуешь опоры. Твоё тело — как пустой скафандр, в котором ты летаешь, но не живёшь.

Твой путь — возвращение в тело. В стопы, в дыхание, в ощущения. Ты научишься чувствовать, а не анализировать.

Твой девиз: «Я возвращаю себе своё тело»

Твоя задача в игре: Каждый раз, когда мысль улетает — возвращай внимание в стопы. Просто возвращай. Без оценки. Без попытки «исправить». Просто будь в теле.

Ключевая практика: Сканирование тела, дыхание в стопы, осознанное движение.

Ты начинаешь свой путь. Твой Компас уже звенит. Пришло время его услышать.""",
    "shell": """🔹 АРХЕТИП «ПАНЦИРЬ»

Ты сжимаешься, чтобы не чувствовать. Твоё тело — броня, защита от мира. Ты терпишь, выдерживаешь, но внутри — напряжение. Ты не позволяешь себе быть уязвимым.

Твой путь — расслабление. Дышать в зажимы. Позволить себе быть живым.

Твой девиз: «Я снимаю свою броню и чувствую себя живым»

Твоя задача в игре: Каждый раз, когда чувствуешь напряжение — остановись, найди зону зажима и дыши в неё. На выдохе — представляй, что броня становится на 1% тоньше.

Ключевая практика: Дыхание в зажимы, самомассаж, осознанное расслабление.

Ты начинаешь свой путь. Твой Компас уже звенит. Пришло время его услышать.""",
    "whirlwind": """🔹 АРХЕТИП «ВИХРЬ»

Твоя энергия размазана. Ты везде и нигде. Ты импульсивен, быстр, но не можешь собраться. Твоя энергия не течёт — она разлетается в разные стороны.

Твой путь — сборка. Найти центр. Собрать энергию в теле и удерживать её.

Твой девиз: «Я собираю себя в центр»

Твоя задача в игре: Каждый раз, когда чувствуешь, что энергия разлетается — верни внимание в центр (точка ниже пупка). На вдохе — собирай, на выдохе — удерживай.

Ключевая практика: Дыхание в центр, движение с фокусом на таз, сборка внимания.

Ты начинаешь свой путь. Твой Компас уже звенит. Пришло время его услышать.""",
    "ghost": """🔹 АРХЕТИП «ПРИЗРАК»

Ты паришь над землёй. Ты не чувствуешь веса, опоры, реальности. Ты невесом. Ты есть, но тебя нет. Ты не чувствуешь своих стоп, своей тяжести, своего присутствия.

Твой путь — укоренение. Чувствовать стопы. Чувствовать давление. Чувствовать, что ты есть.

Твой девиз: «Я возвращаю себе вес и опору»

Твоя задача в игре: Каждый раз, когда чувствуешь себя «невесомым» — остановись, продави пятки в пол и скажи мысленно: «Я здесь».

Ключевая практика: Стояние босиком, осознанная ходьба, приседания с фокусом на стопы.

Ты начинаешь свой путь. Твой Компас уже звенит. Пришло время его услышать.""",
}


async def calculate_archetype(data: dict) -> str:
    """Calculate the user's archetype from their quiz answers.

    Args:
        data: FSM context data dict containing q1_answer through q4_answer.

    Returns:
        Internal archetype name ("head", "shell", "whirlwind", or "ghost").
    """
    scores: dict[str, int] = {"head": 0, "shell": 0, "whirlwind": 0, "ghost": 0}
    scores_map = await load_archetype_scores()

    for q_num in range(1, 5):
        answer = data.get(f"q{q_num}_answer")
        if answer and q_num in scores_map:
            for archetype, points in scores_map[q_num].get(answer, {}).items():
                scores[archetype] += points

    # Return highest-scoring archetype (ties broken by first encountered)
    return max(scores, key=scores.get)  # type: ignore[arg-type]


def get_archetype_name(archetype: str) -> str:
    """Get Russian display name for archetype."""
    return ARCHETYPE_NAMES.get(archetype, archetype)
