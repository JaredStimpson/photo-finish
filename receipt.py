"""Pure formatting of a Photo Finish batch receipt."""
from dataclasses import dataclass

from processing import Settings


@dataclass(frozen=True)
class BatchReceipt:
    status: str
    elapsed: float
    discovered: int
    processed: int
    saved: int
    skipped: int
    failed: int
    input_bytes: int
    output_bytes: int
    source: str
    output: str
    settings: Settings
    error: str = ""
    failure_reasons: tuple[tuple[str, int], ...] = ()
    failure_examples: tuple[str, ...] = ()


def _size(value):
    return f"{value / (1024 * 1024):,.2f} MiB ({value:,} bytes)"


def _duration(seconds):
    minutes, rem = divmod(max(0, seconds), 60)
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours:02d}:{minutes:02d}:{rem:05.2f}"


def format_receipt(receipt):
    settings = receipt.settings
    saved_bytes = receipt.input_bytes - receipt.output_bytes
    pct = 100 * saved_bytes / receipt.input_bytes if receipt.input_bytes else 0.0
    if settings.canvas:
        if settings.canvas_mode == "Border":
            bottom = settings.top if settings.same_top_bottom else settings.bottom
            right = settings.left if settings.same_sides else settings.right
            sizing = (f"Border margins: top {settings.top}, bottom {bottom}, "
                      f"left {settings.left}, right {right} px")
        else:
            sizing = (f"Canvas: {settings.width} × {settings.height} px; "
                      f"ratio {settings.ratio_w}:{settings.ratio_h}; "
                      f"orientation {settings.orientation}; expand {'on' if settings.expand else 'off'}")
        fill = f"Fill: {settings.color}"
    else:
        sizing, fill = "Canvas/border: off", ""
    if settings.lossless:
        reduction = "Lossless PNG; no resizing or sharpening"
    elif settings.reduce:
        reduction = (f"Bicubic reduction: longest edge {settings.max_edge} px; "
                     f"sharpen {'on' if settings.sharpen else 'off'}")
    else:
        reduction = "Reduction: off"
    output_format = settings.format + (f"; quality {settings.quality}" if settings.format == "JPEG" else "")
    lines = [
        "PHOTO FINISH · BATCH RECEIPT",
        "",
        f"Status: {receipt.status}",
        f"Elapsed time: {_duration(receipt.elapsed)}",
        f"Images found: {receipt.discovered}",
        f"Items processed: {receipt.processed}",
        f"Saved: {receipt.saved}    Skipped: {receipt.skipped}    Failed: {receipt.failed}",
        "",
        "SIZE TOTALS · SAVED FILES ONLY",
        f"Before: {_size(receipt.input_bytes)}",
        f"After:  {_size(receipt.output_bytes)}",
        f"Space saved: {_size(saved_bytes)} ({pct:+.1f}%)",
        "A negative saving means the outputs use more space.",
        "",
        "SETTINGS USED",
        sizing,
        fill,
        reduction,
        f"Output: {output_format}; suffix {settings.suffix or '(none)'}",
        f"Subfolders: {'included' if settings.recursive else 'top folder only'}; EXIF: {'kept' if settings.metadata else 'omitted'}",
        "",
        f"Input folder: {receipt.source}",
        f"Output folder: {receipt.output}",
    ]
    if receipt.error:
        lines.extend(["", f"Batch error: {receipt.error}"])
    if receipt.failure_reasons:
        lines.extend(["", "FAILURE REASONS"])
        lines.extend(f"{count} × {reason}" for reason, count in receipt.failure_reasons)
    if receipt.failure_examples:
        lines.extend(["", "FIRST FAILED FILES"])
        lines.extend(receipt.failure_examples)
    return "\n".join(lines) + "\n"
