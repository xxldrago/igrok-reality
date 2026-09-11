"""Archetype scoring logic for the 4-question quiz.

Maps quiz answers to one of four archetypes: Head, Shell, Whirlwind, Ghost.
Each answer awards +2 points to its corresponding archetype.
The archetype with the highest total score wins (ties broken by first encountered).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.bot.services.settings_service import get_setting

# Default fallback scoring (used if settings not configured).
# Mapping follows the ORЪ test spec: A=head (Голова), B=shell (Панцирь),
# C=whirlwind (Вихрь), D=ghost (Призрак).
DEFAULT_ARCHETYPE_SCORES: dict[int, dict[str, dict[str, int]]] = {
    1: {
        "a": {"head": 2},
        "b": {"shell": 2},
        "c": {"whirlwind": 2},
        "d": {"ghost": 2},
    },
    2: {
        "a": {"head": 2},
        "b": {"shell": 2},
        "c": {"whirlwind": 2},
        "d": {"ghost": 2},
    },
    3: {
        "a": {"head": 2},
        "b": {"shell": 2},
        "c": {"whirlwind": 2},
        "d": {"ghost": 2},
    },
    4: {
        "a": {"head": 2},
        "b": {"shell": 2},
        "c": {"whirlwind": 2},
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
    if not intro:
        intro = DEFAULT_INTRO

    # Load questions (fall back to defaults when missing, empty, or invalid)
    questions: list[QuizQuestion] = DEFAULT_QUESTIONS
    questions_json = await get_setting("quiz_questions", "")
    if questions_json:
        try:
            questions_data = json.loads(questions_json)
            parsed = [QuizQuestion(**q) for q in questions_data]
            if parsed:
                questions = parsed
        except Exception:
            questions = DEFAULT_QUESTIONS

    # Load results (fall back to defaults when missing, empty, or invalid)
    results: dict[str, str] = DEFAULT_RESULTS
    results_json = await get_setting("quiz_results", "")
    if results_json:
        try:
            parsed_results = json.loads(results_json)
            if parsed_results:
                results = parsed_results
        except Exception:
            results = DEFAULT_RESULTS

    return QuizConfig(intro=intro, questions=questions, results=results)


async def load_archetype_scores() -> dict[int, dict[str, dict[str, int]]]:
    """Load archetype scoring from settings (defaults when missing/empty)."""
    import json
    scores_json = await get_setting("archetype_scores", "")
    if scores_json:
        try:
            data = json.loads(scores_json)
            if data:
                # Convert string keys to int
                return {int(k): v for k, v in data.items()}
        except Exception:
            pass
    return DEFAULT_ARCHETYPE_SCORES


DEFAULT_INTRO = """⚔️ ПРЕЖДЕ ЧЕМ ТЫ ПОЛУЧИШЬ СВОЙ ПЕРВЫЙ СВИТОК, ОТВЕТЬ НА 4 ВОПРОСА.

Это не экзамен. Это способ понять, какая часть тебя потеряла связь с телом. Ответь честно — и ты получишь ключ к своей ТРОПЕ.

Не думай. Не анализируй. Просто почувствуй. Твоё тело знает ответы, даже если ум сомневается.

Начинаем..."""

DEFAULT_QUESTIONS = [
    QuizQuestion(
        text="ВОПРОС 1. ТВОЁ ТЕЛО СЕГОДНЯ\n\nСядь удобно. Закрой глаза на 10 секунд. Просто почувствуй себя.\n\nЧто ты чувствуешь в теле прямо сейчас?",
        options=[
            {"text": "Мысли крутятся, а тело — пустое. Я не чувствую его", "key": "a"},
            {"text": "Тело тяжёлое, сжатое, будто я в корсете или броне", "key": "b"},
            {"text": "Энергия размазана. Я везде и нигде. Не могу собраться", "key": "c"},
            {"text": "Я будто парю. Нет опоры. Не чувствую земли под ногами", "key": "d"},
        ]
    ),
    QuizQuestion(
        text="ВОПРОС 2. ТВОЯ ТРОПА\n\nПредставь, что ты стоишь на пороге долгого пути. Что ты чувствуешь?",
        options=[
            {"text": "Мне нужно понять, куда идти. Я ищу логику, смысл, карту", "key": "a"},
            {"text": "Я хочу быть готовым ко всему. Я собираю силы, чтобы не сдаться", "key": "b"},
            {"text": "Мне хочется бежать. Вперёд! Я не могу стоять на месте", "key": "c"},
            {"text": "Я не чувствую, что могу идти. Нет опоры. Нет почвы под ногами", "key": "d"},
        ]
    ),
    QuizQuestion(
        text="ВОПРОС 3. ТВОЙ КОМПАС\n\nЕсли бы ты мог услышать свой внутренний голос (Компас), что бы он сказал?",
        options=[
            {"text": "Остановись. Хватит думать. Начни чувствовать", "key": "a"},
            {"text": "Раскройся. Сбрось броню. Ты в безопасности", "key": "b"},
            {"text": "Соберись. Найди центр. Не распыляйся", "key": "c"},
            {"text": "Оприся на землю. Ты существуешь. Ты весишь", "key": "d"},
        ]
    ),
    QuizQuestion(
        text="ВОПРОС 4. ТВОЙ ОТКЛИК\n\nЧто из перечисленного тебе ближе всего? Что звучит как правда?",
        options=[
            {"text": "Я устал жить в голове. Я хочу чувствовать тело", "key": "a"},
            {"text": "Я устал быть сильным. Я хочу быть живым", "key": "b"},
            {"text": "Я устал разрываться. Я хочу быть целым", "key": "c"},
            {"text": "Я устал быть невидимым. Я хочу чувствовать опору", "key": "d"},
        ]
    ),
]

DEFAULT_RESULTS = {
    "head": """🔹 ТВОЙ АРХЕТИП: ГОЛОВА

