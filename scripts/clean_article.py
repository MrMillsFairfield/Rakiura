#!/usr/bin/env python3
"""
Turn a saved web page into a clean, link-free source page for the Rakiura site.

What it does
  * keeps only the article text, headings, lists, tables and pictures
  * removes scripts, iframes, forms, menus, ads and buttons
  * turns EVERY link into plain text (nothing clickable leads out of the site)
  * stores the page's own pictures as local files (needs a page saved with SingleFile,
    which embeds the pictures inside the .html file)
  * shows the site's logo and a one-line APA 7 reference at the top
  * writes sources/<slug>.html and prints the card to paste into a section page

Usage (run from the site folder, the one containing index.html)
  pip install beautifulsoup4 pillow

  python scripts/clean_article.py ~/Downloads/page.html \\
      --section wildlife --slug te-ara-plants-and-animals \\
      --title "Plants and animals" \\
      --author "Walrond, C." --date "2015, May 1" \\
      --apa-title "Stewart Island/Rakiura: Plants and animals" \\
      --site "Te Ara – The Encyclopedia of New Zealand" \\
      --url "https://teara.govt.nz/en/stewart-islandrakiura/page-2" \\
      --logo img/logos/teara.svg --logo-alt "Te Ara" \\
      --desc "Forests, alpine plants, kiwi, kākāpō, penguins and sea lions."

APA fields (APA 7 reference for a web page)
  --author     "Surname, A."  or an organisation name. Leave out for no author.
  --date       "2019, December 6"  (year, month day). Leave out when there is no date: shows (n.d.).
  --apa-title  title as it should appear in the reference (default: --title)
  --site       website name. Leave out when it is the same as the author.
  --kind       e.g. "Blog post", shown in square brackets after the title
  --url        the web address, shown as plain text

Pictures
  --hero  "img/sources/slug/hero.jpg|Caption|Credit"   one big picture, beside the first paragraph
  --image "img/sources/slug/kiwi.jpg|Caption|Credit"   a picture, spread down the text (repeatable)
          (Credit is optional. Use it for a picture that comes from a different website.)
  --image-names a,b,c   file names for pictures found inside the article, in order
  --no-content-images   ignore pictures found inside the article

Page clean-up
  --select "article"   CSS selector for the part of the page to keep (default: the script guesses)
  --remove ".sidebar"  delete something from the kept part (repeatable)
"""

import argparse
import base64
import html
import io
import re
import sys
from pathlib import Path

try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    sys.exit("This script needs BeautifulSoup. Install it with:  pip install beautifulsoup4")
try:
    from PIL import Image
except ImportError:
    Image = None

SITE = Path(__file__).resolve().parent.parent

SECTIONS = {
    "general":  ("general.html",  "General Information"),
    "history":  ("history.html",  "History"),
    "wildlife": ("wildlife.html", "Native Wildlife"),
    "tourism":  ("tourism.html",  "Tourism"),
}

DROP_TAGS = {
    "script", "style", "noscript", "iframe", "object", "embed", "form", "input", "button",
    "select", "textarea", "option", "label", "nav", "header", "footer", "aside", "svg",
    "canvas", "video", "audio", "source", "track", "link", "meta", "base", "template",
    "dialog", "map", "area", "head", "title",
}
JUNK_WORDS = {
    "navbox", "navbar", "navigation", "sidebar", "menu", "breadcrumb", "breadcrumbs", "toc",
    "catlinks", "printfooter", "mw-editsection", "mw-jump-link", "noprint", "metadata",
    "hatnote", "mbox", "ambox", "sistersitebox", "authority-control", "reflist", "references",
    "reference", "advert", "advertisement", "ads", "ad", "cookie", "cookies", "consent",
    "newsletter", "subscribe", "signup", "share", "sharing", "social", "comments", "comment",
    "related", "recommended", "promo", "popup", "modal", "banner", "skip-link",
    "visually-hidden", "sr-only",
}
ALLOWED_TAGS = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "dl", "dt", "dd", "strong", "b",
    "em", "i", "u", "sup", "sub", "small", "mark", "cite", "q", "abbr", "time", "blockquote",
    "br", "hr", "pre", "code", "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption",
    "figure", "figcaption", "img", "div", "section", "article",
}
ALLOWED_ATTRS = {
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan", "scope"}, "ol": {"start"},
}
MAIN_SELECTORS = ["#mw-content-text", "article", "main", "[role=main]", "#content",
                  ".post-content", ".entry-content", ".article-body", ".content"]


