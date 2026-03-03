from pathlib import Path
import zlib


def _load_png_pixels(path: Path):
    data = path.read_bytes()
    signature = b"\x89PNG\r\n\x1a\n"
    assert data.startswith(signature), f"Not a PNG file: {path}"

    offset = len(signature)
    width = height = None
    color_type = None
    idat = bytearray()

    while offset < len(data):
        chunk_len = int.from_bytes(data[offset : offset + 4], "big")
        offset += 4
        chunk_type = data[offset : offset + 4]
        offset += 4
        chunk = data[offset : offset + chunk_len]
        offset += chunk_len
        offset += 4  # skip CRC

        if chunk_type == b"IHDR":
            width = int.from_bytes(chunk[0:4], "big")
            height = int.from_bytes(chunk[4:8], "big")
            bit_depth = chunk[8]
            color_type = chunk[9]
            assert bit_depth == 8, "Only 8-bit PNG icons are supported by this test"
            assert color_type in {2, 6}, "Only RGB/RGBA PNG icons are supported by this test"
        elif chunk_type == b"IDAT":
            idat.extend(chunk)
        elif chunk_type == b"IEND":
            break

    assert width is not None and height is not None and color_type is not None

    bytes_per_pixel = 4 if color_type == 6 else 3
    stride = width * bytes_per_pixel
    raw = zlib.decompress(bytes(idat))
    pixels = bytearray(height * stride)

    def paeth(a: int, b: int, c: int) -> int:
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    src = 0
    for y in range(height):
        filter_type = raw[src]
        src += 1
        row = raw[src : src + stride]
        src += stride
        row_start = y * stride

        if filter_type == 0:
            pixels[row_start : row_start + stride] = row
            continue

        prev_row_start = (y - 1) * stride
        for x in range(stride):
            left = pixels[row_start + x - bytes_per_pixel] if x >= bytes_per_pixel else 0
            up = pixels[prev_row_start + x] if y > 0 else 0
            up_left = pixels[prev_row_start + x - bytes_per_pixel] if (y > 0 and x >= bytes_per_pixel) else 0

            if filter_type == 1:
                value = (row[x] + left) & 0xFF
            elif filter_type == 2:
                value = (row[x] + up) & 0xFF
            elif filter_type == 3:
                value = (row[x] + ((left + up) >> 1)) & 0xFF
            elif filter_type == 4:
                value = (row[x] + paeth(left, up, up_left)) & 0xFF
            else:
                raise AssertionError(f"Unsupported PNG filter type {filter_type}")

            pixels[row_start + x] = value

    return width, height, color_type, pixels, bytes_per_pixel


def _alpha_margins(path: Path):
    width, height, color_type, pixels, bytes_per_pixel = _load_png_pixels(path)

    min_x = width
    min_y = height
    max_x = -1
    max_y = -1

    for y in range(height):
        row_start = y * width * bytes_per_pixel
        for x in range(width):
            alpha = pixels[row_start + x * bytes_per_pixel + 3] if color_type == 6 else 255
            if alpha == 0:
                continue

            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    assert max_x != -1 and max_y != -1, f"Icon is fully transparent: {path}"

    left = min_x
    top = min_y
    right = width - 1 - max_x
    bottom = height - 1 - max_y
    return left, top, right, bottom


def test_desktop_icons_have_optical_padding():
    repo_root = Path(__file__).resolve().parents[2]
    large_icon = repo_root / "src-tauri" / "icons" / "icon.png"
    medium_icon = repo_root / "src-tauri" / "icons" / "128x128.png"

    assert large_icon.exists()
    assert medium_icon.exists()

    large_margins = _alpha_margins(large_icon)
    medium_margins = _alpha_margins(medium_icon)

    assert min(large_margins) >= 30, f"icon.png margins are too small: {large_margins}"
    assert min(medium_margins) >= 8, f"128x128.png margins are too small: {medium_margins}"
