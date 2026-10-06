# Rakiura Stewart Island – Research Hub

A small static website (plain HTML and CSS, no scripts) for students to research Rakiura without leaving the site. No build step, no frameworks, nothing loaded from outside.

```
index.html          home page: four pathway cards
general.html        section pages: one card per source
history.html
wildlife.html
tourism.html
sources/            one page per source (articles, audio, video) + _template.html
audio/              mp3 files
img/logos/          the original logos of the source websites
img/sources/<name>/ pictures for each source
img/cards/          the four home page pictures
img/backdrops/     one background photo per page: home, general, history, wildlife, tourism
img/hero.jpg        optional spare background for any page without its own photo
templates/          copy-and-paste card and page templates
scripts/            clean_article.py, prepare_image.py, extract_media.py
style.css           all the styling
```

## How the layout works

* The home page and the four section pages are exactly one window tall. Cards share the space and their pictures stretch or shrink to fit, so there is nothing to scroll. The number of columns follows the number of cards.
* On a source page (an article) the reading column scrolls normally, but nothing is ever wider than the window.
* Audio pages put the player and transcript side by side; only the transcript scrolls.
* On phones and very narrow windows, everything relaxes into a normal scrolling layout.

## 1. Adding a text source (a saved web page)

1. Save the page with the **SingleFile** browser extension. It stores the page's pictures inside the file.
2. Optional: run `python scripts/extract_media.py page.html` and open the `_extracted/.../index.html` it makes to see every picture and logo on the page. Copy logos into `img/logos/` and photos into `img/sources/<source-name>/`.
3. From the site folder run (`pip install beautifulsoup4 pillow` once first):

   ```
   python scripts/clean_article.py ~/Downloads/page.html \
       --section wildlife --slug te-ara-plants-and-animals \
       --title "Plants and animals" \
       --author "Walrond, C." --date "2015, May 1" \
       --apa-title "Stewart Island/Rakiura: Plants and animals" \
       --site "Te Ara – The Encyclopedia of New Zealand" \
       --url "https://teara.govt.nz/en/stewart-islandrakiura/page-2" \
       --logo img/logos/teara.svg --logo-alt "Te Ara" \
       --image "img/sources/te-ara-plants-and-animals/kiwi.jpg|Stewart Island kiwi" \
       --desc "Forests, alpine plants, kiwi, kākāpō, penguins and sea lions."
   ```
4. It writes `sources/<slug>.html` and prints a card. Paste the card into the matching section page.

What the script does: removes scripts, iframes, forms, menus and ads; turns **every link into plain text**; stores the article's own pictures locally; and shows the logo and a one-line **APA 7 reference** at the top (one click on the reference selects it for copying). Each source page also carries a Content-Security-Policy that stops it loading anything from outside the site.

APA details: `--author` is `"Surname, A."` or an organisation. Leave out `--date` and it shows `(n.d.)`. Leave out `--site` when it is the same as the author. Add `--kind "Blog post"` for blogs. Other options: `--hero`, `--select`, `--remove`, `--logo-light`, `--strapline`. Run the script with `--help` for the lot.

Always open the result and read it. If a page cleans badly, `--select "article"` and `--remove ".sidebar"` let you choose what to keep.

## 2. Adding images

