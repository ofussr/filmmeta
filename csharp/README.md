# FilmMeta — C# read prototype

This directory starts the native rewrite of FilmMeta. It contains a shared C# field model, a read-only metadata adapter, and a console application. The existing Python application remains the reference implementation.

The prototype reads JPEG, classic TIFF, and DNG images, reports all 29 FilmMeta fields and the source of each value, and accepts individual files or folders. It does not write images. Qt/QML, settings migration, metadata writing, and Steam integration are later milestones.

## Download and run on Windows

Open the **C# prototype** workflow in [GitHub Actions](https://github.com/ofussr/filmmeta/actions/workflows/csharp.yml), select a successful run for `rewrite/csharp`, and download the `FilmMeta-Cli-win-x64` artifact. Extract the entire archive to one directory. The published application includes its .NET runtime; no Python, Qt, Rider, or SDK is required to run it.

In PowerShell, from that directory:

```powershell
.\FilmMeta.Cli.exe read "D:\Photos\frame.tif"
.\FilmMeta.Cli.exe read "D:\Photos\Film scans" --recursive
.\FilmMeta.Cli.exe read "D:\Photos\Film scans" --recursive --json > metadata.json
.\FilmMeta.Cli.exe fields
.\FilmMeta.Cli.exe --version
```

`--json` produces one complete report with `files`, `errors`, and `cancelled`. Values use stable identifiers such as `film.name`, `camera.model`, and `copy_lens.serial`. Empty fields remain present in JSON; text output displays populated fields. `sources` identifies the actual selected XMP or EXIF tag. `exif` and `xmp` expose the relevant raw values for diagnosis, not every unrelated tag in the image. The report is written to stdout; the application creates no report file unless the shell redirects its output.

A folder is scanned without subfolders unless `--recursive` is supplied. Symbolic links and directory junctions are skipped during folder traversal. Repeated paths are deduplicated. A failure in one image is reported while processing continues for the others. Exit codes: `0` success, `1` file errors, `2` invalid arguments, `130` cancellation. Ctrl+C cancels between files; the current parser call must finish before cancellation is observed.

## Build in Rider or the .NET CLI

Install the .NET 10 SDK, open `FilmMeta.slnx` in Rider, and restore NuGet packages. From this directory:

```powershell
dotnet restore FilmMeta.slnx --locked-mode
dotnet build FilmMeta.slnx -c Release --no-restore
dotnet run --project tests/FilmMeta.Tests -c Release --no-build
dotnet run --project src/FilmMeta.Cli -c Release -- read "D:\Photos\frame.tif" --json
```

To publish a self-contained Windows x64 package:

```powershell
dotnet publish src/FilmMeta.Cli -c Release -r win-x64 --self-contained true -o artifacts/win-x64
```

The workflow adds the application and dependency license files to the published package. For redistribution, preserve those files. The application version is set in `Directory.Build.props`. It is independent of the unchanged Python application version. The verified SDK is 10.0.401; NuGet dependency graphs and package hashes are committed in `packages.lock.json` files. Runtime-specific publishing may extend the local restore graph; the committed locks describe the ordinary solution build.

## Components

| Project | Responsibility |
| --- | --- |
| `FilmMeta.Core` | Field catalog, field precedence, DNG routing, shared result model |
| `FilmMeta.Metadata` | Read-only MetadataExtractor/XmpCore adapter and input validation |
| `FilmMeta.Cli` | File/folder input, reports, per-file errors, cancellation |
| `FilmMeta.Tests` | Python-oracle compatibility, file preservation, CLI behavior |

The runtime does not import or launch Python and does not use pyexiv2 or Exiv2. Reading currently uses **MetadataExtractor 2.9.3** and **XmpCore 6.1.10.1**. These libraries solve metadata reading; a safe replacement for image metadata writing is not yet selected.

## Compatibility contract

- Own XMP namespace: `urn:filmmeta:metadata:1.0/`. Property names and stable field identifiers are defined in `src/FilmMeta.Core/Resources/fields.json`.
- Priority: nonempty own FilmMeta value, then a compatible AnalogExif value, then standard EXIF/XMP where the existing implementation permits it. Whitespace-only custom values allow fallback.
- AnalogExif URI variants with and without a trailing slash are accepted. XML prefixes are not used to establish identity. Film and scanner names have a leading manufacturer removed only at a complete word boundary, as in the Python implementation.
- Standard camera/lens tags are not assigned to original film equipment in DNG. An explicit `DigitizationType` routes them to the digitizer camera/lens or scanner. Legacy scanner fields can imply the scan method. DNG detection also checks the DNGVersion tag if the extension is TIFF.
- Standard EXIF is preferred over standard XMP. ISO uses ISO Speed Ratings, Recommended Exposure Index, and ISO Speed, followed by the existing XMP alternatives.
- The catalog retains the same 14 default-visible fields. UI field selection is not implemented in this console milestone.
- To keep the current compatibility boundary, BigTIFF and files of 2 GB or larger are rejected even when a library might read them. Reading uses read-only file access, closes the file handle, and does not change modification times or file contents.
- Parser warnings are included in the report. Empty values do not prove the absence of metadata if parsing produced warnings.
- Current settings defaults: Russian language, light theme, AnalogExif mirroring off, standard EXIF writing off. The Python settings file is a JSON object; presets use a version-1 object with films, cameras, lenses, and scanners. These formats are recorded for later migration; the CLI does not read or modify them.
- Future writing must preserve the current blank-field behavior, inactive digitization-role rules, per-file legacy full-name assembly, and digitizer EXIF snapshots. It will require independent integrity tests before writing originals.

## Verification and next milestone

The fixture manifest contains 28 synthetic JPEG/TIFF/DNG inputs and their expected values and tag sources, captured from Python commit `795d83c0e42be50c95cc9a20de7da8a666dd4c74`. Fixtures were created locally using the existing test utilities and pyexiv2; Python is not needed to run the C# tests. They contain generated pixels and invented metadata, not personal photographs. Tests compare the two implementations, verify byte hashes and modification times, and check released file handles, invalid inputs, directory traversal, error reporting, and cancellation.

CI builds and tests on Windows and Linux, then exercises the actual self-contained Windows executable before uploading it. A successful run is a prerequisite for using an artifact. These checks do not replace testing the user's real scans or establish that the later Qt or Steam integrations work.

Next: validate this reader on existing populated scans, select and verify a safe metadata writer, and separately build the small Qt/QML and Steam prototypes.

## License

FilmMeta source uses the repository's [MIT license](../LICENSE). MetadataExtractor uses Apache-2.0; XmpCore declares BSD-3-Clause. The bundled .NET runtime has its own license and third-party notices. See `THIRD_PARTY_NOTICES.txt` and the license files included with a published artifact.
