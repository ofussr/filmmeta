import time

import numpy as np
import pyexiv2
import tifffile
from PIL import Image, ImageCms


def modify(path, exif=None, xmp=None):
    with pyexiv2.ImageData(path.read_bytes()) as image:
        if exif:
            image.modify_exif(exif)
        if xmp:
            image.modify_xmp(xmp)
        output = image.get_bytes()
    path.write_bytes(output)


def picture(tmp_path, kind="tiff"):
    directory = tmp_path / "Фото" / "Зенит ET" / "Мирущенко Михаил"
    directory.mkdir(parents=True, exist_ok=True)
    if kind == "jpeg":
        path = directory / "кадр.JPG"
        pixels = np.arange(16 * 18 * 3, dtype=np.uint8).reshape(16, 18, 3)
        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        Image.fromarray(pixels).save(path, quality=95, icc_profile=icc)
    elif kind == "float64":
        path = directory / "64 бита.TIF"
        pixels = np.linspace(-12.5, 8.75, 16 * 18, dtype=np.float64).reshape(16, 18)
        tifffile.imwrite(path, pixels, metadata=None)
    elif kind == "dng":
        path = directory / "негатив.DNG"
        pixels = np.arange(16 * 18, dtype=np.uint16).reshape(16, 18)
        tifffile.imwrite(
            path,
            pixels,
            metadata=None,
            photometric=32803,
            extratags=[
                (271, "s", 0, "Digitizer", False),
                (272, "s", 0, "RAW Camera", False),
                (33421, "H", 2, (2, 2), False),
                (33422, "B", 4, (0, 1, 1, 2), False),
                (50706, "B", 4, (1, 4, 0, 0), False),
                (50707, "B", 4, (1, 1, 0, 0), False),
                (50708, "s", 0, "Digitizer RAW Camera", False),
                (
                    50721,
                    "2i",
                    9,
                    (1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1),
                    False,
                ),
            ],
        )
    else:
        path = directory / "A001045-R1-00-1.TIF"
        pixels = np.arange(16 * 18 * 3, dtype=np.uint8).reshape(16, 18, 3)
        tifffile.imwrite(path, pixels, photometric="rgb", metadata=None)
    return path


def wait_job(window, application, seconds=10):
    deadline = time.monotonic() + seconds
    while window.job is not None and time.monotonic() < deadline:
        application.processEvents()
        # Yield Python execution so background Qt workers can make progress.
        time.sleep(0.002)
    application.processEvents()
    assert window.job is None, "Background processing did not finish"


def jpeg_scan(data):
    assert data[:2] == b"\xff\xd8"
    offset = 2
    while offset < len(data):
        assert data[offset] == 255
        marker = data[offset + 1]
        size = int.from_bytes(data[offset + 2 : offset + 4], "big")
        if marker == 0xDA:
            return data[offset:]
        offset += 2 + size
    raise AssertionError("No JPEG scan")
