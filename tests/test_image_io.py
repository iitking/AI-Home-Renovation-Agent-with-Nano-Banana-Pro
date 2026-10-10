import tempfile
import unittest
from pathlib import Path

from PIL import Image

from renovation_agent.image_io import ImageError, load_image, nearest_aspect_ratio, save_image_bytes
from helpers import png_bytes


class TestAspect(unittest.TestCase):
    def test_common(self):
        self.assertEqual(nearest_aspect_ratio(1920, 1080), "16:9")
        self.assertEqual(nearest_aspect_ratio(1000, 1000), "1:1")
        self.assertEqual(nearest_aspect_ratio(4032, 3024), "4:3")
        self.assertEqual(nearest_aspect_ratio(3024, 4032), "3:4")
        self.assertEqual(nearest_aspect_ratio(1080, 1920), "9:16")

    def test_invalid(self):
        with self.assertRaises(ImageError):
            nearest_aspect_ratio(0, 10)


class TestLoad(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_loads_and_downscales(self):
        p = self.tmp / "big.jpg"
        Image.new("RGB", (4000, 3000), "white").save(p)
        img = load_image(p)
        self.assertEqual(max(img.size), 2048)
        self.assertEqual(img.mode, "RGB")

    def test_png_with_alpha_converted(self):
        p = self.tmp / "a.png"
        Image.new("RGBA", (100, 100), (255, 0, 0, 128)).save(p)
        self.assertEqual(load_image(p).mode, "RGB")

    def test_exif_rotation_applied(self):
        p = self.tmp / "rot.jpg"
        img = Image.new("RGB", (200, 100), "blue")
        exif = Image.Exif()
        exif[0x0112] = 6  # rotate 90 CW when displayed
        img.save(p, exif=exif)
        self.assertEqual(load_image(p).size, (100, 200))

    def test_errors(self):
        with self.assertRaises(ImageError):
            load_image(self.tmp / "nope.jpg")
        bad = self.tmp / "x.gif"
        bad.write_bytes(b"x")
        with self.assertRaises(ImageError):
            load_image(bad)
        fake = self.tmp / "fake.jpg"
        fake.write_text("not an image")
        with self.assertRaises(ImageError):
            load_image(fake)

    def test_save_bytes(self):
        out = save_image_bytes(png_bytes(), self.tmp / "sub" / "o.png")
        self.assertTrue(out.exists())
        with self.assertRaises(ImageError):
            save_image_bytes(b"garbage", self.tmp / "bad.png")


if __name__ == "__main__":
    unittest.main()

# Verified corrupted formats
