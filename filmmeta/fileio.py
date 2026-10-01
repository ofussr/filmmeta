"""Python file access, size limits and original-file backups."""

from .i18n import tr
import os
import shutil
from pathlib import Path

READ_LIMIT = 2000000000
WRITE_LIMIT = 1000000000
EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".dng"}


def file_bytes(path, limit=READ_LIMIT):
    """Python handles Unicode names, mapped drives and UNC paths itself."""
    if path.stat().st_size >= limit:
        raise ValueError(tr("error.file_limit", limit=limit // 1000000000))
    data = path.read_bytes()
    if len(data) >= limit:
        raise ValueError(tr("error.file_grew"))
    if data[:4] in (b"II+\x00", b"MM\x00+"):
        raise ValueError(tr("error.bigtiff"))
    return data


def fingerprint(path):
    stat = path.stat()
    return (stat.st_size, stat.st_mtime_ns, stat.st_ino, stat.st_dev)


def unique_backup(source):
    number = 0
    while True:
        suffix = ".filmmeta.bak" if number == 0 else f".filmmeta.{number}.bak"
        target = source.with_name(source.name + suffix)
        try:
            stream = target.open("xb")
        except FileExistsError:
            number += 1
            continue
        try:
            with stream, source.open("rb") as original:
                shutil.copyfileobj(original, stream)
                stream.flush()
                os.fsync(stream.fileno())
            shutil.copystat(source, target)
            return target
        except Exception:
            target.unlink(missing_ok=True)
            raise
