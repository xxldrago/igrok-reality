"""Registration flow keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.callbacks.registration import ArchetypeAnswer, ConsentCallback

ARCHETYPE_QUESTIONS = {
    1: {
        "text": "Вопрос 1/4: Как вы обычно подходите к новой задаче?",
        "options": {
            "a": "Анализирую и планирую",
            "b": "Делаю сразу, разберусь по ходу",
            "c": "Жду, пока другие покажут пример",
            "d": "Ищу нестандартное решение",
        },
    },
    2: {
        "text": "Вопрос 2/4: Что для вас важнее в команде?",
        "options": {
            "a": "Чёткий план и роли",
            "b": "Энергия и движение",
            "c": "Стабильность и поддержка",
            "d": "Свобода действий",
        },
    },
    3: {
        "text": "Вопрос 3/4: Как вы справляетесь с трудностями?",
        "options": {
            "a": "Ищу логическое решение",
            "b": "Пробую разные подходы быстро",
            "c": "Нахожу опору в близких",
            "d": "Ухожу в себя, обдумываю",
        },
    },
    4: {
        "text": "Вопрос 4/4: Что вас больше всего мотивирует?",
        "options": {
            "a": "Достижение цели",
            "b": "Новые впечатления",
            "c": "Признание и благодарность",
            "d": "Личный рост",
        },
    },
}


def consent_keyboard() -> InlineKeyboardMarkup:
    """Build the consent approval keyboard with agree/decline buttons."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Я согласен",
        callback_data=ConsentCallback(action="agree"),
    )
    builder.button(
        text="Отказаться",
        callback_data=ConsentCallback(action="decline"),
    )
    builder.adjust(1)
    return builder.as_markup()


def archetype_keyboard(question: int) -> InlineKeyboardMarkup:
    """Build an inline keyboard with answer options for the archetype quiz.

    Args:
        question: Question number (1-4).

    Returns:
        InlineKeyboardMarkup with 4 answer buttons (a/b/c/d).
    """
    q = ARCHETYPE_QUESTIONS[question]
    builder = InlineKeyboardBuilder()
    for letter, text in q["options"].items():
        builder.button(
            text=text,
            callback_data=ArchetypeAnswer(question=question, answer=letter),
        )
    builder.adjust(1)
    return builder.as_markup()
