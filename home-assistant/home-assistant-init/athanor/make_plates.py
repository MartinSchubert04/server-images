"""Inks the one-color plates of the portfolio for Home Assistant. Needs Pillow, so it runs inside the
homeassistant container:

    python3 make_plates.py <plates-src dir> <output dir>

The source PNGs are a single color on transparent. Nothing is rescaled: a dithered image is only
cropped, as DESIGN.md asks.
"""

import sys
from pathlib import Path

from PIL import Image

src, out = Path(sys.argv[1]), Path(sys.argv[2])

# Plate ink of each palette. On the light ones the sidebar is paper, so the plate is inked in `tan`
PLATE = {"srcery": "#baa67f", "umber": "#c9b994", "cinnabar": "#d6ad94", "vellum": "#473c30", "orpiment": "#473922"}
TAN = "#baa67f"

SIDE_PLATE = "friedrich-wanderer.png"
# The wanderer and the top of his rock, 224px wide: the open sidebar minus a 16px margin on each side
SIDE_BOX = (144, 192, 368, 448)


def ink(image: Image.Image, color: str) -> Image.Image:
    alpha = image.convert("RGBA").getchannel("A")
    flat = Image.new("RGBA", image.size, color)
    flat.putalpha(alpha)
    return flat


def save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


side = Image.open(src / SIDE_PLATE).crop(SIDE_BOX)
for palette, color in PLATE.items():
    save(ink(side, color), out / f"side-{palette}.png")

# Full plates in the plate ink, for picture cards
for plate in sorted(src.glob("*.png")):
    save(ink(Image.open(plate), TAN), out / "tan" / plate.name)

print(len(list(out.rglob("*.png"))), "images in", out)
