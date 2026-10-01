"""Shared metadata interoperability, using independently authored XMP packets."""

import xml.etree.ElementTree as ET

import pyexiv2
import pytest

from filmmeta.metadata.reader import read_one
from filmmeta.metadata.writer import write_one, write_files
from .helpers import modify, picture

A = "Xmp.AnalogExif."
F = "Xmp.fm."


@pytest.mark.parametrize("kind", ["jpeg", "tiff", "dng"])
def test_reads_literal_analog_packet_without_changing_file(tmp_path, kind):
    path = picture(tmp_path, kind)
    # Literal URI and alternate prefix independently check the schema identity.
    xml = """<x:xmpmeta xmlns:x="adobe:ns:meta/">
      <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about=""
          xmlns:ae="http://analogexif.sourceforge.net/ns/"
          ae:FilmMaker="Kodak" ae:Film="Kodak Portra 400"
          ae:DevelopProcess="C-41" ae:ScannerMaker="Epson"
          ae:Scanner="Epson V850" ae:RollId="Keep roll"/>
      </rdf:RDF></x:xmpmeta>"""
    with pyexiv2.ImageData(path.read_bytes()) as image:
        image.modify_raw_xmp(xml)
        output = image.get_bytes()
    path.write_bytes(output)
    before = path.read_bytes()
    result = read_one(path)
    assert result.values[("film", "manufacturer")] == "Kodak"
    assert result.values[("film", "name")] == "Portra 400"
    assert result.values[("film", "process")] == "C-41"
    assert result.values[("scanner", "model")] == "V850"
    assert result.values["method"] == "scan"
    assert result.sources[("film", "name")] == A + "Film"
    assert path.read_bytes() == before
    if kind == "dng":
        assert result.values[("camera", "model")] == ""


def test_write_shared_keys_uri_and_full_names(tmp_path):
    path = picture(tmp_path, "jpeg")
    write_one(
        path,
        {
            ("film", "manufacturer"): "Kodak",
            ("film", "name"): "Portra 400",
            ("film", "process"): "C-41",
            "method": "scan",
            ("scanner", "manufacturer"): "Epson",
            ("scanner", "model"): "V850",
        },
        analog_exif=True,
    )
    result = read_one(path)
    assert result.xmp[A + "FilmMaker"] == "Kodak"
    assert result.xmp[A + "Film"] == "Kodak Portra 400"
    assert result.xmp[A + "DevelopProcess"] == "C-41"
    assert result.xmp[A + "Scanner"] == "Epson V850"
    assert result.xmp[F + "FilmName"] == "Portra 400"
    assert result.xmp[F + "ScannerModel"] == "V850"
    with pyexiv2.ImageData(path.read_bytes()) as image:
        root = ET.fromstring(image.read_raw_xmp())
    assert any(
        node.attrib.get("{http://analogexif.sourceforge.net/ns/}Film")
        == "Kodak Portra 400"
        for node in root.iter()
    )


def test_own_priority_and_shared_preservation(tmp_path):
    path = picture(tmp_path)
    modify(
        path,
        xmp={
            F + "FilmManufacturer": "Legacy maker",
            F + "FilmName": "Legacy name",
            F + "FilmProcess": "Legacy process",
            F + "ScannerModel": "Legacy scanner",
            A + "FilmMaker": "Kodak",
            A + "Film": "Kodak Portra 400",
            A + "RollId": "R12",
            A + "Developer": "Keep developer",
        },
    )
    result = read_one(path)
    assert result.values[("film", "manufacturer")] == "Legacy maker"
    assert result.values[("film", "name")] == "Legacy name"
    assert result.values[("film", "process")] == "Legacy process"
    assert result.values[("scanner", "model")] == "Legacy scanner"
    write_one(path, {("film", "name"): "Gold 200"})
    result = read_one(path)
    assert result.xmp[A + "Film"] == "Kodak Portra 400"
    assert result.xmp[F + "FilmName"] == "Gold 200"
    assert result.xmp[F + "FilmProcess"] == "Legacy process"
    assert result.xmp[A + "RollId"] == "R12"
    assert result.xmp[A + "Developer"] == "Keep developer"
    # Editing a shared tag externally cannot override an own value.
    modify(path, xmp={A + "Film": "Kodak Ektar 100"})
    assert read_one(path).values[("film", "name")] == "Gold 200"


def test_partial_legacy_updates_and_batch_names_are_per_file(tmp_path):
    paths = [picture(tmp_path / "one"), picture(tmp_path / "two")]
    for path, name in zip(paths, ["Portra 400", "Gold 200"]):
        modify(path, xmp={F + "FilmManufacturer": "Kodak", F + "FilmName": name})
    results = write_files(
        paths,
        {("film", "manufacturer"): "New maker"},
        False,
        lambda *_: None,
        lambda: False,
        analog_exif=True,
    )
    assert all(success for _, success, _ in results)
    for path, name in zip(paths, ["Portra 400", "Gold 200"]):
        result = read_one(path)
        assert result.xmp[A + "Film"] == "New maker " + name
        assert result.values[("film", "name")] == name
        assert result.xmp[F + "FilmManufacturer"] == "New maker"
        assert result.xmp[F + "FilmName"] == name
    write_one(paths[0], {("film", "manufacturer"): "Next maker"}, analog_exif=True)
    assert read_one(paths[0]).xmp[A + "Film"] == "Next maker Portra 400"


