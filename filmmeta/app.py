"""Command-line parsing and Qt application startup."""

import argparse
import sys

from .version import APP_NAME, VERSION


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        description="Film photograph metadata and personal presets."
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    parser.parse_args(argv)

    # Keep --version usable without importing Qt or the native metadata engine.
    from PySide6.QtWidgets import QApplication, QMessageBox
    from .metadata.reader import register_namespace
    from .ui.library import Library
    from .ui.main_window import Window
    from .ui.about import application_icon

    app = QApplication([sys.argv[0], *argv])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(application_icon())
    try:
        register_namespace()
        library = Library()
        window = Window(library)
    except Exception as error:
        QMessageBox.critical(None, APP_NAME, str(error))
        return 1
    window.show()
    return app.exec()
