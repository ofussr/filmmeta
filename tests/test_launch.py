"""Entry-point and dependency-boundary checks in independent processes."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from filmmeta.version import APP_NAME, VERSION

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("entry", [["run_filmmeta.py"], ["-m", "filmmeta"]])
def test_version_without_site_packages(entry):
    result = subprocess.run(
        [sys.executable, "-S", *entry, "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{APP_NAME} {VERSION}"


def test_core_imports_without_qt():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import importlib.abc
import sys

class NoQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith('PySide6'):
            raise AssertionError('Core imported Qt: ' + fullname)

sys.meta_path.insert(0, NoQt())
from filmmeta.presets import PresetStore
from filmmeta.metadata import read_one, write_one, register_namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image
register_namespace()
with TemporaryDirectory() as directory:
    directory = Path(directory)
    store = PresetStore(directory / 'library.json')
    store.save('cameras', {'manufacturer': 'KMZ', 'model': 'Zenit ET'})
    assert PresetStore(store.path).data == store.data
    image = directory / 'frame.jpg'
    Image.new('RGB', (8, 8)).save(image)
    write_one(image, {('film', 'name'): 'Headless round trip'})
    assert read_one(image).values[('film', 'name')] == 'Headless round trip'
assert not any(name.startswith('PySide6') for name in sys.modules)
""",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_real_application_startup_and_resources():
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from PySide6 import QtWidgets
from PySide6.QtCore import QTimer
from filmmeta.app import main
from filmmeta.version import VERSION
from filmmeta.ui.about import application_icon

OriginalApplication = QtWidgets.QApplication
class AutoCloseApplication(OriginalApplication):
    def exec(self):
        assert self.applicationVersion() == VERSION
        assert not application_icon().pixmap(64, 64).isNull()
        QTimer.singleShot(100, self.quit)
        return super().exec()

QtWidgets.QApplication = AutoCloseApplication
raise SystemExit(main([]))
""",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
