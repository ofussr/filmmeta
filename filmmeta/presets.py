"""Validated personal lists and atomic JSON persistence, independent of Qt."""

from .i18n import tr
import copy
import json
import os
import tempfile
from pathlib import Path
from .fields import FIELDS


def label(entry):
    text = " ".join(
        filter(
            None,
            [entry.get("manufacturer", ""), entry.get("name", entry.get("model", ""))],
        )
    )
    if entry.get("iso"):
        text += f" · ISO {entry['iso']}"
    return text


def check_entry(kind, entry):
    if not isinstance(entry, dict):
        raise ValueError(tr("error.library_entry"))
    row = {}
    for key, _title in FIELDS[kind]:
        value = entry.get(key, "")
        if value is None or isinstance(value, (list, dict, bool)):
            raise ValueError(tr("error.preset_field", field=key))
        value = str(value).strip()
        if value:
            row[key] = value
    name_key = "name" if kind == "films" else "model"
    if not row.get("manufacturer") or not row.get(name_key):
        raise ValueError(tr("error.preset_name"))
    if "iso" in row:
        value = row["iso"]
        if not value.isdecimal() or not 1 <= int(value) <= 65535:
            raise ValueError(tr("error.iso"))
        row["iso"] = int(value)
    if "grain" in row and not row["grain"].isdecimal():
        raise ValueError(tr("error.integer"))
    return row


class PresetStore:
    def __init__(self, path, on_change=None):
        self.path = Path(path)
        self.on_change = on_change
        self.data = {"version": 1, **{key: [] for key in FIELDS}}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError(tr("error.library_format"))
            for kind in FIELDS:
                if not isinstance(data.get(kind), list):
                    raise ValueError(tr("error.library_list", kind=kind))
                data[kind] = [check_entry(kind, row) for row in data[kind]]
            self.data = data

    def commit(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(
            dir=self.path.parent, prefix="library-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)
        self.data = data
        if self.on_change is not None:
            self.on_change()

    def save(self, kind, entry, index=None):
        entry = check_entry(kind, entry)
        data = copy.deepcopy(self.data)
        rows = data[kind]
        if index is not None and rows[index] == entry:
            return
        if any((row == entry for i, row in enumerate(rows) if i != index)):
            raise ValueError(tr("error.duplicate"))
        if index is None:
            rows.append(entry)
        else:
            rows[index] = entry
        self.commit(data)

    def delete(self, kind, index):
        data = copy.deepcopy(self.data)
        del data[kind][index]
        self.commit(data)
