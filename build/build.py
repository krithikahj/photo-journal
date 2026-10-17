#!/usr/bin/env python3
"""
Builds the photo journals website.

Reads every folder in trips/, prepares the photos and videos (resized,
location data removed), and writes the finished site into _site/.
You don't need to run or edit this: GitHub runs it every time you upload.
"""
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:  # iPhone .heic photos
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
TRIPS = ROOT / "trips"
ASSETS = ROOT / "build" / "assets"
CACHE = ROOT / ".cache" / "media"
OUT = ROOT / "_site"

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v"}
PHOTO_SIZES = (1000, 2000)  # longest side, in pixels
VIDEO_MAX = 1280            # longest side, in pixels

esc = html.escape


# ---------------------------------------------------------------- settings

def load_settings():
    defaults = {
        "title": "Krithika’s photo journals",
        "footer": "Photos & words by Krithika",
        "hide_from_search": True,
    }
    path = ROOT / "settings.json"
    if path.exists():
        defaults.update(json.loads(path.read_text(encoding="utf-8")))
    return defaults


# ------------------------------------------------------------- story.md

def parse_story(path):
    """Returns (details, intro, blocks). blocks maps a lower-case file name
    to (first line, remaining text)."""
    details, intro, blocks = {}, "", {}
    if not path.exists():
        return details, intro, blocks
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    if text.lstrip().startswith("---"):
        text = text.lstrip()
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    details[key.strip().lower()] = value.strip().strip('"').strip("'")
            text = text[end + 4:]
    parts = re.split(r"^##[ \t]+(.+?)[ \t]*$", text, flags=re.M)
    intro = parts[0].strip()
    for i in range(1, len(parts), 2):
        # "## IMG_1234.HEIC" or "## IMG_1234.HEIC | art" for an artsy shot
        header = parts[i].strip()
        name, _, flag = header.partition("|")
        is_art = flag.strip().lower() == "art"
        body = parts[i + 1].strip()
        first, _, rest = body.partition("\n")
        blocks[name.strip().lower()] = (first.strip(), rest.strip(), is_art)
    return details, intro, blocks  # blocks keep the order they appear in story.md


def paragraphs(text):
    out = []
    for chunk in re.split(r"\n\s*\n", text.strip()):
        chunk = chunk.strip()
        if chunk:
            out.append("<p>" + "<br>".join(esc(l.strip()) for l in chunk.splitlines()) + "</p>")
    return "\n".join(out)


# ------------------------------------------------------------- media

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()[:16]


def prepare_photo(src, cache_dir):
    """Saves resized copies without any metadata (no GPS, no camera info).
    Returns (width, height, {size: filename})."""
    key = file_hash(src)
    info_file = cache_dir / f"{key}.json"
    names = {s: f"{key}-{s}.jpg" for s in PHOTO_SIZES}
    if info_file.exists() and all((cache_dir / n).exists() for n in names.values()):
        info = json.loads(info_file.read_text())
        return info["w"], info["h"], names

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)  # apply phone rotation, then drop the tag
        icc = im.info.get("icc_profile")
        if im.mode != "RGB":
            im = im.convert("RGB")
        w, h = im.size
        for size, name in names.items():
            copy = im.copy()
            copy.thumbnail((size, size), Image.LANCZOS)
            # Saving without exif= writes no EXIF block, so location is gone.
            copy.save(cache_dir / name, "JPEG", quality=82, optimize=True,
                      progressive=True, icc_profile=icc)
    info_file.write_text(json.dumps({"w": w, "h": h}))
    return w, h, names


def probe_video(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"]), float(data["format"].get("duration", 0))


def prepare_video(src, cache_dir):
    """Compresses the clip and removes all metadata (including location).
    Returns (width, height, seconds, video filename, poster filename)."""
    key = file_hash(src)
    mp4, poster = f"{key}.mp4", f"{key}-poster.jpg"
    info_file = cache_dir / f"{key}.json"
    if not (info_file.exists() and (cache_dir / mp4).exists() and (cache_dir / poster).exists()):
        scale = (f"scale='if(gte(iw,ih),min({VIDEO_MAX},iw),-2)':"
                 f"'if(gte(iw,ih),-2,min({VIDEO_MAX},ih))'")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
             "-map", "0:v:0", "-map", "0:a:0?",
             "-map_metadata", "-1", "-map_metadata:s:v", "-1", "-map_metadata:s:a", "-1",
             "-map_chapters", "-1",
             "-vf", scale, "-c:v", "libx264", "-preset", "slow", "-crf", "27",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             "-c:a", "aac", "-b:a", "96k",
             str(cache_dir / mp4)],
            check=True)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.3", "-i", str(cache_dir / mp4),
             "-frames:v", "1", "-map_metadata", "-1", "-q:v", "4", str(cache_dir / poster)],
            check=True)
        w, h, secs = probe_video(cache_dir / mp4)
        info_file.write_text(json.dumps({"w": w, "h": h, "s": secs}))
    info = json.loads(info_file.read_text())
    return info["w"], info["h"], info["s"], mp4, poster


