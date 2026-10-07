#!/usr/bin/env python3
"""Create browser-compatible copies of embedded HEVC videos during Jekyll builds."""

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

GENERATED_PATH = "assets/optimized-media"
ENCODER_VERSION = "hevc-to-h264-crf22-medium-yuv420p-aac128-faststart-v1"


class VideoOptimizer:
    def __init__(self, source, destination, baseurl=""):
        self.source = source.resolve()
        self.destination = destination.resolve()
        self.baseurl = baseurl.rstrip("/")
        self.cache = self.source / ".image-cache/videos"
        manifest = self.source / "scripts/legacy_asset_paths.json"
        self.aliases = json.loads(manifest.read_text()) if manifest.is_file() else {}
        self.results = {}
        self.used_files = set()
        self.rewritten = 0
        self.executable = None

    def ffmpeg(self):
        if self.executable is None:
            self.executable = os.environ.get("VIDEO_FFMPEG") or shutil.which("ffmpeg")
            if not self.executable:
                from imageio_ffmpeg import get_ffmpeg_exe
                self.executable = get_ffmpeg_exe()
        return self.executable

    def local_video(self, src, page):
        url = urlsplit(src)
        if url.scheme or url.netloc or not url.path or GENERATED_PATH in unquote(url.path):
            return None
        path = unquote(url.path)
        if self.baseurl and path.startswith(self.baseurl + "/"):
            path = path[len(self.baseurl):]
        relative = (Path(path.lstrip("/")) if path.startswith("/") else
                    page.parent.resolve().relative_to(self.destination) / path)
        candidate = (self.source / relative).resolve()
        if not candidate.is_relative_to(self.source / "assets") or candidate.suffix.lower() != ".mp4":
            return None
        if not candidate.is_file() and str(relative) in self.aliases:
            candidate = (self.source / self.aliases[str(relative)]).resolve()
        if not candidate.is_relative_to(self.source / "assets"):
            raise ValueError(f"Video asset must stay inside assets: {src}")
        if not candidate.is_file():
            raise ValueError(f"Missing local video in {page}: {src}")
        return candidate

    def compatible_copy(self, path):
        if path in self.results:
            return self.results[path]
        fingerprint = hashlib.sha256(path.read_bytes() + ENCODER_VERSION.encode()).hexdigest()[:20]
        directory = self.cache / fingerprint
        metadata = directory / "video.json"
        entry = json.loads(metadata.read_text()) if metadata.is_file() else None
        if entry is None:
            probe = subprocess.run([self.ffmpeg(), "-hide_banner", "-i", str(path)],
                                   capture_output=True, text=True)
            match = re.search(r"Video:\s*(\w+)", probe.stderr)
            if not match:
                raise ValueError(f"Cannot read video stream in {path}: {probe.stderr[-1000:]}")
            entry = {"codec": match.group(1)}
            directory.mkdir(parents=True, exist_ok=True)
            metadata.write_text(json.dumps(entry))
        if entry["codec"] != "hevc":
            self.results[path] = None
            return None

        stem = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")[:40] or "video"
        cached = directory / f"{stem}-{fingerprint}-h264.mp4"
        if not cached.is_file() or not cached.stat().st_size:
            temporary = cached.with_suffix(".partial.mp4")
            result = subprocess.run([
                self.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
                "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "medium",
                "-crf", "22", "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-map_metadata", "-1",
                str(temporary),
            ], capture_output=True, text=True)
            if result.returncode:
                temporary.unlink(missing_ok=True)
                raise ValueError(f"Video conversion failed for {path}: {result.stderr[-1000:]}")
            temporary.replace(cached)
        generated = self.destination / GENERATED_PATH / cached.name
        generated.parent.mkdir(parents=True, exist_ok=True)
        if not generated.is_file():
            shutil.copyfile(cached, generated)
        self.used_files.add(generated)
        self.results[path] = quote(f"{self.baseurl}/{GENERATED_PATH}/{cached.name}", safe="/")
        return self.results[path]

    def rewrite_source(self, tag, attrs, page):
        values = dict(attrs)
        path = self.local_video(values.get("src", ""), page)
        if path is None:
            return None
        compatible = self.compatible_copy(path)
        if compatible is None:
            return None
        values["src"] = compatible
        if tag == "source":
            values["type"] = "video/mp4"
        self.rewritten += 1
        return "<" + tag + "".join(
            f' {key}="{html.escape(value, quote=True)}"' if value is not None else f" {key}"
            for key, value in values.items()
        ) + ">"

    def run(self):
        for page in sorted(self.destination.rglob("*.html")):
            original = page.read_text(encoding="utf-8")
            parser = VideoRewriter(original, page, self)
            parser.feed(original)
            rendered = parser.output()
            if rendered != original:
                page.write_text(rendered, encoding="utf-8")
        print(f"Video compatibility: {self.rewritten} HEVC references updated; "
              f"{len(self.used_files)} H.264 files used.")


class VideoRewriter(HTMLParser):
    def __init__(self, content, page, optimizer):
        super().__init__(convert_charrefs=False)
        self.content, self.page, self.optimizer = content, page, optimizer
        self.videos = []
        self.replacements = []
        self.lines = [0] + [m.end() for m in re.finditer("\n", content)]

    def handle_starttag(self, tag, attrs):
        if tag == "video":
            self.videos.append(dict(attrs).get("data-video-optimize") != "false")
        if tag not in {"video", "source"} or not self.videos or not self.videos[-1]:
            return
        replacement = self.optimizer.rewrite_source(tag, attrs, self.page)
        if replacement:
            line, column = self.getpos()
            start = self.lines[line - 1] + column
            self.replacements.append((start, start + len(self.get_starttag_text()), replacement))

    def handle_endtag(self, tag):
        if tag == "video" and self.videos:
            self.videos.pop()

    def output(self):
        result = self.content
        for start, end, replacement in reversed(self.replacements):
            result = result[:start] + replacement + result[end:]
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--destination", type=Path, default=Path("_site"))
    parser.add_argument("--baseurl", default="")
    args = parser.parse_args()
    VideoOptimizer(args.source, args.destination, args.baseurl).run()
