#!/usr/bin/env python3
"""
Pull every picture and logo out of a page saved with the SingleFile extension.

SingleFile stores a page's pictures inside the .html file. This script saves them as
separate files in  _extracted/<page-name>/  and writes an index.html contact sheet there,
so you can open it, see everything, and choose what to use (logos, photos, icons).

Usage
  python scripts/extract_media.py ~/Downloads/saved_page.html
Then open  _extracted/<page-name>/index.html  in your browser.
Copy the files you want into img/logos/ or img/sources/<source-name>/, then use
scripts/prepare_image.py to shrink big photos.

Only for your own use: _extracted/ is not part of the site, don't upload it.
"""
import base64
import hashlib
import html
import re
import sys
from pathlib import Path

EXT = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/gif": "gif",
       "image/webp": "webp", "image/svg+xml": "svg", "image/avif": "avif"}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1]).expanduser()
    raw = src.read_text(encoding="utf-8", errors="replace")
    out = Path(__file__).resolve().parent.parent / "_extracted" / re.sub(r"[^a-zA-Z0-9]+", "-", src.stem).strip("-")[:50]
    out.mkdir(parents=True, exist_ok=True)

    rows, seen = [], set()
    for m in re.finditer(r"data:(image/[a-z+.\-]+);base64,([A-Za-z0-9+/=%]+)", raw):
        mime, payload = m.group(1), m.group(2)
        if mime not in EXT or len(payload) < 400:
            continue
        try:
            data = base64.b64decode(payload)
        except Exception:  # noqa: BLE001
            continue
        digest = hashlib.md5(data).hexdigest()[:8]
        if digest in seen:
            continue
        seen.add(digest)
        name = f"{len(rows) + 1:02d}_{digest}.{EXT[mime]}"
        (out / name).write_bytes(data)
        before = raw[max(0, m.start() - 400):m.start()]
        alt = re.findall(r'alt="([^"]*)"', before + raw[m.end():m.end() + 300])
        rows.append((name, len(data) // 1024, alt[-1] if alt else ""))

    cells = "\n".join(
        f'<figure><img src="{n}" alt=""><figcaption><b>{n}</b><br>{kb} KB<br>{html.escape(a)}</figcaption></figure>'
        for n, kb, a in rows)
    (out / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Extracted pictures</title>'
        '<style>body{font:14px system-ui;background:#ddd;margin:16px}figure{display:inline-block;'
        'vertical-align:top;width:220px;margin:8px;padding:8px;background:#fff;border-radius:8px}'
        'img{max-width:100%;max-height:150px;background:#888;display:block;margin-bottom:6px}</style>'
        f"<h1>{len(rows)} pictures from {html.escape(src.name)}</h1>{cells}", encoding="utf-8")
    print(f"Saved {len(rows)} pictures to {out}\nOpen {out / 'index.html'} in your browser.")


if __name__ == "__main__":
    main()
