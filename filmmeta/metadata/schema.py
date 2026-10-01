"""FilmMeta XMP schema, standard-tag fallbacks and planned changes."""

from ..i18n import tr
import json

NAMESPACE = "urn:filmmeta:metadata:1.0/"
PREFIX = "Xmp.fm."
ANALOG_NAMESPACE = "http://analogexif.sourceforge.net/ns"
ANALOG_PREFIX = "Xmp.AnalogExif."
ANALOG_FIELDS = {
    ("film", "manufacturer"): "FilmMaker",
    ("film", "name"): "Film",
    ("film", "process"): "DevelopProcess",
    ("scanner", "manufacturer"): "ScannerMaker",
    ("scanner", "model"): "Scanner",
    ("film", "alias"): "FilmAlias",
    ("film", "grain"): "FilmGrain",
    ("film", "type"): "FilmType",
    ("exposure", "number"): "ExposureNumber",
    ("exposure", "roll_id"): "RollId",
    ("exposure", "filter"): "Filter",
    ("lens", "serial"): "LensSerialNumber",
    ("scanner", "software"): "ScannerSoftware",
    ("development", "manufacturer"): "DeveloperMaker",
    ("development", "name"): "Developer",
    ("development", "dilution"): "DeveloperDilution",
    ("development", "time"): "DevelopTime",
    ("development", "lab"): "Lab",
    ("development", "lab_address"): "LabAddress",
}
XMP_FIELDS = {
    ("film", "manufacturer"): "FilmManufacturer",
    ("film", "name"): "FilmName",
    ("film", "iso"): "FilmISO",
    ("film", "process"): "FilmProcess",
    ("camera", "manufacturer"): "OriginalCameraMake",
    ("camera", "model"): "OriginalCameraModel",
    ("lens", "manufacturer"): "OriginalLensMake",
    ("lens", "model"): "OriginalLensModel",
    ("scanner", "manufacturer"): "ScannerMake",
    ("scanner", "model"): "ScannerModel",
    ("copy_camera", "manufacturer"): "DigitizerCameraMake",
    ("copy_camera", "model"): "DigitizerCameraModel",
    ("copy_lens", "manufacturer"): "DigitizerLensMake",
    ("copy_lens", "model"): "DigitizerLensModel",
    ("film", "alias"): "FilmAlias",
    ("film", "grain"): "FilmGrain",
    ("film", "type"): "FilmType",
    ("exposure", "number"): "ExposureNumber",
    ("exposure", "roll_id"): "RollId",
    ("exposure", "filter"): "Filter",
    ("lens", "serial"): "OriginalLensSerialNumber",
    ("copy_lens", "serial"): "DigitizerLensSerialNumber",
    ("scanner", "software"): "ScannerSoftware",
    ("development", "manufacturer"): "DeveloperMake",
    ("development", "name"): "DeveloperName",
    ("development", "dilution"): "DeveloperDilution",
    ("development", "time"): "DevelopTime",
    ("development", "lab"): "Lab",
    ("development", "lab_address"): "LabAddress",
}
EXIF_FIELDS = {
    ("camera", "manufacturer"): "Exif.Image.Make",
    ("camera", "model"): "Exif.Image.Model",
    ("lens", "manufacturer"): "Exif.Photo.LensMake",
    ("lens", "model"): "Exif.Photo.LensModel",
    ("film", "iso"): "Exif.Photo.ISOSpeedRatings",
    ("lens", "serial"): "Exif.Photo.LensSerialNumber",
}
STANDARD_XMP = {
    ("camera", "manufacturer"): ["Xmp.tiff.Make"],
    ("camera", "model"): ["Xmp.tiff.Model"],
    ("lens", "manufacturer"): ["Xmp.exifEX.LensMake"],
    ("lens", "model"): ["Xmp.exifEX.LensModel", "Xmp.aux.Lens"],
    ("film", "iso"): ["Xmp.exif.ISOSpeedRatings", "Xmp.exifEX.ISOSpeed"],
    ("lens", "serial"): ["Xmp.exifEX.LensSerialNumber"],
}


