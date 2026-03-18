"""Tests for image compression utility."""

import os
import tempfile
import unittest

import tests.fixtures_env  # noqa: F401

from app import create_app
from app.utils.image import compress_image, create_thumbnail


class ImageCompressionTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["DB_TYPE"] = "postgres"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
        os.environ["TEST_MODE"] = "true"

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.tmpdir = tempfile.mkdtemp()
        self.app.config["UPLOAD_FOLDER"] = self.tmpdir
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
        # Cleanup temp files
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_test_image(self, name, width=2400, height=1600, mode="RGB"):
        """Create a test image file and return its filename."""
        from PIL import Image

        img = Image.new(mode, (width, height), color=(100, 150, 200))
        filepath = os.path.join(self.tmpdir, name)
        if name.endswith(".png"):
            img.save(filepath, "PNG")
        else:
            img.save(filepath, "JPEG")
        return name

    def test_compress_resizes_large_image(self):
        """Large images should be resized to max_width."""
        name = self._create_test_image("big.jpg", width=3000, height=2000)
        result = compress_image(name, max_width=1200)

        self.assertIsNotNone(result)
        from PIL import Image

        with Image.open(os.path.join(self.tmpdir, result)) as img:
            self.assertLessEqual(img.width, 1200)

    def test_compress_keeps_small_image(self):
        """Small images should not be resized."""
        name = self._create_test_image("small.jpg", width=800, height=600)
        result = compress_image(name, max_width=1200)

        self.assertIsNotNone(result)
        from PIL import Image

        with Image.open(os.path.join(self.tmpdir, result)) as img:
            self.assertEqual(img.width, 800)

    def test_compress_converts_png_to_jpg(self):
        """PNG files should be converted to JPEG."""
        name = self._create_test_image("photo.png", width=500, height=500)
        result = compress_image(name)

        self.assertIsNotNone(result)
        self.assertTrue(result.endswith(".jpg"))

    def test_compress_handles_rgba(self):
        """RGBA images should be converted without error."""
        name = self._create_test_image("alpha.png", width=500, height=500, mode="RGBA")
        result = compress_image(name)

        self.assertIsNotNone(result)
        from PIL import Image

        with Image.open(os.path.join(self.tmpdir, result)) as img:
            self.assertEqual(img.mode, "RGB")

    def test_compress_skips_gif(self):
        """GIF files should be returned as-is."""
        from PIL import Image

        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        gif_path = os.path.join(self.tmpdir, "anim.gif")
        img.save(gif_path, "GIF")

        result = compress_image("anim.gif")
        self.assertEqual(result, "anim.gif")

    def test_compress_missing_file_returns_none(self):
        """Missing files should return None."""
        result = compress_image("nonexistent.jpg")
        self.assertIsNone(result)

    def test_create_thumbnail(self):
        """Thumbnail should be created at correct size."""
        name = self._create_test_image("forThumb.jpg", width=1000, height=800)
        thumb = create_thumbnail(name, size=300)

        self.assertIsNotNone(thumb)
        self.assertTrue(thumb.startswith("thumb_"))
        from PIL import Image

        with Image.open(os.path.join(self.tmpdir, thumb)) as img:
            self.assertLessEqual(img.width, 300)
            self.assertLessEqual(img.height, 300)

    def test_file_size_reduced(self):
        """Compressed file should be smaller than original."""
        name = self._create_test_image("large.jpg", width=3000, height=2000)
        original_size = os.path.getsize(os.path.join(self.tmpdir, name))

        result = compress_image(name, max_width=1200, quality=80)
        compressed_size = os.path.getsize(os.path.join(self.tmpdir, result))

        self.assertLess(compressed_size, original_size)


if __name__ == "__main__":
    unittest.main()
