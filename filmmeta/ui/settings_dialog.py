"""Writing, language, theme and per-field display preferences."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from ..fields import DEFAULT_VISIBLE, FORM_FIELDS, ROLES
from ..i18n import LANGUAGES, tr


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(tr("settings.title"))
        self.resize(650, 740)
        outer = QVBoxLayout(self)
        form = QFormLayout()
        self.language = QComboBox()
        for key, label in LANGUAGES.items():
            self.language.addItem(label, key)
        self.language.setCurrentIndex(self.language.findData(settings.data["language"]))
        form.addRow(tr("settings.language"), self.language)
        self.theme = QComboBox()
        for key in ("light", "dark"):
            self.theme.addItem(tr("settings." + key), key)
        self.theme.setCurrentIndex(self.theme.findData(settings.data["theme"]))
        form.addRow(tr("settings.theme"), self.theme)
        outer.addLayout(form)
        self.analog = QCheckBox(tr("settings.analog"))
        self.analog.setChecked(settings.data["analog_exif"])
        outer.addWidget(self.analog)
        self.standard = QCheckBox(tr("window.standard"))
        self.standard.setChecked(settings.data["standard_exif"])
        outer.addWidget(self.standard)
        for key in ("settings.policy", "settings.fields_note"):
            note = QLabel(tr(key))
            note.setWordWrap(True)
            outer.addWidget(note)
        self.fields = QTreeWidget()
        self.fields.setHeaderLabels([tr("settings.fields")])
        self.field_items = {}
        selected = set(settings.data["visible_fields"])
        for role, (kind, title) in ROLES.items():
            group = QTreeWidgetItem([tr(title)])
            group.setSizeHint(0, QSize(0, 22))
            group.setFlags(
                group.flags()
                | Qt.ItemFlag.ItemIsAutoTristate
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            self.fields.addTopLevelItem(group)
            for name, label in FORM_FIELDS[kind]:
                key = f"{role}.{name}"
                item = QTreeWidgetItem(group, [tr(label)])
                item.setSizeHint(0, QSize(0, 22))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    0,
                    Qt.CheckState.Checked
                    if key in selected
                    else Qt.CheckState.Unchecked,
                )
                self.field_items[key] = item
        self.fields.expandAll()
        outer.addWidget(self.fields, 1)
        controls = QHBoxLayout()
        for key, selected in [
            ("settings.defaults", DEFAULT_VISIBLE),
            ("settings.all", self.field_items),
        ]:
            button = QPushButton(tr(key))
            button.clicked.connect(
                lambda _checked=False, values=selected: self.select_fields(values)
            )
            controls.addWidget(button)
        outer.addLayout(controls)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("button.save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            tr("button.cancel")
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def select_fields(self, selected):
        for key, item in self.field_items.items():
            item.setCheckState(
                0, Qt.CheckState.Checked if key in selected else Qt.CheckState.Unchecked
            )

    def values(self):
        return {
            "language": self.language.currentData(),
            "theme": self.theme.currentData(),
            "analog_exif": self.analog.isChecked(),
            "standard_exif": self.standard.isChecked(),
            "visible_fields": [
                key
                for key, item in self.field_items.items()
                if item.checkState(0) == Qt.CheckState.Checked
            ],
        }

    def save(self):
        try:
            self.settings.save(self.values())
        except Exception as error:
            QMessageBox.warning(self, tr("settings.title"), str(error))
            return
        self.accept()