Ты потерял связь с телом. Ты живёшь в мыслях, анализируешь, ищешь ответы, но не чувствуешь опоры. Твоё тело — как пустой скафандр, в котором ты летаешь, но не живёшь.

Твой путь — возвращение в тело. В стопы, в дыхание, в ощущения. Ты научишься чувствовать, а не анализировать.

Твой девиз: «Я возвращаю себе своё тело»

Твоя задача в игре: Каждый раз, когда мысль улетает — возвращай внимание в стопы. Просто возвращай. Без оценки. Без попытки «исправить». Просто будь в теле.

Ключевая практика: Сканирование тела, дыхание в стопы, осознанное движение.

Ты начинаешь свой путь. Твой Компас уже звенит. Пришло время его услышать.""",
    "shell": """🔹 ТВОЙ АРХЕТИП: ПАНЦИРЬ

Ты сжимаешься, чтобы не чувствовать. Твоё тело — броня, защита от мира. Ты терпишь, выдерживаешь, но внутри — напряжение. Ты не позволяешь себе быть уязвимым.

Твой путь — расслабление. Дышать в зажимы. Позволить себе быть живым.

Твой девиз: «Я снимаю свою броню и чувствую себя живым»

Твоя задача в игре: Каждый раз, когда чувствуешь напряжение — остановись, найди зону зажима и дыши в неё. На выдохе — представляй, что броня становится на 1% тоньше.

Ключевая практика: Дыхание в зажимы, самомассаж, осознанное расслабление.

Ты начинаешь свой путь. Твой Компас уже звенит. Пришло время его услышать.""",
    "whirlwind": """🔹 ТВОЙ АРХЕТИП: ВИХРЬ

Твоя энергия размазана. Ты везде и нигде. Ты импульсивен, быстр, но не можешь собраться. Твоя энергия не течёт — она разлетается в разные стороны.

Твой путь — сборка. Найти центр. Собрать энергию в теле и удерживать её.

Твой девиз: «Я собираю себя в центр»

Твоя задача в игре: Каждый раз, когда чувствуешь, что энергия разлетается — верни внимание в центр (точка ниже пупка). На вдохе — собирай, на выдохе — удерживай.

Ключевая практика: Дыхание в центр, движение с фокусом на таз, сборка внимания.

Ты начинаешь свой путь. Твой Компас уже звенит. Пришло время его услышать.""",
    "ghost": """🔹 ТВОЙ АРХЕТИП: ПРИЗРАК

Ты паришь над землёй. Ты не чувствуешь веса, опоры, реальности. Ты невесом. Ты есть, но тебя нет. Ты не чувствуешь своих стоп, своей тяжести, своего присутствия.

Твой путь — укоренение. Чувствовать стопы. Чувствовать давление. Чувствовать, что ты есть.

Твой девиз: «Я возвращаю себе вес и опору»

Твоя задача в игре: Каждый раз, когда чувствуешь себя «невесомым» — остановись, продави пятки в пол и скажи мысленно: «Я здесь».

Ключевая практика: Стояние босиком, осознанная ходьба, приседания с фокусом на стопы.

Ты начинаешь свой путь. Твой Компас уже звенит. Пришло время его услышать.""",
}


async def calculate_archetype(data: dict) -> str:
    """Calculate the user's archetype from their quiz answers.

    Spec algorithm (game «ОРЪ»):
        - Each of the 4 answers votes for one archetype (resolved via the
          scoring map as the highest-scored archetype for that answer).
        - The archetype with the most votes (3-4 of 4) wins.
        - On a split (2-2, 1/1/1/1, ...), the archetype of the FIRST
          question wins (Q1 is the most important).

    Args:
        data: FSM context data dict containing q1_answer through q4_answer.

    Returns:
        Internal archetype name ("head", "shell", "whirlwind", or "ghost").
    """
    scores_map = await load_archetype_scores()

    votes: list[str] = []
    for q_num in range(1, 5):
        answer = data.get(f"q{q_num}_answer")
        if not answer or q_num not in scores_map:
            continue
        points = scores_map[q_num].get(answer, {})
        if not points:
            continue
        votes.append(max(points, key=points.get))  # type: ignore[arg-type]

    if not votes:
        return "head"

    counts: dict[str, int] = {}
    for vote in votes:
        counts[vote] = counts.get(vote, 0) + 1
    best = max(counts.values())
    leaders = [a for a, c in counts.items() if c == best]
    if len(leaders) == 1:
        return leaders[0]
    # Split — Q1 decides
    return votes[0]


def get_archetype_name(archetype: str) -> str:
    """Get Russian display name for archetype."""
    return ARCHETYPE_NAMES.get(archetype, archetype)
