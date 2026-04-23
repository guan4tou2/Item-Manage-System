#!/usr/bin/env python3
"""Generate solid-color PNG placeholder icons for PWA."""
import struct
import zlib
from pathlib import Path


def write_solid_png(path: Path, size: int, rgb: tuple[int, int, int]) -> None:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * size
    raw = row * size
    idat = zlib.compress(raw)
    path.write_bytes(
        signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    out_dir = Path(__file__).parent.parent / "public" / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)
    color = (37, 99, 235)  # #2563eb
    write_solid_png(out_dir / "icon-192.png", 192, color)
    write_solid_png(out_dir / "icon-512.png", 512, color)
    print(f"wrote {out_dir}/icon-192.png and icon-512.png")