| Where it appears | File | Notes |
|---|---|---|
| Background behind one page (its source and audio pages use their section's photo) | `img/backdrops/home.jpg`, `general.jpg`, `history.jpg`, `wildlife.jpg`, `tourism.jpg` | 1920 px wide. A missing photo falls back to `img/hero.jpg`, then to a soft glowing sky. |
| Spare background for any page without its own photo | `img/hero.jpg` | optional, 1920 px wide |
| Home page cards | `img/cards/general.jpg` `history.jpg` `wildlife.jpg` `tourism.jpg` | 900 px wide. |
| A source's card and page | `img/sources/<source-name>/<file>.jpg` | use in `--image`, `--hero`, or in the card's cover. |
| A source website's logo | `img/logos/<name>.svg` | shown on cards and source pages. |

`python scripts/prepare_image.py photo.jpg --as source --name te-ara-plants-and-animals/kiwi` resizes a photo and saves it in the right place (`--as backdrop --name tourism`, `--as hero`, `--as card --name wildlife` and `--as source` are the kinds). To swap a backdrop, run it again with the new photo; the name decides which page it goes behind.

Backdrop photos: only use photos you have permission to publish, and keep a note of the photographer and licence for a credits line.

**Where the current pictures came from:** the logos and photos on this site were taken from the six saved pages (Te Ara, DOC, Ruggedy Range, the Platypus Man blog). Te Ara's saved thumbnails are small (120 x 90), so the sources that use them show them as small pictures or a mosaic. Larger versions will look sharper: replace a file with the same name. Pictures on the Ruggedy Range, DOC and audio pages that come from Te Ara are credited "Te Ara" in their captions.

Good places for more photos: Wikimedia Commons (check each licence and credit it), Unsplash, and the Department of Conservation (ask permission).

## 3. Audio

Copy `templates/audio-page.html` to `sources/<name>.html`, replace each `{{...}}`, put the mp3 in `audio/`, and add an audio card. The transcript for *Te Rakitamau's blushing cheeks* is the teacher's own written version. Fill in the highlighted gaps in its APA reference (author, year, publisher, web address).

## 4. Video (YouTube clip that plays between two times)

Copy `templates/video-page.html` to `sources/<name>.html`. To play the **whole video**, delete `start={{START}}&amp;end={{END}}&amp;` from the address in the page. Otherwise replace `{{VIDEO_ID}}`, `{{START}}` and `{{END}}` (seconds: 1:30 to 3:05 is 90 and 185). Captions are switched on by default (`cc_load_policy=1` in the address), but they only appear if the video has captions, and students can still turn them off. Some videos don't allow embedding, so test each. The `end=` time stops the video, but YouTube's logo and its "more videos" overlay can still be clicked, which is the one place students could leave the site. Your school filter must allow `youtube-nocookie.com`.

## 5. Put it on GitHub Pages

1. Create a repository on GitHub (for example `rakiura-hub`) and upload everything in this folder so `index.html` is at the top level. (Don't upload `_extracted/` if you made one.)
2. **Settings → Pages**, choose **Deploy from a branch**, branch `main`, folder `/ (root)`, Save.
3. After a minute the site is at `https://<your-username>.github.io/rakiura-hub/`.

Things to know:
* A free GitHub account needs a **public** repository for Pages, so anyone with the address can open the site. The pages ask search engines not to index them, but that is not a lock.
* Because it is public, only include text and pictures you have permission to republish. Te Ara text is CC BY-NC 4.0 (credit it, non-commercial). Check the DOC page's terms, and get permission for Ruggedy Range (all rights reserved) and the Platypus Man blog (personal blog, no licence stated, its photos are the author's). Logos belong to their organisations.
* The site can't stop a Chromebook visiting other websites. A truly closed environment has to come from your school's web filter.

## Colours

Section colours are set at the top of `style.css` (`--c-general`, `--c-history`, `--c-wildlife`, `--c-tourism`).

## Where pictures sit inside an article

Pictures are placed inside the text, beside the paragraph they go with (they alternate right and left, and the `--hero` picture is the bigger one at the top). On phones they sit between paragraphs at full width. To move one, open the finished page in `sources/`, cut its `<figure class="fig ...">` block and paste it above the paragraph it should sit beside. Add `left` to the class (`fig left`) to put it on the left, or `big` (`fig big`) for a larger picture. Te Ara's original pictures are only 120 x 90 pixels, so they look a little soft when enlarged; replace a file in `img/sources/` with a bigger version of the same name to sharpen it.


A video card with no picture shows a play button on a night-sky gradient (`class="cover play"`). To use a still from the video instead, save a screenshot in `img/sources/<name>/cover.jpg` and use the single-picture cover from `templates/card-templates.txt`.