def slugify(text):
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()[:60] or "source"


def esc(s):
    return html.escape(s, quote=True)


def dead(tag):
    return getattr(tag, "_decomposed", False)


def is_junk(tag):
    attrs = getattr(tag, "attrs", None)
    if not attrs:
        return False
    words = set()
    for key in ("class", "id"):
        val = attrs.get(key)
        if val:
            words.update(v.lower() for v in (val.split() if isinstance(val, str) else val))
    return bool(words & JUNK_WORDS)


def pick_main(soup):
    for sel in MAIN_SELECTORS:
        found = soup.select_one(sel)
        if found and len(found.get_text(strip=True)) > 200:
            return found
    return soup.body or soup


def guess_title(soup):
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(" ", strip=True)
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    return "Untitled source"


def save_embedded_image(src, slug, name, report):
    """Store a data: picture as a local file. Returns (site-relative path, w, h) or None."""
    try:
        header, b64 = src.split(",", 1)
        data = base64.b64decode(b64)
    except Exception:  # noqa: BLE001
        return None
    if header.startswith("data:image/svg"):      # SVG can carry scripts: skip
        return None
    if Image is None:
        sys.exit("Pictures need Pillow. Install it with:  pip install pillow")
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:  # noqa: BLE001
        return None
    if im.width < 80 or im.height < 80:           # icons and spacers
        return None
    if im.width > 1000:
        im = im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)
    out_dir = SITE / "img" / "sources" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    keep_png = im.format == "PNG" and im.mode in ("RGBA", "LA", "P")
    ext = ".png" if keep_png else ".jpg"
    fname = f"{name}{ext}"
    if keep_png:
        im.save(out_dir / fname, "PNG", optimize=True)
    else:
        im.convert("RGB").save(out_dir / fname, "JPEG", quality=82, optimize=True, progressive=True)
    report["images"] += 1
    return f"img/sources/{slug}/{fname}", im.width, im.height


def clean(main, slug, title, remove_selectors, content_images, image_names):
    report = {"links": 0, "images": 0, "dropped": 0}

    for c in main.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for sel in remove_selectors:
        for tag in main.select(sel):
            if not dead(tag):
                tag.decompose()
    for a in main.find_all("a"):                  # "Back" links in footnotes
        if not dead(a) and a.get_text(strip=True).lower() in {"back", "↩", "↑", "return"}:
            a.decompose()
    for tag in list(main.find_all(True)):
        if dead(tag):
            continue
        if tag.name in DROP_TAGS or is_junk(tag):
            tag.decompose()
    for tag in list(main.find_all(True)):
        if dead(tag):
            continue
        if (tag.has_attr("hidden") or tag.get("aria-hidden") == "true") and tag.name != "img":
            tag.decompose()

    for pic in main.find_all("picture"):
        pic.unwrap()
    n = 0
    for img in list(main.find_all("img")):
        src = (img.get("src") or img.get("data-src") or img.get("data-original") or "").strip()
        stored = None
        if content_images and src.startswith("data:image/"):
            name = image_names[n] if n < len(image_names) else f"img{n + 1:02d}"
            stored = save_embedded_image(src, slug, name, report)
            n += 1
        if stored is None:
            report["dropped"] += 1
            img.decompose()
        else:
            path, w, h = stored
            img["src"] = "../" + path
            img["width"], img["height"] = str(w), str(h)

    for a in main.find_all("a"):                  # every link becomes plain text
        report["links"] += 1
        a.unwrap()

    for box in main.find_all("div"):              # call-out boxes and labels
        classes = box.get("class") or []
        if "topicbox" in classes:
            box.name = "blockquote"
        elif "field__label" in classes:
            box.name = "h2"

    for p in main.find_all("p"):                  # pages that never close <p> tags
        while True:
            inner = p.find("p")
            if inner is None:
                break
            inner.extract()
            p.insert_after(inner)

    for fig in main.find_all("figure"):           # caption doubles as alt text
        cap, img = fig.find("figcaption"), fig.find("img")
        if img is not None and cap is not None and not (img.get("alt") or "").strip():
            img["alt"] = cap.get_text(" ", strip=True)

    for tag in main.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()
    for tag in main.find_all(True):
        keep = ALLOWED_ATTRS.get(tag.name, set())
        for attr in list(tag.attrs):
            if attr not in keep:
                del tag.attrs[attr]

    norm = lambda s: re.sub(r"\W+", "", s).lower()
    first = main.find(["h1", "h2"])
    if first and norm(first.get_text()) == norm(title):
        first.decompose()
    for h1 in main.find_all("h1"):
        h1.name = "h2"
    for _ in range(3):
        for tag in main.find_all(["p", "div", "section", "article", "li", "ul", "ol", "figure",
                                  "figcaption", "blockquote", "tr", "table"]):
            if not tag.get_text(strip=True) and not tag.find("img"):
                tag.decompose()
    return report


