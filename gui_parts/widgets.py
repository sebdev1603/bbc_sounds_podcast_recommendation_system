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
            padx=0, pady=0, highlightthickness=0 if sys.platform != "win32" else 1,
            highlightbackground=background, highlightcolor=ORANGE_HL,
            **kwargs,
        )
        button._rounded_padding = (24, 12) if compact else (32, 16)
        button._hover_target_fg = hover_fg
        button._hover_job = None
        button._hover_step = 0
        button._hover_target = 0
        self.style_rounded_button(button, face, ORANGE_HL if primary else SECONDARY_HOVER_BG)
        button.bind("<Enter>", lambda _e, btn=button: self.animate_button_hover(btn, 5))
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
        """Ease a button's hover state smoothly toward target_step (0..5) with shared cached frames."""
        if not button.winfo_exists():
            return
        if target_step > 0 and (
            str(button.cget("state")) == "disabled"
            or getattr(self, "_transition_active", False)
            or self._is_scrolling()
        ):
            return
        button._hover_target = target_step
        if self._is_reduced_motion():
            self.cancel_button_hover(button)
            if getattr(button, "_hover_step", 0) != target_step:
                button._hover_step = target_step
                self._apply_button_hover_frame(button, target_step)
            return
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
                button._hover_job = self.after(self._anim_frame_interval(18), step_frame)

        step_frame()

    def _apply_button_hover_frame(self, button, step):
        """Render a single quantized hover frame so enter and leave share cached PhotoImages."""
        face, hover = button._rounded_colours
        width, height = button._hover_size
        base_fg = button._hover_base_fg
        t = max(0.0, min(1.0, step / 5.0))
        # Quantize to 5 shared levels (0.0, 0.25, 0.5, 0.75, 1.0) to slash PhotoImage churn on low-end devices.
        raw_eased = ease_out_elastic(t, damping=5.0, frequency=1.10) if getattr(button, "_hover_target", 0) > 0 else 1.0 - (1.0 - t) ** 2
        eased = max(0.0, min(1.0, round(raw_eased * 4.0) / 4.0))
        colour = blend_colour(face, hover, eased)
        inset = max(1, min(3, round(3.0 - 2.0 * eased)))
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
        tile_font = (DEFAULT_FONT, -round(tile * 0.78), "bold")
        sounds_font = (DEFAULT_FONT, -round(tile * 0.86), "bold")
        tile_metrics = self._get_cached_font(tile_font)
        sounds_metrics = self._get_cached_font(sounds_font)
        # Shift uppercase glyphs down by ~half the font's descent so cap-height sits optically centered.
        tile_y_nudge = tile_metrics.metrics("descent") * 0.45
        sounds_y_nudge = sounds_metrics.metrics("descent") * 0.45

        tiles_w = tile * 3 + gap * 2
        sounds_w = sounds_metrics.measure("SOUNDS")
        canvas_w = tiles_w + word_gap + sounds_w + 4
        canvas_h = max(tile, sounds_metrics.metrics("linespace"))
        y0 = round((canvas_h - tile) / 2)
        y1 = y0 + tile
        center_y = (y0 + y1) / 2.0

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
                (x0 + x1) / 2.0,
                center_y + tile_y_nudge,
                text=char,
                fill=LOGO_TILE_FG,
                font=tile_font,
                anchor="center",
                tags=tag,
            )
            tile_items.append((rect_id, text_id))
        logo_canvas.create_text(
            tiles_w + word_gap,
            center_y + sounds_y_nudge,
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

    def _get_rounded_mask(self, width_px, height_px, corner_radius):
        """Return a cached anti-aliased L-mode rounded-rectangle mask for fast cover composition."""
        cache = getattr(self, "_rounded_mask_cache", None)
        if cache is None:
            cache = {}
            self._rounded_mask_cache = cache
        key = (width_px, height_px, corner_radius)
        mask = cache.get(key)
        if mask is None:
            from PIL import Image, ImageDraw
            resample = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
            radius = min(corner_radius, width_px // 2, height_px // 2)
            # 2x supersampled mask rendered once per (w, h, r) size and reused across all cards.
            hi = Image.new("L", (width_px * 2, height_px * 2), 0)
            draw = ImageDraw.Draw(hi)
            draw.rounded_rectangle(
                (0, 0, width_px * 2 - 1, height_px * 2 - 1),
                radius=radius * 2,
                fill=255,
            )
            mask = hi.resize((width_px, height_px), resample)
            if len(cache) > 64:
                cache.clear()
            cache[key] = mask
        return mask

    def _load_podcast_picture_image(self, img_path, width_px, height_px, corner_radius=0, backdrop=None):
        """Load, centre-crop, and optionally round-corner a podcast cover picture."""
        # Preferred path: Pillow handles JPG/PNG/WEBP with exact centre-crop and anti-aliased rounded corners,
        # outputting PPM directly to tk.PhotoImage so python3-pillow-tk / ImageTk is NOT required on Linux.
        try:
            from PIL import Image, ImageOps
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            with Image.open(img_path) as raw_img:
                fitted = ImageOps.fit(
                    raw_img.convert("RGB"),
                    (width_px, height_px),
                    method=resample,
                    centering=(0.5, 0.5),
                )
            if corner_radius > 0:
                mask = self._get_rounded_mask(width_px, height_px, corner_radius)
                if backdrop and isinstance(backdrop, str) and backdrop.startswith("#") and len(backdrop) == 7:
                    bg_rgb = tuple(int(backdrop[p:p + 2], 16) for p in (1, 3, 5))
                else:
                    bg_rgb = (27, 29, 33)
                canvas_img = Image.new("RGB", (width_px, height_px), bg_rgb)
                canvas_img.paste(fitted, (0, 0), mask)
                fitted = canvas_img
            ppm_header = f"P6\n{width_px} {height_px}\n255\n".encode("ascii")
            return tk.PhotoImage(master=self, data=ppm_header + fitted.tobytes(), format="PPM")
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
            if not card_frame.winfo_exists() or getattr(self, "_transition_active", False):
                return
            if hover_state["target"] > 0 and self._is_scrolling():
                return
            cur = hover_state["step"]
            tgt = hover_state["target"]
            if cur == tgt:
                return
            cur += 1 if tgt > cur else -1
            hover_state["step"] = cur

            t = cur / 4.0
            eased = 1.0 - (1.0 - t) ** 2 if tgt > 0 else t * t * (3.0 - 2.0 * t)
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
                hover_state["job"] = self.after(self._anim_frame_interval(18), apply_frame)

        def set_hover_target(target):
            hover_state["target"] = target
            if self._is_reduced_motion():
                if hover_state["job"] is not None:
                    try:
                        self.after_cancel(hover_state["job"])
                    except tk.TclError:
                        pass
                    hover_state["job"] = None
                if hover_state["step"] != target:
                    hover_state["step"] = max(0, target - 1) if target > hover_state["step"] else min(4, target + 1)
                    apply_frame()
                return
            if hover_state["job"] is None and hover_state["step"] != target:
                apply_frame()

        def on_enter(_event=None):
            # Ignore synthetic Enter events fired while hero overlays or scrolling slide cards under the cursor.
            if getattr(self, "_transition_active", False) or self._is_scrolling():
                return
            if hover_state["leave_job"] is not None:
                try:
                    self.after_cancel(hover_state["leave_job"])
                except tk.TclError:
                    pass
                hover_state["leave_job"] = None
            set_hover_target(4)

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
            card_frame._cover_meta = [card_frame, cover, pid, title, category, 92]
            details_pane = tk.Frame(card_frame, bg=CARD_BG)
            details_pane.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=12)
            title_lbl = self.create_label(details_pane, title, 12, TEXT_WHITE, "bold")
            title_lbl.pack(anchor="w")
            open_cmd = (
                lambda _e=None, tid=pid, t=title, c=category, cf=card_frame, cv=cover, tl=title_lbl:
                self.open_podcast_detail(tid, t, c, source_card=cf, source_cover=cv, source_title=tl)
            )
            cover.bind("<Button-1>", open_cmd)
            meta_lbl = self.create_label(details_pane, meta_info, 10, TEXT_GRAY)
            meta_lbl.pack(anchor="w", pady=(5, 0))
            avg_lbl = self.create_label(details_pane, self.podcast_average_text(pid), 9, GOLD_STAR)
            avg_lbl.pack(anchor="w")
            bg_widgets = [details_pane, title_lbl, meta_lbl, avg_lbl]
            view_btn = self.create_button(
                details_pane, "View details",
                open_cmd,
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
        card_frame._cover_meta = [cover_box, cover, pid, title, category, cover_size]

        details_pane = tk.Frame(card_frame, bg=CARD_BG)
        details_pane.pack(fill="both", expand=True, padx=12, pady=11)
        title_lbl = self.create_label(details_pane, title, 12, TEXT_WHITE, "bold", wraplength=max(170, cover_size - 8))
        title_lbl.pack(anchor="w")
        open_cmd = (
            lambda _e=None, tid=pid, t=title, c=category, cf=card_frame, cv=cover, tl=title_lbl:
            self.open_podcast_detail(tid, t, c, source_card=cf, source_cover=cv, source_title=tl)
        )
        cover_box.bind("<Button-1>", open_cmd)
        cover.bind("<Button-1>", open_cmd)
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
            open_cmd,
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
        rating_index=None, show_end=True, ratings_mode=False,
    ):
        """Render a responsive single-Canvas grid of podcast cards (zero child HWNDs for tear-free scrolling)."""
        if not items_list:
            self.render_empty_message(parent_widget, "No programmes to show yet", "Try another search, or explore all programmes.")
            return
        displayed_items = items_list[:max_count]
        if not single_row and not ratings_mode and len(displayed_items) > PODCASTS_PER_PAGE:
            self.paginate_podcasts(
                parent_widget, displayed_items,
                lambda parent, rows, last: self.render_podcast_grid(
                    parent, rows, columns_count, show_play=show_play,
                    show_remove=show_remove, max_count=len(rows), rating_index=rating_index,
                    show_end=show_end and last and len(displayed_items) == len(items_list),
                ),
            )
            return

        bg_col = parent_widget.cget("bg")
        grid_canvas = tk.Canvas(
            parent_widget, bg=bg_col, highlightthickness=0, bd=0, height=1,
        )
        grid_canvas.pack(fill="x")

        class _CanvasRectProxy:
            """Lightweight geometry proxy so hero expand/shrink/play animations target Canvas cards directly."""
            __slots__ = ("_canvas", "_x", "_y", "_w", "_h")

            def __init__(self, cvs, x, y, w, h):
                self._canvas = cvs
                self._x = x
                self._y = y
                self._w = w
                self._h = h

            def winfo_exists(self):
                return self._canvas.winfo_exists()

            def winfo_ismapped(self):
                return self._canvas.winfo_ismapped()

            def winfo_rootx(self):
                return self._canvas.winfo_rootx() + self._x

            def winfo_rooty(self):
                return self._canvas.winfo_rooty() + self._y

            def winfo_width(self):
                return self._w

            def winfo_height(self):
                return self._h

        def rounded_pts(x0, y0, x1, y1, r):
            r = max(2, min(r, (x1 - x0) / 2.0, (y1 - y0) / 2.0))
            return (
                x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r,
                x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
                x0, y1, x0, y1 - r, x0, y0 + r, x0, y0,
            )

        scale = getattr(self, "_ui_scale_factor", 1.0)
        text_scale = getattr(self, "_text_scale", 1.0)
        f_scale = scale * text_scale
        title_font = self._get_cached_font((DEFAULT_FONT, max(9, round(11 * f_scale)), "bold"))
        meta_font = self._get_cached_font((DEFAULT_FONT, max(8, round(9 * f_scale))))
        star_font = self._get_cached_font((DEFAULT_FONT, max(11, round(13 * f_scale))))
        btn_font = self._get_cached_font((DEFAULT_FONT, max(8, round(9 * f_scale)), "bold"))
        end_font = self._get_cached_font((DEFAULT_FONT, max(12, round(15 * f_scale)), "bold"))

        details_txt = translate("Details")
        remove_txt = translate("Remove")
        change_txt = translate("Change rating")
        your_rating_txt = translate("Your rating")
        no_more_txt = translate("No more results")
        hover_bg_col = blend_colour(CARD_BG, SECONDARY_HOVER_BG, 0.55)
        sec_btn_bg = blend_colour(CARD_BG, SECONDARY_HOVER_BG, 0.60)
        sec_btn_hover = SECONDARY_HOVER_BG

        # Precompute card metadata once so layout/reflow stays instant.
        card_entries = []
        for row in displayed_items:
            pid = row[0]
            title = str(row[1])
            category = str(row[2] or "Programme")
            length_mins = row[3] if (not ratings_mode and len(row) > 3) else None
            meta_info = translate(category)
            if length_mins is not None:
                meta_info += f"  ·  {length_mins} min"
            avg_txt = self.podcast_average_text(pid)
            r_val = row[rating_index] if (rating_index is not None and len(row) > rating_index) else None
            card_entries.append((pid, title, category, meta_info, avg_txt, r_val))

        state = {
            "last_w": 0,
            "cards": [],      # list of dicts with bounds, item ids, buttons, proxies
            "hovered": None,  # hovered card index
            "hovered_btn": None,  # (card_idx, btn_idx)
            "resize_job": None,
        }
        grid_canvas._photo_refs = []
        grid_canvas._canvas_card_rects = {}

        def draw_grid(avail_w):
            if not grid_canvas.winfo_exists():
                return
            if avail_w <= 1:
                avail_w = max(320, self.winfo_width() - 110)
            target_card_w = (
                min(355, max(280, round(280 + max(0, avail_w - 1100) * 0.025)))
                if ratings_mode else
                min(330, max(255, round(255 + max(0, avail_w - 1100) * 0.025)))
            )
            cols = max(2, min(14 if ratings_mode else 16, avail_w // target_card_w))
            gap = 10
            card_w = max(180, (avail_w - gap * (cols - 1)) // cols)
            cover_sz = max(140, card_w - 20)
            has_rating_row = ratings_mode or (rating_index is not None)
            text_area_h = round((166 if has_rating_row else 128) * max(0.95, min(1.35, f_scale)))
            card_h = cover_sz + 18 + text_area_h

            visible_entries = card_entries[:cols] if single_row else card_entries
            total_items = len(visible_entries)
            rows_n = max(1, math.ceil(total_items / cols))
            total_h = rows_n * card_h + max(0, rows_n - 1) * gap + 4

            grid_canvas.delete("all")
            grid_canvas._photo_refs = []
            grid_canvas._canvas_card_rects = {}
            state["cards"] = []
            state["hovered"] = None
            state["hovered_btn"] = None
            grid_canvas.configure(height=total_h)

            for idx, (pid, title, category, meta_info, avg_txt, r_val) in enumerate(visible_entries):
                row_i, col_i = divmod(idx, cols)
                x0 = col_i * (card_w + gap)
                y0 = row_i * (card_h + gap)
                x1 = x0 + card_w
                y1 = y0 + card_h

                bg_item = grid_canvas.create_polygon(
                    rounded_pts(x0 + 1, y0 + 1, x1 - 1, y1 - 1, 12),
                    smooth=True, fill=CARD_BG, outline=BORDER_LINE, width=1,
                )

                cov_x = x0 + (card_w - cover_sz) // 2
                cov_y = y0 + 10
                photo, icon, _ = self._get_cover_photo(
                    grid_canvas, pid, title, category, cover_sz, cover_sz,
                    corner_radius=8, backdrop=CARD_BG,
                )
                grid_canvas._photo_refs.append(photo)
                grid_canvas.create_image(cov_x, cov_y, image=photo, anchor="nw")
                if icon is not None:
                    grid_canvas.create_text(
                        cov_x + cover_sz // 2, cov_y + cover_sz // 2,
                        text=icon, fill=TEXT_WHITE,
                        font=self._get_cached_font((DEFAULT_FONT, max(12, cover_sz // 6), "bold")),
                    )

                tx = x0 + 12
                ty = cov_y + cover_sz + 11
                max_tw = max(120, card_w - 24)
                # Keep title cleanly within 2 lines so card heights stay uniform.
                disp_title = title if len(title) <= 44 else (title[:42].rstrip() + "…")
                title_item = grid_canvas.create_text(
                    tx, ty, text=disp_title, fill=TEXT_WHITE, font=title_font,
                    anchor="nw", width=max_tw,
                )
                tb = grid_canvas.bbox(title_item)
                next_y = (tb[3] if tb else ty + 20) + 4
                grid_canvas.create_text(
                    tx, next_y, text=meta_info, fill=TEXT_GRAY, font=meta_font,
                    anchor="nw", width=max_tw,
                )
                next_y += round(17 * max(0.95, f_scale))
                grid_canvas.create_text(
                    tx, next_y, text=avg_txt, fill=GOLD_STAR, font=meta_font,
                    anchor="nw", width=max_tw,
                )
                next_y += round(18 * max(0.95, f_scale))

                if r_val is not None:
                    grid_canvas.create_text(
                        tx, next_y, text=your_rating_txt, fill=TEXT_GRAY, font=meta_font, anchor="nw",
                    )
                    next_y += round(15 * max(0.95, f_scale))
                    try:
                        filled = max(0, min(5, int(round(float(r_val)))))
                    except (TypeError, ValueError):
                        filled = 0
                    for s_i in range(5):
                        grid_canvas.create_text(
                            tx + s_i * round(16 * max(0.95, f_scale)), next_y,
                            text="★", fill=GOLD_STAR if s_i < filled else STAR_EMPTY,
                            font=star_font, anchor="nw",
                        )

                card_proxy = _CanvasRectProxy(grid_canvas, x0, y0, card_w, card_h)
                cover_proxy = _CanvasRectProxy(grid_canvas, cov_x, cov_y, cover_sz, cover_sz)
                title_proxy = _CanvasRectProxy(grid_canvas, tx, ty, max_tw, 24)
                grid_canvas._canvas_card_rects[str(pid)] = (card_proxy, cover_proxy, pid, title, category, cover_sz)

                # Bottom pill buttons.
                btn_h = round(28 * max(0.95, min(1.25, f_scale)))
                by1 = y1 - 11
                by0 = by1 - btn_h
                buttons = []

                def add_btn(bx0, bx1, label_s, primary, action):
                    base_c = ORANGE_ACCENT if primary else sec_btn_bg
                    hov_c = ORANGE_HL if primary else sec_btn_hover
                    fg_c = PRIMARY_BTN_FG if primary else TEXT_WHITE
                    poly = grid_canvas.create_polygon(
                        rounded_pts(bx0, by0, bx1, by1, 8),
                        smooth=True, fill=base_c, outline="",
                    )
                    lbl = grid_canvas.create_text(
                        (bx0 + bx1) / 2.0, (by0 + by1) / 2.0,
                        text=label_s, fill=fg_c, font=btn_font,
                    )
                    buttons.append({
                        "rect": (bx0, by0, bx1, by1),
                        "poly": poly,
                        "lbl": lbl,
                        "base": base_c,
                        "hover": hov_c,
                        "action": action,
                    })

                if ratings_mode:
                    ch_w = max(84, btn_font.measure(change_txt) + 20)
                    rm_w = max(62, btn_font.measure(remove_txt) + 18)
                    add_btn(
                        tx, min(x1 - 12 - rm_w - 6, tx + ch_w), change_txt, False,
                        lambda tid=pid: self.rate_programme(tid, self.show_ratings),
                    )
                    add_btn(
                        x1 - 12 - rm_w, x1 - 12, remove_txt, False,
                        lambda tid=pid: self.remove_rating(tid),
                    )
                else:
                    det_w = max(60, btn_font.measure(details_txt) + 20)
                    add_btn(
                        tx, tx + det_w, details_txt, False,
                        lambda tid=pid, t=title, c=category, cp=card_proxy, cvp=cover_proxy, tp=title_proxy: (
                            self.open_podcast_detail(tid, t, c, source_card=cp, source_cover=cvp, source_title=tp)
                        ),
                    )
                    if show_remove:
                        rm_w = max(60, btn_font.measure(remove_txt) + 18)
                        rx0 = tx + det_w + 6
                        add_btn(
                            rx0, rx0 + rm_w, remove_txt, False,
                            lambda tid=pid: self.remove_from_history(tid),
                        )
                    if show_play:
                        pw = max(36, round(38 * max(0.95, f_scale)))
                        px0 = x1 - 12 - pw
                        play_proxy = _CanvasRectProxy(grid_canvas, px0, by0, pw, btn_h)
                        add_btn(
                            px0, x1 - 12, "▶", True,
                            lambda pp=play_proxy, tid=pid, t=title, c=category, cvp=cover_proxy: (
                                self.play_podcast_to_mini_bar(pp, tid, t, c, cover_widget=cvp)
                            ),
                        )

                state["cards"].append({
                    "rect": (x0, y0, x1, y1),
                    "bg_item": bg_item,
                    "title_item": title_item,
                    "buttons": buttons,
                    "open_action": (
                        lambda tid=pid, t=title, c=category, cp=card_proxy, cvp=cover_proxy, tp=title_proxy:
                        self.open_podcast_detail(tid, t, c, source_card=cp, source_cover=cvp, source_title=tp)
                    ),
                })

            final_row, used_cols = divmod(total_items, cols)
            if show_end and total_items == len(items_list) and used_cols and (not single_row or final_row == 0):
                ex0 = used_cols * (card_w + gap)
                ex1 = cols * card_w + (cols - 1) * gap
                ey = final_row * (card_h + gap) + card_h // 2
                grid_canvas.create_text(
                    (ex0 + ex1) / 2.0, ey, text=no_more_txt, fill="#777b83", font=end_font,
                )

        def set_hover(card_idx, btn_idx):
            prev_c = state["hovered"]
            prev_b = state["hovered_btn"]
            if prev_c == card_idx and prev_b == btn_idx:
                return
            if prev_b is not None:
                pc, pb = prev_b
                if pc < len(state["cards"]) and pb < len(state["cards"][pc]["buttons"]):
                    b = state["cards"][pc]["buttons"][pb]
                    grid_canvas.itemconfigure(b["poly"], fill=b["base"])
            if prev_c is not None and prev_c != card_idx and prev_c < len(state["cards"]):
                c = state["cards"][prev_c]
                grid_canvas.itemconfigure(c["bg_item"], fill=CARD_BG, outline=BORDER_LINE)
                grid_canvas.itemconfigure(c["title_item"], fill=TEXT_WHITE)
            if card_idx is not None and card_idx < len(state["cards"]):
                c = state["cards"][card_idx]
                grid_canvas.itemconfigure(c["bg_item"], fill=hover_bg_col, outline=ORANGE_ACCENT)
                grid_canvas.itemconfigure(c["title_item"], fill=ORANGE_HL)
                if btn_idx is not None and btn_idx < len(c["buttons"]):
                    b = c["buttons"][btn_idx]
                    grid_canvas.itemconfigure(b["poly"], fill=b["hover"])
                grid_canvas.configure(cursor="hand2")
            else:
                grid_canvas.configure(cursor="")
            state["hovered"] = card_idx
            state["hovered_btn"] = (card_idx, btn_idx) if (card_idx is not None and btn_idx is not None) else None

        def hit_test(x, y):
            for ci, c in enumerate(state["cards"]):
                x0, y0, x1, y1 = c["rect"]
                if x0 <= x <= x1 and y0 <= y <= y1:
                    for bi, b in enumerate(c["buttons"]):
                        bx0, by0, bx1, by1 = b["rect"]
                        if bx0 <= x <= bx1 and by0 <= y <= by1:
                            return ci, bi
                    return ci, None
            return None, None

        def on_motion(event):
            if getattr(self, "_transition_active", False) or self._is_scrolling():
                return
            ci, bi = hit_test(event.x, event.y)
            set_hover(ci, bi)

        def on_leave(_event=None):
            set_hover(None, None)

        def on_click(event):
            if self._is_busy_transitioning():
                return
            ci, bi = hit_test(event.x, event.y)
            if ci is None:
                return
            c = state["cards"][ci]
            if bi is not None:
                c["buttons"][bi]["action"]()
            else:
                c["open_action"]()

        def on_configure(event):
            if event.width <= 1 or abs(event.width - state["last_w"]) < 4:
                return
            state["last_w"] = event.width
            if state["resize_job"] is not None:
                try:
                    self.after_cancel(state["resize_job"])
                except tk.TclError:
                    pass
            delay = 80 if getattr(self, "_transition_active", False) else 35
            state["resize_job"] = self.after(delay, lambda w=event.width: draw_grid(w))

        grid_canvas.bind("<Motion>", on_motion)
        grid_canvas.bind("<Leave>", on_leave)
        grid_canvas.bind("<Button-1>", on_click)
        grid_canvas.bind("<Configure>", on_configure)

        init_w = parent_widget.winfo_width()
        if init_w > 1 and parent_widget is getattr(self, "current_page", None):
            # content_pane has padx=46 on both sides; subtract 92px to match grid_canvas's true inner width.
            init_w = max(320, init_w - 92)
        elif init_w <= 1:
            shell_cvs = getattr(self, "_shell_canvas", None)
            if shell_cvs is not None and shell_cvs.winfo_exists() and shell_cvs.winfo_width() > 100:
                init_w = max(320, shell_cvs.winfo_width() - 92)
            else:
                init_w = max(320, self.winfo_width() - 120)
        state["last_w"] = init_w
        draw_grid(init_w)

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
        order_cache = getattr(self, "_tab_podcast_order_cache", None)
        if order_cache is None:
            order_cache = {}
            self._tab_podcast_order_cache = order_cache
        page_key = ("pagination_page", getattr(self, "_active_nav_tab", None), len(items), items[0][0] if items else None)
        page_number = min(page_count - 1, max(0, int(order_cache.get(page_key, 0))))
        status = tk.StringVar(master=wrapper)
        controls = []
        content = self.current_page
        canvas = content.master
        anim_state = {"job": None, "active": False, "holder": None}

        def cancel_page_anim(_event=None):
            if anim_state["job"] is not None:
                try:
                    body.after_cancel(anim_state["job"])
                except tk.TclError:
                    pass
                anim_state["job"] = None
            if anim_state["active"]:
                anim_state["active"] = False
                self._finish_transition()

        wrapper.bind("<Destroy>", cancel_page_anim, add="+")

        def find_grid_canvas():
            for child in body.winfo_children():
                if isinstance(child, tk.Canvas):
                    return child
            return None

        def change_page(number, scroll=False, animate=False):
            nonlocal page_number
            target_num = max(0, min(page_count - 1, number))
            if animate and (anim_state["active"] or self._is_busy_transitioning() or target_num == page_number):
                return
            direction = 1 if target_num > page_number else -1
            if scroll:
                region = canvas.cget("scrollregion")
                if region:
                    height = int(float(region.split()[3]))
                    if height:
                        offset = wrapper.winfo_rooty() - content.winfo_rooty()
                        canvas.yview_moveto(max(0, offset - 8) / height)
                self.cancel_pending_render()

            old_canvas = find_grid_canvas()
            page_number = target_num
            order_cache[page_key] = page_number
            last = page_number == page_count - 1
            status.set(f"Page {page_number + 1} of {page_count}")
            for previous, following in controls:
                previous.configure(state="normal" if page_number else "disabled")
                following.configure(state="disabled" if last else "normal")
            start = page_number * PODCASTS_PER_PAGE

            if not animate or self._is_reduced_motion() or old_canvas is None or not old_canvas.winfo_exists():
                for child in body.winfo_children():
                    child.destroy()
                render_page(body, items[start:start + PODCASTS_PER_PAGE], last)
                return

            # Zero-HWND-move single-Canvas slide: shift canvas items out, swap page, spring new items in.
            self._transition_active = True
            anim_state["active"] = True
            out_dist = 240.0
            in_dist = 260.0
            out_dur = 0.095
            in_dur = 0.250

            def finish_slide():
                anim_state["job"] = None
                anim_state["active"] = False
                self._finish_transition()

            def start_incoming():
                if not body.winfo_exists():
                    finish_slide()
                    return
                for child in body.winfo_children():
                    child.destroy()
                render_page(body, items[start:start + PODCASTS_PER_PAGE], last)
                new_canvas = find_grid_canvas()
                if new_canvas is None or not new_canvas.winfo_exists():
                    finish_slide()
                    return
                cur_offset = [round(direction * in_dist)]
                new_canvas.move("all", cur_offset[0], 0)
                in_st = {"progress": 0.0, "last_t": None}

                def draw_in():
                    anim_state["job"] = None
                    if not body.winfo_exists() or not new_canvas.winfo_exists():
                        finish_slide()
                        return
                    f_t0 = monotonic()
                    dt = 0.016 if in_st["last_t"] is None else max(0.004, min(0.042, f_t0 - in_st["last_t"]))
                    in_st["last_t"] = f_t0
                    in_st["progress"] = min(1.0, in_st["progress"] + dt / in_dur)
                    p = in_st["progress"]
                    eased = 1.0 - (1.0 - p) ** 3 if sys.platform != "win32" else ease_out_elastic(p, damping=4.8, frequency=1.22)
                    desired_x = round(direction * in_dist * (1.0 - eased))
                    dx = desired_x - cur_offset[0]
                    if dx:
                        new_canvas.move("all", dx, 0)
                        cur_offset[0] = desired_x
                    if p < 1.0:
                        spent = (monotonic() - f_t0) * 1000.0
                        anim_state["job"] = body.after(self._next_frame_delay(spent, 16), draw_in)
                    else:
                        if cur_offset[0] != 0:
                            new_canvas.move("all", -cur_offset[0], 0)
                        finish_slide()

                body.after(1, draw_in)

            out_offset = [0]
            out_st = {"progress": 0.0, "last_t": None}

            def draw_out():
                anim_state["job"] = None
                if not body.winfo_exists() or not old_canvas.winfo_exists():
                    start_incoming()
                    return
                f_t0 = monotonic()
                dt = 0.016 if out_st["last_t"] is None else max(0.004, min(0.042, f_t0 - out_st["last_t"]))
                out_st["last_t"] = f_t0
                out_st["progress"] = min(1.0, out_st["progress"] + dt / out_dur)
                p = out_st["progress"]
                desired_x = round(-direction * out_dist * (p * p))
                dx = desired_x - out_offset[0]
                if dx:
                    old_canvas.move("all", dx, 0)
                    out_offset[0] = desired_x
                if p < 1.0:
                    spent = (monotonic() - f_t0) * 1000.0
                    anim_state["job"] = body.after(self._next_frame_delay(spent, 16), draw_out)
                else:
                    start_incoming()

            draw_out()

        for bar in (top, bottom):
            previous = self.create_button(
                bar, "‹ Previous", lambda: change_page(page_number - 1, scroll=True, animate=True), compact=True,
            )
            previous.pack(side="left")
            tk.Label(bar, textvariable=status, bg=background, fg=TEXT_GRAY, font=(DEFAULT_FONT, 10)).pack(
                side="left", padx=12,
            )
            following = self.create_button(
                bar, "Next ›", lambda: change_page(page_number + 1, scroll=True, animate=True), compact=True,
            )
            following.pack(side="left")
            controls.append((previous, following))
        change_page(page_number, animate=False)

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
