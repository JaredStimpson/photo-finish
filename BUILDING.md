# Building and updating Photo Finish

Run `build.bat` **on Windows** to make `dist\photo-finish.exe` with PyInstaller from the project's `.venv`. The EXE runs independently of the virtual environment. The source ZIP does not contain a Windows binary because this project was prepared outside Windows. Setup, launch, and build command windows remain open after finishing for diagnostics.

The batch scripts use their own folder as the working directory. Install Python 3 with working Tcl/Tk support on the build machine. Run `setup.bat` to create `.venv` and install `requirements.txt` before using `launch.bat` or `build.bat`; both scripts also invoke setup if their dependencies are missing.

For source-only edits, replace changed files and keep `.venv`; rerun `build.bat` for a new EXE. If `requirements.txt` changes, rerun `setup.bat`. Recreate `.venv` if Python changes, the project folder moves, or the environment becomes corrupt. `build.bat` uses PyInstaller's `--clean`; deleting build caches is generally unnecessary.

The full repository ZIP excludes `.venv/`, `build/`, `dist/`, and generated caches. From the repository folder, run `python -m unittest discover -s tests -v` with Pillow installed to check processing and receipt formatting. GUI and batch scripts also require a Windows desktop check.
