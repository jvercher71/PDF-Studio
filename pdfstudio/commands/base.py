"""
Command pattern base — every undoable action is a Command.
UndoStack manages the history and exposes undo/redo.
"""
from abc import ABC, abstractmethod
from typing import Optional
from PySide6.QtCore import QObject, Signal


class Command(ABC):
    """Base class for all undoable commands."""

    def __init__(self, description: str = ""):
        self.description = description

    @abstractmethod
    def execute(self) -> None:
        """Apply the command."""

    @abstractmethod
    def undo(self) -> None:
        """Reverse the command."""

    def redo(self) -> None:
        """Re-apply after undo. Defaults to execute()."""
        self.execute()


class UndoStack(QObject):
    """
    Command history with undo/redo.

    Signals:
        changed — emitted whenever the stack changes (for updating menu state)
    """
    changed = Signal()

    def __init__(self, max_history: int = 200, parent=None):
        super().__init__(parent)
        self._stack: list[Command] = []
        self._index: int = -1          # points to last executed command
        self._max_history = max_history
        self._is_clean: bool = True    # True = no changes since last save

    def push(self, command: Command) -> None:
        """Execute command and push it onto the stack."""
        # Discard redo history
        self._stack = self._stack[: self._index + 1]
        command.execute()
        self._stack.append(command)

        # Trim to max
        if len(self._stack) > self._max_history:
            self._stack.pop(0)
        else:
            self._index = len(self._stack) - 1

        self._is_clean = False
        self.changed.emit()

    def undo(self) -> Optional[str]:
        """Undo the last command. Returns its description or None if nothing to undo."""
        if not self.can_undo:
            return None
        command = self._stack[self._index]
        command.undo()
        self._index -= 1
        self.changed.emit()
        return command.description

    def redo(self) -> Optional[str]:
        """Redo the next command. Returns its description or None if nothing to redo."""
        if not self.can_redo:
            return None
        self._index += 1
        command = self._stack[self._index]
        command.redo()
        self.changed.emit()
        return command.description

    def clear(self) -> None:
        self._stack.clear()
        self._index = -1
        self._is_clean = True
        self.changed.emit()

    def mark_clean(self) -> None:
        """Call after save — resets the modified tracking."""
        self._is_clean = True

    @property
    def can_undo(self) -> bool:
        return self._index >= 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._stack) - 1

    @property
    def is_clean(self) -> bool:
        return self._is_clean

    @property
    def undo_description(self) -> str:
        if self.can_undo:
            return self._stack[self._index].description
        return ""

    @property
    def redo_description(self) -> str:
        if self.can_redo:
            return self._stack[self._index + 1].description
        return ""
