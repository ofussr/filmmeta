# Third-party components

FilmMeta uses these separately installed runtime components:

| Component | Purpose | Upstream licensing information |
| --- | --- | --- |
| [PySide6](https://doc.qt.io/qtforpython-6/) | Qt user interface | LGPLv3 / GPLv3 / commercial options; see upstream distribution |
| [pyexiv2](https://github.com/LeoHsiao1/pyexiv2) | Python metadata interface | GPLv3, as declared in its package metadata |
| [Exiv2](https://exiv2.org/) | Native metadata library included by pyexiv2 | GPLv2 or later; see upstream distribution |

Original FilmMeta source is licensed under the MIT License (see LICENSE). Third-party components retain their upstream licenses; FilmMeta's MIT license does not grant additional rights to them. Distribution of an application linked with GPL-licensed pyexiv2 must comply with the GPL for the combined work, including corresponding-source requirements.

The optional development dependencies (pytest, Pillow, NumPy, tifffile and PyInstaller) are used for tests or packaging; they are not needed for normal source execution.
