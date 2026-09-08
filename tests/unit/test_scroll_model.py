"""Tests for the scroll + scroll_archetype_tasks data model structure."""

import sys
from pathlib import Path

import pytest

# Ensure src is on path for local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from app.shared.models.archetype import Archetype
from app.shared.models.scroll import Scroll
from app.shared.models.scroll_archetype_task import ScrollArchetypeTask


def _unique_cols(table, *col_names) -> bool:
    """Return True if a unique constraint or unique index covering exactly the given columns exists.

    ``unique=True`` on a column produces a unique index; an explicit
    ``UniqueConstraint`` produces a constraint. Both enforce uniqueness, and
    either form satisfies the requirement.
    """
    for constraint in table.constraints:
        if hasattr(constraint, "columns"):
            cols = {c.name for c in constraint.columns}
            if cols == set(col_names):
                return True
    for index in table.indexes:
        if index.unique:
            cols = {c.name for c in index.columns}
            if cols == set(col_names):
                return True
    return False


class TestScrollModelColumns:
    """Tests for the restructured 5-section Scroll model."""

    def test_has_5_section_columns(self) -> None:
        """Scroll exposes the 4 shared sections plus the media/publish fields."""
        cols = {c.name for c in Scroll.__table__.columns}
        assert {"common_task", "ritual", "habits", "micromovements"} <= cols
        assert "media_file_id" in cols
        assert "published_at" in cols

    def test_no_legacy_text_or_archetype_columns(self) -> None:
        """The removed per-archetype text/archetype columns must be gone."""
        cols = {c.name for c in Scroll.__table__.columns}
        assert "text" not in cols
        assert "archetype" not in cols

    def test_day_number_unique_constraint(self) -> None:
        """The unique constraint is now on day_number alone (one scroll per day)."""
        assert _unique_cols(Scroll.__table__, "day_number")


class TestScrollArchetypeTaskModel:
    """Tests for the scroll_archetype_tasks model."""

    def test_columns(self) -> None:
        """Task carries scroll fk, archetype code and task text."""
        cols = {c.name for c in ScrollArchetypeTask.__table__.columns}
        assert {"scroll_id", "archetype_code", "task_text"} <= cols

    def test_unique_per_scroll_and_archetype(self) -> None:
        """One task per (scroll, archetype) combination."""
        assert _unique_cols(ScrollArchetypeTask.__table__, "scroll_id", "archetype_code")

    def test_scroll_foreign_key(self) -> None:
        """Task references the scrolls table via foreign key."""
        fks = list(ScrollArchetypeTask.__table__.foreign_keys)
        assert any(fk.column.table is Scroll.__table__ for fk in fks)


class TestArchetypeModel:
    """Tests for the archetypes reference model."""

    def test_columns(self) -> None:
        """Archetype exposes code, name and description."""
        cols = {c.name for c in Archetype.__table__.columns}
        assert {"code", "name", "description"} <= cols

    def test_code_unique_constraint(self) -> None:
        """Archetype code is unique."""
        assert _unique_cols(Archetype.__table__, "code")
