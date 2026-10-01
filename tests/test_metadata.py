import numpy as np
import pyexiv2
import pytest
import tifffile
from PIL import Image

from filmmeta.metadata import writer
from filmmeta.metadata.reader import read_one
from filmmeta.metadata.writer import write_one
from filmmeta.metadata.schema import PREFIX, NAMESPACE, scalar
from .helpers import modify, picture, jpeg_scan


@pytest.mark.parametrize("kind", ["jpeg", "tiff", "float64", "dng"])
def test_unicode_roundtrip_and_original_backup(tmp_path, kind, monkeypatch):
    path = picture(tmp_path, kind)
    modify(
        path,
        exif={"Exif.Photo.ISOSpeedRatings": "100"},
        xmp={"Xmp.dc.description": "Existing caption", "Xmp.xmp.Rating": "3"},
    )
    original = path.read_bytes()
    initial = read_one(path)
    if kind != "jpeg":
        pixels = tifffile.imread(path)
    else:
        pixels = np.asarray(Image.open(path))
        icc = Image.open(path).info.get("icc_profile")
    # Native filename-based construction is deliberately made unusable.
    monkeypatch.setattr(
        pyexiv2,
        "Image",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("Native code received a path")
        ),
    )
    patch = {
        ("film", "manufacturer"): "Foma",
        ("film", "name"): "Фомапан 400",
        ("film", "iso"): "400",
        ("film", "process"): "B&W",
        ("camera", "manufacturer"): "KMZ",
        ("camera", "model"): "Zenit ET",
        ("lens", "manufacturer"): "KMZ",
        ("lens", "model"): "Helios-44-2",
        "method": "scan",
        ("scanner", "manufacturer"): "Fujifilm eSystems, Inc.",
        ("scanner", "model"): "Digital Link",
    }
    backup = write_one(path, patch, standard_exif=True)
    assert backup.read_bytes() == original
    result = read_one(path)
    for key, value in patch.items():
        assert result.values[key] == value
    assert result.xmp["Xmp.xmp.Rating"] == "3"
    assert result.xmp["Xmp.dc.description"] == initial.xmp["Xmp.dc.description"]
    if kind == "dng":
        for key, value in initial.exif.items():
            if key not in {
                "Exif.Image.XMLPacket",
                "Exif.Image.ExifTag",
                "Exif.Image.StripOffsets",
            }:
                assert result.exif[key] == value
        assert result.exif["Exif.Image.UniqueCameraModel"] == "Digitizer RAW Camera"
    else:
        assert result.exif["Exif.Image.Model"] == "Zenit ET"
        assert result.exif["Exif.Photo.ISOSpeedRatings"] == "400"
    if kind == "jpeg":
        assert jpeg_scan(path.read_bytes()) == jpeg_scan(original)
        assert Image.open(path).info.get("icc_profile") == icc
        assert np.array_equal(np.asarray(Image.open(path)), pixels)
    else:
        assert np.array_equal(tifffile.imread(path), pixels)
        assert tifffile.imread(path).dtype == pixels.dtype
    second_original = path.read_bytes()
    second = write_one(path, {("film", "name"): "Second film"})
    assert second != backup and second.read_bytes() == second_original
    assert backup.read_bytes() == original


def test_reads_existing_scanner_exif_and_iso(tmp_path):
    path = picture(tmp_path)
    modify(
        path,
        exif={
            "Exif.Image.Make": "Fujifilm eSystems, Inc.",
            "Exif.Image.Model": "Digital Link",
            "Exif.Photo.LensMake": "KMZ",
            "Exif.Photo.LensModel": "Helios",
            "Exif.Photo.ISOSpeedRatings": "400",
        },
    )
    before = path.read_bytes()
    metadata = read_one(path)
    assert metadata.values[("camera", "manufacturer")] == "Fujifilm eSystems, Inc."
    assert metadata.values[("camera", "model")] == "Digital Link"
    assert metadata.values[("film", "iso")] == "400"
    assert metadata.sources[("film", "iso")] == "Exif.Photo.ISOSpeedRatings"
    assert path.read_bytes() == before


def test_standard_xmp_fallback_and_custom_priority(tmp_path):
    path = picture(tmp_path, "jpeg")
    modify(
        path,
        xmp={
            "Xmp.tiff.Make": "XMP make",
            "Xmp.tiff.Model": "XMP model",
            "Xmp.aux.Lens": "XMP lens",
            "Xmp.exif.ISOSpeedRatings": ["200"],
            PREFIX + "OriginalCameraModel": "Film camera",
        },
    )
    metadata = read_one(path)
    assert metadata.values[("camera", "manufacturer")] == "XMP make"
    assert metadata.values[("camera", "model")] == "Film camera"
    assert metadata.values[("lens", "model")] == "XMP lens"
    assert metadata.values[("film", "iso")] == "200"