def apa_html(author, date, title, kind, site, url):
    out = ""
    if author:
        out += esc(author) + ("" if author.rstrip().endswith(".") else ".") + " "
    out += f"({esc(date) if date else 'n.d.'}). "
    out += f"<em>{esc(title)}</em>"
    if kind:
        out += f" [{esc(kind)}]"
    out += ". "
    if site and site.strip().rstrip(".") != (author or "").strip().rstrip("."):
        out += esc(site) + ". "
    if url:
        out += esc(url)
    return out.strip()


def parse_image_arg(arg):
    parts = [p.strip() for p in arg.split("|")]
    path = parts[0]
    if not (SITE / path).is_file():
        sys.exit(f"Can't find picture {path} (give the path from the site folder, e.g. img/sources/...)")
    size = (0, 0)
    if Image is not None:
        with Image.open(SITE / path) as im:
            size = im.size
    return {"path": path, "caption": parts[1] if len(parts) > 1 else "",
            "credit": parts[2] if len(parts) > 2 else "", "w": size[0], "h": size[1]}


def figure_html(im, extra_class=""):
    dims = f' width="{im["w"]}" height="{im["h"]}"' if im["w"] else ""
    cap = esc(im["caption"])
    credit = f'<span class="credit">{esc(im["credit"])}</span>' if im["credit"] else ""
    figcap = f"<figcaption>{cap}{credit}</figcaption>" if (cap or credit) else ""
    return f'<figure{extra_class}><img src="../{esc(im["path"])}" alt="{cap}"{dims} loading="lazy">{figcap}</figure>'


