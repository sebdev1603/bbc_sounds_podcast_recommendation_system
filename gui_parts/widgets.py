"""Reusable Tkinter widgets, animated rounded buttons, BBC logo, artwork, and batched grids."""
import ctypes
import math
from pathlib import Path
import re
import sys
from time import monotonic
import tkinter as tk
from tkinter import font as tkfont
import unicodedata
import xml.etree.ElementTree as ET

from gui_parts.i18n import translate
from gui_parts.theme import (
    BORDER_LINE,
    CANVA_DIR,
    CARD_BG,
    DARK_BG,
    DEFAULT_FONT,
    GENRE_CIRCLE_COLOURS,
    GENRE_LIST,
    GENRE_TILE_DETAILS,
    GOLD_STAR,
    INPUT_BG,
    LOGO_TILE_BG,
    LOGO_TILE_FG,
    ORANGE_ACCENT,
    ORANGE_HL,
    PALETTE_SWATCHES,
    PODCASTS_PER_PAGE,
    PODCAST_PICTURES_DIR,
    PRIMARY_BTN_FG,
    RoundedPanel,
    SECONDARY_HOVER_BG,
    SECONDARY_HOVER_FG,
    SELECTED_BG,
    STAR_EMPTY,
    TEXT_GRAY,
    TEXT_LIGHT,
    TEXT_WHITE,
    blend_colour,
    ease_out_elastic,
)


