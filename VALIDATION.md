# FilmMeta 0.1.4 validation

## Automated checks

The complete suite passed **53 tests** in a Linux Qt offscreen environment.

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

The test runtime used Python 3.12, PySide6 6.11.2 and pyexiv2 2.16.0 with
Exiv2 0.28.8. Test dependencies include pytest, Pillow, NumPy and tifffile.

| Area | Recorded coverage |
| --- | --- |
| Metadata | JPEG, classic TIFF, float64 TIFF and synthetic CFA DNG round trips through Cyrillic paths |
| Image contents | Exact JPEG compressed scan/ICC preservation; equal TIFF pixel arrays and sample types |
| Existing values | Standard EXIF/XMP fallback, custom-field precedence and alternate XMP prefixes |
| AnalogExif | Literal-URI XMP fixtures with alternate prefixes; own-first reading, preserved shared values by default, optional mirrors and full names; partial/batch edits; additional-field round trips in JPEG/TIFF/DNG |
| DNG | Technical equipment and calibration preservation; detection of changed calibration values |
| Backup/replacement | Exact original backups, unique backup names, failed verification/replacement and concurrent source changes |
| Editing | Changed nonempty fields only; hidden fields excluded from presets and writes; hiding drops only that field's pending edit |
| Preferences | Original visible set and own-only defaults; JSON reload, invalid values, failed commit and Settings cancellation/save |
| Language/theme | Matching translation keys/placeholders; live EN/RU and dark/light changes preserve values, dirty fields and selection |
| Personal lists | JSON add/edit/delete, duplicate rejection, ISO normalization and failed-commit preservation |
| Interface | Existing/mixed values, AnalogExif form loading and editing, failed-file state, explicit preset saving, stale read-result rejection and mixed digitisation batches |
| About/resources | Application version, author, contact, dependency notices and a nonempty icon |
| Entry points | Both `--version` commands run without site packages; core JSON and image read/write operate without Qt; real Qt startup exits cleanly |

## Packaging and visual checks

The PyInstaller spec produced a Linux one-file executable with PyInstaller
6.22.3. Its `--version` command returned `FilmMeta 0.1.4`. An offscreen launch
remained running without an import/startup exception before being terminated by
the check. This startup check does not establish full packaged GUI behavior.

The main window in both themes, Settings and About were rendered and inspected
in the source runtime.
The icon, contact address, version and dependency information were visible.
The README screenshots use small generated fixtures, not user photographs.

## Remaining checks and limits

No Windows executable was built or launched in this environment. The supplied
PyInstaller spec and build script still require a native Windows build and
startup check, including the Windows executable icon. Windows mapped drives
and UNC access have not been exercised.

DNG fixtures are synthetic TIFF-based examples. They do not certify every
vendor's DNG layout. Classic TIFF float64 tests concern sample depth, not
BigTIFF's 64-bit offsets. BigTIFF remains unsupported.

AnalogExif compatibility checks use independently authored fixtures based on
the published property definitions and registered namespace. The actual
AnalogExif application was not launched, and no `.ael` preset import is supplied.

The tests use small fixtures. They do not establish memory use or processing
time for the user's approximately 299 MB TIFF. Reading and writing retain
the existing in-memory path and size limits.
