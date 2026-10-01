"""Qt notification and per-user path adapter for the JSON preset store."""

from pathlib import Path

from PySide6.QtCore import QObject, QStandardPaths, Signal

from ..presets import PresetStore


class Library(QObject):
    changed = Signal()

    def __init__(self, path=None):
        super().__init__()
        directory = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        self.store = PresetStore(
            path or Path(directory) / "library.json", on_change=self.changed.emit
        )

    @property
    def path(self):
        return self.store.path

    @property
    def data(self):
        return self.store.data

    def save(self, kind, entry, index=None):
        self.store.save(kind, entry, index)

    def delete(self, kind, index):
        self.store.delete(kind, index)