class WidgetsMixin:
    """Mixin providing shared UI builders, hover animations, cover art, and pagination."""

    def load_svg_images(self, filename):
        """Extract base64-encoded PNG payloads from a Canva SVG file and cache them."""
        if filename in self.svg_store:
            return self.svg_store[filename]
        extracted_list = []
        target_file = CANVA_DIR / filename
        try:
            root_elem = ET.parse(str(target_file)).getroot()
            for node in root_elem.iter():
                if node.tag.split("}")[-1] != "image":
                    continue
                link = node.attrib.get("href") or node.attrib.get("{http://www.w3.org/1999/xlink}href", "")
                if not link.startswith("data:image/png;base64,"):
                    continue
                b64_payload = link.split(",", 1)[1]
                try:
                    w_val = float(node.attrib.get("width", 0))
                    h_val = float(node.attrib.get("height", 0))
                    extracted_list.append((w_val, h_val, b64_payload))
                except (TypeError, ValueError):
                    continue
        except (OSError, ET.ParseError):
            extracted_list = []
        self.svg_store[filename] = extracted_list
        return extracted_list

    def get_svg_photo_object(self, filename, index=0, dimensions=(240, 260)):
        """Return a subsampled, cached Tk PhotoImage from an embedded Canva SVG image."""
        cache_key = (filename, index, dimensions)
        if cache_key in self.image_store:
            return self.image_store[cache_key]
        image_list = self.load_svg_images(filename)
        if not image_list:
            return None
        target_img = image_list[index % len(image_list)]
        try:
            photo = tk.PhotoImage(data=target_img[2], master=self)
            max_w, max_h = dimensions
            ratio = max(
                1,
                int(math.ceil(photo.width() / float(max_w))),
                int(math.ceil(photo.height() / float(max_h))),
            )
            if ratio > 1:
                photo = photo.subsample(ratio, ratio)
            self.image_store[cache_key] = photo
            return photo
        except tk.TclError:
            return None

    @staticmethod
    def create_label(container, text_val, text_size=12, text_color=None, font_weight="normal", **kwargs):
        """Create a styled Tk label inheriting its container's background by default."""
        if text_color is None:
            text_color = TEXT_WHITE
        return tk.Label(
            container,
            text=translate(text_val),
            font=(DEFAULT_FONT, text_size, font_weight),
            fg=text_color,
            bg=kwargs.pop("bg", container.cget("bg")),
            justify=kwargs.pop("justify", "left"),
            anchor=kwargs.pop("anchor", "w"),
            **kwargs,
        )

    def create_button(self, container, text_val, command_func, primary=False, compact=False, **kwargs):
        """Create a rounded pill button with smooth 5-frame hover colour and scale animation."""
        font_spec = kwargs.pop("font", (DEFAULT_FONT, 10 if compact else 11, "bold" if primary else "normal"))
        face = kwargs.pop("face", ORANGE_ACCENT if primary else INPUT_BG)
        foreground = kwargs.pop("fg", PRIMARY_BTN_FG if primary else TEXT_LIGHT)
        hover_fg = PRIMARY_BTN_FG if primary else SECONDARY_HOVER_FG
        background = container.cget("bg")
        button = tk.Button(
            container,
            text=translate(text_val),
            command=command_func,
            font=font_spec, compound="center",
            bg=background, fg=foreground,
            activebackground=background,
            activeforeground=hover_fg,
            disabledforeground=TEXT_GRAY,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=0, pady=0, highlightthickness=1,
            highlightbackground=background, highlightcolor=ORANGE_HL,
            **kwargs,
        )
        button._rounded_padding = (24, 12) if compact else (32, 16)
        button._hover_target_fg = hover_fg
        button._hover_job = None
        button._hover_step = 0
        button._hover_target = 0
        self.style_rounded_button(button, face, ORANGE_HL if primary else SECONDARY_HOVER_BG)
        button.bind("<Enter>", lambda _e, btn=button: self.animate_button_hover(btn, 12))
        button.bind("<Leave>", lambda _e, btn=button: self.animate_button_hover(btn, 0))
        button.bind("<Destroy>", lambda _e, btn=button: self.cancel_button_hover(btn))
        return button

    def cancel_button_hover(self, button):
        """Cancel any pending hover animation timer on a button."""
        job = getattr(button, "_hover_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except tk.TclError:
                pass
            button._hover_job = None

    def animate_button_hover(self, button, target_step):
        """Ease a button's hover state smoothly toward target_step (0..12) with elastic spring."""
        if not button.winfo_exists():
            return
        if target_step > 0 and str(button.cget("state")) == "disabled":
            return
        button._hover_target = target_step
        if getattr(button, "_hover_job", None) is not None:
            return

        def step_frame():
            button._hover_job = None
            if not button.winfo_exists():
                return
            current = getattr(button, "_hover_step", 0)
            target = getattr(button, "_hover_target", 0)
            if current == target:
                return
            current += 1 if target > current else -1
            button._hover_step = current
            self._apply_button_hover_frame(button, current)
            if current != target:
                button._hover_job = self.after(16, step_frame)

        step_frame()

    def _apply_button_hover_frame(self, button, step):
        """Render a single intermediate frame of a button's elastic hover expansion and tint."""
        face, hover = button._rounded_colours
        width, height = button._hover_size
        base_fg = button._hover_base_fg
        t = step / 12.0
        # Fluid damped elastic spring on enter; smooth cubic ease-out on leave.
        eased = ease_out_elastic(t, damping=4.8, frequency=1.15) if getattr(button, "_hover_target", 0) > 0 else 1.0 - (1.0 - t) ** 3
        colour = blend_colour(face, hover, eased)
        inset = max(0, min(3, round(3.0 - 2.0 * eased)))
        image = self.rounded_button_image(width, height, colour, inset=inset)
        button._current_image = image
        config = {"image": image}
        target_fg = getattr(button, "_hover_target_fg", TEXT_WHITE)
        if isinstance(base_fg, str) and base_fg.startswith("#") and len(base_fg) == 7:
            # Keep text high-contrast when swapping between white and black foregrounds on hover.
            if base_fg.lower() != target_fg.lower() and target_fg.lower() == "#000000":
                config["fg"] = target_fg if eased >= 0.45 else base_fg
            else:
                config["fg"] = blend_colour(base_fg, target_fg, eased)
        button.configure(**config)

    def _get_cached_font(self, font_spec):
        """Return a cached tkfont.Font object for a font specification to avoid Tcl churn."""
        cache = getattr(self, "_font_cache", None)
        if cache is None:
            cache = {}
            self._font_cache = cache
        key = font_spec if isinstance(font_spec, (str, tuple)) else str(font_spec)
        font_obj = cache.get(key)
        if font_obj is None:
            font_obj = tkfont.Font(root=self, font=font_spec)
            cache[key] = font_obj
        return font_obj

    def style_rounded_button(self, button, face, hover):
        """Measure button text and build cached normal rounded pill image (hover built lazily)."""
        self.cancel_button_hover(button)
        button._rounded_colours = (face, hover)
        if getattr(button, "_hover_step", 0) == 0 or not hasattr(button, "_hover_base_fg"):
            button._hover_base_fg = button.cget("fg")
        button._hover_step = 0
        button._hover_target = 0
        metrics = self._get_cached_font(button.cget("font"))
        pad_x, pad_y = button._rounded_padding
        height = metrics.metrics("linespace") + pad_y
        text = button.cget("text")
        width = max(height, metrics.measure(text) + (12 if len(text) == 1 else pad_x))
        button._hover_size = (width, height)
        button._normal_image = self.rounded_button_image(width, height, face, inset=3)
        button.configure(image=button._normal_image)

    def rounded_button_image(self, width, height, colour, inset=3):
        """Rasterize and cache a rounded-rectangle PhotoImage for a button state."""
        key = (width, height, colour, inset)
        if key not in self.button_images:
            # Reserve 3px transparent margin per side so elastic hover bounce never shifts layout.
            canvas_w, canvas_h = width + 6, height + 6
            image = tk.PhotoImage(master=self, width=canvas_w, height=canvas_h)
            left, top = inset, inset
            right, bottom = canvas_w - inset, canvas_h - inset
            pill_w, pill_h = right - left, bottom - top
            radius = min(10, pill_h // 2, pill_w // 2)
            image.put(colour, to=(left, top + radius, right, bottom - radius))
            for y in range(radius):
                dx = radius - math.isqrt(radius ** 2 - (radius - y) ** 2)
                if left + dx < right - dx:
                    image.put(colour, to=(left + dx, top + y, right - dx, top + y + 1))
                    image.put(colour, to=(left + dx, bottom - y - 1, right - dx, bottom - y))
            self.button_images[key] = image
            if len(self.button_images) > 512:
                self.button_images.popitem(last=False)
        self.button_images.move_to_end(key)
        return self.button_images[key]

    @staticmethod
    def create_card_frame(container, **kwargs):
        """Create a RoundedPanel card using CARD_BG by default."""
        return RoundedPanel(container, kwargs.pop("bg", CARD_BG), **kwargs)

    def draw_app_logo(self, container, scaling=1):
        """Render the sharp-square BBC logo paired with orange SOUNDS on one DPI-safe canvas."""
        bg_col = container.cget("bg")
        tile = max(26, round(28 * scaling))
        gap = max(4, round(5 * scaling))
        word_gap = max(9, round(10 * scaling))
        tile_font = ("Arial", -round(tile * 0.92), "bold")
        sounds_font = ("Arial", -round(tile * 0.96), "bold")
        sounds_metrics = self._get_cached_font(sounds_font)

        tiles_w = tile * 3 + gap * 2
        sounds_w = sounds_metrics.measure("SOUNDS")
        canvas_w = tiles_w + word_gap + sounds_w + 2
        canvas_h = max(tile, sounds_metrics.metrics("linespace"))
        y0 = round((canvas_h - tile) / 2)
        y1 = y0 + tile
        center_y = (y0 + y1) / 2

        logo_canvas = tk.Canvas(
            container,
            width=canvas_w,
            height=canvas_h,
            bg=bg_col,
            bd=0,
            highlightthickness=0,
        )
        tile_items = []
        for idx, char in enumerate("BBC"):
            x0 = idx * (tile + gap)
            x1 = x0 + tile
            tag = f"bbc_tile_{idx}"
            rect_id = logo_canvas.create_rectangle(x0, y0, x1, y1, fill=LOGO_TILE_BG, outline="", tags=tag)
            text_id = logo_canvas.create_text(
                (x0 + x1) / 2,
                center_y,
                text=char,
                fill=LOGO_TILE_FG,
                font=tile_font,
                anchor="center",
                tags=tag,
            )
            tile_items.append((rect_id, text_id))
        logo_canvas.create_text(
            tiles_w + word_gap,
            center_y,
            text="SOUNDS",
            fill=ORANGE_ACCENT,
            font=sounds_font,
            anchor="w",
        )

        # Easter egg: once activated via the "snake game" search button, clicking all 3 letters of
        # "BBC" (each stays highlighted for 2 seconds) launches the hidden Snake mini-game.
        egg_state = {"clicked": set(), "tile_jobs": [None, None, None], "reset_job": None}

        def cancel_egg_timers(_event=None):
            if egg_state["reset_job"] is not None:
                try:
                    self.after_cancel(egg_state["reset_job"])
                except tk.TclError:
                    pass
                egg_state["reset_job"] = None
            for idx_j in range(3):
                jid = egg_state["tile_jobs"][idx_j]
                if jid is not None:
                    try:
                        self.after_cancel(jid)
                    except tk.TclError:
                        pass
                    egg_state["tile_jobs"][idx_j] = None

        def reset_single_tile(tile_idx):
            egg_state["tile_jobs"][tile_idx] = None
            egg_state["clicked"].discard(tile_idx)
            if not logo_canvas.winfo_exists():
                return
            rect_id, text_id = tile_items[tile_idx]
            logo_canvas.itemconfigure(rect_id, fill=LOGO_TILE_BG)
            logo_canvas.itemconfigure(text_id, fill=LOGO_TILE_FG)

        def reset_bbc_tiles():
            cancel_egg_timers()
            egg_state["clicked"].clear()
            if not logo_canvas.winfo_exists():
                return
            for rect_id, text_id in tile_items:
                logo_canvas.itemconfigure(rect_id, fill=LOGO_TILE_BG)
                logo_canvas.itemconfigure(text_id, fill=LOGO_TILE_FG)

        def on_bbc_tile_click(tile_idx):
            armed = getattr(self, "_armed_easter_egg", None)
            if armed not in ("snake", "memory", "flappy"):
                return
            prev_job = egg_state["tile_jobs"][tile_idx]
            if prev_job is not None:
                try:
                    self.after_cancel(prev_job)
                except tk.TclError:
                    pass
                egg_state["tile_jobs"][tile_idx] = None
            egg_state["clicked"].add(tile_idx)
            rect_id, text_id = tile_items[tile_idx]
            logo_canvas.itemconfigure(rect_id, fill=ORANGE_ACCENT)
            logo_canvas.itemconfigure(text_id, fill=PRIMARY_BTN_FG)
            if len(egg_state["clicked"]) == 3:
                cancel_egg_timers()
                egg_state["reset_job"] = self.after(180, reset_bbc_tiles)
                if armed == "snake":
                    from gui_parts.snake_game import open_snake_game
                    open_snake_game(self)
                elif armed == "memory":
                    from gui_parts.memory_game import open_memory_game
                    open_memory_game(self)
                elif armed == "flappy":
                    from gui_parts.flappy_game import open_flappy_game
                    open_flappy_game(self)
            else:
                egg_state["tile_jobs"][tile_idx] = self.after(2000, lambda i=tile_idx: reset_single_tile(i))

        for idx in range(3):
            logo_canvas.tag_bind(f"bbc_tile_{idx}", "<Button-1>", lambda _e, i=idx: on_bbc_tile_click(i))

        logo_canvas.bind("<Destroy>", cancel_egg_timers, add="+")
        return logo_canvas

    def render_section_title(self, container, heading, description=None, button_label=None, action_func=None):
        """Render a section heading with an optional subtitle and right-aligned action button."""
        header_bar = tk.Frame(container, bg=container.cget("bg"))
        header_bar.pack(fill="x", pady=(18, 10))
        text_pane = tk.Frame(header_bar, bg=container.cget("bg"))
        text_pane.pack(side="left", fill="x", expand=True)
        self.create_label(text_pane, heading, 18, TEXT_WHITE, "bold").pack(anchor="w")
        if description:
            self.create_label(text_pane, description, 10, TEXT_GRAY).pack(anchor="w", pady=(3, 0))
        if button_label and action_func:
            self.create_button(header_bar, button_label, action_func, compact=True).pack(side="right")
        return header_bar

    def render_page_title(self, container, main_heading, sub_heading=""):
        """Render a centered page title and optional subtitle."""
        self.create_label(
            container, main_heading, 25, TEXT_WHITE, "bold",
            anchor="center", justify="center",
        ).pack(fill="x", pady=(4, 3))
        if sub_heading:
            self.create_label(
                container, sub_heading, 11, TEXT_GRAY,
                anchor="center", justify="center",
            ).pack(fill="x", pady=(0, 16))

    def render_decorative_panel(self, container, filename, idx, bounds, width_px, height_px, label_txt=""):
        """Render an SVG-backed decorative tile with a procedural audio-icon fallback."""
        frame_box = tk.Frame(container, bg=PALETTE_SWATCHES[idx % len(PALETTE_SWATCHES)], width=width_px, height=height_px)
        frame_box.pack_propagate(False)
        img_photo = self.get_svg_photo_object(filename, idx, bounds)
        if img_photo:
            img_lbl = tk.Label(frame_box, image=img_photo, bg=frame_box.cget("bg"))
            img_lbl.image = img_photo
            img_lbl.pack(expand=True, pady=(5, 0))
        else:
            canvas_obj = tk.Canvas(frame_box, width=width_px, height=height_px, bg=frame_box.cget("bg"), highlightthickness=0)
            canvas_obj.pack(fill="both", expand=True)
            outline_colour = blend_colour(frame_box.cget("bg"), "#ffffff", 0.33)
            canvas_obj.create_oval(
                width_px * 0.22, height_px * 0.12, width_px * 0.78, height_px * 0.72,
                outline=outline_colour, width=3,
            )
            canvas_obj.create_arc(
                width_px * 0.28, height_px * 0.18, width_px * 0.72, height_px * 0.62,
                start=25, extent=300, style="arc", outline=ORANGE_HL, width=5
            )
            canvas_obj.create_text(width_px / 2, height_px * 0.43, text="♪", fill=TEXT_WHITE, font=(DEFAULT_FONT, 36, "bold"))
        if label_txt:
            self.create_label(frame_box, label_txt, 9, TEXT_WHITE, "bold", anchor="center", bg=frame_box.cget("bg")).pack(
                side="bottom", fill="x", pady=(0, 7)
            )
        return frame_box

    @staticmethod
    def _normalize_title_key(text):
        """Normalize a podcast title or image filename into (spaced_key, compact_alnum_key)."""
        normalized = unicodedata.normalize("NFKD", str(text or ""))
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
        ascii_text = ascii_text.replace("&", " and ")
        spaced = re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()
        compact = spaced.replace(" ", "")
        return spaced, compact

    @staticmethod
    def _strip_noise_words(spaced_key):
        """Remove common leading/trailing noise words (e.g. 'the', 'bbc', 'podcast') for looser matching."""
        noise = {"the", "a", "an", "bbc", "sounds", "podcast", "podcasts", "radio", "show", "cover", "image"}
        tokens = [tok for tok in spaced_key.split() if tok not in noise]
        return tokens

    def _get_podcast_picture_index(self):
        """Scan bbc_podcasts_pictures once and build lookup maps for fast title/ID matching."""
        cached = getattr(self, "_podcast_picture_index", None)
        if cached is not None:
            return cached

        candidate_roots = []
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidate_roots.append(Path(meipass))
            candidate_roots.append(Path(sys.executable).resolve().parent)
        candidate_roots.append(PODCAST_PICTURES_DIR.parent)

        search_dirs = []
        seen_dirs = set()
        for direct in (PODCAST_PICTURES_DIR, *(r / "bbc_podcasts_pictures" for r in candidate_roots)):
            try:
                resolved = direct.resolve()
            except OSError:
                continue
            if resolved.is_dir() and resolved not in seen_dirs:
                seen_dirs.add(resolved)
                search_dirs.append(resolved)

        # Also catch minor capitalization/spacing variants of the folder name in the project root.
        for root in candidate_roots:
            if not root.is_dir():
                continue
            try:
                for child in root.iterdir():
                    if not child.is_dir():
                        continue
                    _, cname = self._normalize_title_key(child.name)
                    if "podcast" in cname and any(tok in cname for tok in ("picture", "pic", "image", "img", "cover")):
                        resolved = child.resolve()
                        if resolved not in seen_dirs:
                            seen_dirs.add(resolved)
                            search_dirs.append(resolved)
            except OSError:
                continue

        supported_exts = {".jpg", ".jpeg", ".jfif", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
        by_spaced = {}
        by_compact = {}
        by_stripped = {}
        by_pid = {}
        entries = []
        pid_pattern = re.compile(r"^(?:podcast|pod|p|id)?[_\-\s]*0*(\d+)(?:[_\-\s].*)?$", re.IGNORECASE)

        for folder in search_dirs:
            try:
                for item in folder.rglob("*"):
                    if not item.is_file() or item.suffix.lower() not in supported_exts:
                        continue
                    spaced, compact = self._normalize_title_key(item.stem)
                    if not compact:
                        continue
                    resolved = item.resolve()
                    by_spaced.setdefault(spaced, resolved)
                    by_compact.setdefault(compact, resolved)
                    pid_match = pid_pattern.match(item.stem)
                    if pid_match:
                        try:
                            by_pid.setdefault(int(pid_match.group(1)), resolved)
                        except ValueError:
                            pass
                    core_tokens = self._strip_noise_words(spaced)
                    core_compact = "".join(core_tokens)
                    if core_compact:
                        by_stripped.setdefault(core_compact, resolved)
                    entries.append((spaced, compact, core_compact, set(core_tokens), resolved))
            except OSError:
                continue

        index = (by_spaced, by_compact, by_stripped, by_pid, entries)
        self._podcast_picture_index = index
        return index

    def _find_podcast_picture(self, title_text, pid=None):
        """Match a podcast title (or PodcastID) to its image file in bbc_podcasts_pictures."""
        spaced, compact = self._normalize_title_key(title_text)
        by_spaced, by_compact, by_stripped, by_pid, entries = self._get_podcast_picture_index()
        if not entries:
            return None
        if spaced in by_spaced:
            return by_spaced[spaced]
        if compact in by_compact:
            return by_compact[compact]

        core_tokens = self._strip_noise_words(spaced)
        core_compact = "".join(core_tokens)
        if core_compact and core_compact in by_stripped:
            return by_stripped[core_compact]

        # Check if a picture was named by PodcastID (e.g. 'podcast_001_news.png' or '12.jpg').
        if pid is not None:
            try:
                pid_int = int(str(pid).strip())
                if pid_int in by_pid:
                    return by_pid[pid_int]
            except (TypeError, ValueError):
                pass
            pid_str = str(pid).strip().lower()
            if pid_str in by_compact:
                return by_compact[pid_str]

        # Fall back to best high-confidence token/substring match.
        title_token_set = set(core_tokens) if core_tokens else set(spaced.split())
        best_path = None
        best_score = 0.0
        for file_spaced, file_compact, file_core_compact, file_tokens, path in entries:
            if core_compact and file_core_compact and (core_compact in file_core_compact or file_core_compact in core_compact):
                ratio = min(len(core_compact), len(file_core_compact)) / float(max(len(core_compact), len(file_core_compact)))
                if ratio >= 0.60 and ratio > best_score:
                    best_score = ratio
                    best_path = path
                    continue
            if title_token_set and file_tokens:
                overlap = len(title_token_set & file_tokens)
                union = len(title_token_set | file_tokens)
                score = overlap / float(union)
                if score >= 0.60 and score > best_score:
                    best_score = score
                    best_path = path
        return best_path

    def _ensure_gdiplus(self):
        """Initialize Windows GDI+ once so JPG/PNG/BMP/GIF covers decode natively without Pillow."""
        if sys.platform != "win32":
            return None
        gdip = getattr(self, "_gdiplus_dll", None)
        if gdip is not None:
            return gdip if gdip is not False else None
        try:
            class GdiplusStartupInput(ctypes.Structure):
                _fields_ = [
                    ("GdiplusVersion", ctypes.c_uint32),
                    ("DebugEventCallback", ctypes.c_void_p),
                    ("SuppressBackgroundThread", ctypes.c_int),
                    ("SuppressExternalCodecs", ctypes.c_int),
                ]

            class RectI(ctypes.Structure):
                _fields_ = [
                    ("X", ctypes.c_int),
                    ("Y", ctypes.c_int),
                    ("Width", ctypes.c_int),
                    ("Height", ctypes.c_int),
                ]

            class BitmapData(ctypes.Structure):
                _fields_ = [
                    ("Width", ctypes.c_uint),
                    ("Height", ctypes.c_uint),
                    ("Stride", ctypes.c_int),
                    ("PixelFormat", ctypes.c_int),
                    ("Scan0", ctypes.c_void_p),
                    ("Reserved", ctypes.c_size_t),
                ]

            dll = ctypes.windll.gdiplus
            dll.GdiplusStartup.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(GdiplusStartupInput), ctypes.c_void_p]
            dll.GdiplusStartup.restype = ctypes.c_int
            dll.GdipLoadImageFromFile.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_void_p)]
            dll.GdipLoadImageFromFile.restype = ctypes.c_int
            dll.GdipGetImageWidth.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
            dll.GdipGetImageWidth.restype = ctypes.c_int
            dll.GdipGetImageHeight.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
            dll.GdipGetImageHeight.restype = ctypes.c_int
            dll.GdipCreateBitmapFromScan0.argtypes = [
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
            ]
            dll.GdipCreateBitmapFromScan0.restype = ctypes.c_int
            dll.GdipGetImageGraphicsContext.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
            dll.GdipGetImageGraphicsContext.restype = ctypes.c_int
            dll.GdipSetInterpolationMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
            dll.GdipSetInterpolationMode.restype = ctypes.c_int
            dll.GdipDrawImageRectRectI.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ]
            dll.GdipDrawImageRectRectI.restype = ctypes.c_int
            dll.GdipBitmapLockBits.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(RectI), ctypes.c_uint, ctypes.c_int, ctypes.POINTER(BitmapData),
            ]
            dll.GdipBitmapLockBits.restype = ctypes.c_int
            dll.GdipBitmapUnlockBits.argtypes = [ctypes.c_void_p, ctypes.POINTER(BitmapData)]
            dll.GdipBitmapUnlockBits.restype = ctypes.c_int
            dll.GdipDeleteGraphics.argtypes = [ctypes.c_void_p]
            dll.GdipDeleteGraphics.restype = ctypes.c_int
            dll.GdipDisposeImage.argtypes = [ctypes.c_void_p]
            dll.GdipDisposeImage.restype = ctypes.c_int

            token = ctypes.c_size_t(0)
            startup = GdiplusStartupInput(1, None, 0, 0)
            if dll.GdiplusStartup(ctypes.byref(token), ctypes.byref(startup), None) != 0:
                self._gdiplus_dll = False
                return None
            self._gdiplus_token = token
            self._gdiplus_structs = (RectI, BitmapData)
            self._gdiplus_dll = dll
            return dll
        except Exception:
            self._gdiplus_dll = False
            return None

    def _load_image_via_gdiplus(self, img_path, width_px, height_px, corner_radius=0, backdrop=None):
        """Decode and centre-crop any Windows-supported image (JPG/PNG/BMP/GIF) via GDI+ into a PPM PhotoImage."""
        dll = self._ensure_gdiplus()
        if dll is None:
            return None
        RectI, BitmapData = self._gdiplus_structs
        src_img = ctypes.c_void_p()
        dst_bmp = ctypes.c_void_p()
        gfx = ctypes.c_void_p()
        locked = False
        bmp_data = BitmapData()
        try:
            if dll.GdipLoadImageFromFile(str(img_path), ctypes.byref(src_img)) != 0 or not src_img.value:
                return None
            sw = ctypes.c_uint(0)
            sh = ctypes.c_uint(0)
            dll.GdipGetImageWidth(src_img, ctypes.byref(sw))
            dll.GdipGetImageHeight(src_img, ctypes.byref(sh))
            src_w, src_h = int(sw.value), int(sh.value)
            if src_w <= 0 or src_h <= 0:
                return None

            # Compute centre-crop rectangle matching target aspect ratio so artwork fills cleanly without stretching.
            target_ratio = width_px / float(height_px)
            src_ratio = src_w / float(src_h)
            if src_ratio > target_ratio:
                crop_h = src_h
                crop_w = max(1, round(src_h * target_ratio))
                crop_x = (src_w - crop_w) // 2
                crop_y = 0
            else:
                crop_w = src_w
                crop_h = max(1, round(src_w / target_ratio))
                crop_x = 0
                crop_y = (src_h - crop_h) // 2

            PIXEL_FORMAT_24RGB = 0x00021808
            if dll.GdipCreateBitmapFromScan0(width_px, height_px, 0, PIXEL_FORMAT_24RGB, None, ctypes.byref(dst_bmp)) != 0:
                return None
            if dll.GdipGetImageGraphicsContext(dst_bmp, ctypes.byref(gfx)) != 0:
                return None
            # InterpolationModeHighQualityBicubic (7), UnitPixel (2).
            dll.GdipSetInterpolationMode(gfx, 7)
            dll.GdipDrawImageRectRectI(
                gfx, src_img, 0, 0, width_px, height_px,
                crop_x, crop_y, crop_w, crop_h, 2, None, None, None,
            )

            rect = RectI(0, 0, width_px, height_px)
            if dll.GdipBitmapLockBits(dst_bmp, ctypes.byref(rect), 1, PIXEL_FORMAT_24RGB, ctypes.byref(bmp_data)) != 0:
                return None
            locked = True

            stride = abs(bmp_data.Stride)
            raw_bytes = ctypes.string_at(bmp_data.Scan0, stride * height_px)
            bg_bytes = bytes.fromhex(backdrop[1:]) if (corner_radius > 0 and backdrop and backdrop.startswith("#") and len(backdrop) == 7) else None
            corner_r = min(corner_radius, width_px // 2, height_px // 2) if bg_bytes else 0

            pixels = bytearray(f"P6\n{width_px} {height_px}\n255\n".encode("ascii"))
            row_len = width_px * 3
            for y in range(height_px):
                start = y * stride
                bgr_row = raw_bytes[start:start + row_len]
                # Convert Windows GDI+ BGR byte order to PPM RGB order.
                rgb_row = bytearray(row_len)
                rgb_row[0::3] = bgr_row[2::3]
                rgb_row[1::3] = bgr_row[1::3]
                rgb_row[2::3] = bgr_row[0::3]
                if corner_r > 0:
                    if y < corner_r:
                        dy_c = corner_r - y
                    elif y >= height_px - corner_r:
                        dy_c = y - (height_px - corner_r - 1)
                    else:
                        dy_c = 0
                    if dy_c > 0:
                        inset = corner_r - math.isqrt(max(0, corner_r ** 2 - dy_c ** 2))
                        if inset > 0:
                            rgb_row[0:inset * 3] = bg_bytes * inset
                            rgb_row[(width_px - inset) * 3:row_len] = bg_bytes * inset
                pixels.extend(rgb_row)
            return tk.PhotoImage(master=self, data=bytes(pixels), format="PPM")
        except Exception:
            return None
        finally:
            if locked and dst_bmp.value:
                dll.GdipBitmapUnlockBits(dst_bmp, ctypes.byref(bmp_data))
            if gfx.value:
                dll.GdipDeleteGraphics(gfx)
            if dst_bmp.value:
                dll.GdipDisposeImage(dst_bmp)
            if src_img.value:
                dll.GdipDisposeImage(src_img)

    def _load_podcast_picture_image(self, img_path, width_px, height_px, corner_radius=0, backdrop=None):
        """Load, centre-crop, and optionally round-corner a podcast cover picture."""
        # Preferred path: Pillow handles JPG/PNG/WEBP with LANCZOS centre-crop and anti-aliased rounded corners.
        try:
            from PIL import Image, ImageDraw, ImageOps, ImageTk
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            with Image.open(img_path) as raw_img:
                fitted = ImageOps.fit(
                    raw_img.convert("RGBA"),
                    (width_px, height_px),
                    method=resample,
                    centering=(0.5, 0.5),
                )
            if corner_radius > 0:
                radius = min(corner_radius, width_px // 2, height_px // 2)
                # Render a 2x supersampled rounded-rectangle mask for smooth anti-aliased corners.
                mask = Image.new("L", (width_px * 2, height_px * 2), 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle(
                    (0, 0, width_px * 2 - 1, height_px * 2 - 1),
                    radius=radius * 2,
                    fill=255,
                )
                mask = mask.resize((width_px, height_px), resample)
                if backdrop and isinstance(backdrop, str) and backdrop.startswith("#") and len(backdrop) == 7:
                    bg_rgb = tuple(int(backdrop[p:p + 2], 16) for p in (1, 3, 5)) + (255,)
                else:
                    bg_rgb = (0, 0, 0, 0)
                canvas_img = Image.new("RGBA", (width_px, height_px), bg_rgb)
                canvas_img.paste(fitted, (0, 0), mask)
                fitted = canvas_img
            return ImageTk.PhotoImage(fitted, master=self)
        except Exception:
            pass

        # Second path: native Windows GDI+ decodes JPG/JPEG/JFIF/PNG/BMP/GIF with zero pip dependencies.
        gdi_photo = self._load_image_via_gdiplus(
            img_path, width_px, height_px, corner_radius=corner_radius, backdrop=backdrop,
        )
        if gdi_photo is not None:
            return gdi_photo

        # Final fallback without Pillow/GDI+ (supports PNG/GIF natively in Tkinter).
        if img_path.suffix.lower() in (".png", ".gif"):
            try:
                photo = tk.PhotoImage(master=self, file=str(img_path))
                ratio = max(
                    1,
                    int(math.ceil(photo.width() / float(width_px))),
                    int(math.ceil(photo.height() / float(height_px))),
                )
                if ratio > 1:
                    photo = photo.subsample(ratio, ratio)
                return photo
            except tk.TclError:
                pass
        return None

    def _get_cover_photo(
        self, container, pid, title_text, category_text, width_px, height_px,
        corner_radius=0, backdrop=None,
    ):
        """Return (PhotoImage, fallback_icon_or_None, bg_colour) for a podcast cover."""
        container_bg = backdrop if (corner_radius > 0 and backdrop) else container.cget("bg")
        pic_path = self._find_podcast_picture(title_text, pid=pid)
        if pic_path is not None:
            pic_key = ("file", str(pic_path), width_px, height_px, corner_radius, container_bg if corner_radius > 0 else "")
            image = self.cover_images.get(pic_key)
            if image is None:
                image = self._load_podcast_picture_image(
                    pic_path, width_px, height_px,
                    corner_radius=corner_radius,
                    backdrop=container_bg if corner_radius > 0 else None,
                )
                if image is not None:
                    self.cover_images[pic_key] = image
                    if len(self.cover_images) > 256:
                        self.cover_images.popitem(last=False)
            else:
                self.cover_images.move_to_end(pic_key)

            if image is not None:
                return image, None, container_bg

        fallback_colours = ("#6e4dbb", "#d85d43", "#178d9a", "#b44272", "#658d31", "#c47b1c")
        try:
            design_index = int(pid)
        except (TypeError, ValueError):
            design_index = sum(ord(char) for char in str(title_text))

        category = str(category_text or "BBC Sounds")
        genre = GENRE_TILE_DETAILS.get(category)
        colour = genre[0] if genre else fallback_colours[design_index % len(fallback_colours)]
        icon = genre[1] if genre else category[:1].upper()
        pattern = design_index % 3
        bg_colour = backdrop if (corner_radius > 0 and backdrop) else colour
        key = (colour, pattern, width_px, height_px, corner_radius, bg_colour)
        image = self.cover_images.get(key)
        if image is None:
            image = self.make_cover_image(
                colour, pattern, width_px, height_px,
                corner_radius=corner_radius, backdrop=bg_colour if corner_radius > 0 else None,
            )
            self.cover_images[key] = image
            if len(self.cover_images) > 256:
                self.cover_images.popitem(last=False)
        self.cover_images.move_to_end(key)
        return image, icon, bg_colour

    def generate_podcast_cover(
        self, container, pid, title_text, category_text, width_px, height_px,
        corner_radius=0, backdrop=None,
    ):
        """Return a cached cover artwork label using bbc_podcasts_pictures (or procedural fallback)."""
        image, icon, bg_colour = self._get_cover_photo(
            container, pid, title_text, category_text, width_px, height_px,
            corner_radius=corner_radius, backdrop=backdrop,
        )
        if icon is None:
            cover = tk.Label(
                container, image=image, bg=bg_colour,
                cursor="hand2", bd=0, highlightthickness=0,
            )
            cover.image = image
            return cover

        cover = tk.Label(
            container, image=image, compound="center", text=icon,
            font=(DEFAULT_FONT, max(11, min(width_px, height_px) // 6), "bold"),
            bg=bg_colour, fg=TEXT_WHITE, cursor="hand2", bd=0, highlightthickness=0,
        )
        cover.image = image
        return cover

    def update_podcast_cover(
        self, cover_label, pid, title_text, category_text, width_px, height_px,
        corner_radius=0, backdrop=None,
    ):
        """Re-render a podcast cover label's image at a new size without rebuilding the card."""
        if not cover_label.winfo_exists():
            return
        image, icon, bg_colour = self._get_cover_photo(
            cover_label.master, pid, title_text, category_text, width_px, height_px,
            corner_radius=corner_radius, backdrop=backdrop,
        )
        if icon is None:
            cover_label.configure(image=image, text="", bg=bg_colour)
        else:
            cover_label.configure(
                image=image, compound="center", text=icon,
                font=(DEFAULT_FONT, max(11, min(width_px, height_px) // 6), "bold"),
                bg=bg_colour,
            )
        cover_label.image = image

    def make_cover_image(self, colour, pattern, width, height, corner_radius=0, backdrop=None):
        """Rasterize a reusable cover background in PPM format with optional rounded corners."""
        base = bytes.fromhex(colour[1:])
        light = bytes.fromhex(blend_colour(colour, "#ffffff", 0.20)[1:])
        dark = bytes.fromhex(blend_colour(colour, "#000000", 0.55)[1:])
        rim = bytes.fromhex(blend_colour(colour, "#ffffff", 0.55)[1:])
        bg_bytes = bytes.fromhex(backdrop[1:]) if (corner_radius > 0 and backdrop and backdrop.startswith("#")) else None
        corner_r = min(corner_radius, width // 2, height // 2) if bg_bytes else 0
        stripe_width = max(5, width // 9)
        stripes = (light * stripe_width + base * stripe_width) * (width // (2 * stripe_width) + 2)
        centre_x, centre_y = width // 2, height // 2
        radius = min(width, height) // 4
        pixels = bytearray(f"P6\n{width} {height}\n255\n".encode("ascii"))
        for y in range(height):
            if pattern == 0:
                edge = max(0, min(width, width - (y - height // 4) * 2))
                row = bytearray(light * edge + base * (width - edge))
            elif pattern == 1:
                shift = (y % (2 * stripe_width)) * 3
                row = bytearray(stripes[shift:shift + width * 3])
            else:
                row = bytearray((base if y < height * 0.72 else light) * width)
            dy = y - centre_y
            for ring_radius, ring_colour in ((radius + 2, rim), (radius, dark)):
                if abs(dy) <= ring_radius:
                    span = math.isqrt(ring_radius ** 2 - dy ** 2)
                    left, right = centre_x - span, centre_x + span + 1
                    row[left * 3:right * 3] = ring_colour * (right - left)
            if corner_r > 0:
                if y < corner_r:
                    dy_c = corner_r - y
                elif y >= height - corner_r:
                    dy_c = y - (height - corner_r - 1)
                else:
                    dy_c = 0
                if dy_c > 0:
                    inset = corner_r - math.isqrt(max(0, corner_r ** 2 - dy_c ** 2))
                    if inset > 0:
                        row[0:inset * 3] = bg_bytes * inset
                        row[(width - inset) * 3:width * 3] = bg_bytes * inset
            pixels.extend(row)
        return tk.PhotoImage(master=self, data=bytes(pixels), format="PPM")

    def create_star_rating_bar(self, container, score_val, star_size=18, background_col=None):
        """Build a 5-star display strip for a numeric rating."""
        row_pane = tk.Frame(container, bg=background_col or container.cget("bg"))
        numeric_score = int(score_val or 0)
        for val in range(1, 6):
            star_color = GOLD_STAR if val <= numeric_score else STAR_EMPTY
            self.create_label(row_pane, "★", star_size, star_color, bg=row_pane.cget("bg")).pack(
                side="left", padx=1
            )
        return row_pane

    def create_genre_circle(self, container, genre_name, idx, size=54, background_col=None):
        """Draw a concentric coloured circular badge with the genre's initial."""
        if background_col is None:
            background_col = CARD_BG
        palette_idx = GENRE_LIST.index(genre_name) if genre_name in GENRE_LIST else idx
        light_col, middle_col, outline_col = GENRE_CIRCLE_COLOURS[palette_idx % len(GENRE_CIRCLE_COLOURS)]
        circle_canvas = tk.Canvas(container, width=size, height=size, bg=background_col, highlightthickness=0, cursor="hand2")
        for inset, fill_col in [(2, outline_col), (5, middle_col), (10, light_col), (16, middle_col)]:
            circle_canvas.create_oval(inset, inset, size - inset, size - inset, fill=fill_col, outline="")
        circle_canvas.create_oval(2, 2, size - 2, size - 2, outline=outline_col, width=2)
        circle_canvas.create_text(size / 2, size / 2, text=genre_name[:1].upper(), fill="#ffffff", font=(DEFAULT_FONT, 14, "bold"))
        return circle_canvas

    def create_default_profile_avatar(self, container, size=112):
        """Draw a clean, neutral white-and-grey default profile avatar."""
        avatar = tk.Canvas(
            container, width=size, height=size, bg=container.cget("bg"),
            highlightthickness=0,
        )
        # Outer grey circular badge with a crisp light border ring.
        centre = size / 2
        outer_margin = size * 0.06
        avatar.create_oval(
            outer_margin, outer_margin,
            size - outer_margin, size - outer_margin,
            fill="#55585e", outline="#e7e8ea", width=3,
        )

        # Draw a minimal white head-and-shoulders silhouette and mask the bottom edge.
        head_radius = size * 0.16
        head_y = size * 0.38
        shoulder_top = size * 0.57
        silhouette = "#f4f4f5"
        avatar.create_oval(
            centre - head_radius, head_y - head_radius,
            centre + head_radius, head_y + head_radius,
            fill=silhouette, outline="",
        )
        avatar.create_oval(
            size * 0.23, shoulder_top,
            size * 0.77, size * 0.88,
            fill=silhouette, outline="",
        )
        avatar.create_rectangle(
            size * 0.18, size * 0.79, size * 0.82, size * 0.92,
            fill="#55585e", outline="",
        )
        return avatar

    def build_genre_tile(self, parent_widget, genre_name, idx, selected=False):
        """Create a compact selectable genre card with a coloured circular badge."""
        bg_col = SELECTED_BG if selected else CARD_BG
        border_col = ORANGE_ACCENT if selected else BORDER_LINE
        tile_box = RoundedPanel(parent_widget, bg_col, border_col)
        canvas_marker = self.create_genre_circle(tile_box, genre_name, idx, 45, bg_col)
        canvas_marker.pack(pady=(10, 3))
        self.create_label(tile_box, genre_name, 9, ORANGE_HL if selected else TEXT_WHITE, "bold", anchor="center", bg=bg_col).pack(
            fill="x", padx=3, pady=(0, 10)
        )
        return tile_box

    def _attach_podcast_card_hover(self, card_frame, bg_widgets, title_label, *, base_bg=None):
        """Animate a card's highlight colour and outward growth on hover without grid reflow."""
        rest_bg = base_bg or CARD_BG
        is_light = getattr(self, "_theme_name", "dark") == "light"
        hover_bg = (
            blend_colour(rest_bg, ORANGE_ACCENT, 0.07)
            if is_light else blend_colour(rest_bg, "#ffffff", 0.06)
        )
        base_inset = 3
        card_frame.set_inset(base_inset)
        hover_state = {
            "step": 0,
            "target": 0,
            "job": None,
            "leave_job": None,
            "last_bg": rest_bg,
            "last_bd": BORDER_LINE,
            "last_inset": base_inset,
            "last_title": TEXT_WHITE,
        }

        def cancel_jobs(_event=None):
            for key in ("job", "leave_job"):
                jid = hover_state[key]
                if jid is not None:
                    try:
                        self.after_cancel(jid)
                    except tk.TclError:
                        pass
                    hover_state[key] = None

        def is_pointer_inside():
            if not card_frame.winfo_exists():
                return False
            try:
                px, py = card_frame.winfo_pointerxy()
                w = card_frame.winfo_containing(px, py)
            except tk.TclError:
                return False
            while w is not None:
                if w is card_frame:
                    return True
                w = getattr(w, "master", None)
            return False

        def apply_frame():
            hover_state["job"] = None
            if not card_frame.winfo_exists():
                return
            cur = hover_state["step"]
            tgt = hover_state["target"]
            if cur == tgt:
                return
            cur += 1 if tgt > cur else -1
            hover_state["step"] = cur

            t = cur / 6.0
            eased = 1.0 - (1.0 - t) ** 3 if tgt > 0 else t * t * (3.0 - 2.0 * t)
            inset = max(0, min(base_inset, round(base_inset * (1.0 - eased))))
            cur_bg = blend_colour(rest_bg, hover_bg, eased)
            cur_bd = blend_colour(BORDER_LINE, ORANGE_ACCENT, eased)
            cur_title = blend_colour(TEXT_WHITE, ORANGE_HL, eased * 0.55)

            if inset != hover_state["last_inset"]:
                card_frame.set_inset(inset)
                hover_state["last_inset"] = inset
            if cur_bg != hover_state["last_bg"] or cur_bd != hover_state["last_bd"]:
                card_frame.set_surface(cur_bg, cur_bd)
                if cur_bg != hover_state["last_bg"]:
                    for widget in bg_widgets:
                        if not widget.winfo_exists():
                            continue
                        try:
                            if isinstance(widget, tk.Button):
                                widget.configure(bg=cur_bg, activebackground=cur_bg, highlightbackground=cur_bg)
                            elif getattr(widget, "_sync_highlight_bg", False):
                                widget.configure(bg=cur_bg, highlightbackground=cur_bg)
                            else:
                                widget.configure(bg=cur_bg)
                        except tk.TclError:
                            pass
                hover_state["last_bg"] = cur_bg
                hover_state["last_bd"] = cur_bd
            if title_label is not None and title_label.winfo_exists() and cur_title != hover_state["last_title"]:
                title_label.configure(fg=cur_title)
                hover_state["last_title"] = cur_title

            if cur != tgt:
                hover_state["job"] = self.after(16, apply_frame)

        def set_hover_target(target):
            hover_state["target"] = target
            if hover_state["job"] is None and hover_state["step"] != target:
                apply_frame()

        def on_enter(_event=None):
            if hover_state["leave_job"] is not None:
                try:
                    self.after_cancel(hover_state["leave_job"])
                except tk.TclError:
                    pass
                hover_state["leave_job"] = None
            set_hover_target(6)

        def on_leave(_event=None):
            if hover_state["leave_job"] is not None:
                try:
                    self.after_cancel(hover_state["leave_job"])
                except tk.TclError:
                    pass
            def check_and_leave():
                hover_state["leave_job"] = None
                if not is_pointer_inside():
                    set_hover_target(0)
            hover_state["leave_job"] = self.after(18, check_and_leave)

        # Bind enter/leave across the card and all descendants so moving over child widgets never flickers.
        bound = [card_frame, card_frame.backdrop]
        stack = list(card_frame.winfo_children())
        while stack:
            child = stack.pop()
            bound.append(child)
            stack.extend(child.winfo_children())
        for widget in bound:
            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
        card_frame.bind("<Destroy>", cancel_jobs, add="+")

    def render_podcast_card(
        self, parent_widget, podcast_data, compact=False,
        show_play_btn=False, show_remove_btn=False, rating_value=None,
        cover_size=240,
    ):
        """Build a podcast card with cover art, metadata, average rating, and action buttons."""
        pid, title, category, length_mins = podcast_data[:4]
        card_frame = self.create_card_frame(parent_widget)
        meta_info = str(category or "Programme")
        if length_mins is not None:
            meta_info += f"  ·  {length_mins} min"

        if compact:
            card_frame.pack(fill="x", pady=5)
            cover = self.generate_podcast_cover(card_frame, pid, title, category, 92, 92)
            cover.pack(side="left", padx=11, pady=10)
            cover.bind("<Button-1>", lambda _e, tid=pid, t=title, c=category: self.open_podcast_detail(tid, t, c))
            details_pane = tk.Frame(card_frame, bg=CARD_BG)
            details_pane.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=12)
            title_lbl = self.create_label(details_pane, title, 12, TEXT_WHITE, "bold")
            title_lbl.pack(anchor="w")
            meta_lbl = self.create_label(details_pane, meta_info, 10, TEXT_GRAY)
            meta_lbl.pack(anchor="w", pady=(5, 0))
            avg_lbl = self.create_label(details_pane, self.podcast_average_text(pid), 9, GOLD_STAR)
            avg_lbl.pack(anchor="w")
            bg_widgets = [details_pane, title_lbl, meta_lbl, avg_lbl]
            view_btn = self.create_button(
                details_pane, "View details",
                lambda target_id=pid, t=title, c=category: self.open_podcast_detail(target_id, t, c),
                compact=True,
            )
            view_btn.pack(anchor="w", pady=(9, 0))
            bg_widgets.append(view_btn)
            if show_play_btn:
                play_btn = self.create_button(card_frame, "▶  Listen", lambda: None, primary=True, compact=True)
                play_btn.configure(
                    command=lambda b=play_btn, cv=cover, target_id=pid, t=title, c=category: (
                        self.play_podcast_to_mini_bar(b, target_id, t, c, cover_widget=cv)
                    )
                )
                play_btn.pack(side="right", padx=12)
                bg_widgets.append(play_btn)
            if show_remove_btn:
                rem_btn = self.create_button(card_frame, "Remove", lambda target_id=pid: self.remove_from_history(target_id), compact=True)
                rem_btn.pack(side="right", padx=(0, 3))
                bg_widgets.append(rem_btn)
            self._attach_podcast_card_hover(card_frame, bg_widgets, title_lbl)
            return card_frame

        cover_box = tk.Frame(card_frame, bg=CARD_BG, height=cover_size, cursor="hand2")
        cover_box.pack_propagate(False)
        cover_box.pack(fill="x", padx=9, pady=(9, 0))
        cover = self.generate_podcast_cover(
            cover_box, pid, title, category, cover_size, cover_size,
            corner_radius=8, backdrop=CARD_BG,
        )
        cover.pack(fill="both", expand=True)
        open_cmd = lambda _e=None, tid=pid, t=title, c=category: self.open_podcast_detail(tid, t, c)
        cover_box.bind("<Button-1>", open_cmd)
        cover.bind("<Button-1>", open_cmd)
        card_frame._cover_meta = [cover_box, cover, pid, title, category, cover_size]

        details_pane = tk.Frame(card_frame, bg=CARD_BG)
        details_pane.pack(fill="both", expand=True, padx=12, pady=11)
        title_lbl = self.create_label(details_pane, title, 12, TEXT_WHITE, "bold", wraplength=max(170, cover_size - 8))
        title_lbl.pack(anchor="w")
        meta_lbl = self.create_label(details_pane, meta_info, 9, TEXT_GRAY)
        meta_lbl.pack(anchor="w", pady=(4, 3))
        avg_lbl = self.create_label(details_pane, self.podcast_average_text(pid), 9, GOLD_STAR)
        avg_lbl.pack(anchor="w", pady=(0, 9))
        bg_widgets = [cover_box, details_pane, title_lbl, meta_lbl, avg_lbl]
        if rating_value is not None:
            yr_lbl = self.create_label(details_pane, "Your rating", 9, TEXT_GRAY)
            yr_lbl.pack(anchor="w")
            star_bar = self.create_star_rating_bar(details_pane, rating_value, star_size=14, background_col=CARD_BG)
            star_bar.pack(anchor="w", pady=(0, 9))
            bg_widgets.extend([yr_lbl, star_bar, *star_bar.winfo_children()])
        button_strip = tk.Frame(details_pane, bg=CARD_BG)
        button_strip.pack(fill="x", side="bottom")
        bg_widgets.append(button_strip)
        det_btn = self.create_button(
            button_strip, "Details",
            lambda target_id=pid, t=title, c=category: self.open_podcast_detail(target_id, t, c),
            compact=True,
        )
        det_btn.pack(side="left")
        bg_widgets.append(det_btn)
        if show_remove_btn:
            rem_btn = self.create_button(
                button_strip, "Remove", lambda target_id=pid: self.remove_from_history(target_id), compact=True
            )
            rem_btn.pack(side="left", padx=(6, 0))
            bg_widgets.append(rem_btn)
        if show_play_btn:
            play_btn = self.create_button(button_strip, "▶", lambda: None, primary=True, compact=True)
            play_btn.configure(
                command=lambda b=play_btn, cv=cover, target_id=pid, t=title, c=category: (
                    self.play_podcast_to_mini_bar(b, target_id, t, c, cover_widget=cv)
                )
            )
            play_btn.pack(side="right")
            bg_widgets.append(play_btn)
        self._attach_podcast_card_hover(card_frame, bg_widgets, title_lbl)
        return card_frame

    def render_podcast_grid(
        self, parent_widget, items_list, columns_count=6,
        show_play=False, show_remove=False, max_count=8, single_row=False,
        rating_index=None, show_end=True,
    ):
        """Render a responsive, batched (and paginated when needed) grid of podcast cards."""
        if not items_list:
            self.render_empty_message(parent_widget, "No programmes to show yet", "Try another search, or explore all programmes.")
            return
        displayed_items = items_list[:max_count]
        if not single_row and len(displayed_items) > PODCASTS_PER_PAGE:
            self.paginate_podcasts(
                parent_widget, displayed_items,
                lambda parent, rows, last: self.render_podcast_grid(
                    parent, rows, columns_count, show_play=show_play,
                    show_remove=show_remove, max_count=len(rows), rating_index=rating_index,
                    show_end=show_end and last and len(displayed_items) == len(items_list),
                ),
            )
            return

        grid_container = tk.Frame(parent_widget, bg=parent_widget.cget("bg"))
        grid_container.pack(fill="x")

        end_message = self.create_label(
            grid_container, "No more results", 15, "#777b83", "bold", anchor="center",
        )
        rendered_cards = []
        current_columns = [0]
        max_configured_cols = [0]
        current_cover_size = [0]
        cover_resize_job = [None]

        def compute_grid_metrics():
            available_width = grid_container.winfo_width()
            if available_width <= 1:
                available_width = max(1, self.winfo_width() - 110)
            # Grow card width only modestly on wide monitors so extra space adds more cards per row.
            target_card_w = min(330, max(255, round(255 + max(0, available_width - 1100) * 0.025)))
            responsive_columns = max(2, min(16, available_width // target_card_w))
            col_width = available_width // responsive_columns
            # Fill card box width (subtract 10px card padx and 18px cover padx) with no side gaps.
            target_cover = max(160, col_width - 28)
            return responsive_columns, target_cover

        def refresh_card_covers():
            cover_resize_job[0] = None
            if not grid_container.winfo_exists():
                return
            target_size = current_cover_size[0]
            for card_widget in rendered_cards:
                if not card_widget.winfo_exists():
                    continue
                meta = getattr(card_widget, "_cover_meta", None)
                if not meta or meta[5] == target_size:
                    continue
                cover_box, cover_lbl, pid, title, category, _old_size = meta
                if cover_box.winfo_exists():
                    cover_box.configure(height=target_size)
                self.update_podcast_cover(
                    cover_lbl, pid, title, category, target_size, target_size,
                    corner_radius=8, backdrop=CARD_BG,
                )
                meta[5] = target_size

        def schedule_cover_refresh():
            if cover_resize_job[0] is not None:
                try:
                    self.after_cancel(cover_resize_job[0])
                except tk.TclError:
                    pass
            cover_resize_job[0] = self.after(50, refresh_card_covers)

        def reflow_cards(_event=None):
            responsive_columns, target_cover = compute_grid_metrics()
            columns_changed = responsive_columns != current_columns[0]
            cover_changed = current_cover_size[0] == 0 or abs(target_cover - current_cover_size[0]) >= 2
            if cover_changed:
                current_cover_size[0] = target_cover
                if rendered_cards:
                    schedule_cover_refresh()
            if not columns_changed and _event is not None:
                return
            current_columns[0] = responsive_columns
            if columns_changed:
                span = max(max_configured_cols[0], responsive_columns)
                max_configured_cols[0] = span
                for col_idx in range(span):
                    grid_container.grid_columnconfigure(
                        col_idx, weight=1 if col_idx < responsive_columns else 0,
                        uniform="programme" if col_idx < responsive_columns else "",
                    )
            visible_count = responsive_columns if single_row else len(rendered_cards)
            first_card = 0 if columns_changed else len(rendered_cards) - 1
            for card_idx in range(first_card, len(rendered_cards)):
                card_widget = rendered_cards[card_idx]
                if card_idx >= visible_count:
                    card_widget.grid_remove()
                    continue
                card_widget.grid(
                    row=card_idx // responsive_columns,
                    column=card_idx % responsive_columns,
                    sticky="nsew", padx=5, pady=5,
                )

            item_count = len(rendered_cards)
            final_row, used_columns = divmod(item_count, responsive_columns)
            if show_end and item_count == len(items_list) and used_columns and (not single_row or final_row == 0):
                end_message.grid(
                    row=final_row, column=used_columns,
                    columnspan=responsive_columns - used_columns,
                    sticky="nsew", padx=5, pady=5,
                )
            else:
                end_message.grid_remove()

        def render_card(podcast):
            if current_cover_size[0] == 0:
                _, current_cover_size[0] = compute_grid_metrics()
            rating_value = podcast[rating_index] if rating_index is not None and len(podcast) > rating_index else None
            card = self.render_podcast_card(
                grid_container, podcast, show_play_btn=show_play,
                show_remove_btn=show_remove, rating_value=rating_value,
                cover_size=current_cover_size[0],
            )
            rendered_cards.append(card)
            reflow_cards()

        grid_container.bind("<Configure>", reflow_cards)
        self.render_in_batches(displayed_items, render_card)

    def paginate_podcasts(self, parent, items, render_page):
        """Wrap a list of programmes with Previous/Next page controls."""
        if len(items) <= PODCASTS_PER_PAGE:
            render_page(parent, items, True)
            return

        background = parent.cget("bg")
        wrapper = tk.Frame(parent, bg=background)
        wrapper.pack(fill="x")
        top = tk.Frame(wrapper, bg=background)
        top.pack(pady=5)
        body = tk.Frame(wrapper, bg=background)
        body.pack(fill="x")
        bottom = tk.Frame(wrapper, bg=background)
        bottom.pack(pady=5)
        page_count = math.ceil(len(items) / PODCASTS_PER_PAGE)
        page_number = 0
        status = tk.StringVar(master=wrapper)
        controls = []
        content = self.current_page
        canvas = content.master

        def change_page(number, scroll=False):
            nonlocal page_number
            if scroll:
                region = canvas.cget("scrollregion")
                if region:
                    height = int(float(region.split()[3]))
                    if height:
                        offset = wrapper.winfo_rooty() - content.winfo_rooty()
                        canvas.yview_moveto(max(0, offset - 8) / height)
                self.cancel_pending_render()
            page_number = number
            for child in body.winfo_children():
                child.destroy()
            last = page_number == page_count - 1
            status.set(f"Page {page_number + 1} of {page_count}")
            for previous, following in controls:
                previous.configure(state="normal" if page_number else "disabled")
                following.configure(state="disabled" if last else "normal")
            start = page_number * PODCASTS_PER_PAGE
            render_page(body, items[start:start + PODCASTS_PER_PAGE], last)

        for bar in (top, bottom):
            previous = self.create_button(
                bar, "‹ Previous", lambda: change_page(page_number - 1, scroll=True), compact=True,
            )
            previous.pack(side="left")
            tk.Label(bar, textvariable=status, bg=background, fg=TEXT_GRAY, font=(DEFAULT_FONT, 10)).pack(
                side="left", padx=12,
            )
            following = self.create_button(
                bar, "Next ›", lambda: change_page(page_number + 1, scroll=True), compact=True,
            )
            following.pack(side="left")
            controls.append((previous, following))
        change_page(0)

    def render_empty_message(self, parent_widget, heading, subtitle):
        """Display a styled empty-state card with a heading and helpful hint."""
        box_pane = self.create_card_frame(parent_widget)
        box_pane.pack(fill="x", pady=8)
        self.create_label(box_pane, heading, 13, TEXT_WHITE, "bold").pack(anchor="w", padx=16, pady=(15, 5))
        self.create_label(box_pane, subtitle, 10, TEXT_GRAY, wraplength=700).pack(anchor="w", padx=16, pady=(0, 15))

    def render_in_batches(self, items_list, render_item):
        """Queue items to render incrementally across event-loop ticks to keep the UI responsive."""
        self._render_queue.append([iter(items_list), render_item])
        if self._pending_render_id is None:
            self._pending_render_id = self.after_idle(self._render_next_batch)

    def _render_next_batch(self):
        """Render a small time-sliced batch of queued widgets and re-apply UI scaling on completion."""
        self._pending_render_id = None
        if getattr(self, "_transition_active", False):
            self._pending_render_id = self.after(20, self._render_next_batch)
            return
        if monotonic() < self._scroll_priority_until:
            self._pending_render_id = self.after(24, self._render_next_batch)
            return
        deadline = monotonic() + 0.008
        rendered_count = 0
        while self._render_queue and rendered_count < 6:
            items_iter, render_item = self._render_queue[0]
            try:
                item = next(items_iter)
            except StopIteration:
                self._render_queue.pop(0)
                continue
            try:
                render_item(item)
            except tk.TclError:
                self._render_queue.pop(0)
                continue
            rendered_count += 1
            if monotonic() >= deadline:
                break
        if self._render_queue:
            self._pending_render_id = self.after(4, self._render_next_batch)
        elif abs(self._ui_scale_factor - 1.0) >= 0.025 and self.current_page is not None and self.current_page.winfo_exists():
            self._scale_widget_tree(self.current_page, self._ui_scale_factor)

    def cancel_pending_render(self):
        """Cancel any scheduled batched rendering work when leaving a page."""
        if self._pending_render_id is not None:
            try:
                self.after_cancel(self._pending_render_id)
            except tk.TclError:
                pass
            self._pending_render_id = None
        self._render_queue.clear()
