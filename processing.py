"""Image processing for Photo Finish. No GUI dependencies."""
from dataclasses import dataclass
from pathlib import Path
import math
import os
import re

from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class Settings:
    canvas: bool = True
    canvas_mode: str = "Canvas"  # Canvas (target size) or Border (pixel margins)
    ratio_w: int = 2
    ratio_h: int = 3
    width: int = 2000
    height: int = 3000
    orientation: str = "Auto"  # Auto, Portrait, Landscape
    color: str = "#FFFFFF"
    reduce: bool = False
    max_edge: int = 2560
    sharpen: bool = True
    quality: int = 85
    format: str = "PNG"  # PNG or JPEG
    metadata: bool = False
    recursive: bool = False
    suffix: str = "_finished"
    expand: bool = False
    top: int = 100
    bottom: int = 100
    left: int = 100
    right: int = 100
    same_top_bottom: bool = True
    same_sides: bool = True
    lossless: bool = True


def parse_ratio(value):
    match = re.fullmatch(r"\s*(\d+)\s*[:/]\s*(\d+)\s*", value)
    if not match or int(match[1]) == 0 or int(match[2]) == 0:
        raise ValueError("Enter a ratio such as 2:3 or 4:5.")
    a, b = int(match[1]), int(match[2])
    if a > 10000 or b > 10000:
        raise ValueError("Ratio numbers must be 10,000 or smaller.")
    factor = math.gcd(a, b)
    return a // factor, b // factor


def linked_dimension(value, numerator, denominator):
    return max(1, round(value * numerator / denominator))


def validate(settings):
    if settings.canvas_mode not in ("Canvas", "Border"):
        raise ValueError("Choose Canvas or Border sizing.")
    if settings.lossless and (settings.reduce or settings.format != "PNG"):
        raise ValueError("Lossless mode requires PNG output with reduction turned off.")
    if settings.format not in ("PNG", "JPEG"):
        raise ValueError("Choose PNG or JPEG output.")
    if settings.orientation not in ("Auto", "Portrait", "Landscape"):
        raise ValueError("Choose Auto, Portrait, or Landscape orientation.")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", settings.color):
        raise ValueError("Border color must be a six-digit hex color, such as #FFFFFF.")
    if settings.canvas and settings.canvas_mode == "Canvas":
        if not 1 <= settings.width <= 100000 or not 1 <= settings.height <= 100000:
            raise ValueError("Canvas dimensions must be 1–100,000 pixels.")
        if settings.ratio_w < 1 or settings.ratio_h < 1:
            raise ValueError("Ratio components must be positive.")
    if settings.canvas and settings.canvas_mode == "Border":
        if any(not 0 <= value <= 100000 for value in (settings.top, settings.bottom, settings.left, settings.right)):
            raise ValueError("Border widths must be 0–100,000 pixels.")
    if not 1 <= settings.max_edge <= 100000:
        raise ValueError("Longest edge must be 1–100,000 pixels.")
    if not 40 <= settings.quality <= 95:
        raise ValueError("JPEG quality must be 40–95.")
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', settings.suffix) or settings.suffix.endswith((" ", ".")):
        raise ValueError("Suffix contains characters Windows does not allow in filenames.")


def list_jpgs(source, output, recursive):
    """Snapshot inputs; never follow symlinks or traverse an output subtree."""
    files_found = []
    for root, dirs, names in os.walk(source, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(root) / d).is_symlink()
                         and not (Path(root) / d).resolve().is_relative_to(output))
        for name in sorted(names):
            path = Path(root) / name
            if path.suffix.lower() in (".jpg", ".jpeg") and not path.is_symlink():
                files_found.append(path)
        if not recursive:
            break
    return files_found


