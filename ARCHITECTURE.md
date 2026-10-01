# FilmMeta architecture

FilmMeta 0.1.4 is a Python package with a small source launcher. Metadata and
personal-list storage do not import Qt. The interface uses those modules through
background jobs and a notification adapter.

## Module boundaries

| Module | Responsibility |
| --- | --- |
| `run_filmmeta.py`, `filmmeta/__main__.py` | Source and package entry points |
| `filmmeta/app.py` | Command-line arguments and application startup |
| `filmmeta/version.py` | Application name, version, author and contact |
| `filmmeta/fields.py` | Field/role definitions, stable IDs and the default visible set |
| `filmmeta/settings.py` | Validated atomic preferences; independent of Qt |
| `filmmeta/i18n.py`, `filmmeta/locales/` | Stable translation keys and Russian/English catalogues |
| `filmmeta/fileio.py` | Python file access, container/size checks and unique backups |
| `filmmeta/presets.py` | Validation, duplicate checks and atomic JSON preset storage |
| `filmmeta/metadata/schema.py` | XMP properties, standard-tag fallback and change planning |
| `filmmeta/metadata/reader.py` | Embedded metadata reading and field provenance |
| `filmmeta/metadata/writer.py` | Change verification, DNG preservation and file replacement |
| `filmmeta/ui/main_window.py` | Workspace, selection state and job coordination |
| `filmmeta/ui/forms.py` | Current values, manual edits and preset selection/saving |
| `filmmeta/ui/library.py` | Per-user data location and Qt preset-change notifications |
| `filmmeta/ui/library_dialog.py` | Personal-list management window |
| `filmmeta/ui/settings_dialog.py` | Language, theme, writing options and per-field display selection |
| `filmmeta/ui/workers.py` | Qt background jobs, progress and interruption |
| `filmmeta/ui/about.py`, `filmmeta/ui/theme.py` | About, resource access and light palette |
| `filmmeta/resources/` | Application icon and component notices |

`filmmeta/__init__.py` exposes application identity only. Importing the package
or requesting `--version` does not load Qt or pyexiv2. Normal GUI startup loads
both runtime dependencies.

## Reading and editing

Python reads the selected image path and passes bytes to `pyexiv2.ImageData`.
The reader maps embedded EXIF/XMP to the film and equipment fields, retaining
the original dictionaries and the source tag for each value. DNG technical
equipment remains distinct from the original film exposure.

The main window combines selected-file values. Differing values have a visible
placeholder. Programmatic form loading does not mark fields as edited. A file
selection change cancels pending reads between files and discards stale results
using a selection counter. Failed or incomplete reads disable writing.

## Writing

The interface collects changed, nonempty fields. The writer filters digital
equipment edits against each image's recorded or inferred digitisation mode.
`schema.py` always plans own XMP edits, with independent opt-in AnalogExif copies
and JPEG/TIFF EXIF mirroring. The interface excludes hidden fields from presets
and patches; visibility never writes metadata.

The writer modifies an in-memory image, reopens the result, verifies planned
tags and checks DNG technical values. It then writes a temporary file beside
the source, creates a unique original-file backup and replaces the source after
checking its file identity, size and modification time. This retains the write
policy used in 0.1.1.

Cancellation is checked between files. The worker cannot interrupt a native
metadata call already in progress.

## Personal lists

`PresetStore` accepts an explicit path and operates without a QApplication.
Changes are validated before an atomic JSON replacement. An optional callback
notifies consumers after a successful commit. The Qt adapter supplies the
existing application-data path and translates that callback into a signal.

The `library.json` version remains `1`; optional preset fields extend existing
rows without adding new library categories. FilmMeta XMP retains schema version
`1` and namespace `urn:filmmeta:metadata:1.0/`. Own properties are authoritative;
shared AnalogExif properties supply missing values. Neither reads nor changing
writing preferences migrates files.

`settings.json` stores language, theme, the two writing options and visible
`role.field` IDs independently from personal presets. It is validated and
replaced atomically. Unknown field IDs are ignored for forward compatibility;
invalid values are reported without overwriting the file.

## Translation and theme changes

`tr(key, **values)` loads `locales/ru.json` and `locales/en.json` using package
resources. Field and role definitions contain keys rather than displayed text.
The interface retranslates existing widgets and dynamic statuses, preserving
user-entered data, selection and pending edits. Historical log entries retain
the language in which they were generated. Preference changes are disabled
while a metadata job is running. Themes use explicit Fusion palettes for
active, inactive and disabled controls.

## Build and resources

`FilmMeta.spec` analyzes `run_filmmeta.py`, includes native pyexiv2 files and
collects package data. About and the application icon use `importlib.resources`
to find packaged resources. The Windows script invokes the spec from the
project directory. The source archive contains the entire package and launcher.

## Tests

Tests are grouped into metadata, presets, interface and entry-point checks.
Shared image fixtures are in `tests/helpers.py`. Tests patch the responsible
reader or writer module rather than relying on a global single-file namespace.
See [VALIDATION.md](VALIDATION.md) for the recorded validation.
