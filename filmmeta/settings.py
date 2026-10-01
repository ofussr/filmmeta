"""Validated, atomic preferences independent of Qt and personal presets."""

import json
import os
from pathlib import Path
import tempfile
from .fields import DEFAULT_VISIBLE, FIELD_IDS
from .i18n import tr

DEFAULTS = {
    "language": "ru",
    "theme": "light",
    "analog_exif": False,
    "standard_exif": False,
    "visible_fields": DEFAULT_VISIBLE,
}


class Settings:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.validate({})
        if self.path.exists():
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            self.data = self.validate(saved)

    @staticmethod
    def validate(data):
        if not isinstance(data, dict):
            raise ValueError(tr("error.settings"))
        result = {
            **DEFAULTS,
            **{key: value for key, value in data.items() if key in DEFAULTS},
        }
        if result["language"] not in {"ru", "en"}:
            raise ValueError(tr("error.language"))
        if result["theme"] not in {"light", "dark"}:
            raise ValueError(tr("error.theme"))
        if any(
            type(result[key]) is not bool for key in ("analog_exif", "standard_exif")
        ):
            raise ValueError(tr("error.write_preference"))
        fields = result["visible_fields"]
        if not isinstance(fields, list) or any(
            not isinstance(key, str) for key in fields
        ):
            raise ValueError(tr("error.visible_fields"))
        result["visible_fields"] = list(
            dict.fromkeys(key for key in fields if key in FIELD_IDS)
        )
        return result

    def save(self, data):
        candidate = self.validate(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(
            dir=self.path.parent, prefix="settings-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(candidate, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)
        self.data = candidate