def canvas_size(settings, image_size):
    """Return final canvas size, keeping the portrait/landscape ratio per image."""
    width, height = settings.width, settings.height
    if settings.orientation == "Auto":
        if (image_size[0] > image_size[1]) != (width > height) and width != height:
            width, height = height, width
    elif (settings.orientation == "Landscape") != (width > height) and width != height:
        width, height = height, width
    if image_size[0] <= width and image_size[1] <= height:
        return width, height
    if not settings.expand:
        raise ValueError(f"Photo {image_size[0]}×{image_size[1]} exceeds canvas {width}×{height}; enable auto-expand or reduction.")
    # Use integer multiples of the selected dimensions: exact ratio, no clipping.
    multiple = max(math.ceil(image_size[0] / width), math.ceil(image_size[1] / height))
    if width * multiple > 100000 or height * multiple > 100000:
        raise ValueError("Expanded canvas exceeds the 100,000 pixel dimension limit.")
    return width * multiple, height * multiple


def image_layout(settings, image_size):
    """Return (output size, photo origin); photo pixels are never clipped."""
    if not settings.canvas:
        return image_size, (0, 0)
    if settings.canvas_mode == "Border":
        right = settings.left if settings.same_sides else settings.right
        bottom = settings.top if settings.same_top_bottom else settings.bottom
        size = (image_size[0] + settings.left + right, image_size[1] + settings.top + bottom)
        origin = (settings.left, settings.top)
    else:
        size = canvas_size(settings, image_size)
        origin = ((size[0] - image_size[0]) // 2, (size[1] - image_size[1]) // 2)
    if max(size) > 100000 or size[0] * size[1] > 150_000_000:
        raise ValueError("Output exceeds the 100,000 pixel edge or 150 megapixel limit.")
    return size, origin


def output_path(source_file, input_root, output_root, settings):
    relative = source_file.relative_to(input_root)
    ext = ".png" if settings.format == "PNG" else ".jpg"
    return output_root / relative.parent / (relative.stem + settings.suffix + ext)


def sibling_output_folder(source, suffix):
    """Derive the adjacent output directory without creating or touching it."""
    if not source.name:
        raise ValueError("Choose a named input folder for automatic output.")
    if not suffix:
        raise ValueError("Enter a nonempty image suffix for automatic output.")
    if re.search(r'[<>:"/\\|?*\x00-\x1f]', suffix) or suffix.endswith((" ", ".")):
        raise ValueError("Suffix contains characters Windows does not allow in filenames.")
    return source.parent / (source.name + suffix)


def process_image(source, destination, settings):
    """Create output exclusively; errors never leave a partially written file."""
    validate(settings)
    if destination.exists():
        raise FileExistsError(f"Output already exists: {destination.name}")
    with Image.open(source) as original:
        if original.format != "JPEG":
            raise ValueError("Input is not a JPEG image.")
        icc = original.info.get("icc_profile")
        image = ImageOps.exif_transpose(original)
        exif = image.getexif().tobytes() if settings.metadata else None
        image = image.convert("RGB")
        initial_size = image.size
        if settings.reduce:
            scale = min(1.0, settings.max_edge / max(image.size))
            if scale < 1:
                image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.BICUBIC)
                if settings.sharpen:
                    image = image.filter(ImageFilter.UnsharpMask(radius=0.7, percent=80, threshold=3))
        if settings.canvas:
            size, origin = image_layout(settings, image.size)
            canvas = Image.new("RGB", size, settings.color)
            canvas.paste(image, origin)
            image = canvas
        options = {}
        if icc:
            options["icc_profile"] = icc
        if exif:
            options["exif"] = exif
        if settings.format == "JPEG":
            options.update(format="JPEG", quality=settings.quality, optimize=True, progressive=True, subsampling=2)
        else:
            options.update(format="PNG", compress_level=6)
            if settings.metadata:
                # Preserve basic print density where Pillow exposes it.
                dpi = original.info.get("dpi")
                if dpi and all(isinstance(v, (int, float)) and v > 0 for v in dpi):
                    options["dpi"] = dpi
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as handle:
            try:
                image.save(handle, **options)
            except BaseException:
                handle.close()
                destination.unlink(missing_ok=True)
                raise
    return initial_size, image.size, source.stat().st_size, destination.stat().st_size