# ------------------------------------------------------------- trips

def folder_defaults(name):
    match = re.match(r"^(\d{4})[-_ ]*(.*)$", name)
    year, rest = (match.group(1), match.group(2)) if match else ("", name)
    title = re.sub(r"[-_]+", " ", rest).strip().title() or name
    return year, title


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "trip"


def media_kind(path):
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        return "video"
    if ext in PHOTO_EXT:
        return "art" if ".art" in path.stem.lower() else "story"
    return None


def collect_trips():
    trips = []
    if not TRIPS.exists():
        return trips
    for folder in sorted(p for p in TRIPS.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        details, intro, blocks = parse_story(folder / "story.md")
        if details.get("hidden", "").lower() in ("yes", "true"):
            print(f"  hidden: {folder.name}")
            continue
        # Files listed in story.md come first, in that order; any others follow by name.
        story_order = {name: i for i, name in enumerate(blocks)}
        files = sorted((p for p in folder.iterdir() if p.is_file() and media_kind(p)),
                       key=lambda p: (story_order.get(p.name.lower(), len(story_order)), p.name.lower()))
        if not files:
            print(f"  skipping {folder.name}: no photos or videos")
            continue
        year, title = folder_defaults(folder.name)
        trips.append({
            "folder": folder,
            "slug": slugify(folder.name),
            "title": details.get("title") or title,
            "year": details.get("year") or year,
            "where": details.get("where", ""),
            "intro": intro,
            "blocks": blocks,
            "files": files,
        })
    trips.sort(key=lambda t: (t["year"], t["folder"].name), reverse=True)
    return trips


# ------------------------------------------------------------- html

def head(title, settings, css_path):
    robots = '<meta name="robots" content="noindex, nofollow">\n' if settings["hide_from_search"] else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
{robots}<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400&family=Newsreader:ital,opsz,wght@0,6..72,400;1,6..72,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="{css_path}">
</head>
"""


ARROW = ('<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="1.5" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')


def render_home(trips, settings):
    first, _, rest = settings["title"].partition(" ")
    heading = esc(first) + ("<br>" + esc(rest) if rest else "")
    rows = []
    for t in trips:
        rows.append(f"""<a class="row" href="trips/{t['slug']}/index.html">
<span class="year">{esc(t['year'])}</span>
<span class="title">{esc(t['title'])}</span>
<span class="where">{esc(t['where'])}</span>
{ARROW}
</a>""")
    rows_html = "\n".join(rows) or '<p class="empty">No journals yet.</p>'
    return head(settings["title"], settings, "site.css") + f"""<body class="home">
<main class="wrap">
<h1>{heading}</h1>
<section class="list" aria-label="Journals">
<div class="list-head"><span>Journals</span><button class="sort" type="button" aria-label="Change order">Newest first ↓</button></div>
<div class="rows">
{rows_html}
</div>
</section>
<footer class="foot">{esc(settings['footer'])}</footer>
</main>
<script src="site.js" defer></script>
</body>
</html>
"""


def clock(seconds):
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def render_trip(trip, items, next_trip, settings):
    n = len(items)
    layers, steps = [], []
    for i, it in enumerate(items):
        num = f"{i + 1:02d}"
        title, text = it["title"], it["text"]
        orient = " is-portrait" if it["h"] > it["w"] else ""
        active = " is-active" if i == 0 else ""
        alt = esc(title or f"{it['kind'].capitalize()} {i + 1}")
        if it["kind"] == "video":
            layers.append(f"""<figure class="layer kind-video{orient}{active}" data-i="{i}">
<video muted loop playsinline preload="none" poster="{it['poster']}" aria-label="{alt}"><source src="{it['src']}" type="video/mp4"></video>
<button class="sound" type="button" aria-pressed="false">Sound on</button>
</figure>""")
        else:
            src1, src2 = it["srcs"]
            load = (f'src="{src1}" srcset="{src1} 1000w, {src2} 2000w"' if i < 2 else
                    f'data-src="{src1}" data-srcset="{src1} 1000w, {src2} 2000w"')
            layers.append(f"""<figure class="layer kind-{it['kind']}{orient}{active}" data-i="{i}">
<img {load} sizes="(max-width: 800px) 100vw, 62vw" alt="{alt}" decoding="async">
</figure>""")

        if it["kind"] == "art":
            body = ""  # artsy shots show only their caption, no label
            if title:
                body += f'<p class="caption">{esc(title)}</p>'
            if text:
                body += "\n" + paragraphs(text)
        else:
            label = f"{num} — Video · {clock(it['secs'])}" if it["kind"] == "video" else num
            body = f'<div class="label accent">{label}</div>'
            if title:
                body += f"\n<h2>{esc(title)}</h2>"
            if text:
                body += "\n" + paragraphs(text)
        steps.append(f'<article class="step kind-{it["kind"]}{active}" data-i="{i}">\n{body}\n</article>')

    kicker = " · ".join(x for x in (trip["year"], trip["where"]) if x)
    intro = paragraphs(trip["intro"]) if trip["intro"] else ""
    if next_trip:
        next_html = f'<a class="next" href="../{next_trip["slug"]}/index.html">Next: {esc(next_trip["title"])} →</a>'
    else:
        next_html = ""
    layers_html = "\n".join(layers)
    steps_html = "\n".join(steps)
    return head(f"{trip['title']} · {settings['title']}", settings, "../../site.css") + f"""<body class="trip">
<nav class="topnav"><a href="../../index.html">← All journals</a></nav>
<header class="trip-head">
<div class="label muted">{esc(kicker)}</div>
<h1>{esc(trip['title'])}</h1>
<div class="intro">{intro}</div>
</header>
<main class="story">
<div class="stage">
<div class="frame">
{layers_html}
</div>
<div class="meter"><span class="count">01 / {n:02d}</span><div class="bar"><i style="width:{100 / n:.1f}%"></i></div></div>
</div>
<div class="steps">
{steps_html}
</div>
</main>
<footer class="trip-end">
<div class="label muted">End of trip</div>
{next_html}
<a class="back label" href="../../index.html">Back to all journals</a>
</footer>
<script src="../../site.js" defer></script>
</body>
</html>
"""


# ------------------------------------------------------------- main

def build():
    settings = load_settings()
    trips = collect_trips()
    print(f"Building {len(trips)} journal(s)")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for asset in ASSETS.iterdir():
        shutil.copy2(asset, OUT / asset.name)
    if settings["hide_from_search"]:
        (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    (OUT / ".nojekyll").write_text("")

    for idx, trip in enumerate(trips):
        print(f"- {trip['folder'].name}")
        cache_dir = CACHE / trip["slug"]
        cache_dir.mkdir(parents=True, exist_ok=True)
        out_dir = OUT / "trips" / trip["slug"]
        out_dir.mkdir(parents=True)
        mentioned = set()
        items = []
        for f in trip["files"]:
            title, text, is_art = trip["blocks"].get(f.name.lower(), ("", "", False))
            kind = media_kind(f)
            if is_art and kind == "story":
                kind = "art"
            if f.name.lower() in trip["blocks"]:
                mentioned.add(f.name.lower())
            try:
                if kind == "video":
                    w, h, secs, mp4, poster = prepare_video(f, cache_dir)
                    for name in (mp4, poster):
                        shutil.copy2(cache_dir / name, out_dir / name)
                    items.append({"kind": kind, "w": w, "h": h, "secs": secs,
                                  "src": mp4, "poster": poster, "title": title, "text": text})
                else:
                    w, h, names = prepare_photo(f, cache_dir)
                    for name in names.values():
                        shutil.copy2(cache_dir / name, out_dir / name)
                    items.append({"kind": kind, "w": w, "h": h,
                                  "srcs": (names[PHOTO_SIZES[0]], names[PHOTO_SIZES[1]]),
                                  "title": title, "text": text})
            except Exception as err:  # one bad file shouldn't stop the whole site
                print(f"  ! couldn't use {f.name}: {err}", file=sys.stderr)
        for name in sorted(set(trip["blocks"]) - mentioned):
            print(f"  note: story.md mentions '{name}' but there's no such file in the folder")
        if not items:
            continue
        # Next goes to the next older trip and wraps to the newest at the end.
        # Only trips shown on the site count, so it never points at a hidden one.
        next_trip = trips[(idx + 1) % len(trips)] if len(trips) > 1 else None
        (out_dir / "index.html").write_text(render_trip(trip, items, next_trip, settings), encoding="utf-8")

    (OUT / "index.html").write_text(render_home(trips, settings), encoding="utf-8")
    print(f"Done: {OUT}")


if __name__ == "__main__":
    build()