def scalar(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        items = list(dict.fromkeys((str(item).strip() for item in value)))
        return ", ".join(items)
    return str(value).strip()


def first_value(exif, xmp, key):
    tags = [EXIF_FIELDS[key]]
    if key == ("film", "iso"):
        tags += ["Exif.Photo.RecommendedExposureIndex", "Exif.Photo.ISOSpeed"]
    for tag in tags:
        value = scalar(exif.get(tag))
        if value:
            return (value, tag)
    for tag in STANDARD_XMP.get(key, []):
        value = scalar(xmp.get(tag))
        if value:
            return (value, tag)
    return ("", "")


def custom_value(xmp, key):
    """Own fields are authoritative; AnalogExif supplies missing values."""
    tags = [PREFIX + XMP_FIELDS[key]]
    if key in ANALOG_FIELDS:
        tags.append(ANALOG_PREFIX + ANALOG_FIELDS[key])
    for tag in tags:
        value = scalar(xmp.get(tag))
        if value:
            return (value, tag)
    return ("", "")


def short_name(name, maker):
    """Remove a manufacturer only at a complete word boundary."""
    if maker and name.casefold().startswith(maker.casefold() + " "):
        return name[len(maker) :].strip()
    return name


def full_name(name, maker):
    if not maker or name.casefold() == maker.casefold():
        return name
    return maker + " " + short_name(name, maker)


def custom_name(xmp, role, field):
    name, source = custom_value(xmp, (role, field))
    if source.startswith(ANALOG_PREFIX):
        maker = scalar(xmp.get(ANALOG_PREFIX + ANALOG_FIELDS[role, "manufacturer"]))
        name = short_name(name, maker or custom_value(xmp, (role, "manufacturer"))[0])
    return name


def make_tags(patch, standard_exif, is_dng, old_exif, old_xmp, analog_exif=False):
    xmp, exif = ({}, {})
    edited = {}
    method = patch.get("method")
    inactive = (
        {"copy_camera", "copy_lens"}
        if method == "scan"
        else {"scanner"}
        if method == "camera"
        else set()
    )
    for key, value in patch.items():
        if key == "method":
            if value in {"scan", "camera"}:
                xmp[PREFIX + "DigitizationType"] = value
            continue
        if key not in XMP_FIELDS:
            raise ValueError(tr("error.field", field=key))
        if key[0] in inactive or not value:
            continue
        value = str(value).strip()
        if not value:
            continue
        if key == ("film", "iso") and (
            not value.isdecimal() or not 1 <= int(value) <= 65535
        ):
            raise ValueError(tr("error.iso"))
        edited[key] = value
        if key in {("film", "grain"), ("exposure", "number")} and (
            not value.isdecimal()
        ):
            raise ValueError(tr("error.integer"))
        xmp[PREFIX + XMP_FIELDS[key]] = value
        if analog_exif and key in ANALOG_FIELDS:
            xmp[ANALOG_PREFIX + ANALOG_FIELDS[key]] = value
        if standard_exif and (not is_dng) and (key in EXIF_FIELDS):
            exif[EXIF_FIELDS[key]] = value
    for role, field in (("film", "name"), ("scanner", "model")):
        if not analog_exif:
            break
        maker_key, name_key = ((role, "manufacturer"), (role, field))
        if maker_key not in edited and name_key not in edited:
            continue
        old_maker, _ = custom_value(old_xmp, maker_key)
        old_name = custom_name(old_xmp, role, field)
        maker = edited.get(maker_key, old_maker)
        name = edited.get(name_key, old_name)
        if name:
            xmp[ANALOG_PREFIX + ANALOG_FIELDS[name_key]] = full_name(name, maker)
        if maker:
            xmp[ANALOG_PREFIX + ANALOG_FIELDS[maker_key]] = maker
    if not xmp:
        raise ValueError(tr("error.empty"))
    xmp[PREFIX + "SchemaVersion"] = "1"
    if inactive:
        for key, tag in XMP_FIELDS.items():
            if key[0] in inactive and PREFIX + tag in old_xmp:
                xmp[PREFIX + tag] = None
        for key, tag in ANALOG_FIELDS.items():
            if analog_exif and key[0] in inactive and (ANALOG_PREFIX + tag in old_xmp):
                xmp[ANALOG_PREFIX + tag] = None
    if exif and PREFIX + "PreviousDigitizerExif" not in old_xmp:
        snapshot = {
            tag: old_exif[tag] for tag in EXIF_FIELDS.values() if tag in old_exif
        }
        if snapshot:
            xmp[PREFIX + "PreviousDigitizerExif"] = json.dumps(
                snapshot, ensure_ascii=False
            )
    for key, exif_tag in EXIF_FIELDS.items():
        if exif_tag not in exif:
            continue
        for tag in STANDARD_XMP.get(key, []):
            xmp[tag] = (
                [exif[exif_tag]]
                if tag == "Xmp.exif.ISOSpeedRatings"
                else exif[exif_tag]
            )
    return (exif, xmp)
