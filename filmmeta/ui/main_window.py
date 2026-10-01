"""Main workspace, selection state and background read/write coordination."""

from ..i18n import tr, set_language
import json
import os
from pathlib import Path
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from ..version import APP_NAME, VERSION
from ..fields import ROLES, FIELDS
from ..settings import Settings
from ..fileio import EXTENSIONS
from ..metadata.reader import read_files
from ..metadata.writer import write_files
from ..metadata.schema import EXIF_FIELDS, first_value
from .about import show_about
from .forms import PresetBox, FieldBox
from .library_dialog import LibraryDialog
from .workers import Job
from .settings_dialog import SettingsDialog
from .theme import apply_theme


class Window(QMainWindow):
    def __init__(self, library, settings=None):
        super().__init__()
        self.library = library
        self.settings = settings or Settings(library.path.with_name("settings.json"))
        set_language(self.settings.data["language"])
        apply_theme(QApplication.instance(), self.settings.data["theme"])
        self.job = None
        self.mode = ""
        self.stamp = 0
        self.pending_read = False
        self.read_ok = False
        self.dirty = set()
        self.raw = {}
        self.metadata = {}
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(1140, 850)
        self.setMinimumSize(800, 600)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        toolbar = QHBoxLayout()
        self.add_button = QPushButton(tr("window.open"))
        self.remove_button = QPushButton(tr("window.remove"))
        self.book_button = QPushButton(tr("window.library"))
        self.inspect_button = QPushButton(tr("window.inspect"))
        for button in [
            self.add_button,
            self.remove_button,
            self.book_button,
            self.inspect_button,
        ]:
            toolbar.addWidget(button)
        outer.addLayout(toolbar)
        splitter = QSplitter()
        outer.addWidget(splitter, 1)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.files = QTreeWidget()
        self.files.setHeaderLabels([tr("window.file"), tr("window.state")])
        self.files.setRootIsDecorated(False)
        self.files.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.files.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        left_layout.addWidget(self.files, 1)
        self.selection_label = QLabel(tr("window.selected", count=0))
        left_layout.addWidget(self.selection_label)
        overview = self.overview_group = QGroupBox(tr("window.overview"))
        overview_layout = QFormLayout(overview)
        self.overview = {}
        for tag, title in [
            ("Exif.Image.Make", tr("field.manufacturer")),
            ("Exif.Image.Model", tr("field.model")),
            ("Exif.Photo.LensModel", tr("window.lens")),
            ("Exif.Photo.ISOSpeedRatings", tr("field.iso")),
        ]:
            field = QLineEdit()
            field.setReadOnly(True)
            field.setPlaceholderText(tr("form.unspecified"))
            overview_layout.addRow(title, field)
            self.overview[tag] = field
        left_layout.addWidget(overview)
        self.info = QLabel(tr("window.open_info"))
        self.info_key = "window.open_info"
        self.info.setWordWrap(True)
        left_layout.addWidget(self.info)
        splitter.addWidget(left)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.editor = QWidget()
        editor_layout = QVBoxLayout(self.editor)
        self.boxes = {}
        self.add_box("film", editor_layout)
        self.add_box("exposure", editor_layout)
        self.add_box("development", editor_layout)
        original_row = QHBoxLayout()
        for role in ["camera", "lens"]:
            self.add_box(role, original_row)
        editor_layout.addLayout(original_row)
        digitization = self.digitization_group = QGroupBox(tr("window.method"))
        digit_layout = QVBoxLayout(digitization)
        self.method = QComboBox()
        for title, value in [
            (tr("method.unspecified"), ""),
            (tr("method.scan"), "scan"),
            (tr("method.camera"), "camera"),
            (tr("form.mixed"), "__mixed__"),
        ]:
            self.method.addItem(title, value)
        digit_layout.addWidget(self.method)
        self.add_box("scanner", digit_layout)
        copy_row = QHBoxLayout()
        for role in ["copy_camera", "copy_lens"]:
            self.add_box(role, copy_row)
        digit_layout.addLayout(copy_row)
        editor_layout.addWidget(digitization)
        self.standard = QCheckBox(tr("window.standard"))
        self.standard.setChecked(self.settings.data["standard_exif"])
        self.standard.toggled.connect(self.save_standard_preference)
        self.standard.setToolTip(tr("window.standard_tip"))
        editor_layout.addWidget(self.standard)
        note = self.edit_note = QLabel(tr("window.edit_note"))
        note.setWordWrap(True)
        editor_layout.addWidget(note)
        editor_layout.addStretch()
        scroll.setWidget(self.editor)
        splitter.addWidget(scroll)
        splitter.setSizes([400, 740])
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.log.setPlaceholderText(tr("window.log"))
        outer.addWidget(self.log)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        outer.addWidget(self.progress)
        bottom = QHBoxLayout()
        self.reset_button = QPushButton(tr("window.reload"))
        self.cancel_button = QPushButton(tr("window.cancel"))
        self.cancel_button.setEnabled(False)
        self.write_button = QPushButton(tr("window.write"))
        self.write_button.setEnabled(False)
        for button in [self.reset_button, self.cancel_button, self.write_button]:
            bottom.addWidget(button)
        outer.addLayout(bottom)
        self.add_button.clicked.connect(self.add_files)
        self.remove_button.clicked.connect(self.remove_files)
        self.book_button.clicked.connect(self.open_library)
        self.inspect_button.clicked.connect(self.inspect)
        self.files.itemSelectionChanged.connect(self.request_read)
        self.method.currentIndexChanged.connect(self.update_visibility)
        self.method.activated.connect(lambda _index: self.mark_dirty("method"))
        self.reset_button.clicked.connect(self.request_read)
        self.cancel_button.clicked.connect(self.cancel)
        self.write_button.clicked.connect(self.write)
        self.settings_action = QAction(tr("menu.settings"), self)
        self.settings_action.triggered.connect(self.open_settings)
        self.menuBar().addAction(self.settings_action)
        help_menu = self.help_menu = self.menuBar().addMenu(tr("menu.help"))
        about = self.about_action = QAction(tr("menu.about"), self)
        about.triggered.connect(self.about)
        help_menu.addAction(about)
        self.update_visibility()
        self.update_write_button()

    def add_box(self, role, layout):
        kind, title = ROLES[role]
        box = (
            PresetBox(self.library, kind, title)
            if kind in FIELDS
            else FieldBox(kind, title)
        )
        box.edited.connect(lambda key, r=role: self.mark_dirty((r, key)))
        self.boxes[role] = box
        layout.addWidget(box)

    @Slot()
    def open_library(self):
        dialog = LibraryDialog(self.library, self)
        dialog.exec()
        dialog.deleteLater()

    @Slot()
    def about(self):
        show_about(self)

    @Slot()
    def open_settings(self):
        if self.job is not None:
            return
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_preferences()
        dialog.deleteLater()

    def apply_preferences(self):
        set_language(self.settings.data["language"])
        apply_theme(QApplication.instance(), self.settings.data["theme"])
        self.standard.blockSignals(True)
        self.standard.setChecked(self.settings.data["standard_exif"])
        self.standard.blockSignals(False)
        self.retranslate()
        self.update_visibility()
        self.update_write_button()

    def save_standard_preference(self, checked):
        try:
            self.settings.save({**self.settings.data, "standard_exif": checked})
        except Exception as error:
            self.standard.blockSignals(True)
            self.standard.setChecked(self.settings.data["standard_exif"])
            self.standard.blockSignals(False)
            QMessageBox.warning(self, tr("settings.title"), str(error))

    def set_info(self, key):
        self.info_key = key
        self.info.setText(tr(key))

    def retranslate(self):
        for widget, key in [
            (self.add_button, "window.open"),
            (self.remove_button, "window.remove"),
            (self.book_button, "window.library"),
            (self.inspect_button, "window.inspect"),
            (self.reset_button, "window.reload"),
            (self.cancel_button, "window.cancel"),
            (self.write_button, "window.write"),
            (self.standard, "window.standard"),
            (self.edit_note, "window.edit_note"),
            (self.settings_action, "menu.settings"),
            (self.about_action, "menu.about"),
        ]:
            widget.setText(tr(key))
        self.help_menu.setTitle(tr("menu.help"))
        self.overview_group.setTitle(tr("window.overview"))
        self.digitization_group.setTitle(tr("window.method"))
        self.standard.setToolTip(tr("window.standard_tip"))
        self.log.setPlaceholderText(tr("window.log"))
        self.files.setHeaderLabels([tr("window.file"), tr("window.state")])
        self.selection_label.setText(tr("window.selected", count=len(self.paths())))
        self.set_info(self.info_key)
        for index, key in enumerate(
            ("method.unspecified", "method.scan", "method.camera", "form.mixed")
        ):
            self.method.setItemText(index, tr(key))
        for box in self.boxes.values():
            box.retranslate()
        for field, key in zip(
            self.overview.values(),
            ("field.manufacturer", "field.model", "window.lens", "field.iso"),
        ):
            self.overview_group.layout().labelForField(field).setText(tr(key))
            field.setPlaceholderText(
                tr(field.property("placeholder_key") or "form.unspecified")
            )
        for index in range(self.files.topLevelItemCount()):
            item = self.files.topLevelItem(index)
            key = item.data(1, Qt.ItemDataRole.UserRole)
            if key:
                item.setText(1, tr(key))
                if key == "window.read":
                    item.setToolTip(1, tr("window.read_tip"))
        self.statusBar().showMessage(
            tr("window.changed", count=len(self.dirty))
            if self.dirty
            else tr("window.done")
        )

    def mark_dirty(self, key):
        self.dirty.add(key)
        self.update_write_button()

    def update_visibility(self, *_args):
        method = self.method.currentData()
        selected = set(self.settings.data["visible_fields"])
        for role, box in self.boxes.items():
            visible = box.form.show_fields(
                {field for field in box.form.fields if f"{role}.{field}" in selected}
            )
            if role == "scanner":
                visible = visible and method in {"scan", "__mixed__"}
            elif role in {"copy_camera", "copy_lens"}:
                visible = visible and method in {"camera", "__mixed__"}
            box.setVisible(visible)
        self.dirty = {
            key
            for key in self.dirty
            if key == "method" or f"{key[0]}.{key[1]}" in selected
        }

    def paths(self):
        return [
            Path(item.data(0, Qt.ItemDataRole.UserRole))
            for item in self.files.selectedItems()
        ]

    def file_item(self, path):
        for i in range(self.files.topLevelItemCount()):
            item = self.files.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == str(path):
                return item
        return None

    def add_paths(self, names):
        known = {
            os.path.normcase(
                self.files.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
            )
            for i in range(self.files.topLevelItemCount())
        }
        self.files.blockSignals(True)
        try:
            for name in names:
                path = Path(os.path.abspath(os.fspath(name)))
                if path.suffix.lower() not in EXTENSIONS:
                    self.log.appendPlainText(tr("window.skipped", name=path.name))
                    continue
                canonical = os.path.normcase(str(path))
                if canonical in known:
                    continue
                known.add(canonical)
                item = QTreeWidgetItem([path.name, tr("window.waiting")])
                item.setData(1, Qt.ItemDataRole.UserRole, "window.waiting")
                item.setData(0, Qt.ItemDataRole.UserRole, str(path))
                item.setToolTip(0, str(path))
                self.files.addTopLevelItem(item)
            if names:
                self.files.selectAll()
        finally:
            self.files.blockSignals(False)
        self.request_read()

    @Slot()
    def add_files(self):
        names, _filter = QFileDialog.getOpenFileNames(
            self, tr("window.open_title"), "", tr("window.filter")
        )
        if names:
            self.add_paths(names)

    @Slot()
    def remove_files(self):
        self.files.blockSignals(True)
        try:
            for item in self.files.selectedItems():
                self.files.takeTopLevelItem(self.files.indexOfTopLevelItem(item))
        finally:
            self.files.blockSignals(False)
        self.request_read()

    @Slot()
    def request_read(self):
        self.stamp += 1
        self.pending_read = True
        self.read_ok = False
        self.write_button.setEnabled(False)
        self.editor.setEnabled(False)
        self.selection_label.setText(tr("window.selected", count=len(self.paths())))
        if self.job is not None and self.mode == "read":
            self.job.requestInterruption()
        if self.job is None:
            self.start_read()

    def start_read(self):
        self.pending_read = False
        self.dirty.clear()
        paths, stamp = (self.paths(), self.stamp)
        self.raw, self.metadata = ({}, {})
        if not paths:
            self.load_values({})
            self.editor.setEnabled(True)
            self.set_info("window.select_info")
            self.update_write_button()
            return
        self.begin(
            "read",
            lambda progress, cancelled: read_files(paths, progress, cancelled),
            lambda result: self.loaded(result, stamp),
            len(paths),
        )

    def loaded(self, result, stamp):
        if stamp != self.stamp:
            return
        entries, errors = result
        self.read_ok = (
            bool(entries) and (not errors) and (len(entries) == len(self.paths()))
        )
        self.metadata = {str(entry.path): entry for entry in entries}
        self.raw = {
            str(entry.path): {"EXIF": entry.exif, "XMP": entry.xmp} for entry in entries
        }
        combined, sources = ({}, {})
        if entries:
            for key in entries[0].values:
                values = {entry.values[key] for entry in entries}
                combined[key] = next(iter(values)) if len(values) == 1 else None
                tags = {entry.sources.get(key, "") for entry in entries} - {""}
                sources[key] = ", ".join(sorted(tags))
        self.load_values(combined, sources, failed=bool(errors))
        for entry in entries:
            item = self.file_item(entry.path)
            if item:
                item.setText(1, tr("window.read"))
                item.setData(1, Qt.ItemDataRole.UserRole, "window.read")
                item.setToolTip(1, tr("window.read_tip"))
        for path, error in errors.items():
            item = self.file_item(path)
            if item:
                item.setText(1, tr("form.failed"))
                item.setData(1, Qt.ItemDataRole.UserRole, "form.failed")
                item.setToolTip(1, error)
            self.log.appendPlainText(
                tr("window.read_error_log", path=path, error=error)
            )
        if errors:
            self.set_info("window.read_failed")
        elif not self.read_ok:
            self.set_info("window.read_stopped")
        elif any((entry.is_dng for entry in entries)):
            self.set_info("window.dng_info")
        else:
            self.set_info("window.fallback_info")
        self.load_overview(entries)

    def load_overview(self, entries):
        for tag, field in self.overview.items():
            values = set()
            key = next(
                (key for key, exif_tag in EXIF_FIELDS.items() if exif_tag == tag)
            )
            for entry in entries:
                values.add(first_value(entry.exif, entry.xmp, key)[0])
            field.setText(next(iter(values)) if len(values) == 1 else "")
            field.setProperty(
                "placeholder_key",
                "form.mixed" if len(values) > 1 else "form.unspecified",
            )
            field.setPlaceholderText(
                tr("form.mixed") if len(values) > 1 else tr("form.unspecified")
            )

    def load_values(self, values, sources=None, failed=False):
        sources = sources or {}
        for role, box in self.boxes.items():
            box.load(
                {key: values.get((role, key), "") for key in box.form.fields},
                {key: sources.get((role, key), "") for key in box.form.fields},
                failed,
            )
        method = values.get("method", "")
        index = self.method.findData("__mixed__" if method is None else method)
        self.method.setCurrentIndex(max(index, 0))
        self.dirty.clear()
        if not values:
            self.load_overview([])

    def update_write_button(self):
        self.write_button.setEnabled(
            bool(self.dirty) and self.read_ok and (self.job is None)
        )
        self.reset_button.setEnabled(bool(self.paths()) and self.job is None)
        if self.dirty and self.job is None:
            self.statusBar().showMessage(tr("window.changed", count=len(self.dirty)))

    def begin(self, mode, function, callback, count):
        self.mode = mode
        self.settings_action.setEnabled(False)
        self.editor.setEnabled(False)
        for button in [self.write_button, self.inspect_button, self.reset_button]:
            button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, count)
        self.progress.setValue(0)
        if mode == "write":
            for widget in [self.files, self.add_button, self.remove_button]:
                widget.setEnabled(False)
        self.job = Job(function, self)
        self.job.result.connect(callback)
        self.job.failed.connect(self.failure)
        self.job.progress.connect(self.show_progress)
        self.job.finished.connect(self.job_finished)
        self.job.start()

    @Slot(int, str)
    def show_progress(self, value, text):
        self.progress.setValue(value)
        self.statusBar().showMessage(text)

    @Slot(str)
    def failure(self, error):
        self.read_ok = False
        self.log.appendPlainText(tr("window.error_log", error=error))

    @Slot()
    def cancel(self):
        if self.job is not None:
            self.job.requestInterruption()
            self.cancel_button.setEnabled(False)

    @Slot()
    def job_finished(self):
        mode, job = (self.mode, self.job)
        cancelled = job.isInterruptionRequested()
        self.job = None
        self.settings_action.setEnabled(True)
        job.deleteLater()
        for widget in [
            self.files,
            self.add_button,
            self.remove_button,
            self.inspect_button,
            self.editor,
        ]:
            widget.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.statusBar().showMessage(
            tr("window.stopped") if cancelled else tr("window.done")
        )
        if mode == "write" and cancelled:
            self.log.appendPlainText(tr("window.write_stopped"))
        if mode == "write":
            self.request_read()
        elif self.pending_read:
            self.start_read()
        else:
            self.update_write_button()

    def collect_patch(self):
        patch = {}
        method = self.method.currentData()
        for key in self.dirty:
            if key == "method":
                if method in {"scan", "camera"}:
                    patch[key] = method
                continue
            role, field = key
            if f"{role}.{field}" not in self.settings.data["visible_fields"]:
                continue
            if role == "scanner" and method not in {"scan", "__mixed__"}:
                continue
            if role in {"copy_camera", "copy_lens"} and method not in {
                "camera",
                "__mixed__",
            }:
                continue
            value = self.boxes[role].form.values()[field]
            if value:
                patch[key] = value
        return patch

    @Slot()
    def write(self):
        patch = self.collect_patch()
        if not patch:
            self.statusBar().showMessage(tr("error.empty"))
            return
        iso = patch.get(("film", "iso"))
        if iso and (not iso.isdecimal() or not 1 <= int(iso) <= 65535):
            QMessageBox.warning(self, tr("field.iso"), tr("error.iso"))
            return
        paths, standard = (self.paths(), self.standard.isChecked())
        analog = self.settings.data["analog_exif"]
        if self.job is not None or not self.read_ok:
            return
        methods = {path: self.metadata[str(path)].values["method"] for path in paths}

        def run(progress, cancelled):
            return write_files(
                paths,
                patch,
                standard,
                progress,
                cancelled,
                methods=methods,
                analog_exif=analog,
            )

        self.begin("write", run, self.written, len(paths))

    def written(self, results):
        for path, ok, message in results:
            self.log.appendPlainText(
                tr(
                    "window.result_log",
                    state=tr("window.done") if ok else tr("window.error"),
                    path=path,
                    message=message,
                )
            )

    @Slot()
    def inspect(self):
        paths = self.paths()
        if not paths or str(paths[0]) not in self.raw:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("window.metadata", name=paths[0].name))
        dialog.resize(850, 650)
        layout = QVBoxLayout(dialog)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(
            json.dumps(self.raw[str(paths[0])], ensure_ascii=False, indent=2)
        )
        layout.addWidget(text)
        dialog.exec()
        dialog.deleteLater()

    def closeEvent(self, event):
        if self.job is not None:
            self.statusBar().showMessage(tr("window.busy"))
            event.ignore()
        else:
            event.accept()
