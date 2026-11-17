# photo-finish working plan

## Purpose

Finish batches of JPG photographs by optionally reducing them and adding a specified solid-color canvas. Preserve source files and offer lossless PNG output for unchanged decoded source pixels. The GUI groups related controls and reflows to one column on narrow windows.

## Version 1.1 implemented

- Input/output folder selection, optional recursive scan, JPG/JPEG only, mirrored folders, skip existing outputs, cancellation, progress, per-photo log.
- Bicubic reduction with maximum edge, no upscaling, optional sharpening only when resized, default JPEG quality 85, progressive optimized JPEG output.
- PNG or JPEG export, optional EXIF retention, applied EXIF orientation, retained ICC profile.
- Canvas on/off, color hex input and picker. Canvas mode uses ratio presets/custom ratio, linked pixel width/height, Auto/Portrait/Landscape orientation, centered placement, and optional ratio-preserving expansion. Border mode uses top/bottom/left/right pixel margins with optional linked top/bottom and left/right pairs.
- Lossless checkbox disables reduction controls and JPEG output, and exports exact decoded pixels in PNG (the original JPG bytes are not preserved).
- First-photo preview, scrollable GUI sections, responsive two-column/one-column layout, one-file Windows build scripts.

## Prior feature index for future decisions

| # | Feature | v1 status |
|---:|---|---|
| 1 | Ratio presets and custom ratio | Included |
| 2 | Linked width and height | Included |
| 3 | Pixels, inches, and DPI inputs | Pixels only |
| 4 | Portrait/landscape toggle | Included, plus Auto |
| 5 | Minimum border and auto-expand | Auto-expand included; minimum border pending |
| 6 | Placement controls | Canvas mode centered; Border mode sets margins |
| 7 | Unequal margins | Included in Border mode |
| 8 | Live preview and batch summary | First photo preview and batch run summary included |
| 9 | Mixed-orientation batch rules | Auto orientation included |
| 10 | Output naming and folder rules | Suffix, mirrored folders, skip existing included |
| 11 | EXIF orientation and color profile handling | Included for common RGB JPGs |
| 12 | JPEG-preserving output mode | Pending; ordinary JPEG output recompresses |

## Delivery and updates

Release as a complete repository ZIP. Each update should say which files changed, whether `setup.bat` must be rerun, whether `.venv` must be rebuilt, and whether build/cache cleanup is necessary. A one-file EXE requires a Windows build and verification there.
