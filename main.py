"""Photo Finish: batch canvas and JPG reduction for Windows."""
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from processing import Settings, image_layout, linked_dimension, list_jpgs, output_path, parse_ratio, process_image, validate


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("photo-finish · Batch canvas & JPG reduction")
        self.geometry("1060x850")
        self.minsize(600, 560)
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.widgets = []
        self.preview_file = None
        self.preview_ref = None
        self.preview_job = None
        self.link_guard = False
        self.active_dimension = "height"
        self.source = tk.StringVar()
        self.output = tk.StringVar()
        self.recursive = tk.BooleanVar(value=False)
        self.canvas_on = tk.BooleanVar(value=True)
        self.canvas_mode = tk.StringVar(value="Canvas")
        self.ratio = tk.StringVar(value="2:3")
        self.width = tk.StringVar(value="2000")
        self.height = tk.StringVar(value="3000")
        self.orientation = tk.StringVar(value="Auto")
        self.color = tk.StringVar(value="#FFFFFF")
        self.expand = tk.BooleanVar(value=False)
        self.top_border = tk.StringVar(value="100")
        self.bottom_border = tk.StringVar(value="100")
        self.left_border = tk.StringVar(value="100")
        self.right_border = tk.StringVar(value="100")
        self.same_top_bottom = tk.BooleanVar(value=True)
        self.same_sides = tk.BooleanVar(value=True)
        self.lossless = tk.BooleanVar(value=True)
        self.reduce = tk.BooleanVar(value=False)
        self.max_edge = tk.StringVar(value="2560")
        self.sharpen = tk.BooleanVar(value=True)
        self.quality = tk.IntVar(value=85)
        self.format = tk.StringVar(value="PNG")
        self.metadata = tk.BooleanVar(value=False)
        self.suffix = tk.StringVar(value="_finished")
        self.status = tk.StringVar(value="Select JPGs and review the settings.")
        self.preview_info = tk.StringVar(value="Select an input folder to preview its first JPG.")
        self._layout()
        self.top_border.trace_add("write", lambda *_: self._sync_border("vertical"))
        self.left_border.trace_add("write", lambda *_: self._sync_border("horizontal"))
        self.width.trace_add("write", lambda *_: self._link("width"))
        self.height.trace_add("write", lambda *_: self._link("height"))
        self.ratio.trace_add("write", lambda *_: self._link("ratio"))
        for var in (self.width, self.height, self.ratio, self.orientation, self.color,
                    self.canvas_on, self.canvas_mode, self.reduce, self.max_edge, self.expand,
                    self.format, self.top_border, self.bottom_border, self.left_border,
                    self.right_border, self.same_top_bottom, self.same_sides, self.lossless):
            var.trace_add("write", lambda *_: self.schedule_preview())
        self.source.trace_add("write", lambda *_: self.schedule_preview(find_file=True))
        self.format.trace_add("write", lambda *_: self._update_states())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(80, self.poll)
        self.after(150, self._adapt)
        self._update_states()

    def add(self, widget):
        self.widgets.append(widget)
        return widget

    def _layout(self):
        outer = ttk.Frame(self, padding=(12, 10))
        outer.pack(fill="both", expand=True)
        outer.bind("<Configure>", lambda event: self.status_label.configure(wraplength=max(200, event.width - 30)) if hasattr(self, "status_label") else None)
        ttk.Label(outer, text="photo-finish", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Finish photo sets with a solid-color canvas and optional bicubic JPG reduction.").pack(anchor="w", pady=(0, 8))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        self.scroller = tk.Canvas(body, highlightthickness=0, borderwidth=0)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.scroller.yview)
        self.scroller.configure(yscrollcommand=scroll.set)
        self.scroller.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.content = ttk.Frame(self.scroller, padding=(2, 2, 10, 12))
        self.window_id = self.scroller.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda _: self.scroller.configure(scrollregion=self.scroller.bbox("all")))
        self.scroller.bind("<Configure>", self._canvas_resize)
        self.scroller.bind("<MouseWheel>", self._wheel)
        self.content.bind("<MouseWheel>", self._wheel)
        self.bind_all("<MouseWheel>", self._wheel)
        for column in (0, 1):
            self.content.columnconfigure(column, weight=1, uniform="columns")
        self.files = self._section("1 · Files", 0, 0)
        self.size_box = self._section("2 · Canvas & border", 0, 1)
        self.reduction = self._section("3 · Photo reduction", 1, 0)
        self.export = self._section("4 · Output", 1, 1)
        self.review = self._section("5 · Preview", 2, 0, span=2)
        self._files()
        self._canvas_controls()
        self._reduction_controls()
        self._export_controls()
        self._preview_controls()
        bar = ttk.Frame(outer)
        bar.pack(fill="x", pady=(8, 0))
        self.start_button = ttk.Button(bar, text="Start batch", command=self.start_batch)
        self.start_button.pack(side="left")
        self.cancel_button = ttk.Button(bar, text="Cancel", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        self.progress = ttk.Progressbar(bar, orient="horizontal", mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.status_label = ttk.Label(outer, textvariable=self.status, wraplength=970)
        self.status_label.pack(anchor="w", fill="x", pady=(6, 0))

    def _section(self, label, row, col, span=1):
        group = ttk.LabelFrame(self.content, text=label, padding=10)
        group.grid(row=row, column=col, columnspan=span, sticky="nsew", padx=4, pady=5)
        group.columnconfigure(1, weight=1)
        return group

    def _row(self, parent, row, label, variable, browse=False, width=None):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        entry = self.add(ttk.Entry(parent, textvariable=variable, width=width))
        entry.grid(row=row, column=1, sticky="ew", pady=4)
        if browse:
            self.add(ttk.Button(parent, text="Browse…", command=lambda: self.choose_folder(variable))).grid(row=row, column=2, padx=(6, 0))
        return entry

    def _check(self, parent, row, label, variable, cmd=None):
        widget = self.add(ttk.Checkbutton(parent, text=label, variable=variable, command=cmd))
        widget.grid(row=row, column=0, columnspan=3, sticky="w", pady=3)
        return widget

    def _files(self):
        self._row(self.files, 0, "Input", self.source, browse=True)
        self._row(self.files, 1, "Output", self.output, browse=True)
        self._check(self.files, 2, "Include subfolders and preserve their structure", self.recursive)
        self.add(ttk.Button(self.files, text="Refresh preview", command=lambda: self.schedule_preview(find_file=True))).grid(row=3, column=0, columnspan=3, sticky="w", pady=(5, 0))

    def _canvas_controls(self):
        self.canvas_toggle = self._check(self.size_box, 0, "Add solid-color canvas / border", self.canvas_on, self._update_states)
        modes = ttk.Frame(self.size_box)
        modes.grid(row=1, column=0, columnspan=3, sticky="w", pady=(3, 4))
        self.mode_widgets = []
        for name in ("Canvas", "Border"):
            widget = self.add(ttk.Radiobutton(modes, text=f"{name} mode", variable=self.canvas_mode, value=name,
                                              command=self._update_states))
            widget.pack(side="left", padx=(0, 18))
            self.mode_widgets.append(widget)
        self.color_widget = self._row(self.size_box, 2, "Fill color", self.color, width=12)
        self.color_picker = self.add(ttk.Button(self.size_box, text="Pick…", command=self.pick_color))
        self.color_picker.grid(row=2, column=2, padx=(6, 0))
        self.canvas_frame = ttk.Frame(self.size_box)
        self.canvas_frame.grid(row=3, column=0, columnspan=3, sticky="ew")
        self.canvas_frame.columnconfigure(1, weight=1)
        ttk.Label(self.canvas_frame, text="Ratio (W:H)").grid(row=0, column=0, sticky="w")
        self.add(ttk.Combobox(self.canvas_frame, textvariable=self.ratio, values=("2:3", "3:2", "4:5", "5:4", "1:1", "16:9", "9:16"), width=10)).grid(row=0, column=1, sticky="w", pady=4)
        self._row(self.canvas_frame, 1, "Width (px)", self.width, width=12)
        self._row(self.canvas_frame, 2, "Height (px)", self.height, width=12)
        ttk.Label(self.canvas_frame, text="Orientation").grid(row=3, column=0, sticky="w")
        self.orientation_widget = self.add(ttk.Combobox(self.canvas_frame, textvariable=self.orientation, values=("Auto", "Portrait", "Landscape"), state="readonly", width=13))
        self.orientation_widget.grid(row=3, column=1, sticky="w", pady=4)
        self._check(self.canvas_frame, 4, "Expand canvas if a photo won't fit", self.expand)
        ttk.Label(self.canvas_frame, text="Target dimensions and ratio; the photo is centered.", wraplength=390).grid(row=5, column=0, columnspan=3, sticky="w", pady=(3, 0))
        self.border_frame = ttk.Frame(self.size_box)
        self.border_frame.grid(row=4, column=0, columnspan=3, sticky="ew")
        self.border_frame.columnconfigure(1, weight=1)
        self._row(self.border_frame, 0, "Top (px)", self.top_border, width=12)
        self._row(self.border_frame, 1, "Bottom (px)", self.bottom_border, width=12)
        self._row(self.border_frame, 2, "Left (px)", self.left_border, width=12)
        self._row(self.border_frame, 3, "Right (px)", self.right_border, width=12)
        self._check(self.border_frame, 4, "Same top and bottom", self.same_top_bottom, lambda: (self._sync_border("vertical"), self._update_states()))
        self._check(self.border_frame, 5, "Same sides", self.same_sides, lambda: (self._sync_border("horizontal"), self._update_states()))
        self.bottom_widget = next(w for w in self.border_frame.winfo_children() if isinstance(w, ttk.Entry) and str(w.cget("textvariable")) == str(self.bottom_border))
        self.right_widget = next(w for w in self.border_frame.winfo_children() if isinstance(w, ttk.Entry) and str(w.cget("textvariable")) == str(self.right_border))
        ttk.Label(self.border_frame, text="Adds these margins to each photo's current size.", wraplength=390).grid(row=6, column=0, columnspan=3, sticky="w", pady=(3, 0))

    def _reduction_controls(self):
        self._check(self.reduction, 0, "Lossless: keep decoded photo pixels (PNG)", self.lossless, self._update_states)
        self.reduce_widget = self.add(ttk.Checkbutton(self.reduction, text="Downsize photos before adding the canvas", variable=self.reduce, command=self._update_states))
        self.reduce_widget.grid(row=1, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Label(self.reduction, text="Longest edge (px)").grid(row=2, column=0, sticky="w")
        self.max_edge_widget = self.add(ttk.Combobox(self.reduction, textvariable=self.max_edge, values=("1600", "1920", "2560", "3000", "3840", "4096"), width=12))
        self.max_edge_widget.grid(row=2, column=1, sticky="w", pady=4)
        self.sharpen_widget = self.add(ttk.Checkbutton(self.reduction, text="Light sharpen after downsizing", variable=self.sharpen))
        self.sharpen_widget.grid(row=3, column=0, columnspan=3, sticky="w", pady=3)
        ttk.Label(self.reduction, text="Reduction never upscales. Sharpening runs only if resized.", wraplength=400).grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def _export_controls(self):
        ttk.Label(self.export, text="Format").grid(row=0, column=0, sticky="w")
        self.format_widget = self.add(ttk.Combobox(self.export, textvariable=self.format, values=("PNG", "JPEG"), state="readonly", width=10))
        self.format_widget.grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(self.export, text="JPEG quality").grid(row=1, column=0, sticky="w")
        self.quality_widget = self.add(ttk.Scale(self.export, from_=40, to=95, variable=self.quality, orient="horizontal"))
        self.quality_widget.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(self.export, textvariable=self.quality, width=3).grid(row=1, column=2, padx=(6, 0))
        self._row(self.export, 2, "Name suffix", self.suffix, width=16)
        self._check(self.export, 3, "Keep EXIF (may include location data)", self.metadata)
        ttk.Label(self.export, text="PNG preserves processed pixels exactly. JPEG recompresses; quality applies to JPEG only. ICC profiles are retained. Existing files are skipped.", wraplength=400).grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def _preview_controls(self):
        self.review.columnconfigure(0, weight=1)
        self.preview_canvas = tk.Canvas(self.review, width=440, height=230, bg="#e9e9e9", highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, sticky="ew")
        self.preview_canvas.bind("<Configure>", lambda _: self.schedule_preview())
        self.preview_label = ttk.Label(self.review, textvariable=self.preview_info)
        self.preview_label.grid(row=1, column=0, sticky="w", pady=(4, 4))
        self.review.bind("<Configure>", lambda event: self.preview_label.configure(wraplength=max(200, event.width - 26)))
        self.log = tk.Text(self.review, height=5, state="disabled", wrap="word")
        self.log.grid(row=2, column=0, sticky="ew")

    def _canvas_resize(self, event):
        self.scroller.itemconfigure(self.window_id, width=event.width)
        self._adapt()

    def _adapt(self):
        narrow = self.scroller.winfo_width() < 850
        if getattr(self, "_narrow", None) == narrow:
            return
        self._narrow = narrow
        if narrow:
            for idx, group in enumerate((self.files, self.size_box, self.reduction, self.export, self.review)):
                group.grid_configure(row=idx, column=0, columnspan=2)
        else:
            for group, row, col, span in ((self.files, 0, 0, 1), (self.size_box, 0, 1, 1),
                                           (self.reduction, 1, 0, 1), (self.export, 1, 1, 1), (self.review, 2, 0, 2)):
                group.grid_configure(row=row, column=col, columnspan=span)

    def _wheel(self, event):
        self.scroller.yview_scroll(-int(event.delta / 120), "units")

    def _link(self, changed):
        if self.link_guard:
            return
        try:
            rw, rh = parse_ratio(self.ratio.get())
            source = self.active_dimension if changed == "ratio" else changed
            value = int((self.width if source == "width" else self.height).get())
            if value < 1:
                return
            self.link_guard = True
            if source == "width":
                self.height.set(str(linked_dimension(value, rh, rw)))
            else:
                self.width.set(str(linked_dimension(value, rw, rh)))
            if changed != "ratio":
                self.active_dimension = changed
        except ValueError:
            pass
        finally:
            self.link_guard = False

    def _sync_border(self, axis):
        if axis == "vertical" and self.same_top_bottom.get():
            self.bottom_border.set(self.top_border.get())
        elif axis == "horizontal" and self.same_sides.get():
            self.right_border.set(self.left_border.get())

    def _state(self, widget, enabled):
        widget.configure(state=("readonly" if widget in (self.orientation_widget, self.format_widget) else "normal") if enabled else "disabled")

    def _update_states(self):
        if self.lossless.get():
            if self.reduce.get():
                self.reduce.set(False)
            if self.format.get() != "PNG":
                self.format.set("PNG")
        if self.running:
            return
        canvas_enabled = self.canvas_on.get()
        for widget in self.mode_widgets + [self.color_widget, self.color_picker]:
            self._state(widget, canvas_enabled)
        if canvas_enabled and self.canvas_mode.get() == "Border":
            self.canvas_frame.grid_remove()
            self.border_frame.grid()
        else:
            self.border_frame.grid_remove()
            if canvas_enabled:
                self.canvas_frame.grid()
            else:
                self.canvas_frame.grid_remove()
        for widget in self.border_frame.winfo_children():
            if widget in self.widgets:
                self._state(widget, canvas_enabled and self.canvas_mode.get() == "Border")
        self._state(self.bottom_widget, canvas_enabled and self.canvas_mode.get() == "Border" and not self.same_top_bottom.get())
        self._state(self.right_widget, canvas_enabled and self.canvas_mode.get() == "Border" and not self.same_sides.get())
        for widget in self.canvas_frame.winfo_children():
            if widget in self.widgets:
                self._state(widget, canvas_enabled and self.canvas_mode.get() == "Canvas")
        self._state(self.reduce_widget, not self.lossless.get())
        self._state(self.max_edge_widget, not self.lossless.get() and self.reduce.get())
        self._state(self.sharpen_widget, not self.lossless.get() and self.reduce.get())
        self._state(self.format_widget, not self.lossless.get())
        self._state(self.quality_widget, not self.lossless.get() and self.format.get() == "JPEG")

    def settings(self):
        if self.canvas_on.get() and self.canvas_mode.get() == "Canvas":
            rw, rh = parse_ratio(self.ratio.get())
            width, height = int(self.width.get()), int(self.height.get())
        else:
            rw, rh, width, height = 2, 3, 2000, 3000
        if self.canvas_on.get() and self.canvas_mode.get() == "Border":
            top, bottom, left, right = (int(var.get()) for var in
                                        (self.top_border, self.bottom_border, self.left_border, self.right_border))
        else:
            top = bottom = left = right = 0
        settings = Settings(canvas=self.canvas_on.get(), canvas_mode=self.canvas_mode.get(),
                            ratio_w=rw, ratio_h=rh, width=width, height=height,
                            orientation=self.orientation.get(), color=self.color.get().strip(),
                            expand=self.expand.get(), top=top, bottom=bottom, left=left, right=right,
                            same_top_bottom=self.same_top_bottom.get(), same_sides=self.same_sides.get(),
                            lossless=self.lossless.get(), reduce=self.reduce.get(),
                            max_edge=2560 if self.lossless.get() else int(self.max_edge.get()),
                            sharpen=self.sharpen.get(), quality=round(self.quality.get()),
                            format=self.format.get(), metadata=self.metadata.get(),
                            recursive=self.recursive.get(), suffix=self.suffix.get())
        validate(settings)
        return settings

    def choose_folder(self, variable):
        folder = filedialog.askdirectory(title="Select input JPG folder" if variable is self.source else "Select output folder")
        if folder:
            variable.set(folder)

    def pick_color(self):
        picked = colorchooser.askcolor(color=self.color.get(), parent=self)
        if picked[1]:
            self.color.set(picked[1].upper())

    def schedule_preview(self, find_file=False):
        if find_file:
            self.preview_file = None
        if self.preview_job is not None:
            self.after_cancel(self.preview_job)
        self.preview_job = self.after(250, self.draw_preview)

    def draw_preview(self):
        self.preview_job = None
        panel = self.preview_canvas
        panel.delete("all")
        self.preview_ref = None
        try:
            settings = self.settings()
            if self.preview_file is None:
                if not self.source.get().strip():
                    self.preview_info.set("Select an input folder to preview its first JPG.")
                    return
                source = Path(self.source.get().strip()).expanduser().resolve()
                if not source.is_dir():
                    self.preview_info.set("Select an input folder to preview its first JPG.")
                    return
                candidates = list_jpgs(source, source / "_no_output_", settings.recursive)
                self.preview_file = candidates[0] if candidates else None
            if self.preview_file is None:
                self.preview_info.set("No JPGs found in the selected folder.")
                return
            with Image.open(self.preview_file) as original:
                if original.format != "JPEG":
                    raise ValueError("First file is not a valid JPG.")
                source_size = original.size
                if original.getexif().get(274, 1) in (5, 6, 7, 8):
                    source_size = (source_size[1], source_size[0])
                original.draft("RGB", (1100, 1100))
                image = ImageOps.exif_transpose(original).convert("RGB")
            effective = source_size
            if settings.reduce:
                factor = min(1.0, settings.max_edge / max(effective))
                effective = (max(1, round(effective[0] * factor)), max(1, round(effective[1] * factor)))
            size, origin = image_layout(settings, effective)
            avail_w = max(100, panel.winfo_width() - 20)
            avail_h = max(100, panel.winfo_height() - 16)
            scale = min(avail_w / size[0], avail_h / size[1])
            shown_size = (max(1, round(size[0] * scale)), max(1, round(size[1] * scale)))
            photo_size = (max(1, round(effective[0] * scale)), max(1, round(effective[1] * scale)))
            image.thumbnail(photo_size, Image.Resampling.LANCZOS)
            image = image.resize(photo_size, Image.Resampling.LANCZOS)
            result = Image.new("RGB", shown_size, settings.color if settings.canvas else "#FFFFFF")
            result.paste(image, (round(origin[0] * scale), round(origin[1] * scale)))
            self.preview_ref = ImageTk.PhotoImage(result)
            panel.create_image(panel.winfo_width() // 2, panel.winfo_height() // 2, image=self.preview_ref)
            self.preview_info.set(f"{self.preview_file.name} · photo {effective[0]}×{effective[1]} → output {size[0]}×{size[1]} · {settings.format}")
        except (ValueError, OSError) as exc:
            self.preview_info.set(f"Preview: {exc}")

    def start_batch(self):
        try:
            settings = self.settings()
            if not self.source.get().strip() or not self.output.get().strip():
                raise ValueError("Choose input and output folders.")
            source = Path(self.source.get().strip()).expanduser().resolve()
            output = Path(self.output.get().strip()).expanduser().resolve()
            if not source.is_dir():
                raise ValueError("Input folder does not exist.")
            if source == output:
                raise ValueError("Select a separate output folder to protect the originals.")
            if output.exists() and not output.is_dir():
                raise ValueError("Output path must be a folder.")
            if source.is_relative_to(output) and not settings.suffix and settings.format == "JPEG":
                raise ValueError("Use a filename suffix when output contains the input folder.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Check settings", str(exc))
            return
        self.stop.clear()
        self.running = True
        for widget in self.widgets:
            widget.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.configure(value=0)
        self.status.set("Finding JPGs…")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        threading.Thread(target=self.worker, args=(source, output, settings), daemon=True).start()

    def worker(self, source, output, settings):
        saved = skipped = failed = total_in = total_out = 0
        try:
            files = list_jpgs(source, output, settings.recursive)
            self.events.put(("total", len(files)))
            for index, path in enumerate(files, 1):
                if self.stop.is_set():
                    break
                destination = output_path(path, source, output, settings)
                try:
                    if destination.resolve() == path.resolve():
                        raise ValueError("Output would overwrite the input image.")
                    _, final, before, after = process_image(path, destination, settings)
                    saved += 1
                    total_in += before
                    total_out += after
                    self.events.put(("log", f"{path.relative_to(source)} → {final[0]}×{final[1]} · {before / 1048576:.1f} → {after / 1048576:.1f} MB"))
                except FileExistsError:
                    skipped += 1
                    self.events.put(("log", f"SKIPPED existing: {destination.name}"))
                except Exception as exc:
                    failed += 1
                    self.events.put(("log", f"ERROR {path.relative_to(source)}: {exc}"))
                self.events.put(("progress", index, len(files)))
            label = "Canceled" if self.stop.is_set() else ("No JPGs found" if not files else "Finished")
            sizes = f" · {total_in / 1048576:.1f} → {total_out / 1048576:.1f} MB" if saved else ""
            self.events.put(("done", f"{label}: {saved} saved, {skipped} skipped, {failed} failed{sizes}"))
        except Exception as exc:
            self.events.put(("done", f"Batch stopped: {exc}"))

    def poll(self):
        for _ in range(100):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event[0] == "total":
                self.progress.configure(maximum=max(1, event[1]))
            elif event[0] == "progress":
                self.progress.configure(value=event[1])
                self.status.set(f"Processed {event[1]} of {event[2]}")
            elif event[0] == "log":
                self.log.configure(state="normal")
                self.log.insert("end", event[1] + "\n")
                if int(self.log.index("end-1c").split(".")[0]) > 500:
                    self.log.delete("1.0", "50.0")
                self.log.see("end")
                self.log.configure(state="disabled")
            elif event[0] == "done":
                self.running = False
                self.status.set(event[1])
                for widget in self.widgets:
                    widget.configure(state="normal")
                self._update_states()
                self.start_button.configure(state="normal")
                self.cancel_button.configure(state="disabled")
        self.after(80, self.poll)

    def cancel(self):
        self.stop.set()
        self.status.set("Canceling after the current photo…")
        self.cancel_button.configure(state="disabled")

    def close(self):
        if self.running:
            self.cancel()
            self.after(100, self._close_when_idle)
        else:
            self.destroy()

    def _close_when_idle(self):
        if self.running:
            self.after(100, self._close_when_idle)
        else:
            self.destroy()


if __name__ == "__main__":
    App().mainloop()
