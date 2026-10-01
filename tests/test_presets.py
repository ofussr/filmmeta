import json

import pytest

from filmmeta import presets as presets_module
from filmmeta.presets import PresetStore


def test_json_library_crud_duplicate_and_failed_save(tmp_path, monkeypatch):
    path = tmp_path / "Мои плёнки" / "library.json"
    library = PresetStore(path)
    row = {
        "manufacturer": "Foma",
        "name": "Fomapan 400",
        "iso": "400",
        "process": "B&W",
    }
    library.save("films", row)
    before = path.read_bytes()
    assert json.loads(before)["films"][0]["iso"] == 400
    with pytest.raises(ValueError, match="уже есть"):
        library.save("films", row)
    assert path.read_bytes() == before
    loaded = PresetStore(path)
    loaded.save("films", {**row, "name": "Updated"}, 0)
    assert PresetStore(path).data["films"][0]["name"] == "Updated"
    loaded.delete("films", 0)
    assert PresetStore(path).data["films"] == []
    monkeypatch.setattr(
        presets_module.os,
        "replace",
        lambda *_: (_ for _ in ()).throw(PermissionError("blocked")),
    )
    with pytest.raises(PermissionError):
        loaded.save("films", row)
    assert loaded.data["films"] == [] and PresetStore(path).data["films"] == []
