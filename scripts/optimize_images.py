#!/usr/bin/env python3
"""Optimize rendered Jekyll images without changing Markdown or original assets."""

import argparse
import hashlib
import html
import io
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from PIL import Image, ImageCms, ImageOps

WIDTHS = (480, 960, 1600, 2400)
QUALITY = 85
ENCODER_VERSION = f"webp-{QUALITY}-method6-{WIDTHS}-pillow{Image.__version__}-v1"
GENERATED_PATH = "assets/optimized-media"
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}
CARD_SIZES = (
    "(max-width: 600px) calc(100vw - 2rem), "
    "(max-width: 1024px) calc(50vw - 1.75rem), "
    "(max-width: 1152px) calc(33.3333vw - 1.6667rem), 358px"
)


def body_sizes(classes, ancestors):
    """Estimate slots from this site's sidebar and optional composition classes."""
    fraction = 1.0
    for name, value in {
        "media--half": 0.5,
        "media--two-thirds": 2 / 3,
        "media--three-quarters": 0.75,
    }.items():
        if name in classes:
            fraction = value
    columns = 3 if "three-column" in ancestors else 2 if "two-column" in ancestors else 1
    slots = []
    for breakpoint, count, sidebar, cap in [
        (600, 1, 0, None),
        (1023, min(columns, 2), 0, None),
        (1279, columns, 200, None),
        (None, columns, 300, 940),
    ]:
        scale = fraction / count
        gap = 1.5 * (count - 1) * scale
        if cap:
            slot = f"calc({cap * scale:.4g}px - {gap:.4g}rem)"
        else:
            slot = f"calc({100 * scale:.6g}vw - {(2 * scale + gap):.6g}rem"
            if sidebar:
                slot += f" - {sidebar * scale:.6g}px"
            slot += ")"
        slots.append(f"(max-width: {breakpoint}px) {slot}" if breakpoint else slot)
    return ", ".join(slots)


