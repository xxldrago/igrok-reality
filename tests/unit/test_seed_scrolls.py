"""Tests for seed data structure and seed_scrolls idempotent upsert logic."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Ensure src is on path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.shared.models.archetype import Archetype
from app.shared.models.scroll import Scroll
from app.shared.models.scroll_archetype_task import ScrollArchetypeTask

SEED_MODULE = str(Path(__file__).resolve().parents[2] / "src" / "tools" / "seed_scrolls.py")

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("seed_scrolls", SEED_MODULE)
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)


class TestSeedDataStructure:
    """Tests for the restructured scrolls.json data file."""

    def test_has_90_unique_days(self) -> None:
        """The JSON holds exactly one entry per day for 90 days."""
        data = seed.load_scrolls_from_json()
        assert len(data) == 90
        days = [e["day_number"] for e in data]
        assert sorted(days) == list(range(1, 91))

    def test_each_entry_has_5_sections_and_4_archetype_tasks(self) -> None:
        """Each day entry carries 4 shared sections plus 4 archetype tasks."""
        for entry in seed.load_scrolls_from_json():
            for section in ("common_task", "ritual", "habits", "micromovements"):
                assert entry[section] != ""
            assert set(entry["archetype_tasks"].keys()) == {
                "head",
                "shell",
                "whirlwind",
                "ghost",
            }
            for task_text in entry["archetype_tasks"].values():
                assert task_text != ""


class TestSeedIdempotency:
    """Tests for the scroll seeding upsert logic."""

    def _fake_session(self, scrolls=None, tasks=None, archetypes=None):
        """Build a fake session whose select results are consumed sequentially."""
        scrolls = scrolls if scrolls is not None else []
        tasks = tasks if tasks is not None else []
        archetypes = archetypes if archetypes is not None else ["head"]

        # query plan: per entry -- 1 scroll select, then 4 task selects
        # plus ensure_archetypes runs 4 selects first
        def execute_side_effect(*args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=None)
            return result

        def flush_side_effect():
            # Mirror SQLAlchemy's flush-time assignment of the UUID primary key
            # default so created Scroll instances carry a usable id.
            for call in session.add.call_args_list:
                obj = call.args[0]
                if isinstance(obj, Scroll) and obj.id is None:
                    obj.id = uuid4()

        session = MagicMock()
        session.execute = AsyncMock(side_effect=execute_side_effect)
        session.commit = AsyncMock()
        session.flush = AsyncMock(side_effect=flush_side_effect)
        session.add = MagicMock()
        return session

    @pytest.mark.asyncio
    async def test_seed_creates_scrolls_and_tasks(self) -> None:
        """Seeding inserts 90 scrolls and 4 tasks each when none exist."""
        session = self._fake_session()

        with patch.object(seed, "session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            count = await seed.seed_scrolls()

            assert count == 90
            # New scrolls + archetype tasks are added to the session.
            added = [a for call in session.add.call_args_list for a in call.args]
            scrolls_added = [a for a in added if isinstance(a, Scroll)]
            tasks_added = [a for a in added if isinstance(a, ScrollArchetypeTask)]
            assert len(scrolls_added) == 90
            assert len(tasks_added) == 90 * 4
            # Every task references a scroll.
            for task in tasks_added:
                assert task.scroll_id is not None
                assert task.archetype_code in {"head", "shell", "whirlwind", "ghost"}

    @pytest.mark.asyncio
    async def test_seed_is_idempotent(self) -> None:
        """Re-running the seed should update, not duplicate, scrolls and tasks."""
        # Simulate an existing scroll for every day so nothing new is added.
        session = MagicMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()

        def execute_side_effect(*args, **kwargs):
            result = MagicMock()
            table = args[0].get_final_froms()[0]
            if table is Scroll.__table__:
                result.scalar_one_or_none = MagicMock(return_value=Scroll(
                    day_number=1, common_task="c", ritual="r",
                    habits="h", micromovements="m",
                ))
            elif table is ScrollArchetypeTask.__table__:
                result.scalar_one_or_none = MagicMock(return_value=ScrollArchetypeTask())
            else:  # archetype exists
                result.scalar_one_or_none = MagicMock(return_value=Archetype())
            return result

        session.execute = AsyncMock(side_effect=execute_side_effect)

        with patch.object(seed, "session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            count = await seed.seed_scrolls()

            assert count == 90
            # No Scroll or ScrollArchetypeTask should be freshly added.
            added = [a for call in session.add.call_args_list for a in call.args]
            assert all(
                not isinstance(a, (Scroll, ScrollArchetypeTask)) for a in added
            )

    @pytest.mark.asyncio
    async def test_ensure_archetypes_inserts_missing(self) -> None:
        """Missing archetypes are inserted during seeding."""
        session = MagicMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()

        insert_archetype = MagicMock(return_value=True)

        def execute_side_effect(*args, **kwargs):
            result = MagicMock()
            result.scalar_one_or_none = MagicMock(return_value=None)  # always missing
            return result

        session.execute = AsyncMock(side_effect=execute_side_effect)

        with patch.object(seed, "session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await seed.seed_scrolls()

            added = [a for call in session.add.call_args_list for a in call.args]
            archetypes_added = [a for a in added if isinstance(a, Archetype)]
            assert len(archetypes_added) == 4


class TestCanonicalArchetypes:
    """Tests for the canonical archetype seed constants."""

    def test_four_canonical_codes(self) -> None:
        """The four canonical archetype codes are present."""
        assert set(seed.CANONICAL_ARCHETYPES.keys()) == {
            "head",
            "shell",
            "whirlwind",
            "ghost",
        }

    def test_names_are_russian(self) -> None:
        """The canonical archetype display names are Russian."""
        assert seed.CANONICAL_ARCHETYPES["head"] == "Голова"
        assert seed.CANONICAL_ARCHETYPES["shell"] == "Панцирь"
        assert seed.CANONICAL_ARCHETYPES["whirlwind"] == "Вихрь"
        assert seed.CANONICAL_ARCHETYPES["ghost"] == "Призрак"
