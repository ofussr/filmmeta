import pytest
from PySide6.QtWidgets import QApplication

from filmmeta.version import APP_NAME
from filmmeta.metadata.reader import register_namespace
from filmmeta.i18n import set_language


@pytest.fixture(scope="session", autouse=True)
def application():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName(APP_NAME)
    register_namespace()
    yield app


@pytest.fixture(autouse=True)
def reset_language():
    set_language("ru")
    yield
    set_language("ru")