def spread_pictures(node, hero, imgs):
    """Put the pictures inside the text, beside paragraphs, instead of in a strip at the top.
    The hero picture goes beside the first long paragraph; the others are spaced evenly down the
    page, alternating right and left. To change a position afterwards, just move the
    <figure class="fig ..."> in the finished page, above the paragraph it should sit beside."""
    paras = [p for p in node.find_all("p")
             if not p.find_parent(["blockquote", "figure"]) and len(p.get_text(strip=True)) >= 150]
    if not paras:
        paras = [p for p in node.find_all("p") if not p.find_parent(["blockquote", "figure"])]
    if not paras:
        return
    placed = []
    start = 0
    if hero:
        placed.append((0, hero, "fig big"))
        start = 1
    rest = paras[start:] or paras
    n = len(imgs)
    for k, im in enumerate(imgs):
        # centre of the k-th of n equal slices of the remaining paragraphs
        idx = start + min(len(rest) - 1, int((k + 0.5) * len(rest) / n)) if len(rest) else 0
        side = "fig left" if (k % 2 == 1) else "fig"
        placed.append((idx, im, side))
    seen = set()
    for idx, im, cls in placed:
        while idx in seen and idx + 1 < len(paras):   # never two pictures at the same paragraph
            idx += 1
        seen.add(idx)
        fig = BeautifulSoup(figure_html(im, f' class="{cls}"'), "html.parser").figure
        for a in ("width", "height"):                 # the stylesheet sizes it
            fig.img.attrs.pop(a, None)
        paras[idx].insert_before(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--section", required=True, choices=SECTIONS)
    ap.add_argument("--slug")
    ap.add_argument("--title")
    ap.add_argument("--author", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--apa-title")
    ap.add_argument("--site", default="")
    ap.add_argument("--kind", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--logo", help="logo file, from the site folder, e.g. img/logos/teara.svg")
    ap.add_argument("--logo-alt", default="")
    ap.add_argument("--logo-light", action="store_true", help="logo needs a light background (dark logos)")
    ap.add_argument("--strapline", help="optional second logo line, e.g. img/logos/teara-strapline.svg")
    ap.add_argument("--hero")
    ap.add_argument("--image", action="append", default=[])
    ap.add_argument("--image-names", default="")
    ap.add_argument("--no-content-images", action="store_true")
    ap.add_argument("--select")
    ap.add_argument("--remove", action="append", default=[])
    ap.add_argument("--desc", default="One or two sentences about what this source covers.")
    args = ap.parse_args()

    soup = BeautifulSoup(Path(args.input).expanduser().read_text(encoding="utf-8", errors="replace"), "html.parser")
    title = args.title or guess_title(soup)
    slug = args.slug or slugify(title)

    if args.select:
        node = soup.select_one(args.select)
        if node is None:
            sys.exit(f"--select '{args.select}' matched nothing in the page")
    else:
        node = pick_main(soup)

    names = [n.strip() for n in args.image_names.split(",") if n.strip()]
    report = clean(node, slug, title, args.remove, not args.no_content_images, names)
    imgs = [parse_image_arg(a) for a in args.image]
    hero = parse_image_arg(args.hero) if args.hero else None
    spread_pictures(node, hero, imgs)
    body = re.sub(r"\n\s*\n+", "\n", node.decode_contents().strip())

    section_file, section_name = SECTIONS[args.section]
    logo_html = ""
    if args.logo:
        cls = "logo on-light" if args.logo_light else "logo"
        logo_html = f'<img class="{cls}" src="../{esc(args.logo)}" alt="{esc(args.logo_alt or args.site)}">'
        if args.strapline:
            logo_html += f'<img class="strap" src="../{esc(args.strapline)}" alt="">'
    elif args.site:
        logo_html = f'<span class="wordmark">{esc(args.site)}</span>'
    apa = apa_html(args.author, args.date, args.apa_title or title, args.kind, args.site, args.url)
    hero_html = gallery_html = ""      # pictures now sit inside the text (see spread_pictures)

    template = (SITE / "sources" / "_template.html").read_text(encoding="utf-8")
    out = (template
           .replace("{{TITLE}}", esc(title))
           .replace("{{SECTION_CLASS}}", args.section)
           .replace("{{SECTION_FILE}}", section_file)
           .replace("{{SECTION_NAME}}", section_name)
           .replace("{{LOGO}}", logo_html)
           .replace("{{APA}}", apa)
           .replace("{{HERO}}", hero_html)
           .replace("{{GALLERY}}", gallery_html)
           .replace("{{CONTENT}}", body))

    problems = []
    if re.search(r"<a[\s>]", body, re.I):
        problems.append("a link tag remains")
    if re.search(r"<(script|iframe|form|object|embed)\b", body, re.I):
        problems.append("a script/iframe/form remains")
    if re.search(r"""\bsrc\s*=\s*["'](?!\.\./img/)""", body, re.I):
        problems.append("a picture points outside the site")
    if problems:
        sys.exit("Refusing to write the page: " + "; ".join(problems))

    out_path = SITE / "sources" / f"{slug}.html"
    out_path.write_text(out, encoding="utf-8")

    words = len(re.sub(r"<[^>]+>", " ", body).split())
    first_pic = (imgs[0]["path"] if imgs else None)
    cover = (f'<span class="cover"><img src="{args.hero.split("|")[0]}" alt=""><span class="badge">Text</span></span>' if args.hero
             else f'<span class="cover"><img src="{first_pic}" alt=""><span class="badge">Text</span></span>' if first_pic
             else '<span class="cover tile"><span class="badge">Text</span></span>')
    logo_card = (f'<img class="{"logo on-light" if args.logo_light else "logo"}" src="{args.logo}" alt="{esc(args.logo_alt or args.site)}">'
                 if args.logo else f'<span class="wordmark">{esc(args.site)}</span>')
    print(f"\nWrote sources/{slug}.html  ({words} words, {report['links']} links turned into plain text, "
          f"{report['images']} pictures stored, {report['dropped']} dropped)")
    print(f"\nPaste this card into {section_file}, inside <main class=\"sources\">:\n")
    print(f'''      <a class="source" data-type="text" href="sources/{slug}.html">
        {cover}
        <span class="source-body">
          <span class="source-title">{esc(title)}</span>
          <span class="source-desc">{esc(args.desc)}</span>
          <span class="source-from">{logo_card}</span>
        </span>
      </a>''')


if __name__ == "__main__":
    main()
