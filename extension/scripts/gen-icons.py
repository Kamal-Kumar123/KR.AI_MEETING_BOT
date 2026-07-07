"""Generate small, valid PNG icons (16/48/128) for the extension.

Chrome notifications fail to load oversized images, so we render compact
brand icons: a purple rounded square with a white record dot.
No external dependencies (pure zlib + struct PNG encoder).
"""
import os
import struct
import zlib

BG = (109, 94, 252, 255)      # brand purple #6d5efc
DOT = (255, 255, 255, 255)    # white record dot
TRANSPARENT = (0, 0, 0, 0)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "icons")


def make_pixels(size: int):
    radius = size * 0.22          # rounded corners
    cx = cy = (size - 1) / 2.0
    dot_r = size * 0.30           # white circle radius
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            # rounded-rect background mask
            inside = True
            corners = [
                (radius, radius),
                (size - radius, radius),
                (radius, size - radius),
                (size - radius, size - radius),
            ]
            # only test corner regions
            if x < radius and y < radius:
                inside = (x - radius) ** 2 + (y - radius) ** 2 <= radius ** 2
            elif x > size - radius and y < radius:
                inside = (x - (size - radius)) ** 2 + (y - radius) ** 2 <= radius ** 2
            elif x < radius and y > size - radius:
                inside = (x - radius) ** 2 + (y - (size - radius)) ** 2 <= radius ** 2
            elif x > size - radius and y > size - radius:
                inside = (x - (size - radius)) ** 2 + (y - (size - radius)) ** 2 <= radius ** 2

            if not inside:
                row += bytes(TRANSPARENT)
                continue

            # white record dot in the center
            if (x - cx) ** 2 + (y - cy) ** 2 <= dot_r ** 2:
                row += bytes(DOT)
            else:
                row += bytes(BG)
        rows.append(bytes(row))
    return rows


def write_png(path: str, size: int):
    rows = make_pixels(size)
    raw = bytearray()
    for row in rows:
        raw += b"\x00" + row  # filter type 0 per scanline

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for s in (16, 48, 128):
        out = os.path.join(OUT_DIR, f"icon{s}.png")
        write_png(out, s)
        print(f"wrote {out} ({os.path.getsize(out)} bytes)")
