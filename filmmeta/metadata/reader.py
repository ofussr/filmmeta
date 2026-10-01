"""Read existing embedded metadata through image bytes."""

from ..i18n import tr
from dataclasses import dataclass
from pathlib import Path
import pyexiv2
from ..fields import FIELDS, ROLES
from ..fileio import file_bytes
from .schema import (
    NAMESPACE,
    PREFIX,
    ANALOG_NAMESPACE,
    ANALOG_PREFIX,
    XMP_FIELDS,
    EXIF_FIELDS,
    scalar,
    first_value,
    custom_value,
    custom_name,
)


def register_namespace():
    pyexiv2.registerNs(NAMESPACE, "fm")
    pyexiv2.registerNs(ANALOG_NAMESPACE, "AnalogExif")


@dataclass
class Metadata:
    path: Path
    values: dict
    sources: dict
    exif: dict
    xmp: dict
    is_dng: bool


def decode_metadata(path, exif, xmp):
    is_dng = path.suffix.lower() == ".dng" or "Exif.Image.DNGVersion" in exif
    values = {key: "" for key in XMP_FIELDS}
    sources = {}
    for key in XMP_FIELDS:
        values[key], sources[key] = custom_value(xmp, key)
        if not values[key] and key in EXIF_FIELDS and (not is_dng):
            values[key], sources[key] = first_value(exif, xmp, key)
    for role, field in (("film", "name"), ("scanner", "model")):
        key = (role, field)
        if sources[key].startswith(ANALOG_PREFIX):
            values[key] = custom_name(xmp, role, field)
    values["method"] = scalar(xmp.get(PREFIX + "DigitizationType"))
    if values["method"] not in {"scan", "camera"}:
        values["method"] = ""
        if any(
            (
                sources["scanner", field].startswith(ANALOG_PREFIX)
                for field in ("manufacturer", "model")
            )
        ):
            values["method"] = "scan"
    if is_dng and values["method"] == "camera":
        for role, original in [("copy_camera", "camera"), ("copy_lens", "lens")]:
            for field, _title in FIELDS[ROLES[role][0]]:
                key = (role, field)
                if not values[key]:
                    values[key], sources[key] = first_value(
                        exif, xmp, (original, field)
                    )
    if is_dng and values["method"] == "scan":
        for field in ("manufacturer", "model"):
            key = ("scanner", field)
            if not values[key]:
                values[key], sources[key] = first_value(exif, xmp, ("camera", field))
    return Metadata(path, values, sources, exif, xmp, is_dng)


def read_one(path):
    path = Path(path)
    data = file_bytes(path)
    with pyexiv2.ImageData(data) as image:
        exif, xmp = (image.read_exif(), image.read_xmp())
    return decode_metadata(path, exif, xmp)


def read_files(paths, progress, cancelled):
    entries, errors = ([], {})
    for index, path in enumerate(paths, 1):
        if cancelled():
            break
        try:
            entries.append(read_one(path))
        except Exception as error:
            errors[str(path)] = str(error)
        progress(index, tr("progress.read", name=path.name))
    return (entries, errors)
