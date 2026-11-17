# photo-finish working plan

## Purpose

Finish batches of JPG photographs by optionally reducing them and adding a specified solid-color canvas. Preserve source files and offer lossless PNG output for unchanged decoded source pixels. The GUI groups related controls and reflows to one column on narrow windows.

## Version 1.6 implemented

- Input/output folder selection, optional recursive scan, common single-frame photo formats, mirrored folders, skip existing outputs, cancellation, progress, per-photo log.
- Bicubic reduction with maximum edge, no upscaling, optional sharpening only when resized, default JPEG quality 85, progressive optimized JPEG output.
- PNG or JPEG export, optional EXIF retention, applied EXIF orientation, retained ICC profile.
- Canvas on/off, color hex input and picker. Canvas mode uses ratio presets/custom ratio, linked pixel width/height, Auto/Portrait/Landscape orientation, centered placement, and optional ratio-preserving expansion. Border mode uses top/bottom/left/right pixel margins with optional linked top/bottom and left/right pairs.
- Lossless checkbox disables reduction controls and JPEG output, and exports exact decoded pixels in PNG (the original JPG bytes are not preserved).
- First-photo preview, scrollable GUI sections, responsive two-column/one-column layout, one-file Windows build scripts.
- Optional pop-up batch receipt after each run, including elapsed time, discovered/processed/saved/skipped/failed counts, saved-file input and output byte totals and percentage change, and active processing settings. The receipt can be copied to the clipboard.
- Optional automatic sibling output folder named from the input folder plus the image suffix; disables the manual output field, updates its path as input/suffix changes, and restores the prior manual path when turned off. Empty suffixes and output symlinks are rejected in this mode.
- Startup defaults to Border mode with 100 px margins so large source photos fit without being resized. Canvas expansion starts enabled. Failed batch receipts list error reasons and examples; when no photos save, the status line shows the first failure.
- Input validation and preview use the same decoded format check with a JPEG-signature fallback. An unsupported-format failure includes the decoder's format label and file header bytes for diagnosis.
- Image decoding accepts supported JPEG, PNG, TIFF, BMP, WebP, GIF and AVIF; PNG can be read from a .JPG filename. RGBA PNG output retains alpha, JPEG flattens alpha onto the fill color, and multi-frame or high-bit-depth lossless input errors explain the limitation. Same-stem mixed-format inputs receive distinct output filenames.
- README contains app use and behavior; build and maintenance instructions are in BUILDING.md.

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
