"""Personal-list add, edit and delete window."""

from ..i18n import tr
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from ..fields import TITLES, ROLES, DEFAULT_VISIBLE
from ..presets import label
from .forms import Form


class LibraryDialog(QDialog):
    def __init__(self, library, parent):
        super().__init__(parent)
        self.library = library
        self.setWindowTitle(tr("library.title"))
        self.resize(570, 460)
        layout = QVBoxLayout(self)
        self.kind = QComboBox()
        for key, title in TITLES.items():
            self.kind.addItem(tr(title), key)
        self.rows = QListWidget()
        layout.addWidget(self.kind)
        layout.addWidget(self.rows)
        buttons = QHBoxLayout()
        for title, callback in [
            (tr("library.add"), lambda: self.edit(False)),
            (tr("library.edit"), lambda: self.edit(True)),
            (tr("library.delete"), self.delete),
        ]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        note = QLabel(tr("library.path", path=library.path))
        note.setWordWrap(True)
        note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(note)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.button(QDialogButtonBox.StandardButton.Close).setText(tr("button.close"))
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        self.kind.currentIndexChanged.connect(self.refresh)
        library.changed.connect(self.refresh)
        self.rows.itemDoubleClicked.connect(lambda _item: self.edit(True))
        self.refresh()

    def refresh(self):
        self.rows.clear()
        for entry in self.library.data[self.kind.currentData()]:
            self.rows.addItem(label(entry))

    def edit(self, existing):
        kind = self.kind.currentData()
        index = self.rows.currentRow() if existing else None
        if existing and index < 0:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(
            tr("library.edit_title") if existing else tr("library.add_title")
        )
        layout = QVBoxLayout(dialog)
        form = Form(kind)
        # Required preset identity stays editable; optional fields follow the
        # display preferences for the corresponding equipment/film roles.
        selected = getattr(self.parent(), "settings", None)
        selected = (
            selected.data["visible_fields"] if selected is not None else DEFAULT_VISIBLE
        )
        visible = {
            field
            for field in form.fields
            if any(
                f"{role}.{field}" in selected
                for role, (role_kind, _) in ROLES.items()
                if role_kind == kind
            )
        }
        visible.update({"manufacturer", "name" if kind == "films" else "model"})
        form.show_fields(visible)
        if existing:
            form.load(self.library.data[kind][index])
        layout.addWidget(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("button.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("button.cancel")
        )
        layout.addWidget(buttons)

        def save():
            try:
                self.library.save(kind, form.values(), index)
                dialog.accept()
            except Exception as error:
                QMessageBox.warning(dialog, tr("library.entry"), str(error))

        buttons.accepted.connect(save)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()
        dialog.deleteLater()

    def delete(self):
        index = self.rows.currentRow()
        if index >= 0:
            try:
                self.library.delete(self.kind.currentData(), index)
            except Exception as error:
                QMessageBox.warning(self, tr("library.error_title"), str(error))
