import time

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from filmmeta.metadata import reader
from filmmeta.metadata.reader import read_one
from filmmeta.metadata.writer import write_one
from filmmeta.ui.main_window import Window
from filmmeta.ui.library import Library
from filmmeta.version import VERSION, AUTHOR, EMAIL
from .helpers import modify, picture, wait_job


def test_gui_existing_and_mixed_values_edited_only(tmp_path, application):
    p1 = picture(tmp_path / "first")
    p2 = picture(tmp_path / "second")
    modify(
        p1,
        exif={
            "Exif.Image.Make": "Fujifilm",
            "Exif.Image.Model": "Digital Link",
            "Exif.Photo.ISOSpeedRatings": "400",
        },
    )
    modify(
        p2,
        exif={
            "Exif.Image.Make": "Fujifilm",
            "Exif.Image.Model": "Other model",
            "Exif.Photo.ISOSpeedRatings": "400",
        },
    )
    window = Window(Library(tmp_path / "library.json"))
    window.show()
    window.add_paths([p1, p2])
    wait_job(window, application)
    assert window.read_ok
    assert not window.dirty and not window.write_button.isEnabled()
    assert window.boxes["camera"].form.fields["manufacturer"].text() == "Fujifilm"
    model = window.boxes["camera"].form.fields["model"]
    assert model.text() == "" and model.placeholderText() == "Разные значения"
    assert window.boxes["film"].form.fields["iso"].text() == "400"
    field = window.boxes["film"].form.fields["process"]
    QTest.keyClicks(field, "C-41")
    assert window.dirty == {("film", "process")}
    window.write()
    wait_job(window, application)
    assert read_one(p1).exif["Exif.Image.Model"] == "Digital Link"
    assert read_one(p2).exif["Exif.Image.Model"] == "Other model"
    assert read_one(p1).values[("film", "process")] == "C-41"
    assert read_one(p2).values[("film", "process")] == "C-41"
    assert not window.dirty
    window.close()


def test_gui_bad_file_state_and_preset_save(tmp_path, application):
    path = tmp_path / "missing.TIF"
    library = Library(tmp_path / "library.json")
    window = Window(library)
    window.add_paths([path])
    wait_job(window, application)
    assert not window.read_ok
    assert window.files.topLevelItem(0).text(1) == "Ошибка чтения"
    assert not window.write_button.isEnabled()
    box = window.boxes["camera"]
    box.form.load({"manufacturer": "KMZ", "model": "Zenit ET"})
    box.save()
    assert library.data["cameras"] == [{"manufacturer": "KMZ", "model": "Zenit ET"}]
    assert box.combo.count() == 2
    window.close()


def test_about_has_application_version_and_author(tmp_path, monkeypatch):
    window = Window(Library(tmp_path / "library.json"))
    captured = []

    def capture(dialog):
        captured.append(
            dialog.text() + dialog.informativeText() + dialog.detailedText()
        )
        assert not dialog.iconPixmap().isNull()
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "exec", capture)
    window.about()
    assert VERSION in captured[0] and AUTHOR in captured[0]
    assert "pyexiv2" in captured[0] and EMAIL in captured[0]
    assert "Third-party" in captured[0]
    window.close()


def test_gui_selection_changes_during_read_do_not_load_stale_values(
    tmp_path, application, monkeypatch
):
    p1 = picture(tmp_path / "first")
    p2 = picture(tmp_path / "second")
    modify(p1, exif={"Exif.Image.Model": "First"})
    modify(p2, exif={"Exif.Image.Model": "Second"})
    original = read_one

    def delayed(path):
        time.sleep(0.03)
        return original(path)

    monkeypatch.setattr(reader, "read_one", delayed)
    window = Window(Library(tmp_path / "library.json"))
    window.add_paths([p1, p2])
    window.files.clearSelection()
    window.files.topLevelItem(1).setSelected(True)
    wait_job(window, application)
    assert window.read_ok
    assert window.boxes["camera"].form.fields["model"].text() == "Second"
    window.close()


def test_mixed_digitisation_edits_only_applicable_files(tmp_path, application):
    scan = picture(tmp_path / "scan")
    camera = picture(tmp_path / "camera")
    write_one(scan, {"method": "scan", ("scanner", "model"): "Old scanner"})
    write_one(
        camera, {"method": "camera", ("copy_camera", "model"): "Reproduction camera"}
    )
    camera_before = camera.read_bytes()
    window = Window(Library(tmp_path / "library.json"))
    window.add_paths([scan, camera])
    wait_job(window, application)
    assert window.method.currentData() == "__mixed__"
    field = window.boxes["scanner"].form.fields["model"]
    QTest.keyClicks(field, "New scanner")
    window.write()
    wait_job(window, application)
    assert read_one(scan).values[("scanner", "model")] == "New scanner"
    assert camera.read_bytes() == camera_before
    window.close()


def test_gui_loads_analogexif_and_edits_shared_field(tmp_path, application):
    path = picture(tmp_path)
    modify(
        path,
        xmp={
            "Xmp.AnalogExif.FilmMaker": "Kodak",
            "Xmp.AnalogExif.Film": "Kodak Portra 400",
            "Xmp.AnalogExif.ScannerMaker": "Epson",
            "Xmp.AnalogExif.Scanner": "Epson V850",
        },
    )
    window = Window(Library(tmp_path / "library.json"))
    window.add_paths([path])
    wait_job(window, application)
    assert window.boxes["film"].form.fields["name"].text() == "Portra 400"
    assert window.boxes["scanner"].form.fields["model"].text() == "V850"
    assert window.method.currentData() == "scan"
    assert not window.dirty and not window.write_button.isEnabled()
    name = window.boxes["film"].form.fields["name"]
    name.selectAll()
    QTest.keyClicks(name, "Gold 200")
    window.write()
    wait_job(window, application)
    result = read_one(path)
    assert result.xmp["Xmp.fm.FilmName"] == "Gold 200"
    assert result.xmp["Xmp.AnalogExif.Film"] == "Kodak Portra 400"
    assert result.xmp["Xmp.AnalogExif.Scanner"] == "Epson V850"
    window.close()
