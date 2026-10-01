"""Application identity and runtime/component information."""

import platform
from importlib.resources import files

import pyexiv2
from PySide6.QtCore import qVersion
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox

from ..version import APP_NAME, VERSION, AUTHOR, EMAIL
from ..i18n import tr


def application_icon():
    return QIcon(str(files("filmmeta.resources").joinpath("filmmeta.svg")))


def show_about(parent):
    message = QMessageBox(parent)
    message.setWindowTitle(tr("about.title"))
    message.setIconPixmap(application_icon().pixmap(96, 96))
    message.setText(f"{APP_NAME} {VERSION}")
    message.setInformativeText(
        tr("about.summary") + "\n\n" + f"{AUTHOR}\n{EMAIL}\n\n"
        f"Python {platform.python_version()} · Qt {qVersion()}\n"
        f"pyexiv2 {pyexiv2.__version__} · Exiv2 {pyexiv2.__exiv2_version__}"
    )
    message.setDetailedText(
        files("filmmeta.resources")
        .joinpath("THIRD_PARTY_NOTICES.txt")
        .read_text(encoding="utf-8")
    )
    message.setStandardButtons(QMessageBox.StandardButton.Ok)
    message.button(QMessageBox.StandardButton.Ok).setText(tr("button.ok"))
    # QMessageBox's details button is a Qt-owned control, so supply our own text.
    details = next(
        (
            button
            for button in message.buttons()
            if message.buttonRole(button) == QMessageBox.ButtonRole.ActionRole
        ),
        None,
    )
    if details is not None:
        details.setText(tr("about.details"))
        expanded = False

        def translate_toggle():
            nonlocal expanded
            expanded = not expanded
            details.setText(tr("about.hide_details" if expanded else "about.details"))

        details.clicked.connect(translate_toggle)
    message.exec()
