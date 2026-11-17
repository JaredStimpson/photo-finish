import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image, features

from main import App
from processing import (Settings, canvas_size, image_layout, list_images,
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
        before, after, _, _, frames = process_image(self.jpg, dest, settings)
        self.assertEqual(before, (101, 151))
        self.assertEqual(after, (54, 80))
        self.assertEqual(frames, 1)
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
        files = list_images(self.source, output, True)
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

    def test_jpeg_signature_allows_unusual_decoder_format_report(self):
        real_open = Image.open

        def unusual_format(path):
            image = real_open(path)
            image.format = "MPO"
            image.n_frames = 2
            return image

        with patch("processing.Image.open", side_effect=unusual_format):
            destination = self.root / "signature.png"
            process_image(self.jpg, destination, Settings(canvas=False))
        with Image.open(destination) as result:
            self.assertEqual(result.size, (101, 151))

    def test_mislabeled_png_is_processed_from_jpg_filename(self):
        misleading = self.source / "misleading.jpg"
        Image.new("RGB", (8, 8), "red").save(misleading, format="PNG")
        destination = self.root / "normalized.png"
        process_image(misleading, destination, Settings(canvas=False))
        with Image.open(destination) as result:
            self.assertEqual(result.getpixel((0, 0)), (255, 0, 0))

    def test_other_static_formats_and_input_extension_filter(self):
        for fmt, suffix in (("PNG", ".png"), ("TIFF", ".tiff"), ("BMP", ".bmp"), ("GIF", ".gif")):
            image = self.source / f"photo_{fmt}{suffix}"
            Image.new("RGB", (12, 10), "green").save(image, format=fmt)
            target = self.root / f"result_{fmt}.png"
            process_image(image, target, Settings(canvas=False))
            with Image.open(target) as result:
                self.assertEqual(result.size, (12, 10))
        if features.check("webp"):
            webp = self.source / "photo.webp"
            Image.new("RGB", (12, 10), "green").save(webp, format="WEBP")
            process_image(webp, self.root / "webp.png", Settings(canvas=False))
        if features.check("avif"):
            avif = self.source / "photo.avif"
            Image.new("RGB", (12, 10), "green").save(avif, format="AVIF")
            process_image(avif, self.root / "avif.png", Settings(canvas=False))
        self.assertIn(self.jpg, list_images(self.source, self.root / "unused", False))

    def test_rgba_png_preserves_alpha_and_jpeg_flattens_onto_fill(self):
        source = self.source / "alpha.png"
        image = Image.new("RGBA", (32, 16), (200, 30, 10, 0))
        for y in range(16):
            for x in range(16, 32):
                image.putpixel((x, y), (10, 20, 30, 255))
        image.save(source)
        settings = Settings(canvas_mode="Border", top=1, left=1, color="#FFFFFF")
        result = self.root / "alpha_finished.png"
        process_image(source, result, settings)
        with Image.open(result) as finished:
            self.assertEqual(finished.mode, "RGBA")
            self.assertEqual(finished.getpixel((1, 1)), (200, 30, 10, 0))
            self.assertEqual(finished.getpixel((0, 0)), (255, 255, 255, 255))
        jpeg = self.root / "flattened.jpg"
        process_image(source, jpeg, replace(settings, lossless=False, format="JPEG", quality=95))
        with Image.open(jpeg) as finished:
            self.assertEqual(finished.mode, "RGB")
            self.assertGreater(min(finished.getpixel((5, 8))), 200)
        reduced = self.root / "reduced_alpha.png"
        process_image(source, reduced, Settings(canvas=False, lossless=False, reduce=True,
                                                max_edge=16, sharpen=True))
        with Image.open(reduced) as finished:
            self.assertEqual(finished.size, (16, 8))
            self.assertEqual(finished.mode, "RGBA")

    def test_palette_png_with_transparency_keeps_visible_and_alpha_pixels(self):
        source = self.source / "palette.png"
        image = Image.new("P", (2, 1))
        image.putpalette([255, 0, 0, 0, 0, 255] + [0] * 762)
        image.putdata([0, 1])
        image.info["transparency"] = 1
        image.save(source)
        target = self.root / "palette_finished.png"
        process_image(source, target, Settings(canvas=False))
        with Image.open(target) as finished:
            self.assertEqual(finished.mode, "RGBA")
            self.assertEqual(finished.getpixel((0, 0)), (255, 0, 0, 255))
            self.assertEqual(finished.getpixel((1, 0)), (0, 0, 255, 0))

    def test_lossless_rejects_high_depth_instead_of_silent_conversion(self):
        source = self.source / "high_depth.tiff"
        Image.new("I;16", (3, 3), 1000).save(source)
        with self.assertRaisesRegex(ValueError, "Lossless PNG cannot retain"):
            process_image(source, self.root / "high_depth.png", Settings(canvas=False))

    def test_multiframe_images_are_not_silently_truncated(self):
        animated = self.source / "animated.gif"
        Image.new("RGB", (3, 3), "red").save(animated, save_all=True,
                                                append_images=[Image.new("RGB", (3, 3), "blue")], duration=50)
        with self.assertRaisesRegex(ValueError, "Multi-frame image"):
            process_image(animated, self.root / "animated.png", Settings(canvas=False))

    def test_multi_picture_jpeg_uses_primary_frame_and_reports_count(self):
        real_open = Image.open

        def windows_like_mpo(path):
            image = real_open(path)
            image.format = "MPO"
            image.n_frames = 2
            return image

        target = self.root / "primary.png"
        with patch("processing.Image.open", side_effect=windows_like_mpo):
            _, size, _, _, frames = process_image(self.jpg, target, Settings(canvas=False))
        self.assertEqual((size, frames), ((101, 151), 2))
        with Image.open(target) as output:
            with Image.open(self.jpg) as original:
                self.assertEqual(output.tobytes(), original.convert("RGB").tobytes())

    def test_preview_uses_same_jpeg_signature_check(self):
        class Panel:
            def delete(self, *_):
                pass

            def winfo_width(self):
                return 500

            def winfo_height(self):
                return 230

            def create_image(self, *_, **__):
                pass

        class Info:
            value = ""

            def set(self, value):
                self.value = value

        info = Info()
        stub = SimpleNamespace(preview_job=None, preview_canvas=Panel(), preview_ref=None,
                               preview_file=self.jpg, preview_info=info,
                               settings=lambda: Settings(canvas=False))
        real_open = Image.open

        def unusual_format(path):
            image = real_open(path)
            image.format = "MPO"
            image.n_frames = 2
            return image

        with patch("main.Image.open", side_effect=unusual_format), patch("main.ImageTk.PhotoImage", side_effect=lambda im: im):
            App.draw_preview(stub)
        self.assertIn("sample.jpg · photo 101×151", info.value)
        self.assertIn("first of 2 JPEG frames", info.value)


if __name__ == "__main__":
    unittest.main()
