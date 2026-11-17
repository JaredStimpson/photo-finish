import unittest
import tempfile
from pathlib import Path
from queue import Queue
from threading import Event
from time import perf_counter
from types import SimpleNamespace

from PIL import Image
from main import App
from processing import Settings
from receipt import BatchReceipt, format_receipt


class ReceiptTests(unittest.TestCase):
    def receipt(self, **changes):
        fields = dict(status="Finished", elapsed=65.25, discovered=4, processed=4,
                      saved=2, skipped=1, failed=1, input_bytes=4 * 1024 * 1024,
                      output_bytes=3 * 1024 * 1024, source="C:/Photos", output="C:/Finished",
                      settings=Settings(canvas_mode="Border", top=40, bottom=100,
                                        left=20, right=90), error="")
        fields.update(changes)
        return BatchReceipt(**fields)

    def test_counts_savings_and_active_margins(self):
        text = format_receipt(self.receipt())
        self.assertIn("Elapsed time: 00:01:05.25", text)
        self.assertIn("Items processed: 4", text)
        self.assertIn("Saved: 2    Skipped: 1    Failed: 1", text)
        self.assertIn("Space saved: 1.00 MiB (1,048,576 bytes) (+25.0%)", text)
        self.assertIn("top 40, bottom 40, left 20, right 20 px", text)

    def test_larger_png_and_canceled_batch(self):
        text = format_receipt(self.receipt(status="Canceled", processed=1,
                                           saved=1, skipped=0, failed=0,
                                           input_bytes=1024 * 1024,
                                           output_bytes=2 * 1024 * 1024))
        self.assertIn("Status: Canceled", text)
        self.assertIn("Space saved: -1.00 MiB (-1,048,576 bytes) (-100.0%)", text)

    def test_empty_batch_and_outer_error(self):
        text = format_receipt(self.receipt(status="Stopped", discovered=0,
                                           processed=0, saved=0, skipped=0, failed=0,
                                           input_bytes=0, output_bytes=0,
                                           error="Cannot scan input folder"))
        self.assertIn("Space saved: 0.00 MiB (0 bytes) (+0.0%)", text)
        self.assertIn("Batch error: Cannot scan input folder", text)

    def test_worker_receipt_counts_saved_skipped_and_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / "input", Path(directory) / "output"
            source.mkdir()
            output.mkdir()
            Image.new("RGB", (20, 20), "red").save(source / "good.jpg")
            Image.new("RGB", (20, 20), "blue").save(source / "existing.jpg")
            (output / "existing_finished.png").write_bytes(b"existing output")
            (source / "bad.jpg").write_bytes(b"not a JPEG")
            worker = SimpleNamespace(events=Queue(), stop=Event())
            App.worker(worker, source, output, Settings(canvas=False), perf_counter(), True)
            events = []
            while not worker.events.empty():
                events.append(worker.events.get_nowait())
            receipt = events[-1][2]
            self.assertEqual(events[-1][0], "done")
            self.assertEqual(receipt.discovered, 3)
            self.assertEqual((receipt.processed, receipt.saved, receipt.skipped, receipt.failed), (3, 1, 1, 1))
            self.assertGreater(receipt.input_bytes, 0)
            self.assertGreater(receipt.output_bytes, 0)


if __name__ == "__main__":
    unittest.main()
