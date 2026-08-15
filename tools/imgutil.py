"""Shared image-saving helper.

Reference sheets live in docs/images and are committed, so they need to be small.
They are dithered and flat-shaded -- a handful of distinct colours across the
whole image -- so an adaptive palette costs nothing visually and cuts them by
roughly two thirds. Truecolour PNG on this content is pure waste.
"""

from pathlib import Path

from PIL import Image


def save_compact(img: Image.Image, path: Path, colors: int = 64) -> int:
    """Write as a palette PNG. Returns the size in bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("P", palette=Image.ADAPTIVE, colors=colors).save(
        path, "PNG", optimize=True)
    return path.stat().st_size


def report(path: Path) -> str:
    kb = path.stat().st_size / 1024
    return f"{path.name:<28} {kb:>6.0f} KB"