@pytest.mark.parametrize(
    "maker,name,expected",
    [
        ("Kodak", "Kodak Portra", "Kodak Portra"),
        ("Kodak", "kodak Portra", "Kodak Portra"),
        ("Fuji", "Fujifilm Pro", "Fuji Fujifilm Pro"),
        ("", "Unknown film", "Unknown film"),
        ("Kodak", "Kodak", "Kodak"),
    ],
)
def test_manufacturer_is_not_duplicated_or_partially_stripped(
    tmp_path, maker, name, expected
):
    path = picture(tmp_path)
    write_one(
        path,
        {("film", "manufacturer"): maker, ("film", "name"): name},
        analog_exif=True,
    )
    assert read_one(path).xmp[A + "Film"] == expected


def test_explicit_method_and_unexposed_analog_fields(tmp_path):
    path = picture(tmp_path)
    modify(
        path,
        xmp={
            A + "ScannerMaker": "Epson",
            A + "Scanner": "Epson V850",
            A + "ScannerSoftware": "Keep software",
            A + "ExposureNumber": "12",
            F + "ScannerModel": "Old model",
            F + "DigitizationType": "camera",
        },
    )
    assert read_one(path).values["method"] == "camera"
    write_one(path, {"method": "camera"})
    result = read_one(path)
    assert result.xmp[A + "Scanner"] == "Epson V850"
    assert result.xmp[A + "ScannerMaker"] == "Epson"
    assert F + "ScannerModel" not in result.xmp
    assert result.xmp[A + "ScannerSoftware"] == "Keep software"
    assert result.xmp[A + "ExposureNumber"] == "12"


def test_default_writes_own_only_and_preserves_exif(tmp_path):
    path = picture(tmp_path)
    modify(
        path,
        exif={"Exif.Image.Model": "Digitizer"},
        xmp={
            A + "FilmMaker": "Kodak",
            A + "Film": "Kodak Portra 400",
            A + "FilmAlias": "Old alias",
        },
    )
    write_one(
        path,
        {
            ("film", "name"): "Gold 200",
            ("film", "alias"): "New alias",
            ("camera", "model"): "Film camera",
        },
    )
    result = read_one(path)
    assert result.xmp[F + "FilmName"] == "Gold 200"
    assert result.xmp[F + "FilmAlias"] == "New alias"
    assert result.xmp[A + "Film"] == "Kodak Portra 400"
    assert result.xmp[A + "FilmAlias"] == "Old alias"
    assert result.exif["Exif.Image.Model"] == "Digitizer"
    assert result.values[("film", "name")] == "Gold 200"


def test_own_maker_with_shared_full_name_uses_shared_maker_to_split(tmp_path):
    path = picture(tmp_path)
    modify(path, xmp={A + "FilmMaker": "Kodak", A + "Film": "Kodak Portra 400"})
    write_one(path, {("film", "manufacturer"): "New maker"})
    assert read_one(path).values[("film", "name")] == "Portra 400"
    write_one(path, {("film", "manufacturer"): "Next maker"}, analog_exif=True)
    result = read_one(path)
    assert result.xmp[A + "Film"] == "Next maker Portra 400"
    assert result.values[("film", "name")] == "Portra 400"


@pytest.mark.parametrize("kind", ["jpeg", "tiff", "dng"])
def test_all_additional_fields_round_trip_and_compatible_mirror(tmp_path, kind):
    path = picture(tmp_path, kind)
    patch = {
        ("film", "alias"): "RVP 50",
        ("film", "grain"): "9",
        ("film", "type"): "135",
        ("exposure", "number"): "0",
        ("exposure", "roll_id"): "R12",
        ("exposure", "filter"): "Hoya R72",
        ("lens", "serial"): "ABC123",
        ("development", "manufacturer"): "Kodak",
        ("development", "name"): "XTOL",
        ("development", "dilution"): "1:1",
        ("development", "time"): "13 min",
        ("development", "lab"): "Lab A",
        ("development", "lab_address"): "Street A",
        "method": "scan",
        ("scanner", "software"): "SilverFast",
    }
    write_one(path, patch, analog_exif=True)
    result = read_one(path)
    assert all(result.values[key] == value for key, value in patch.items())
    assert result.xmp[A + "FilmAlias"] == "RVP 50"
    assert result.xmp[A + "Developer"] == "XTOL"
    assert result.xmp[A + "ExposureNumber"] == "0"
    assert result.xmp[A + "ScannerSoftware"] == "SilverFast"
    if kind == "dng":
        assert result.exif["Exif.Image.Model"] == "RAW Camera"
