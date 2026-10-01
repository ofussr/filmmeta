"""Stable translation keys, loaded without GUI or metadata dependencies."""

from importlib.resources import files
import json

LANGUAGES = {"ru": "Русский", "en": "English"}
_language = "ru"
CATALOGS = {
    language: json.loads(
        files("filmmeta")
        .joinpath("locales", language + ".json")
        .read_text(encoding="utf-8")
    )
    for language in LANGUAGES
}


def set_language(language):
    global _language
    if language not in LANGUAGES:
        raise ValueError("Unsupported interface language: " + str(language))
    _language = language


def language():
    return _language


def tr(key, **values):
    # Missing keys raise rather than silently showing untranslated identifiers.
    return CATALOGS[_language][key].format(**values)
