"""Unit tests for pdfstudio.commands.base — Command and UndoStack."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication

from pdfstudio.commands.base import Command, UndoStack


@pytest.fixture(scope="session", autouse=True)
def _qapp():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


class FakeCommand(Command):
    """Test command that appends/pops from a shared list."""

    def __init__(self, name: str, log: list[str]) -> None:
        super().__init__(f"op:{name}")
        self.name = name
        self.log = log

    def execute(self) -> None:
        self.log.append(f"+{self.name}")

    def undo(self) -> None:
        self.log.append(f"-{self.name}")


class TestPushAndExecute:
    def test_push_executes_command(self) -> None:
        log: list[str] = []
        stack = UndoStack()
        stack.push(FakeCommand("a", log))
        assert log == ["+a"]

    def test_push_enables_undo(self) -> None:
        stack = UndoStack()
        assert not stack.can_undo
        stack.push(FakeCommand("a", []))
        assert stack.can_undo
        assert not stack.can_redo


class TestUndoRedo:
    def test_undo_reverses(self) -> None:
        log: list[str] = []
        stack = UndoStack()
        stack.push(FakeCommand("a", log))
        stack.push(FakeCommand("b", log))
        stack.undo()
        assert log == ["+a", "+b", "-b"]
        assert stack.can_redo
        assert stack.can_undo

    def test_redo_reapplies(self) -> None:
        log: list[str] = []
        stack = UndoStack()
        stack.push(FakeCommand("a", log))
        stack.undo()
        stack.redo()
        assert log == ["+a", "-a", "+a"]

    def test_push_discards_redo_history(self) -> None:
        log: list[str] = []
        stack = UndoStack()
        stack.push(FakeCommand("a", log))
        stack.push(FakeCommand("b", log))
        stack.undo()
        assert stack.can_redo
        stack.push(FakeCommand("c", log))
        assert not stack.can_redo  # 'b' redo is discarded by 'c'

    def test_undo_empty_returns_none(self) -> None:
        stack = UndoStack()
        assert stack.undo() is None

    def test_redo_empty_returns_none(self) -> None:
        stack = UndoStack()
        stack.push(FakeCommand("a", []))
        assert stack.redo() is None


class TestMaxHistoryTrim:
    """Regression: index must point to the last command after overflow."""

    def test_trim_keeps_latest(self) -> None:
        log: list[str] = []
        stack = UndoStack(max_history=3)
        for name in "abcde":
            stack.push(FakeCommand(name, log))

        # Should only remember 'c', 'd', 'e' with 'e' at the top.
        assert stack.undo_description == "op:e"
        stack.undo()
        assert stack.undo_description == "op:d"
        stack.undo()
        assert stack.undo_description == "op:c"
        stack.undo()
        assert stack.undo_description == ""  # exhausted

    def test_trim_does_not_break_undo(self) -> None:
        """The old code left `_index` stale on overflow; verify it now tracks."""
        stack = UndoStack(max_history=2)
        stack.push(FakeCommand("a", []))
        stack.push(FakeCommand("b", []))
        stack.push(FakeCommand("c", []))  # 'a' evicted
        assert stack.can_undo
        assert stack.undo_description == "op:c"


class TestCleanState:
    def test_push_marks_dirty(self) -> None:
        stack = UndoStack()
        assert stack.is_clean
        stack.push(FakeCommand("a", []))
        assert not stack.is_clean

    def test_mark_clean_emits_changed(self, qtbot) -> None:
        """Regression: mark_clean used to skip the changed signal."""
        stack = UndoStack()
        stack.push(FakeCommand("a", []))
        with qtbot.waitSignal(stack.changed, timeout=500):
            stack.mark_clean()
        assert stack.is_clean

    def test_clear_resets_state(self) -> None:
        stack = UndoStack()
        stack.push(FakeCommand("a", []))
        stack.push(FakeCommand("b", []))
        stack.clear()
        assert not stack.can_undo
        assert not stack.can_redo
        assert stack.is_clean


class TestChangedSignal:
    def test_push_emits_changed(self, qtbot) -> None:
        stack = UndoStack()
        with qtbot.waitSignal(stack.changed, timeout=500):
            stack.push(FakeCommand("a", []))

    def test_undo_emits_changed(self, qtbot) -> None:
        stack = UndoStack()
        stack.push(FakeCommand("a", []))
        with qtbot.waitSignal(stack.changed, timeout=500):
            stack.undo()
