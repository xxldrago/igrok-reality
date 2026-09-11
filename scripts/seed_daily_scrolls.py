"""Seed script for daily_scrolls — generates content for 90 days × scroll types.

Run: python -m scripts.seed_daily_scrolls
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # project root (scripts package)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select

from app.shared.database import session_factory
from app.shared.models.daily_scroll import DailyScroll
from app.shared.models.scroll_type import ScrollType
from app.bot.services.day_type import get_available_scroll_codes, get_day_type, MEDITATION_DAYS, BREATHING_DAYS, AWARENESS_DAYS
from scripts.seed_scroll_types import SCROLL_TYPES


# Template content for each scroll type
TEMPLATES = {
    "rassvet": {
        "title": "🌅 Свиток Рассвета",
        "content": (
            "Утро начинается с простого:\n"
            "1. Медленно потянитесь в постели\n"
            "2. Выпейте стакан воды с лимоном\n"
            "3. Сделайте 5 глубоких вдохов\n\n"
            "Ваше тело просыпается. День начинается с заботы о себе."
        ),
    },
    "ogne": {
        "title": "🔥 Свиток Огня",
        "content": (
            "Контрастный душ — это энергия:\n"
            "1. 30 секунд тёплой воды\n"
            "2. 15 секунд холодной воды\n"
            "3. Повторите 3 раза\n"
            "4. Завершите холодной водой\n\n"
            "Самомассаж: помассируйте уши, шею, ступни (2 мин)."
        ),
    },
    "korni": {
        "title": "🧘 Свиток Корней",
        "content": (
            "Медитация дня:\n"
            "1. Сядьте удобно, закройте глаза\n"
            "2. Следуйте аудиогиду (5-10 минут)\n"
            "3. Обратите внимание на тело и дыхание\n\n"
            "💬 Вопрос дня: За что вы благодарны сегодня?"
        ),
    },
    "vetr": {
        "title": "🌬️ Свиток Ветра",
        "content": (
            "Дыхательная практика:\n"
            "1. Вдох через нос на 4 счёта\n"
            "2. Задержка на 4 счёта\n"
            "3. Выдох через рот на 6 счётов\n"
            "4. Повторите 10 раз\n\n"
            "Сфокусируйтесь на зоне недели во время дыхания."
        ),
    },
    "sledy": {
        "title": "👣 Свиток Следов",
        "content": (
            "Микро-привычка дня:\n"
            "Встройте одну маленькую привычку в свой быт:\n\n"
            "Примеры:\n"
            "• Чистите зубы 2 минуты (таймер)\n"
            "• 10 приседаний после пробуждения\n"
            "• Стакан воды перед едой\n"
            "• 3 минуты тишины перед сном\n\n"
            "Выберите одну и выполните."
        ),
    },
    "zrya": {
        "title": "👁️ Свиток Зря",
        "content": (
            "Теория дня:\n\n"
            "Осознанность — это способность замечать свои мысли, "
            "эмоции и действия без осуждения.\n\n"
            "Попробуйте сегодня:\n"
            "• Заметить момент, когда вы действуете на автопилоте\n"
            "• Остановиться и сделать 3 осознанных вдоха\n"
            "• Задать вопрос: «Что я сейчас чувствую?»"
        ),
    },
    "pitaniye": {
        "title": "🥗 Свиток Питания",
        "content": (
            "Рекомендации по питанию:\n\n"
            "Сегодня попробуйте:\n"
            "• Ешьте медленно, пережевывая каждую порцию\n"
            "• Выпейте 1.5-2 литра воды\n"
            "• Добавьте в рацион овощи или фрукты\n"
            "• Не ешьте за 2 часа до сна\n\n"
            "Запишите, что вы ели сегодня — без осуждения, просто наблюдение."
        ),
    },
    "integratsiya": {
        "title": "🌙 Интеграция Истока",
        "content": (
            "Ночная практика:\n"
            "1. Лягте удобно, закройте глаза\n"
            "2. Проговорите про себя 3 вещи, за которые благодарны\n"
            "3. Сделайте 10 медленных вдохов\n"
            "4. Представьте, как ваше тело расслабляется\n\n"
            "Сон — это время восстановления. Доверьтесь ему."
        ),
    },
    "otchet": {
        "title": "📝 Отчёт о дне",
        "content": (
            "Подведём итоги дня:\n\n"
            "Ответьте на 3 вопроса:\n"
            "1. Что я сделал(а) сегодня для себя?\n"
            "2. Что дало мне энергию?\n"
            "3. Что я хочу сделать завтра?\n\n"
            "Запишите кратко — это ваш дневник прогресса."
        ),
    },
}

# Day-specific content variations
DAY_1_CONTENT = {
    "korni": (
        "🧘 Первая медитация:\n"
        "1. Сядьте удобно, закройте глаза\n"
        "2. Следуйте аудиогиду (10 минут)\n"
        "3. Обратите внимание на тело и дыхание\n\n"
        "💬 Вопрос первой недели: Кем я хочу стать через 90 дней?"
    ),
}

# Breathing day content
BREATHING_CONTENT = {
    "vetr_extra_14": (
        "🌬️ Дыхание сидя (день дыхания):\n"
        "1. Сядьте ровно, ноги на полу\n"
        "2. Вдох через нос на 4 счёта\n"
        "3. Задержка на 4 счёта\n"
        "4. Выдох через рот на 6 счётов\n"
        "5. Повторите 10 раз\n\n"
        "Сфокусируйтесь на ощущениях в теле."
    ),
    "vetr_extra_21": (
        "🌬️ Дыхание лёжа (день дыхания):\n"
        "1. Лягте на спину, руки вдоль тела\n"
        "2. Вдох животом на 4 счёта\n"
        "3. Задержка на 4 счёта\n"
        "4. Медленный выдох на 6 счётов\n"
        "5. Повторите 10 раз\n\n"
        "Позвольте телу полностью расслабиться."
    ),
}

# Awareness day content
AWARENESS_CONTENT = {
    "zrya": (
        "🔮 День осознания — вопросы для самоанализа:\n\n"
        "1. Какие привычки мне мешают?\n"
        "2. Что я делаю на автопилоте?\n"
        "3. Когда я чувствую себя наиболее живым(ой)?\n"
        "4. Чего я избегаю и почему?\n\n"
        "Запишите ответы — это начало трансформации."
    ),
    "otchet": (
        "📝 Отчёт дня осознания (+5 XP):\n\n"
        "Подведите итог недели:\n"
        "1. Что я понял(а) о себе за эту неделю?\n"
        "2. Какая привычка далась легче всего?\n"
        "3. Что было сложнее всего?\n"
        "4. Как я хочу изменить следующую неделю?\n\n"
        "Это важный момент для роста."
    ),
}


async def upsert_scroll_types(session) -> dict[str, ScrollType]:
    """Ensure all 9 scroll types exist and match the canonical definition.

    Inserts missing types and updates fields of existing ones (hour, xp,
    description, ...), so the DB can never drift from the code.
    Returns {code: ScrollType}.
    """
    result = await session.execute(select(ScrollType))
    existing = {st.code: st for st in result.scalars().all()}

    for data in SCROLL_TYPES:
        st = existing.get(data["code"])
        if st is None:
            st = ScrollType(**data)
            session.add(st)
            print(f"  + type {data['code']}: {data['name']}")
        else:
            changed = [k for k, v in data.items() if getattr(st, k) != v]
            if changed:
                for k in changed:
                    setattr(st, k, data[k])
                print(f"  ~ type {data['code']}: updated {changed}")
            else:
                print(f"  = type {data['code']}: ok")
        existing[data["code"]] = st

    await session.flush()
    result = await session.execute(select(ScrollType))
    return {st.code: st for st in result.scalars().all()}


async def seed_daily_scrolls(rebuild: bool = False) -> None:
    """Generate and insert daily scrolls for 90 days.

    Always upserts scroll types first, then fills missing daily scrolls.
    With rebuild=True deletes ALL daily_scrolls and regenerates from scratch.
    Ends with a strict coverage check — exits non-zero on any gap.

    Args:
        rebuild: when True, delete ALL existing daily_scrolls first so
            missing/partial days are fully regenerated.
    """
    from sqlalchemy import delete

    async with session_factory() as session:
        # 1. Scroll types first — never silently skip codes again
        print("Upserting scroll types...")
        scroll_types = await upsert_scroll_types(session)
        await session.commit()

        missing_types = set(TEMPLATES) - set(scroll_types)
        if missing_types:
            print(f"ERROR: scroll types still missing after upsert: {sorted(missing_types)}")
            raise SystemExit(1)

        # 2. Daily scrolls
        if rebuild:
            await session.execute(delete(DailyScroll))
            await session.commit()
            print("Rebuild mode: deleted all existing daily_scrolls")

        created = 0
        skipped = 0

        for day in range(1, 91):
            available_codes = get_available_scroll_codes(day)
            day_type = get_day_type(day)

            for code in available_codes:
                st = scroll_types.get(code)
                if st is None:
                    continue

                # Check if already exists
                result = await session.execute(
                    select(DailyScroll).where(
                        DailyScroll.day_number == day,
                        DailyScroll.scroll_type_id == st.id,
                    )
                )
                if result.scalar_one_or_none() is not None:
                    skipped += 1
                    continue

                # Get template content
                template = TEMPLATES.get(code, {"title": code, "content": ""})
                title = template["title"]
                content = template["content"]

                # Day-specific overrides
                if day == 1 and code == "korni" and "korni" in DAY_1_CONTENT:
                    content = DAY_1_CONTENT["korni"]
                elif day in BREATHING_DAYS and code == "vetr":
                    # Use different breathing content for the 14:00 and 21:00 slots
                    pass  # Handled by scheduler using is_breathing_day_only flag
                elif day in AWARENESS_DAYS:
                    if code == "zrya" and "zrya" in AWARENESS_CONTENT:
                        content = AWARENESS_CONTENT["zrya"]
                    elif code == "otchet" and "otchet" in AWARENESS_CONTENT:
                        content = AWARENESS_CONTENT["otchet"]
                        title = "📝 Отчёт дня осознания"

                daily_scroll = DailyScroll(
                    day_number=day,
                    scroll_type_id=st.id,
                    title=title,
                    content=content,
                )
                session.add(daily_scroll)
                created += 1

        await session.commit()
        print(f"Created {created} daily scrolls, skipped {skipped} existing")

        # Strict coverage check: days 1-90 vs expected scroll codes
        result = await session.execute(select(ScrollType))
        type_ids = {st.id: st.code for st in result.scalars().all()}
        result = await session.execute(
            select(DailyScroll.day_number, DailyScroll.scroll_type_id)
        )
        present: dict[int, set[str]] = {}
        per_type: dict[str, int] = {}
        for day_number, type_id in result.all():
            code = type_ids.get(type_id, "?")
            present.setdefault(day_number, set()).add(code)
            per_type[code] = per_type.get(code, 0) + 1

        gap_days: list[str] = []
        for day in range(1, 91):
            expected = set(get_available_scroll_codes(day))
            missing = expected - present.get(day, set())
            if missing:
                gap_days.append(f"day {day}: missing {sorted(missing)}")

        # Per-type totals vs expected
        expected_per_type: dict[str, int] = {}
        for day in range(1, 91):
            for code in get_available_scroll_codes(day):
                expected_per_type[code] = expected_per_type.get(code, 0) + 1
        type_gaps = {
            code: (expected_per_type.get(code, 0), per_type.get(code, 0))
            for code in expected_per_type
            if per_type.get(code, 0) != expected_per_type.get(code, 0)
        }

        total = sum(per_type.values())
        print(f"Total daily scrolls: {total}")
        if gap_days:
            print(f"GAPS ({len(gap_days)} days incomplete):")
            for line in gap_days:
                print(f"  {line}")
        if type_gaps:
            print("TYPE GAPS (expected vs actual):")
            for code, (exp, act) in sorted(type_gaps.items()):
                print(f"  {code}: expected {exp}, got {act}")
        if gap_days or type_gaps:
            raise SystemExit(1)
        print("Coverage OK: all 90 days have every expected scroll")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed daily scrolls for 90 days")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Delete all daily_scrolls and regenerate from scratch",
    )
    args = parser.parse_args()
    asyncio.run(seed_daily_scrolls(rebuild=args.rebuild))
