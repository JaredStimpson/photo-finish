import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image

from processing import (Settings, canvas_size, image_layout, list_jpgs,
                        output_path, parse_ratio, process_image, sibling_output_folder)


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "input"
        self.source.mkdir()
        self.jpg = self.source / "sample.jpg"
        image = Image.new("RGB", (101, 151))
        for y in range(151):
            for x in range(101):
                image.putpixel((x, y), (x * 2 % 256, y * 3 % 256, (x + y) % 256))
        image.save(self.jpg, quality=89)

    def test_exact_decoded_pixels_and_border_in_png(self):
        settings = Settings(width=150, height=225, color="#F9F1DD")
        target = self.root / "out" / "sample_finished.png"
        process_image(self.jpg, target, settings)
        with Image.open(self.jpg) as source, Image.open(target) as result:
            self.assertEqual(result.size, (150, 225))
            self.assertEqual(result.getpixel((0, 0)), (249, 241, 221))
            self.assertEqual(result.getpixel((149, 224)), (249, 241, 221))
            self.assertEqual(result.crop((24, 37, 125, 188)).tobytes(), source.convert("RGB").tobytes())

    def test_auto_orientation_and_exact_multiple_expansion(self):
        settings = Settings(width=200, height=300, expand=True)
        self.assertEqual(canvas_size(settings, (350, 190)), (600, 400))
        self.assertEqual(canvas_size(settings, (201, 301)), (400, 600))
        with self.assertRaises(ValueError):
            canvas_size(replace(settings, expand=False), (201, 301))

    def test_reducer_jpeg_and_no_upscaling(self):
        settings = Settings(canvas=False, lossless=False, reduce=True, max_edge=80, format="JPEG")
        dest = self.root / "reduced.jpg"
        before, after, _, _ = process_image(self.jpg, dest, settings)
        self.assertEqual(before, (101, 151))
        self.assertEqual(after, (54, 80))
        with Image.open(dest) as result:
            self.assertEqual(result.size, (54, 80))
            self.assertEqual(result.format, "JPEG")
        with self.assertRaises(FileExistsError):
            process_image(self.jpg, dest, settings)

    def test_ratio_and_nested_output_scan(self):
        self.assertEqual(parse_ratio(" 4 : 6 "), (2, 3))
        with self.assertRaises(ValueError):
            parse_ratio("0:3")
        output = self.source / "out"
        output.mkdir()
        (output / "already.jpg").write_bytes(b"not an input")
        files = list_jpgs(self.source, output, True)
        self.assertEqual(files, [self.jpg])
        self.assertEqual(output_path(self.jpg, self.source, output, Settings()), output / "sample_finished.png")

    def test_exif_orientation_is_applied_and_metadata_is_optional(self):
        rotated = self.source / "rotated.jpg"
        image = Image.new("RGB", (30, 20), "red")
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "Example camera"
        image.save(rotated, exif=exif)
        no_metadata = self.root / "no_metadata.png"
        keep_metadata = self.root / "keep_metadata.png"
        process_image(rotated, no_metadata, Settings(canvas=False))
        process_image(rotated, keep_metadata, Settings(canvas=False, metadata=True))
        with Image.open(no_metadata) as result:
            self.assertEqual(result.size, (20, 30))
            self.assertNotIn(315, result.getexif())
        with Image.open(keep_metadata) as result:
            self.assertEqual(result.size, (20, 30))
            self.assertEqual(result.getexif()[315], "Example camera")
            self.assertEqual(result.getexif().get(274, 1), 1)

    def test_border_mode_links_pairs_and_keeps_source_pixels(self):
        settings = Settings(canvas_mode="Border", top=13, bottom=99, left=7, right=99,
                            same_top_bottom=True, same_sides=True, color="#FFFFFF")
        self.assertEqual(image_layout(settings, (101, 151)), ((115, 177), (7, 13)))
        target = self.root / "linked.png"
        process_image(self.jpg, target, settings)
        with Image.open(self.jpg) as source, Image.open(target) as result:
            self.assertEqual(result.size, (115, 177))
            self.assertEqual(result.crop((7, 13, 108, 164)).tobytes(), source.convert("RGB").tobytes())
            self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))
        independent = replace(settings, same_top_bottom=False, same_sides=False, bottom=5, right=19)
        self.assertEqual(image_layout(independent, (101, 151)), ((127, 169), (7, 13)))

    def test_lossless_mode_rejects_recompression_and_resizing(self):
        with self.assertRaisesRegex(ValueError, "Lossless mode"):
            process_image(self.jpg, self.root / "wrong.jpg", Settings(canvas=False, format="JPEG"))
        with self.assertRaisesRegex(ValueError, "Lossless mode"):
            process_image(self.jpg, self.root / "wrong.png", Settings(canvas=False, reduce=True))

    def test_automatic_sibling_folder_preserves_input_and_existing_outputs(self):
        sibling = sibling_output_folder(self.source, "_finished")
        self.assertEqual(sibling, self.root / "input_finished")
        self.assertFalse(sibling.exists())
        destination = output_path(self.jpg, self.source, sibling, Settings(canvas=False))
        process_image(self.jpg, destination, Settings(canvas=False))
        before = destination.read_bytes()
        with self.assertRaises(FileExistsError):
            process_image(self.jpg, destination, Settings(canvas=False))
        self.assertEqual(destination.read_bytes(), before)
        self.assertTrue(self.jpg.exists())
        with self.assertRaises(ValueError):
            sibling_output_folder(self.source, "")
        with self.assertRaises(ValueError):
            sibling_output_folder(self.source, "../bad")


if __name__ == "__main__":
    unittest.main()
