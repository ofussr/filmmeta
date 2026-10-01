"""Preferences, live translations and hidden-field write boundaries."""

import json
import string

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog

from filmmeta.fields import DEFAULT_VISIBLE, FIELD_IDS
from filmmeta.i18n import CATALOGS, tr
from filmmeta.metadata.reader import read_one
from filmmeta.settings import Settings
from filmmeta.ui.library import Library
from filmmeta.ui.main_window import Window
from filmmeta.ui.settings_dialog import SettingsDialog
from .helpers import modify, picture, wait_job


def test_preferences_defaults_roundtrip_and_failed_commit(tmp_path, monkeypatch):
    settings = Settings(tmp_path / "settings.json")
    assert settings.data["language"] == "ru"
    assert settings.data["theme"] == "light"
    assert not settings.data["analog_exif"] and not settings.data["standard_exif"]
    assert settings.data["visible_fields"] == DEFAULT_VISIBLE
    settings.save(
        {
            **settings.data,
            "language": "en",
            "theme": "dark",
            "analog_exif": True,
            "visible_fields": ["film.name", "film.alias"],
        }
    )
    assert Settings(settings.path).data == settings.data
    before = settings.path.read_bytes()
    import filmmeta.settings as module

    monkeypatch.setattr(
        module.os,
        "replace",
        lambda *_: (_ for _ in ()).throw(PermissionError("blocked")),
    )
    with pytest.raises(PermissionError):
        settings.save({**settings.data, "theme": "light"})
    assert settings.path.read_bytes() == before
    assert settings.data["theme"] == "dark"


@pytest.mark.parametrize(
    "value",
    [
        {"language": "xx"},
        {"theme": "xx"},
        {"analog_exif": "false"},
        {"visible_fields": "film.name"},
    ],
)
def test_invalid_settings_not_overwritten(tmp_path, value):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(value))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        Settings(path)
    assert path.read_bytes() == before


def test_catalogues_have_identical_keys_and_format_parameters():
    assert set(CATALOGS["ru"]) == set(CATALOGS["en"])
    formatter = string.Formatter()
    for key in CATALOGS["ru"]:
        fields = [
            {
                field
                for _, field, _, _ in formatter.parse(CATALOGS[language][key])
                if field is not None
            }
            for language in ("ru", "en")
        ]
        assert fields[0] == fields[1], key


def test_live_language_theme_preserve_selection_values_and_edits(tmp_path, application):
    path = picture(tmp_path)
    modify(path, xmp={"Xmp.fm.FilmName": "Existing film"})
    window = Window(Library(tmp_path / "library.json"))
    window.show()
    window.add_paths([path])
    wait_job(window, application)
    name = window.boxes["film"].form.fields["name"]
    name.selectAll()
    QTest.keyClicks(name, "Pending film")
    dirty = set(window.dirty)
    window.settings.save({**window.settings.data, "language": "en", "theme": "dark"})
    window.apply_preferences()
    assert name.text() == "Pending film"
    assert window.dirty == dirty
    assert window.paths() == [path]
    assert window.add_button.text() == "Open files…"
    assert window.boxes["film"].title() == "Film"
    assert window.boxes["film"].form.layout().labelForField(name).text() == "Name"
    assert window.files.topLevelItem(0).text(1) == "Read"
    assert window.write_button.isEnabled()
    assert application.palette().color(QPalette.ColorRole.Window).lightness() < 80
    window.settings.save({**window.settings.data, "language": "ru", "theme": "light"})
    window.apply_preferences()
    assert name.text() == "Pending film" and window.dirty == dirty
    assert window.add_button.text() == "Открыть файлы…"
    assert application.palette().color(QPalette.ColorRole.Window).lightness() > 200
    window.close()


def test_hidden_fields_are_read_preserved_and_excluded_from_preset(
    tmp_path, application
):
    path = picture(tmp_path)
    modify(
        path,
        xmp={
            "Xmp.fm.FilmAlias": "Keep own alias",
            "Xmp.AnalogExif.FilmAlias": "Keep shared alias",
        },
    )
    library = Library(tmp_path / "library.json")
    library.save(
        "films", {"manufacturer": "Kodak", "name": "Portra", "alias": "Preset alias"}
    )
    window = Window(library)
    window.show()
    window.add_paths([path])
    wait_job(window, application)
    box = window.boxes["film"]
    assert box.form.fields["alias"].isHidden()
    assert box.form.fields["alias"].text() == "Keep own alias"
    assert window.boxes["exposure"].isHidden()
    box.choose(1)
    assert ("film", "alias") not in window.dirty
    assert box.form.fields["alias"].text() == "Keep own alias"
    window.write()
    wait_job(window, application)
    result = read_one(path)
    assert result.xmp["Xmp.fm.FilmAlias"] == "Keep own alias"
    assert result.xmp["Xmp.AnalogExif.FilmAlias"] == "Keep shared alias"
    window.settings.save(
        {**window.settings.data, "visible_fields": [*DEFAULT_VISIBLE, "film.alias"]}
    )
    window.apply_preferences()
    field = box.form.fields["alias"]
    assert not field.isHidden()
    field.selectAll()
    QTest.keyClicks(field, "New alias")
    window.write()
    wait_job(window, application)
    assert read_one(path).xmp["Xmp.fm.FilmAlias"] == "New alias"
    assert read_one(path).xmp["Xmp.AnalogExif.FilmAlias"] == "Keep shared alias"
    window.close()


def test_hiding_pending_field_excludes_it_and_keeps_other_edits(tmp_path, application):
    path = picture(tmp_path)
    window = Window(Library(tmp_path / "library.json"))
    window.add_paths([path])
    wait_job(window, application)
    QTest.keyClicks(window.boxes["film"].form.fields["name"], "New name")
    QTest.keyClicks(window.boxes["film"].form.fields["process"], "C-41")
    window.settings.save(
        {
            **window.settings.data,
            "visible_fields": [key for key in DEFAULT_VISIBLE if key != "film.process"],
        }
    )
    window.apply_preferences()
    assert window.collect_patch() == {("film", "name"): "New name"}
    window.write()
    wait_job(window, application)
    assert "Xmp.fm.FilmProcess" not in read_one(path).xmp
    window.close()


def test_settings_dialog_cancel_defaults_all_and_accepted_ui_write(
    tmp_path, application
):
    path = picture(tmp_path)
    window = Window(Library(tmp_path / "library.json"))
    dialog = SettingsDialog(window.settings, window)
    assert set(dialog.values()["visible_fields"]) == set(DEFAULT_VISIBLE)
    dialog.select_fields(FIELD_IDS)
    assert set(dialog.values()["visible_fields"]) == FIELD_IDS
    dialog.reject()
    assert not window.settings.path.exists()
    dialog = SettingsDialog(window.settings, window)
    dialog.analog.setChecked(True)
    dialog.field_items["film.alias"].setCheckState(0, Qt.CheckState.Checked)
    dialog.save()
    assert dialog.result() == QDialog.DialogCode.Accepted
    window.apply_preferences()
    window.add_paths([path])
    wait_job(window, application)
    QTest.keyClicks(window.boxes["film"].form.fields["alias"], "RVP 50")
    window.write()
    wait_job(window, application)
    result = read_one(path)
    assert result.xmp["Xmp.fm.FilmAlias"] == "RVP 50"
    assert result.xmp["Xmp.AnalogExif.FilmAlias"] == "RVP 50"
    assert Settings(window.settings.path).data["analog_exif"]
    window.close()