def test_dng_exif_is_shown_separately(tmp_path):
    path = picture(tmp_path, "dng")
    modify(path, exif={"Exif.Photo.ISOSpeedRatings": "100"})
    result = read_one(path)
    assert result.values[("camera", "model")] == ""
    assert result.values[("film", "iso")] == ""
    assert result.exif["Exif.Image.Model"] == "RAW Camera"
    modify(path, xmp={PREFIX + "DigitizationType": "camera"})
    result = read_one(path)
    assert result.values[("copy_camera", "model")] == "RAW Camera"


def test_method_change_removes_only_incompatible_own_fields(tmp_path):
    path = picture(tmp_path)
    write_one(
        path,
        {
            "method": "camera",
            ("copy_camera", "model"): "Camera Z",
            ("copy_lens", "model"): "Macro 60",
        },
    )
    modify(path, xmp={"Xmp.dc.subject": ["Keep me"]})
    write_one(path, {"method": "scan", ("scanner", "model"): "Scanner"})
    result = read_one(path)
    assert PREFIX + "DigitizerCameraModel" not in result.xmp
    assert PREFIX + "DigitizerLensModel" not in result.xmp
    assert scalar(result.xmp["Xmp.dc.subject"]) == "Keep me"


def test_xmp_only_and_blank_field_preservation(tmp_path):
    path = picture(tmp_path)
    modify(path, exif={"Exif.Image.Model": "Existing model"})
    write_one(path, {("film", "name"): "Portra", ("camera", "model"): ""}, False)
    result = read_one(path)
    assert result.exif["Exif.Image.Model"] == "Existing model"
    assert PREFIX + "OriginalCameraModel" not in result.xmp


def test_failure_leaves_original_and_no_backup(tmp_path, monkeypatch):
    path = picture(tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(
        writer,
        "verify_tags",
        lambda *_: (_ for _ in ()).throw(ValueError("verification error")),
    )
    with pytest.raises(ValueError, match="verification error"):
        write_one(path, {("film", "name"): "Test"})
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.filmmeta.bak"))
    assert not list(path.parent.glob(".filmmeta-*"))


def test_replace_failure_has_original_backup(tmp_path, monkeypatch):
    path = picture(tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(
        writer.os,
        "replace",
        lambda *_: (_ for _ in ()).throw(PermissionError("locked file")),
    )
    with pytest.raises(PermissionError):
        write_one(path, {("film", "name"): "Test"})
    assert path.read_bytes() == before
    assert path.with_name(path.name + ".filmmeta.bak").read_bytes() == before
    assert not list(path.parent.glob(".filmmeta-*"))


def test_file_changed_during_processing_not_replaced(tmp_path, monkeypatch):
    path = picture(tmp_path)
    changed = b"modified externally"
    original_verify = writer.verify_tags

    def change(actual, planned):
        original_verify(actual, planned)
        path.write_bytes(changed)

    monkeypatch.setattr(writer, "verify_tags", change)
    with pytest.raises(ValueError, match="изменился"):
        write_one(path, {("film", "name"): "Test"})
    assert path.read_bytes() == changed


def test_bigtiff_rejected_and_size_checked_before_read(tmp_path, monkeypatch):
    big = tmp_path / "big.tif"
    tifffile.imwrite(big, np.zeros((3, 3), dtype=np.uint8), bigtiff=True)
    with pytest.raises(ValueError, match="BigTIFF"):
        read_one(big)
    path = picture(tmp_path)
    monkeypatch.setattr(writer, "WRITE_LIMIT", 1)
    with pytest.raises(ValueError, match="лимита"):
        write_one(path, {("film", "name"): "Test"})


def test_dng_preservation_check_detects_camera_or_calibration_change(
    tmp_path, monkeypatch
):
    path = picture(tmp_path, "dng")
    before = path.read_bytes()
    original_verify = writer.verify_dng_exif

    def damage(actual, original):
        altered = dict(actual)
        altered["Exif.Image.ColorMatrix1"] = "0/1"
        original_verify(altered, original)

    monkeypatch.setattr(writer, "verify_dng_exif", damage)
    with pytest.raises(ValueError, match="ColorMatrix1"):
        write_one(path, {("film", "name"): "Test"})
    assert path.read_bytes() == before


def test_custom_namespace_alternative_prefix(tmp_path):
    path = picture(tmp_path)
    xml = (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        f'<rdf:Description rdf:about="" xmlns:film="{NAMESPACE}" '
        'film:FilmName="Alternative prefix"/></rdf:RDF></x:xmpmeta>'
    )
    with pyexiv2.ImageData(path.read_bytes()) as image:
        image.modify_raw_xmp(xml)
        output = image.get_bytes()
    path.write_bytes(output)
    assert read_one(path).values[("film", "name")] == "Alternative prefix"
