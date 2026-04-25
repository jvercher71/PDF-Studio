"""
Commands for form field operations — all go through UndoStack.
"""

from pdfstudio.commands.base import Command
from pdfstudio.engine.fields import FieldDef
from pdfstudio.models.document_model import DocumentModel


class AddFieldCommand(Command):
    def __init__(self, model: DocumentModel, fd: FieldDef):
        super().__init__(f"Add {fd.field_type.value} field '{fd.name}'")
        self._model = model
        self._fd = fd

    def execute(self) -> None:
        self._model.add_field(self._fd)

    def undo(self) -> None:
        self._model.delete_field(self._fd.page_index, self._fd.name)


class DeleteFieldCommand(Command):
    def __init__(self, model: DocumentModel, fd: FieldDef):
        super().__init__(f"Delete field '{fd.name}'")
        self._model = model
        self._fd = fd

    def execute(self) -> None:
        self._model.delete_field(self._fd.page_index, self._fd.name)

    def undo(self) -> None:
        self._model.add_field(self._fd)


class SetFieldValueCommand(Command):
    def __init__(self, model: DocumentModel, page_index: int, name: str, old_value, new_value):
        super().__init__(f"Edit field '{name}'")
        self._model = model
        self._page = page_index
        self._name = name
        self._old = old_value
        self._new = new_value

    def execute(self) -> None:
        self._model.set_field_value(self._page, self._name, self._new)

    def undo(self) -> None:
        self._model.set_field_value(self._page, self._name, self._old)
