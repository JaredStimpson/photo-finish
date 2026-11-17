# Photo Finish v1

A Windows desktop tool for finishing JPG photo sets. It can downsize with bicubic filtering and optional light sharpening, then center the photo on a solid-color canvas. It scans `.jpg` and `.jpeg` files only. Source files are never intentionally overwritten; existing output files are skipped.

## Windows use

1. Install Python 3 with Tcl/Tk enabled. From this folder, double-click `setup.bat` once (or use Command Prompt). It creates `.venv` and installs the packages in `requirements.txt`.
2. Run `launch.bat` to open the application. Choose separate input and output folders.
3. Choose the canvas ratio and enter either width or height; the other field updates. Auto orientation swaps the canvas per photo. If an image exceeds the canvas, enable **Expand canvas** or reduce it first. Expansion uses whole multiples of your canvas dimensions so the ratio stays exact.
4. Choose **PNG** when decoded source pixels and exact border color must be preserved. Turn off photo reduction. Choose **JPEG** when a smaller, recompressed file is more useful. The JPEG quality slider only controls JPEG output.
5. Run the batch. A preview shows the first JPG; the status and log report saved, skipped, and failed files. Cancel finishes the current image before stopping.

EXIF orientation is applied before processing. ICC color profiles are copied to the output. Optional EXIF retention can include GPS location data. With metadata off, EXIF is omitted. The photo is centered; odd-pixel differences put the extra pixel on the right or bottom.

## Build a single Windows executable

Run `build.bat` **on Windows**. It uses the project's `.venv` and PyInstaller to create `dist\PhotoFinish.exe`. Launch the EXE directly; it does not require the project's virtual environment. The scripts use their own folder as the working directory, so they also work when called from another folder. Python and Tk support must be installed on the build PC. PyInstaller builds the executable for the OS on which it runs; this source ZIP does not include a prebuilt Windows binary.

## Updating

- If only `main.py`, `processing.py`, documentation, or `.bat` scripts change, replace those files. Keep `.venv`; rerun `build.bat` if you need a new EXE.
- If `requirements.txt` changes, replace it and run `setup.bat` again. Recreate `.venv` only if Python or its Tcl/Tk installation changes or the environment becomes corrupt.
- Build cache cleanup is normally unnecessary: `build.bat` uses PyInstaller's `--clean`. If troubleshooting a persistent build issue, remove `build/` and the generated `.spec` file, then rerun it. Python `__pycache__/` may be removed but does not normally need cleaning.

The full source ZIP intentionally excludes generated `.venv/`, `build/`, `dist/`, and cache files. Extract the ZIP over an earlier source folder, then use the actions above. A Windows-built EXE, when supplied later, should be distributed separately or included in a release ZIP after building on Windows.

## Development check

With Pillow installed, run `python -m unittest discover -s tests -v` from this folder. GUI launch and `.bat` build must also be checked on a Windows machine with a desktop session.
