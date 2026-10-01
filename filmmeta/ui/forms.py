"""Editable forms and explicit personal-preset selection/saving."""

from ..i18n import tr
from PySide6.QtCore import Signal
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from ..fields import FORM_FIELDS
from ..presets import label


class Form(QWidget):
    edited = Signal(str)

    def __init__(self, kind):
        super().__init__()
        self.fields = {}
        self.kind = kind
        self.active_fields = {key for key, _ in FORM_FIELDS[kind]}
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for key, title in FORM_FIELDS[kind]:
            field = QLineEdit()
            field.setPlaceholderText(tr("form.unspecified"))
            field.setProperty("placeholder_key", "form.unspecified")
            field.setClearButtonEnabled(True)
            if key == "iso":
                field.setValidator(QIntValidator(1, 65535, field))
            field.textEdited.connect(lambda _text, k=key: self.edited.emit(k))
            self.fields[key] = field
            layout.addRow(tr(title), field)

    def retranslate(self):
        for key, title in FORM_FIELDS[self.kind]:
            field = self.fields[key]
            self.layout().labelForField(field).setText(tr(title))
            field.setPlaceholderText(tr(field.property("placeholder_key")))
            if field.property("mixed_value"):
                field.setToolTip(tr("form.mixed_tip"))

    def show_fields(self, fields):
        self.active_fields = set(fields)
        for key, field in self.fields.items():
            visible = key in self.active_fields
            field.setVisible(visible)
            self.layout().labelForField(field).setVisible(visible)
        return bool(self.active_fields)

    def values(self):
        return {key: field.text().strip() for key, field in self.fields.items()}

    def load(self, values, sources=None, failed=False):
        sources = sources or {}
        for key, field in self.fields.items():
            value = values.get(key, "")
            field.setText("" if value is None else str(value))
            placeholder = (
                "form.failed"
                if failed
                else "form.mixed"
                if value is None
                else "form.unspecified"
            )
            field.setProperty("placeholder_key", placeholder)
            field.setProperty("mixed_value", value is None)
            field.setPlaceholderText(tr(placeholder))
            field.setToolTip(
                tr("form.mixed_tip") if value is None else sources.get(key, "")
            )


class PresetBox(QGroupBox):
    edited = Signal(str)

    def __init__(self, library, kind, title):
        super().__init__(tr(title))
        self.title_key = title
        self.library, self.kind = (library, kind)
        layout = QVBoxLayout(self)
        self.combo = QComboBox()
        self.combo.setMinimumContentsLength(15)
        self.combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.form = Form(kind)
        save = self.save_button = QPushButton(tr("preset.save"))
        layout.addWidget(self.combo)
        layout.addWidget(self.form)
        layout.addWidget(save)
        self.combo.activated.connect(self.choose)
        self.form.edited.connect(self.manual_edit)
        save.clicked.connect(self.save)
        library.changed.connect(self.refresh)
        self.refresh()

    def retranslate(self):
        self.setTitle(tr(self.title_key))
        self.save_button.setText(tr("preset.save"))
        self.combo.setItemText(0, tr("preset.manual"))
        self.form.retranslate()

    def refresh(self):
        self.combo.clear()
        self.combo.addItem(tr("preset.manual"))
        for row in self.library.data[self.kind]:
            self.combo.addItem(label(row))

    def choose(self, index):
        if index:
            row = self.library.data[self.kind][index - 1]
            current = self.form.values()
            current.update({key: row.get(key, "") for key in self.form.active_fields})
            self.form.load(current)
            for key in self.form.active_fields:
                if current[key]:
                    self.edited.emit(key)

    def manual_edit(self, key):
        self.combo.setCurrentIndex(0)
        self.edited.emit(key)

    def save(self):
        try:
            self.library.save(self.kind, self.form.values())
            self.setToolTip(tr("preset.saved"))
        except Exception as error:
            QMessageBox.warning(self, tr("preset.title"), str(error))

    def load(self, values, sources=None, failed=False):
        self.combo.setCurrentIndex(0)
        self.form.load(values, sources, failed)


class FieldBox(QGroupBox):
    """Optional per-image fields without adding new personal-list categories."""

    edited = Signal(str)

    def __init__(self, kind, title):
        super().__init__(tr(title))
        self.title_key = title
        self.form = Form(kind)
        self.form.edited.connect(self.edited.emit)
        QVBoxLayout(self).addWidget(self.form)

    def retranslate(self):
        self.setTitle(tr(self.title_key))
        self.form.retranslate()

    def load(self, values, sources=None, failed=False):
        self.form.load(values, sources, failed)
