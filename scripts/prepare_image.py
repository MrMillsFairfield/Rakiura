#!/usr/bin/env python3
"""
Resize and compress a photo and save it where the site expects it.

Big camera photos make pages slow on school Chromebooks. This shrinks them to a sensible
size (usually 100 to 400 KB).

Usage (run from the site folder, the one containing index.html)
  pip install pillow

  python scripts/prepare_image.py ~/Downloads/beach.jpg --as backdrop --name tourism
  python scripts/prepare_image.py ~/Downloads/beach.jpg --as hero
  python scripts/prepare_image.py ~/Downloads/kiwi.jpg  --as card   --name wildlife
  python scripts/prepare_image.py ~/Downloads/kiwi.jpg  --as source --name te-ara-plants-and-animals/kiwi

What each one is
  backdrop img/backdrops/<page>.jpg         background behind one page and its sources
                                            --name home | general | history | wildlife | tourism
  hero    img/hero.jpg                      spare background for any page without its own (optional)
  card    img/cards/<section>.jpg           picture on a home page card
                                            --name general | history | wildlife | tourism
  source  img/sources/<folder>/<file>.jpg   a picture for one source (its card cover or page)
                                            --name <source-folder>/<file-name>

Keep a note of who took each photo and its licence, for your credits.
"""
import argparse
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("This script needs Pillow. Install it with:  pip install pillow")

SITE = Path(__file__).resolve().parent.parent
SECTIONS = ("general", "history", "wildlife", "tourism")
PAGES = ("home",) + SECTIONS
KINDS = {"backdrop": (1920, 78), "hero": (1920, 78), "card": (900, 82), "source": (1000, 82)}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--as", dest="kind", required=True, choices=KINDS)
    ap.add_argument("--name")
    args = ap.parse_args()
    max_w, quality = KINDS[args.kind]

    if args.kind == "hero":
        out = SITE / "img" / "hero.jpg"
    elif args.kind == "backdrop":
        if args.name not in PAGES:
            sys.exit("--name for backdrop must be one of: " + ", ".join(PAGES))
        out = SITE / "img" / "backdrops" / f"{args.name}.jpg"
    elif args.kind == "card":
        if args.name not in SECTIONS:
            sys.exit("--name for card must be one of: " + ", ".join(SECTIONS))
        out = SITE / "img" / "cards" / f"{args.name}.jpg"
    else:
        if not args.name or "/" not in args.name:
            sys.exit("--name for source must look like  source-folder/file-name")
        folder, fname = (slug(x) for x in args.name.split("/", 1))
        out = SITE / "img" / "sources" / folder / f"{fname}.jpg"

    src = Path(args.input).expanduser()
    if not src.is_file():
        sys.exit(f"Can't find {src}")
    im = ImageOps.exif_transpose(Image.open(src))
    if im.mode in ("RGBA", "LA", "P"):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (14, 23, 27))
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
    kb = out.stat().st_size / 1024
    print(f"Saved {out.relative_to(SITE)}  ({im.width} x {im.height}, {kb:.0f} KB)")
    if kb > 600:
        print("  That is still large. A less detailed photo will compress better.")
    print("Remember to note the photographer and licence for your credits.")


if __name__ == "__main__":
    main()
