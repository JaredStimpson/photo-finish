# Photo Finish

Photo Finish processes batches of JPG/JPEG photographs. It can add a solid-color canvas or border, optionally downsize photos, and save PNG or JPEG output. Original photos are left in place; existing outputs are skipped.

## Use

1. On Windows, run `setup.bat` once if you plan to use the Python version, then run `launch.bat`. If you have `photo-finish.exe`, open it directly.
2. Choose an **Input** folder and either select an **Output** folder or check **Output folder beside input**. With the box checked, the Output field is disabled and displays a sibling folder named from the input folder plus the image suffix: `Photos` with `_finished` writes to `Photos_finished`. Changing the input or suffix updates that folder. Unchecking restores the manual output choice. A nonempty suffix is required for automatic output. If that sibling folder already exists, existing output files are skipped; the app never deletes them. Select **Include subfolders** to scan subfolders and keep their structure in the output.
3. In **Canvas mode**, enter a target ratio and either width or height in pixels. The other dimension follows the ratio. Auto orientation turns the canvas to match each photo. If a photo will not fit, choose **Expand canvas** or enable reduction.
4. In **Border mode**, enter pixel margins to add around each photo. **Same top and bottom** and **Same sides** begin checked; bottom and right follow the corresponding fields until you uncheck them. This mode determines output size from each photo and its margins.
5. Choose the fill color. **Lossless** is checked by default and exports PNG with the original decoded photo pixels unchanged. Uncheck it to enable bicubic reduction or JPEG output. Reduction never upscales and can apply light sharpening after downsizing. JPEG output recompresses, and its quality slider controls the amount of compression.
6. Check **Print receipt** beside **Start batch** to open a receipt window when the run ends. It shows elapsed time, counts, before/after totals, space saved, and the settings used. Uncheck it to skip the window. The receipt has a **Copy receipt** button.
7. Use **Start batch** to process the folder. The preview shows the first JPG; the log shows each saved, skipped, or failed file. **Cancel** stops after the current photo finishes.

The receipt's size totals compare only successfully saved files with their input files. A negative space saving means the output uses more space, which is common with PNG. EXIF orientation is applied before processing. ICC profiles are copied; the optional EXIF setting may retain location data. The PNG file differs from the original JPG even when its decoded photo pixels are unchanged.