class Optimizer:
    def __init__(self, source, destination, baseurl=""):
        self.source = source.resolve()
        self.destination = destination.resolve()
        self.baseurl = baseurl.rstrip("/")
        self.cache = self.source / ".image-cache"
        self.images = {}
        self.used_files = set()
        self.rewritten = 0

    def local_image(self, src, page):
        url = urlsplit(src)
        if url.scheme or url.netloc or not url.path:
            return None
        path = unquote(url.path)
        if self.baseurl and path.startswith(self.baseurl + "/"):
            path = path[len(self.baseurl):]
        if path.startswith("/"):
            relative = Path(path.lstrip("/"))
        else:
            relative = page.parent.resolve().relative_to(self.destination) / path
        candidate = (self.source / relative).resolve()
        if not candidate.is_relative_to(self.source / "assets"):
            return None
        if candidate.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            return None
        if not candidate.is_file():
            raise ValueError(f"Missing local image in {page}: {src}")
        if candidate.is_relative_to(self.source / "assets/responsive-media"):
            return None
        return candidate

    def variants(self, path):
        if path in self.images:
            return self.images[path]
        fingerprint = hashlib.sha256(path.read_bytes() + ENCODER_VERSION.encode()).hexdigest()[:20]
        directory = self.cache / fingerprint
        metadata = directory / "image.json"
        if metadata.is_file():
            entry = json.loads(metadata.read_text())
            if all((directory / item["name"]).is_file() for item in entry["variants"]):
                self.images[path] = (directory, entry)
                return self.images[path]

        with Image.open(path) as source:
            if getattr(source, "is_animated", False):
                self.images[path] = None
                return None
            image = ImageOps.exif_transpose(source)
            alpha = "A" in image.getbands() or "transparency" in image.info
            mode = "RGBA" if alpha else "RGB"
            profile = image.info.get("icc_profile")
            if profile:
                if image.mode not in {"RGB", "RGBA", "CMYK", "L", "LAB"}:
                    image = image.convert(mode)
                image = ImageCms.profileToProfile(
                    image, ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                    ImageCms.createProfile("sRGB"), outputMode=mode,
                )
            else:
                image = image.convert(mode)
            width, height = image.size
            targets = sorted({min(width, target) for target in WIDTHS})
            directory.mkdir(parents=True, exist_ok=True)
            stem = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")[:40] or "image"
            variants = []
            for target in targets:
                target_height = max(1, round(height * target / width))
                resized = image.resize((target, target_height), Image.Resampling.LANCZOS)
                name = f"{stem}-{fingerprint}-{target}.webp"
                resized.save(directory / name, "WEBP", quality=QUALITY, method=6)
                variants.append({"name": name, "width": target, "height": target_height})
            entry = {"width": width, "height": height, "variants": variants}
            metadata.write_text(json.dumps(entry))
        self.images[path] = (directory, entry)
        return self.images[path]

    def rewrite_image(self, attrs, ancestors, page):
        values = dict(attrs)
        if values.get("data-image-optimize") == "false" or "picture" in ancestors:
            return None
        src = values.get("src", "")
        if not src or GENERATED_PATH in unquote(urlsplit(src).path):
            return None
        if values.get("srcset"):
            return None
        path = self.local_image(src, page)
        if path is None:
            return None
        result = self.variants(path)
        if result is None:
            return None
        directory, entry = result
        classes = set((values.get("class") or "").split())
        card = "archive__item-teaser" in ancestors
        avatar = "home-intro" in ancestors
        selected = entry["variants"]
        if card or avatar:
            selected = [item for item in selected if item["width"] <= 960]
        fallback = next((item for item in selected if item["width"] >= 960), selected[-1])
        generated = self.destination / GENERATED_PATH
        generated.mkdir(parents=True, exist_ok=True)
        for item in selected:
            target = generated / item["name"]
            if not target.is_file():
                shutil.copyfile(directory / item["name"], target)
            self.used_files.add(target)
        def url(item):
            return quote(f"{self.baseurl}/{GENERATED_PATH}/{item['name']}", safe="/")
        values["src"] = url(fallback)
        values["srcset"] = ", ".join(f"{url(item)} {item['width']}w" for item in selected)
        if not values.get("sizes"):
            if avatar:
                values["sizes"] = "88px"
            elif card:
                values["sizes"] = CARD_SIZES
            elif "external-link-card" in ancestors:
                values["sizes"] = "(max-width: 600px) calc(100vw - 2rem), 12rem"
            elif "page__hero" in ancestors:
                values["sizes"] = "100vw"
            else:
                values["sizes"] = body_sizes(classes, ancestors)
        values.setdefault("width", str(entry["width"]))
        values.setdefault("height", str(entry["height"]))
        if not avatar and "page__hero" not in ancestors:
            values.setdefault("loading", "lazy")
        values.setdefault("decoding", "async")
        self.rewritten += 1
        return "<img" + "".join(
            f' {key}="{html.escape(value, quote=True)}"' if value is not None else f" {key}"
            for key, value in values.items()
        ) + ">"

    def rewrite_poster(self, attrs, page):
        values = dict(attrs)
        poster = values.get("poster", "")
        if not poster or values.get("data-image-optimize") == "false" or GENERATED_PATH in unquote(urlsplit(poster).path):
            return None
        path = self.local_image(poster, page)
        result = self.variants(path) if path else None
        if result is None:
            return None
        directory, entry = result
        selected = next((item for item in entry["variants"] if item["width"] >= 1600), entry["variants"][-1])
        target = self.destination / GENERATED_PATH / selected["name"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file():
            shutil.copyfile(directory / selected["name"], target)
        self.used_files.add(target)
        values["poster"] = quote(f"{self.baseurl}/{GENERATED_PATH}/{selected['name']}", safe="/")
        self.rewritten += 1
        return "<video" + "".join(
            f' {key}="{html.escape(value, quote=True)}"' if value is not None else f" {key}"
            for key, value in values.items()
        ) + ">"

    def restore_legacy_assets(self):
        """Keep published original-asset URLs working after source reorganization."""
        manifest = self.source / "scripts/legacy_asset_paths.json"
        if not manifest.is_file():
            return
        aliases = json.loads(manifest.read_text(encoding="utf-8"))
        for previous, current in aliases.items():
            source = (self.source / current).resolve()
            destination = (self.destination / previous).resolve()
            if not source.is_relative_to(self.source / "assets") or not destination.is_relative_to(self.destination / "assets"):
                raise ValueError(f"Legacy asset mapping must stay inside assets: {previous} -> {current}")
            if not source.is_file():
                raise ValueError(f"Legacy asset mapping points to a missing original: {current}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        print(f"Legacy asset compatibility: {len(aliases)} original URLs restored.")

    def run(self):
        for page in sorted(self.destination.rglob("*.html")):
            original = page.read_text(encoding="utf-8")
            parser = ImageRewriter(original, page, self)
            parser.feed(original)
            updated = parser.output()
            if updated != original:
                page.write_text(updated, encoding="utf-8")
        self.restore_legacy_assets()
        print(f"Image optimization: {self.rewritten} image references updated; "
              f"{len(self.used_files)} optimized files used.")


class ImageRewriter(HTMLParser):
    """Replace only img start tags, preserving all other markup byte for byte."""
    def __init__(self, content, page, optimizer):
        super().__init__(convert_charrefs=False)
        self.content = content
        self.page = page
        self.optimizer = optimizer
        self.stack = []
        self.replacements = []
        self.lines = [0]
        self.lines.extend(match.end() for match in re.finditer("\n", content))

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        ancestors = {name for name, _ in self.stack}
        ancestors.update(token for _, tokens in self.stack for token in tokens)
        if tag in {"img", "video"}:
            replacement = (self.optimizer.rewrite_image(attrs, ancestors, self.page) if tag == "img"
                           else self.optimizer.rewrite_poster(attrs, self.page))
            if replacement:
                line, column = self.getpos()
                start = self.lines[line - 1] + column
                self.replacements.append((start, start + len(self.get_starttag_text()), replacement))
        if tag not in VOID_TAGS:
            self.stack.append((tag, set((values.get("class") or "").split())))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def output(self):
        result = self.content
        for start, end, replacement in reversed(self.replacements):
            result = result[:start] + replacement + result[end:]
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--destination", type=Path, default=Path("_site"))
    parser.add_argument("--baseurl", default="")
    args = parser.parse_args()
    if not args.destination.is_dir():
        parser.error("The destination must be an existing Jekyll build directory.")
    Optimizer(args.source, args.destination, args.baseurl).run()


if __name__ == "__main__":
    main()
