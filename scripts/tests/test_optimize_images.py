import hashlib
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image, ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from optimize_images import ImageRewriter, Optimizer


class Images(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.items = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.items.append(dict(attrs))


class OptimizeImagesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name)
        self.assets = self.source / "assets/projects/demo"
        self.assets.mkdir(parents=True)
        self.destination = self.source / "_site"
        self.page = self.destination / "projects/demo/index.html"
        self.page.parent.mkdir(parents=True)

    def image(self, name="original image.png", size=(1800, 1000), mode="RGB"):
        path = self.assets / name
        color = (255, 0, 0, 128) if mode == "RGBA" else "red"
        Image.new(mode, size, color).save(path)
        return path

    def rewrite(self, text, baseurl=""):
        optimizer = Optimizer(self.source, self.destination, baseurl)
        parser = ImageRewriter(text, self.page, optimizer)
        parser.feed(text)
        return parser.output(), optimizer

    def test_card_and_body_use_different_widths_without_changing_original(self):
        path = self.image()
        original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        text = ('<div class="archive__item-teaser"><img src="/assets/projects/demo/original%20image.png"></div>\n'
                '<p><img src="/assets/projects/demo/original%20image.png" alt="A &amp; B" title="x &gt; y"></p>')
        rendered, _ = self.rewrite(text)
        card, body = Images(rendered).items
        self.assertIn("480w", card["srcset"])
        self.assertIn("960w", card["srcset"])
        self.assertNotIn("1600w", card["srcset"])
        self.assertIn("1600w", body["srcset"])
        self.assertIn("1800w", body["srcset"])
        self.assertEqual(body["alt"], "A & B")
        self.assertEqual(body["title"], "x > y")
        self.assertEqual((body["width"], body["height"]), ("1800", "1000"))
        self.assertEqual(body["loading"], "lazy")
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original_hash)
        self.assertIn('</div>\n<p>', rendered)
        for item in Images(rendered).items:
            for candidate in item["srcset"].split(", "):
                url, descriptor = candidate.split()
                with Image.open(self.destination / url.lstrip("/")) as image:
                    self.assertEqual(image.width, int(descriptor[:-1]))

    def test_small_transparent_image_is_not_upscaled(self):
        self.image(size=(200, 100), mode="RGBA")
        rendered, _ = self.rewrite('<img src="/assets/projects/demo/original%20image.png">')
        image = Images(rendered).items[0]
        self.assertEqual(len(image["srcset"].split(", ")), 1)
        with Image.open(self.destination / image["src"].lstrip("/")) as result:
            self.assertEqual(result.size, (200, 100))
            self.assertIn("A", result.getbands())

    def test_remote_svg_gif_picture_explicit_srcset_and_optout_are_preserved(self):
        self.image()
        text = ('<img src="https://example.com/image.png">'
                '<img src="/assets/animation.gif"><img src="/assets/vector.svg">'
                '<picture><source srcset="x.webp"><img src="/assets/projects/demo/original%20image.png"></picture>'
                '<img src="/assets/projects/demo/original%20image.png" srcset="x.webp 960w">'
                '<img src="/assets/projects/demo/original%20image.png" data-image-optimize="false">')
        rendered, optimizer = self.rewrite(text)
        self.assertEqual(rendered, text)
        self.assertEqual(optimizer.rewritten, 0)

    def test_animated_webp_is_preserved(self):
        path = self.assets / "animation.webp"
        Image.new("RGB", (10, 10), "red").save(
            path, save_all=True, append_images=[Image.new("RGB", (10, 10), "blue")], duration=100, loop=0,
        )
        text = '<img src="/assets/projects/demo/animation.webp">'
        self.assertEqual(self.rewrite(text)[0], text)

    def test_baseurl_relative_paths_and_repeat_processing(self):
        self.image()
        text = ('<img src="/portfolio/assets/projects/demo/original%20image.png">'
                '<img src="../../assets/projects/demo/original%20image.png">')
        rendered, _ = self.rewrite(text, "/portfolio")
        for item in Images(rendered).items:
            self.assertTrue(item["src"].startswith("/portfolio/assets/optimized-media/"))
        self.assertEqual(self.rewrite(rendered, "/portfolio")[0], rendered)

    def test_changed_original_invalidates_cache_and_missing_variant_is_restored(self):
        path = self.image(size=(100, 50))
        text = '<img src="/assets/projects/demo/original%20image.png">'
        first, _ = self.rewrite(text)
        src = Images(first).items[0]["src"]
        generated = self.destination / src.lstrip("/")
        generated.unlink()
        self.assertEqual(self.rewrite(text)[0], first)
        self.assertTrue(generated.is_file())
        Image.new("RGB", (100, 50), "blue").save(path)
        second, _ = self.rewrite(text)
        self.assertNotEqual(Images(second).items[0]["src"], src)

    def test_missing_image_fails_but_paths_outside_assets_are_ignored(self):
        with self.assertRaisesRegex(ValueError, "Missing local image"):
            self.rewrite('<img src="/assets/missing.png">')
        text = '<img src="/assets/../../outside.png">'
        self.assertEqual(self.rewrite(text)[0], text)

    def test_existing_attributes_and_composition_classes_are_kept(self):
        self.image(size=(100, 50))
        text = ('<div class="two-column"><img src="/assets/projects/demo/original%20image.png" '
                'class="media--half" loading="eager" width="50" height="25" style="border:0"></div>')
        rendered, _ = self.rewrite(text)
        image = Images(rendered).items[0]
        self.assertEqual(image["loading"], "eager")
        self.assertEqual(image["width"], "50")
        self.assertEqual(image["height"], "25")
        self.assertEqual(image["style"], "border:0")
        self.assertIn("25vw", image["sizes"])

    def test_exif_orientation_and_palette_color_profile(self):
        photo = self.assets / "photo.jpg"
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (100, 50), "red").save(photo, exif=exif)
        rendered, _ = self.rewrite('<img src="/assets/projects/demo/photo.jpg">')
        attrs = Images(rendered).items[0]
        self.assertEqual((attrs["width"], attrs["height"]), ("50", "100"))
        palette = self.assets / "palette.png"
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        Image.new("RGB", (50, 50), "blue").convert("P").save(palette, icc_profile=profile)
        rendered, _ = self.rewrite('<img src="/assets/projects/demo/palette.png">')
        self.assertIn("/assets/optimized-media/", Images(rendered).items[0]["src"])

    def test_legacy_asset_url_is_restored_with_identical_bytes(self):
        original = self.image()
        scripts = self.source / "scripts"
        scripts.mkdir()
        (scripts / "legacy_asset_paths.json").write_text(json.dumps({
            "assets/old-cover.png": "assets/projects/demo/original image.png",
        }))
        optimizer = Optimizer(self.source, self.destination)
        optimizer.restore_legacy_assets()
        self.assertEqual((self.destination / "assets/old-cover.png").read_bytes(), original.read_bytes())

    def test_legacy_asset_mapping_rejects_paths_outside_assets(self):
        scripts = self.source / "scripts"
        scripts.mkdir()
        manifest = scripts / "legacy_asset_paths.json"
        manifest.write_text(json.dumps({"../outside.png": "assets/projects/demo/original.png"}))
        with self.assertRaisesRegex(ValueError, "must stay inside assets"):
            Optimizer(self.source, self.destination).restore_legacy_assets()


if __name__ == "__main__":
    unittest.main()
