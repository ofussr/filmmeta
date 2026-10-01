"""Verify metadata changes and replace files with original-file backups."""

from ..i18n import tr
import os
import shutil
import tempfile
from pathlib import Path
import pyexiv2
from ..fileio import WRITE_LIMIT, file_bytes, fingerprint, unique_backup
from .schema import make_tags, scalar


def verify_tags(actual, planned):
    for key, value in planned.items():
        if value is None:
            if key in actual:
                raise ValueError(tr("error.delete_tag", tag=key))
        elif scalar(actual.get(key)) != scalar(value):
            raise ValueError(tr("error.verify_tag", tag=key))


def verify_dng_exif(actual, original):
    structural = {
        "XMLPacket",
        "ExifTag",
        "GPSTag",
        "InteroperabilityTag",
        "SubIFDs",
        "StripOffsets",
        "TileOffsets",
        "JPEGInterchangeFormat",
    }
    unchanged = {
        key: value
        for key, value in original.items()
        if key.rsplit(".", 1)[-1] not in structural
    }
    verify_tags(actual, unchanged)


def write_one(path, patch, standard_exif=False, analog_exif=False):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(tr("error.symlink"))
    baseline = fingerprint(path)
    data = file_bytes(path, WRITE_LIMIT)
    with pyexiv2.ImageData(data) as image:
        old_exif, old_xmp = (image.read_exif(), image.read_xmp())
        is_dng = path.suffix.lower() == ".dng" or "Exif.Image.DNGVersion" in old_exif
        exif, xmp = make_tags(
            patch, standard_exif, is_dng, old_exif, old_xmp, analog_exif
        )
        if exif:
            image.modify_exif(exif)
        image.modify_xmp(xmp)
        output = image.get_bytes()
    del data
    with pyexiv2.ImageData(output) as image:
        actual_exif = image.read_exif()
        verify_tags(actual_exif, exif)
        if is_dng:
            verify_dng_exif(actual_exif, old_exif)
        verify_tags(image.read_xmp(), xmp)
    fd, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=".filmmeta-", suffix=path.suffix
    )
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(output)
            stream.flush()
            os.fsync(stream.fileno())
        del output
        shutil.copystat(path, temporary)
        if fingerprint(path) != baseline:
            raise ValueError(tr("error.concurrent"))
        backup = unique_backup(path)
        if fingerprint(path) != baseline:
            raise ValueError(tr("error.concurrent_final"))
        os.replace(temporary, path)
        return backup
    finally:
        temporary.unlink(missing_ok=True)


def write_files(
    paths, patch, standard, progress, cancelled, methods=None, analog_exif=False
):
    """Write a batch, optionally filtering digitizer fields by each file's mode."""
    results = []
    for index, path in enumerate(paths, 1):
        if cancelled():
            break
        try:
            per_file = patch
            if methods is not None:
                applicable = patch.get("method", methods[path])
                per_file = {
                    key: value
                    for key, value in patch.items()
                    if key == "method"
                    or key[0] not in {"scanner", "copy_camera", "copy_lens"}
                    or (key[0] == "scanner" and applicable == "scan")
                    or (
                        key[0] in {"copy_camera", "copy_lens"}
                        and applicable == "camera"
                    )
                }
            if per_file:
                backup = write_one(path, per_file, standard, analog_exif)
                results.append((str(path), True, tr("write.backup", name=backup.name)))
            else:
                results.append((str(path), True, tr("write.skipped")))
        except Exception as error:
            results.append((str(path), False, str(error)))
        progress(index, tr("progress.write", name=path.name))
    return results
