"""Exercise the real build hook with only Markdown and original-size images."""
import shutil
import json
import subprocess
import tempfile
import time
import unittest
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image


class Sources(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.items = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.items.append(dict(attrs).get("src", ""))


class JekyllIntegrationTest(unittest.TestCase):
    def test_watch_optimizes_added_markdown_and_updated_original(self):
        repository = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, destination = root / "source", root / "output"
            (source / "_layouts").mkdir(parents=True)
            projects = source / "content/_projects"
            projects.mkdir(parents=True)
            (source / "assets/projects/first").mkdir(parents=True)
            shutil.copytree(repository / "_plugins", source / "_plugins")
            shutil.copytree(repository / "scripts", source / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
            (source / "scripts/legacy_asset_paths.json").write_text(json.dumps({
                "assets/projects/old-original.png": "assets/projects/first/original.png",
            }))
            (source / "_config.yml").write_text(
                'exclude: [scripts, .image-cache]\n'
                'collections_dir: content\n'
                'collections:\n  projects:\n    output: true\n    permalink: /projects/:path/\n'
                'defaults:\n  - scope:\n      path: ""\n      type: projects\n'
                '    values:\n      layout: default\n'
            )
            (source / "_layouts/default.html").write_text(
                '<html><body><section class="page__content">{{ content }}</section></body></html>'
            )
            original = source / "assets/projects/first/original.png"
            Image.new("RGB", (1200, 700), "red").save(original)
            (projects / "first.md").write_text(
                '---\ntitle: First\n---\n![First](/assets/projects/first/original.png)\n'
            )
            log_path = root / "jekyll.log"
            with log_path.open("w") as log:
                process = subprocess.Popen(
                    ["bundle", "exec", "jekyll", "build", "--watch", "--force_polling", "--source", str(source),
                     "--destination", str(destination)],
                    cwd=repository, stdout=log, stderr=subprocess.STDOUT,
                )
                try:
                    def await_condition(condition):
                        deadline = time.monotonic() + 25
                        while time.monotonic() < deadline:
                            if condition():
                                return
                            if process.poll() is not None:
                                break
                            time.sleep(0.1)
                        self.fail("Jekyll watch did not update output:\n" + log_path.read_text())

                    first_page = destination / "projects/first/index.html"
                    def image_source(page):
                        if not page.is_file():
                            return ""
                        images = Sources(page.read_text()).items
                        return images[0] if images else ""

                    await_condition(lambda: "Auto-regeneration: enabled" in log_path.read_text()
                                    and "/assets/optimized-media/" in image_source(first_page))
                    # Listen starts its baseline scan asynchronously; allow it to settle.
                    time.sleep(1)
                    first_url = image_source(first_page)
                    Image.new("RGB", (1200, 700), "blue").save(original)
                    await_condition(lambda: "/assets/optimized-media/" in image_source(first_page)
                                    and image_source(first_page) != first_url)
                    (source / "assets/projects/second").mkdir()
                    second = source / "assets/projects/second/original.png"
                    Image.new("RGB", (900, 500), "green").save(second)
                    markdown = '---\ntitle: Second\n---\n![Second](/assets/projects/second/original.png)\n'
                    (projects / "second.md").write_text(markdown)
                    second_page = destination / "projects/second/index.html"
                    await_condition(lambda: "/assets/optimized-media/" in image_source(second_page))
                    self.assertEqual((projects / "second.md").read_text(), markdown)
                    self.assertTrue((destination / image_source(second_page).lstrip("/")).is_file())
                    with Image.open(second) as image:
                        self.assertEqual(image.size, (900, 500))
                    self.assertEqual((destination / "assets/projects/old-original.png").read_bytes(), original.read_bytes())
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
