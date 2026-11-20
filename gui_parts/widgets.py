"""Reusable Tkinter widgets, animated rounded buttons, BBC logo, artwork, and batched grids."""
import math
from time import monotonic
import tkinter as tk
from tkinter import font as tkfont
import xml.etree.ElementTree as ET

from gui_parts.theme import (
    BORDER_LINE,
    CANVA_DIR,
    CARD_BG,
    DARK_BG,
    DEFAULT_FONT,
    GENRE_CIRCLE_COLOURS,
    GENRE_TILE_DETAILS,
    GOLD_STAR,
    INPUT_BG,
    LOGO_TILE_BG,
    LOGO_TILE_FG,
    ORANGE_ACCENT,
    ORANGE_HL,
    PALETTE_SWATCHES,
    PODCASTS_PER_PAGE,
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
            text=text_val,
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
            text=text_val,
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
        """Ease a button's hover state smoothly toward target_step (0..5)."""
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
                button._hover_job = self.after(18, step_frame)

        step_frame()

    def _apply_button_hover_frame(self, button, step):
        """Render a single intermediate frame of a button's hover expansion and tint."""
        face, hover = button._rounded_colours
        width, height = button._hover_size
        base_fg = button._hover_base_fg
        t = step / 5.0
        eased = 1.0 - (1.0 - t) ** 2
        colour = blend_colour(face, hover, eased)
        inset = round(2 * (1.0 - eased))
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
        button._normal_image = self.rounded_button_image(width, height, face, inset=2)
        button.configure(image=button._normal_image)

    def rounded_button_image(self, width, height, colour, inset=2):
        """Rasterize and cache a rounded-rectangle PhotoImage for a button state."""
        key = (width, height, colour, inset)
        if key not in self.button_images:
            canvas_w, canvas_h = width + 4, height + 4
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
        for idx, char in enumerate("BBC"):
            x0 = idx * (tile + gap)
            x1 = x0 + tile
            logo_canvas.create_rectangle(x0, y0, x1, y1, fill=LOGO_TILE_BG, outline="")
            logo_canvas.create_text(
                (x0 + x1) / 2,
                center_y,
                text=char,
                fill=LOGO_TILE_FG,
                font=tile_font,
                anchor="center",
            )
        logo_canvas.create_text(
            tiles_w + word_gap,
            center_y,
            text="SOUNDS",
            fill=ORANGE_ACCENT,
            font=sounds_font,
            anchor="w",
        )
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

    def generate_podcast_cover(
        self, container, pid, title_text, category_text, width_px, height_px,
        corner_radius=0, backdrop=None,
    ):
        """Return a cached procedurally generated cover artwork label for a podcast."""
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
            if len(self.cover_images) > 128:
                self.cover_images.popitem(last=False)
        self.cover_images.move_to_end(key)

        cover = tk.Label(
            container, image=image, compound="center", text=icon,
            font=(DEFAULT_FONT, max(11, min(width_px, height_px) // 6), "bold"),
            bg=bg_colour, fg=TEXT_WHITE, cursor="hand2", bd=0, highlightthickness=0,
        )
        cover.image = image
        return cover

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
        light_col, middle_col, outline_col = GENRE_CIRCLE_COLOURS[idx % len(GENRE_CIRCLE_COLOURS)]
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

    def render_podcast_card(
        self, parent_widget, podcast_data, compact=False,
        show_play_btn=False, show_remove_btn=False, rating_value=None,
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
            details_pane = tk.Frame(card_frame, bg=CARD_BG)
            details_pane.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=12)
            self.create_label(details_pane, title, 12, TEXT_WHITE, "bold").pack(anchor="w")
            self.create_label(details_pane, meta_info, 10, TEXT_GRAY).pack(anchor="w", pady=(5, 0))
            self.create_label(details_pane, self.podcast_average_text(pid), 9, GOLD_STAR).pack(anchor="w")
            self.create_button(
                details_pane, "View details",
                lambda target_id=pid: self.transition_to(lambda: self.show_detail(target_id), "Programme details", direction=1),
                compact=True,
            ).pack(anchor="w", pady=(9, 0))
            if show_play_btn:
                self.create_button(card_frame, "▶  Listen", lambda target_id=pid: self.listen(target_id), primary=True, compact=True).pack(
                    side="right", padx=12
                )
            if show_remove_btn:
                self.create_button(card_frame, "Remove", lambda target_id=pid: self.remove_from_history(target_id), compact=True).pack(
                    side="right", padx=(0, 3)
                )
            return card_frame

        cover = self.generate_podcast_cover(card_frame, pid, title, category, 178, 142)
        cover.pack(fill="x", padx=9, pady=(9, 0))
        details_pane = tk.Frame(card_frame, bg=CARD_BG)
        details_pane.pack(fill="both", expand=True, padx=12, pady=11)
        self.create_label(details_pane, title, 12, TEXT_WHITE, "bold", wraplength=170).pack(anchor="w")
        self.create_label(details_pane, meta_info, 9, TEXT_GRAY).pack(anchor="w", pady=(4, 3))
        self.create_label(details_pane, self.podcast_average_text(pid), 9, GOLD_STAR).pack(anchor="w", pady=(0, 9))
        if rating_value is not None:
            self.create_label(details_pane, "Your rating", 9, TEXT_GRAY).pack(anchor="w")
            self.create_star_rating_bar(details_pane, rating_value, star_size=14, background_col=CARD_BG).pack(
                anchor="w", pady=(0, 9)
            )
        button_strip = tk.Frame(details_pane, bg=CARD_BG)
        button_strip.pack(fill="x", side="bottom")
        self.create_button(
            button_strip, "Details",
            lambda target_id=pid: self.transition_to(lambda: self.show_detail(target_id), "Programme details", direction=1),
            compact=True,
        ).pack(side="left")
        if show_remove_btn:
            self.create_button(
                button_strip, "Remove", lambda target_id=pid: self.remove_from_history(target_id), compact=True
            ).pack(side="left", padx=(6, 0))
        if show_play_btn:
            self.create_button(button_strip, "▶", lambda target_id=pid: self.listen(target_id), primary=True, compact=True).pack(side="right")
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

        def reflow_cards(_event=None):
            available_width = grid_container.winfo_width()
            if available_width <= 1:
                available_width = max(1, self.winfo_width() - 110)
            responsive_columns = max(2, min(columns_count, available_width // 260))
            columns_changed = responsive_columns != current_columns[0]
            if not columns_changed and _event is not None:
                return
            current_columns[0] = responsive_columns
            if columns_changed:
                for col_idx in range(columns_count):
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
            rating_value = podcast[rating_index] if rating_index is not None and len(podcast) > rating_index else None
            card = self.render_podcast_card(
                grid_container, podcast, show_play_btn=show_play,
                show_remove_btn=show_remove, rating_value=rating_value,
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
            render_item(item)
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
            self.after_cancel(self._pending_render_id)
            self._pending_render_id = None
        self._render_queue.clear()
