import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from imageio_ffmpeg import get_ffmpeg_exe

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_videos import VideoOptimizer, VideoRewriter


class Sources(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.items = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag in {"source", "video"}:
            self.items.append((tag, dict(attrs)))


class PrepareVideosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixtures.cleanup)
        cls.ffmpeg = get_ffmpeg_exe()
        cls.encoded = {}
        for codec, encoder in [("hevc", "libx265"), ("h264", "libx264")]:
            path = Path(cls.fixtures.name) / (codec + ".mp4")
            args = [cls.ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "color=c=red:size=64x48:rate=4:duration=0.5", "-c:v", encoder, "-pix_fmt", "yuv420p"]
            if codec == "hevc":
                args += ["-x265-params", "pools=1:log-level=error", "-tag:v", "hvc1"]
            subprocess.run(args + [str(path)], check=True, capture_output=True)
            cls.encoded[codec] = path.read_bytes()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name)
        self.assets = self.source / "assets/projects/demo"
        self.assets.mkdir(parents=True)
        self.video = self.assets / "Original, video.mp4"
        self.video.write_bytes(self.encoded["hevc"])
        self.destination = self.source / "_site"
        self.page = self.destination / "projects/demo/index.html"
        self.page.parent.mkdir(parents=True)

    def rewrite(self, text, baseurl=""):
        optimizer = VideoOptimizer(self.source, self.destination, baseurl)
        parser = VideoRewriter(text, self.page, optimizer)
        parser.feed(text)
        return parser.output(), optimizer

    def test_hevc_rewritten_as_decodable_faststart_h264_original_unchanged(self):
        original = hashlib.sha256(self.video.read_bytes()).hexdigest()
        text = ('<video controls muted loop poster="poster.jpg">\n'
                '<source src="/assets/projects/demo/Original%2C%20video.mp4" '
                'type="video/mp4; codecs=hvc1"></video>')
        rendered, optimizer = self.rewrite(text)
        attrs = Sources(rendered).items[1][1]
        self.assertEqual(attrs["type"], "video/mp4")
        generated = self.destination / attrs["src"].lstrip("/")
        self.assertTrue(generated.exists())
        probe = subprocess.run([self.ffmpeg, "-hide_banner", "-i", str(generated)], capture_output=True, text=True)
        self.assertIn("Video: h264", probe.stderr)
        subprocess.run([self.ffmpeg, "-v", "error", "-i", str(generated), "-f", "null", "-"],
                       check=True, capture_output=True)
        data = generated.read_bytes()
        self.assertLess(data.index(b"moov"), data.index(b"mdat"))
        self.assertEqual(hashlib.sha256(self.video.read_bytes()).hexdigest(), original)
        self.assertIn('<video controls muted loop poster="poster.jpg">\n', rendered)
        self.assertEqual(len(optimizer.used_files), 1)

    def test_compatible_h264_and_nonvideo_remote_and_optout_untouched(self):
        self.video.write_bytes(self.encoded["h264"])
        text = ('<video src="/assets/projects/demo/Original%2C%20video.mp4"></video>'
                '<video src="https://example.com/video.mp4"></video>'
                '<video src="/assets/animation.webm"></video>'
                '<video src="/assets/missing.mp4" data-video-optimize="false"></video>'
                '<audio><source src="/assets/audio.mp4"></audio>')
        rendered, optimizer = self.rewrite(text)
        self.assertEqual(rendered, text)
        self.assertEqual(optimizer.rewritten, 0)

    def test_cached_transcode_reused_and_missing_build_copy_restored(self):
        text = '<video src="/assets/projects/demo/Original%2C%20video.mp4"></video>'
        first, optimizer = self.rewrite(text)
        cached = next(optimizer.cache.rglob("*-h264.mp4"))
        timestamp = cached.stat().st_mtime_ns
        generated = next(iter(optimizer.used_files))
        generated.unlink()
        self.assertEqual(self.rewrite(text)[0], first)
        self.assertTrue(generated.is_file())
        self.assertEqual(cached.stat().st_mtime_ns, timestamp)
        self.video.write_bytes(self.encoded["h264"])
        self.assertEqual(self.rewrite(text)[0], text)

    def test_baseurl_legacy_alias_and_repeat_processing(self):
        scripts = self.source / "scripts"
        scripts.mkdir()
        (scripts / "legacy_asset_paths.json").write_text(json.dumps({
            "assets/old video.mp4": "assets/projects/demo/Original, video.mp4",
        }))
        text = '<video><source src="/portfolio/assets/old%20video.mp4"></video>'
        rendered, _ = self.rewrite(text, "/portfolio")
        src = Sources(rendered).items[1][1]["src"]
        self.assertTrue(src.startswith("/portfolio/assets/optimized-media/"))
        self.assertEqual(self.rewrite(rendered, "/portfolio")[0], rendered)

    def test_missing_local_video_fails_and_outside_asset_paths_ignored(self):
        with self.assertRaisesRegex(ValueError, "Missing local video"):
            self.rewrite('<video src="/assets/missing.mp4"></video>')
        text = '<video src="/assets/../../private.mp4"></video>'
        self.assertEqual(self.rewrite(text)[0], text)


if __name__ == "__main__":
    unittest.main()
