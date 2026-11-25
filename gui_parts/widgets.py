"""Reusable Tkinter widgets, animated rounded buttons, BBC logo, artwork, and batched grids."""
import ctypes
import math
from pathlib import Path
import re
import struct
import sys
from time import monotonic
import tkinter as tk
from tkinter import font as tkfont
import unicodedata
import xml.etree.ElementTree as ET
import zlib

from gui_parts.i18n import translate
from gui_parts.theme import (
    ACTION_BTN_BG,
    ACTION_BTN_FG,
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
    TITLEBAR_DARK_MODE,
    blend_colour,
    ease_out_elastic,
    rounded_rect_points,
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
        button.bind("<Enter>", lambda _e, btn=button: self.animate_button_hover(btn, 10))
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
        """Ease a button's hover state smoothly toward target_step (0..6) with elastic pop-up."""
        if not button.winfo_exists():
            return
        if target_step > 0 and (
            str(button.cget("state")) == "disabled"
            or getattr(self, "_transition_active", False)
            or self._is_scrolling()
        ):
            return
        button._hover_target = target_step
        if self._is_reduced_motion() or (target_step == 0 and self._is_scrolling()):
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
                button._hover_job = self.after(self._anim_frame_interval(16), step_frame)

        step_frame()

    def _apply_button_hover_frame(self, button, step):
        """Render a single bouncy elastic pop-up hover frame with overshoot, lift, and soft shadow."""
        face, hover = button._rounded_colours
        width, height = button._hover_size
        base_fg = button._hover_base_fg
        t = max(0.0, min(1.0, step / 10.0))
        # Lively damped elastic spring on enter (clear pop-up overshoot + mini-bounce settle); snappy ease-out on leave.
        if getattr(button, "_hover_target", 0) > 0:
            raw_eased = ease_out_elastic(t, damping=3.0, frequency=1.65)
        else:
            raw_eased = 1.0 - (1.0 - t) ** 2.4
        # Quantize colour blend to 5 shared levels while preserving full elastic overshoot for size & lift.
        color_t = max(0.0, min(1.0, round(max(0.0, min(1.0, raw_eased)) * 4.0) / 4.0))
        colour = blend_colour(face, hover, color_t)
        # Resting inset=5 -> overshoots to 0 at spring peak -> rebounds & settles cleanly at inset=2.
        inset = max(0, min(5, round(5.0 - 3.0 * raw_eased)))
        lift = max(0, min(3, round(2.2 * raw_eased)))
        y_shift = getattr(button, "_hover_y_shift", 0)
        border_colour = getattr(button, "_rounded_border", None)
        icon_spec = getattr(button, "_rounded_icon", None)
        image = self.rounded_button_image(
            width, height, colour, inset=inset, y_shift=y_shift, lift=lift,
            border_colour=border_colour, icon_spec=icon_spec,
        )
        button._current_image = image
        config = {"image": image}
        target_fg = getattr(button, "_hover_target_fg", TEXT_WHITE)
        if isinstance(base_fg, str) and base_fg.startswith("#") and len(base_fg) == 7:
            # Keep text high-contrast when swapping between white and black foregrounds on hover.
            if base_fg.lower() != target_fg.lower() and target_fg.lower() == "#000000":
                config["fg"] = target_fg if color_t >= 0.45 else base_fg
            else:
                config["fg"] = blend_colour(base_fg, target_fg, color_t)
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
        base_pad_x, base_pad_y = button._rounded_padding
        pad_scale = max(0.90, min(1.50, getattr(self, "_ui_scale_factor", 1.0)))
        pad_x = round(base_pad_x * pad_scale)
        pad_y = round(base_pad_y * pad_scale)
        height = metrics.metrics("linespace") + pad_y
        text = button.cget("text")
        single_pad = round(12 * pad_scale)
        width = max(height, metrics.measure(text) + (single_pad if len(text) == 1 else pad_x))
        # Optical vertical compensation for Linux/macOS FreeType font metrics (Windows GDI already centers vertically).
        if sys.platform == "win32":
            y_shift = 0
        else:
            has_descender = any(ch in text for ch in "gjpqy,;")
            descent = metrics.metrics("descent")
            y_shift = max(0, min(4, round(descent * (0.25 if has_descender else 0.50))))
        button._hover_size = (width, height)
        button._hover_y_shift = y_shift
        bg_col = str(button.cget("bg")).lower()
        face_l = str(face).lower()
        is_primary = face_l in (ORANGE_ACCENT.lower(), ORANGE_HL.lower())
        is_flat = face_l == bg_col
        if not is_primary and not is_flat:
            border_colour = blend_colour(BORDER_LINE, TEXT_WHITE, 0.14) if TITLEBAR_DARK_MODE == 0 else BORDER_LINE
        else:
            border_colour = None
        button._rounded_border = border_colour
        icon_kind = getattr(button, "_icon_kind", None)
        icon_spec = (icon_kind, button.cget("fg"), metrics.measure(text)) if icon_kind else None
        button._rounded_icon = icon_spec
        button._normal_image = self.rounded_button_image(
            width, height, face, inset=5, y_shift=y_shift, lift=0,
            border_colour=border_colour, icon_spec=icon_spec,
        )
        button.configure(image=button._normal_image)

    @staticmethod
    def _build_aa_pill_png(w, h, left, top, right, bottom, radius, rgb, lift=0, border_rgb=None):
        """Pure-Python signed-distance anti-aliased RGBA PNG rounded pill (zero Pillow dependency)."""
        r, g, b = rgb
        buf = bytearray(w * h * 4)
        # Soft translucent drop shadow underneath the pill when popped out on hover.
        if lift > 0:
            sh_drop = min(3, lift + 1)
            sh_a = 50 if lift == 1 else (75 if lift == 2 else 95)
            sl, sr = left + 1, right - 1
            st, sb = top + sh_drop, min(h, bottom + sh_drop)
            srad = float(min(radius, (sr - sl) / 2.0, (sb - st) / 2.0))
            sh_span = bytes((0, 0, 0, sh_a))
            s_in_l = int(math.ceil(sl + srad))
            s_in_r = int(math.floor(sr - srad))
            for y in range(max(0, st), min(h, sb)):
                dy = (st + srad - 0.5 - y) if y < st + srad else (y - (sb - srad - 0.5) if y >= sb - srad else 0.0)
                row_off = y * w * 4
                if dy <= 0.0:
                    if sr > sl:
                        buf[row_off + sl * 4:row_off + sr * 4] = sh_span * (sr - sl)
                else:
                    if s_in_r > s_in_l:
                        buf[row_off + s_in_l * 4:row_off + s_in_r * 4] = sh_span * (s_in_r - s_in_l)
                    for x in (*range(max(0, sl), min(w, s_in_l)), *range(max(0, s_in_r), min(w, sr))):
                        dx = (sl + srad - 0.5 - x) if x < sl + srad else (x - (sr - srad - 0.5))
                        cov = max(0.0, min(1.0, srad + 0.5 - math.hypot(dx, dy)))
                        if cov > 0.0:
                            buf[row_off + x * 4 + 3] = int(sh_a * cov)

        # Anti-aliased pill body with exact sub-pixel corner coverage and optional 1px border.
        rad = float(radius)
        solid_rgba = bytes((r, g, b, 255))
        border_rgba = bytes((*border_rgb, 255)) if border_rgb is not None else None
        inner_l = int(math.ceil(left + rad))
        inner_r = int(math.floor(right - rad))
        for y in range(max(0, top), min(h, bottom)):
            dy = (top + rad - 0.5 - y) if y < top + rad else (y - (bottom - rad - 0.5) if y >= bottom - rad else 0.0)
            row_off = y * w * 4
            if dy <= 0.0:
                if right > left:
                    if border_rgba is not None and right - left >= 2:
                        buf[row_off + left * 4:row_off + (left + 1) * 4] = border_rgba
                        if right - 1 > left + 1:
                            buf[row_off + (left + 1) * 4:row_off + (right - 1) * 4] = solid_rgba * (right - left - 2)
                        buf[row_off + (right - 1) * 4:row_off + right * 4] = border_rgba
                    else:
                        buf[row_off + left * 4:row_off + right * 4] = solid_rgba * (right - left)
            else:
                if inner_r > inner_l:
                    span_rgba = border_rgba if (border_rgba is not None and (y == top or y == bottom - 1)) else solid_rgba
                    buf[row_off + inner_l * 4:row_off + inner_r * 4] = span_rgba * (inner_r - inner_l)
                for x in (*range(max(0, left), min(w, inner_l)), *range(max(0, inner_r), min(w, right))):
                    dx = (left + rad - 0.5 - x) if x < left + rad else (x - (right - rad - 0.5))
                    edge_dist = rad + 0.5 - math.hypot(dx, dy)
                    cov = max(0.0, min(1.0, edge_dist))
                    if cov > 0.0:
                        if border_rgb is not None:
                            in_cov = max(0.0, min(1.0, edge_dist - 1.0))
                            pr = border_rgb[0] + (r - border_rgb[0]) * in_cov
                            pg = border_rgb[1] + (g - border_rgb[1]) * in_cov
                            pb = border_rgb[2] + (b - border_rgb[2]) * in_cov
                        else:
                            pr, pg, pb = r, g, b
                        idx = row_off + x * 4
                        da = buf[idx + 3] / 255.0
                        oa = cov + da * (1.0 - cov)
                        if oa > 0.0:
                            buf[idx] = round((pr * cov) / oa)
                            buf[idx + 1] = round((pg * cov) / oa)
                            buf[idx + 2] = round((pb * cov) / oa)
                            buf[idx + 3] = round(oa * 255)

        stride = w * 4
        raw = bytearray((stride + 1) * h)
        for y in range(h):
            raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)] = buf[y * stride:(y + 1) * stride]

        def _chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
        return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(bytes(raw), 1)) + _chunk(b"IEND", b"")

    def rounded_button_image(self, width, height, colour, inset=5, y_shift=0, lift=0, border_colour=None, icon_spec=None):
        """Rasterize and cache a smooth anti-aliased rounded-rectangle PhotoImage with optional hover pop-up lift."""
        key = (width, height, colour, inset, y_shift, lift, border_colour, icon_spec)
        if key not in self.button_images:
            # Reserve 6px transparent margin per side so elastic hover overshoot & shadow never shift layout,
            # plus 2*y_shift at the bottom so compound="center" text sits optically centered in the pill.
            margin = 6
            canvas_w = width + margin * 2
            canvas_h = height + margin * 2 + y_shift * 2
            left = inset
            right = canvas_w - inset
            # Expand symmetrically around the text (no vertical pill shift) so text stays dead-center on hover.
            top = inset
            bottom = height + margin * 2 - inset
            pill_w, pill_h = right - left, bottom - top
            radius = min(max(10, round(pill_h * 0.28)), pill_h // 2, pill_w // 2)
            c = str(colour).lstrip("#")
            rgb = (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
            border_rgb = None
            if isinstance(border_colour, str) and border_colour.startswith("#") and len(border_colour) == 7:
                bc = border_colour.lstrip("#")
                border_rgb = (int(bc[0:2], 16), int(bc[2:4], 16), int(bc[4:6], 16))
            image = None
            try:
                import io
                from PIL import Image, ImageDraw
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
                rgba = (*rgb, 255)
                ss = 3
                hi = Image.new("RGBA", (canvas_w * ss, canvas_h * ss), (0, 0, 0, 0))
                draw = ImageDraw.Draw(hi)
                # Subtle translucent drop shadow underneath the pill when popped out on hover.
                if lift > 0:
                    sh_drop = min(3, lift + 1) * ss
                    sh_alpha = 50 if lift == 1 else (75 if lift == 2 else 95)
                    draw.rounded_rectangle(
                        (
                            left * ss + ss,
                            top * ss + sh_drop,
                            right * ss - 1 - ss,
                            min(canvas_h * ss - 1, bottom * ss - 1 + sh_drop),
                        ),
                        radius=radius * ss,
                        fill=(0, 0, 0, sh_alpha),
                    )
                draw.rounded_rectangle(
                    (left * ss, top * ss, right * ss - 1, bottom * ss - 1),
                    radius=radius * ss,
                    fill=rgba,
                    outline=(*border_rgb, 255) if border_rgb is not None else None,
                    width=ss if border_rgb is not None else 0,
                )
                if icon_spec and icon_spec[0] == "cloud":
                    ic_hex = str(icon_spec[1]).lstrip("#")
                    ic_rgba = (
                        (int(ic_hex[0:2], 16), int(ic_hex[2:4], 16), int(ic_hex[4:6], 16), 255)
                        if len(ic_hex) == 6 else (255, 255, 255, 255)
                    )
                    txt_w = icon_spec[2]
                    iw = max(14.0, pill_h * 0.54) * ss
                    ih = iw * 0.64
                    ix0 = max((left + 8) * ss, ((canvas_w - txt_w) / 2.0 - 2.0) * ss)
                    iy0 = ((top + bottom) / 2.0) * ss - ih * 0.52
                    # Classic iCloud-style fluffy cloud: flat rounded base + 3 smooth overlapping domes.
                    draw.rounded_rectangle(
                        (ix0 + iw * 0.04, iy0 + ih * 0.46, ix0 + iw * 0.96, iy0 + ih),
                        radius=ih * 0.27, fill=ic_rgba,
                    )
                    for cx_f, cy_f, r_f in (
                        (0.27, 0.62, 0.27),
                        (0.50, 0.40, 0.36),
                        (0.75, 0.64, 0.24),
                    ):
                        cx_p, cy_p, rp = ix0 + iw * cx_f, iy0 + ih * cy_f, iw * r_f
                        draw.ellipse((cx_p - rp, cy_p - rp, cx_p + rp, cy_p + rp), fill=ic_rgba)
                aa = hi.resize((canvas_w, canvas_h), resample)
                buf = io.BytesIO()
                aa.save(buf, format="PNG", compress_level=1)
                image = tk.PhotoImage(master=self, data=buf.getvalue())
            except Exception:
                image = None
            if image is None:
                # Zero-dependency anti-aliased RGBA PNG fallback so Windows without Pillow matches Linux exactly.
                try:
                    png_bytes = self._build_aa_pill_png(
                        canvas_w, canvas_h, left, top, right, bottom, radius, rgb,
                        lift=lift, border_rgb=border_rgb,
                    )
                    image = tk.PhotoImage(master=self, data=png_bytes)
                except Exception:
                    image = None
            if image is None:
                image = tk.PhotoImage(master=self, width=canvas_w, height=canvas_h)
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
        # On Linux/macOS (FreeType/Xft), shift uppercase glyphs down by ~half the descent so cap-height
        # sits optically centered; Windows GDI already balances internal leading with descent.
        tile_y_nudge = 0.0 if sys.platform == "win32" else tile_metrics.metrics("descent") * 0.45
        sounds_y_nudge = 0.0 if sys.platform == "win32" else sounds_metrics.metrics("descent") * 0.45

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

    PREMADE_AVATARS = (
        ("default", "Classic"),
        ("vinyl", "Vinyl"),
        ("headphones", "Studio"),
        ("mic", "Host"),
        ("waves", "Waves"),
        ("owl", "Night Owl"),
        ("bot", "Bot"),
        ("sunset", "Sunset"),
    )

    def draw_profile_avatar(self, avatar, size, avatar_key="default", *, selected=False):
        """Paint one of the premade BBC Sounds circular profile pictures onto an existing Canvas."""
        avatar.delete("all")
        c = size / 2.0
        m = size * 0.06
        r = c - m
        ring_col = ORANGE_ACCENT if selected else "#e7e8ea"
        ring_w = max(2, round(size * (0.045 if selected else 0.026)))
        key = avatar_key if any(k == avatar_key for k, _ in self.PREMADE_AVATARS) else "default"

        bg_map = {
            "default": "#55585e",
            "vinyl": "#181a20",
            "headphones": "#1e2a4a",
            "mic": "#4f1d2e",
            "waves": ORANGE_ACCENT,
            "owl": "#262147",
            "bot": "#173c47",
            "sunset": "#2a2042",
        }
        bg = bg_map[key]
        avatar.create_oval(m, m, size - m, size - m, fill=bg, outline=ring_col, width=ring_w)

        if key == "default":
            hr = size * 0.16
            avatar.create_oval(c - hr, size * 0.38 - hr, c + hr, size * 0.38 + hr, fill="#f4f4f5", outline="")
            avatar.create_oval(size * 0.23, size * 0.57, size * 0.77, size * 0.88, fill="#f4f4f5", outline="")
            avatar.create_rectangle(size * 0.18, size * 0.79, size * 0.82, size * 0.92, fill=bg, outline="")
            avatar.create_oval(m, m, size - m, size - m, fill="", outline=ring_col, width=ring_w)
        elif key == "vinyl":
            for frac, stroke in ((0.76, "#2c303a"), (0.60, "#252832"), (0.46, "#313540")):
                gr = r * frac
                avatar.create_oval(c - gr, c - gr, c + gr, c + gr, fill="", outline=stroke, width=1)
            lr = r * 0.38
            avatar.create_oval(c - lr, c - lr, c + lr, c + lr, fill=ORANGE_ACCENT, outline="#ffffff", width=max(1, round(size * 0.02)))
            sp = max(2.5, r * 0.11)
            avatar.create_oval(c - sp, c - sp, c + sp, c + sp, fill="#111215", outline="#ffffff", width=1)
        elif key == "headphones":
            arc_r = r * 0.56
            avatar.create_arc(
                c - arc_r, c - arc_r * 1.05, c + arc_r, c + arc_r * 0.95,
                start=0, extent=180, style="arc", outline="#f4f4f5", width=max(2, round(size * 0.065)),
            )
            ew, eh = size * 0.13, size * 0.24
            avatar.create_rectangle(c - arc_r - ew * 0.45, c - eh * 0.1, c - arc_r + ew * 0.55, c + eh * 0.9, fill=ORANGE_ACCENT, outline="")
            avatar.create_rectangle(c + arc_r - ew * 0.55, c - eh * 0.1, c + arc_r + ew * 0.45, c + eh * 0.9, fill=ORANGE_ACCENT, outline="")
        elif key == "mic":
            mw, mh = size * 0.16, size * 0.27
            avatar.create_oval(c - mw, c - mh * 1.1, c + mw, c + mh * 0.55, fill="#f4f4f5", outline="")
            for dy in (-0.55, -0.25, 0.05):
                avatar.create_line(c - mw * 0.65, c + mh * dy, c + mw * 0.65, c + mh * dy, fill="#4f1d2e", width=max(1, round(size * 0.02)))
            sr = size * 0.24
            avatar.create_arc(c - sr, c - sr * 0.65, c + sr, c + sr * 0.95, start=195, extent=150, style="arc", outline=ORANGE_ACCENT, width=max(2, round(size * 0.045)))
            avatar.create_line(c, c + sr * 0.95, c, c + sr * 1.32, fill="#f4f4f5", width=max(2, round(size * 0.04)))
            avatar.create_line(c - sr * 0.5, c + sr * 1.32, c + sr * 0.5, c + sr * 1.32, fill="#f4f4f5", width=max(2, round(size * 0.04)), capstyle="round")
        elif key == "waves":
            heights = (0.22, 0.46, 0.64, 0.42, 0.24)
            bw = max(2, round(size * 0.07))
            gap = size * 0.12
            start_x = c - gap * 2
            for idx, hf in enumerate(heights):
                bx = start_x + idx * gap
                hh = r * hf * 0.85
                avatar.create_line(bx, c - hh, bx, c + hh, fill="#ffffff", width=bw, capstyle="round")
        elif key == "owl":
            # Minimalist geometric night owl.
            avatar.create_polygon(c - r * 0.42, c - r * 0.56, c - r * 0.15, c - r * 0.34, c - r * 0.44, c - r * 0.16, fill="#d8dcf0", outline="")
            avatar.create_polygon(c + r * 0.42, c - r * 0.56, c + r * 0.15, c - r * 0.34, c + r * 0.44, c - r * 0.16, fill="#d8dcf0", outline="")
            avatar.create_oval(c - r * 0.48, c - r * 0.44, c + r * 0.48, c + r * 0.56, fill="#d8dcf0", outline="")
            er, pr = r * 0.19, r * 0.09
            for sx in (-1, 1):
                ex = c + sx * r * 0.20
                ey = c - r * 0.04
                avatar.create_oval(ex - er, ey - er, ex + er, ey + er, fill="#ffffff", outline="#262147", width=max(1, round(size * 0.02)))
                avatar.create_oval(ex - pr, ey - pr, ex + pr, ey + pr, fill="#1a1830", outline="")
            avatar.create_polygon(c - r * 0.09, c + r * 0.10, c + r * 0.09, c + r * 0.10, c, c + r * 0.27, fill=ORANGE_ACCENT, outline="")
        elif key == "bot":
            avatar.create_line(c, c - r * 0.62, c, c - r * 0.36, fill="#a8e4f0", width=max(2, round(size * 0.04)))
            ar = max(2.5, r * 0.10)
            avatar.create_oval(c - ar, c - r * 0.72, c + ar, c - r * 0.72 + ar * 2, fill=ORANGE_ACCENT, outline="")
            avatar.create_rectangle(c - r * 0.48, c - r * 0.36, c + r * 0.48, c + r * 0.40, fill="#e6f4f7", outline="")
            er = max(2.5, r * 0.12)
            for sx in (-1, 1):
                ex = c + sx * r * 0.20
                avatar.create_oval(ex - er, c - r * 0.14 - er, ex + er, c - r * 0.14 + er, fill=ORANGE_ACCENT, outline="")
            avatar.create_line(c - r * 0.22, c + r * 0.16, c + r * 0.22, c + r * 0.16, fill="#173c47", width=max(2, round(size * 0.045)), capstyle="round")
        elif key == "sunset":
            sr = r * 0.36
            avatar.create_oval(c - sr, c - r * 0.44, c + sr, c - r * 0.44 + sr * 2, fill="#ffba42", outline="")
            avatar.create_arc(m + 2, m + 2, size - m - 2, size - m - 2, start=185, extent=170, fill="#d94e34", outline="")
            avatar.create_arc(m + 2, m + 2, size - m - 2, size - m - 2, start=205, extent=130, fill="#1b2642", outline="")
            avatar.create_line(c - r * 0.42, c + r * 0.26, c + r * 0.42, c + r * 0.26, fill="#ffcf70", width=max(1, round(size * 0.03)), capstyle="round")
            avatar.create_line(c - r * 0.26, c + r * 0.42, c + r * 0.26, c + r * 0.42, fill="#ffcf70", width=max(1, round(size * 0.025)), capstyle="round")
            avatar.create_oval(m, m, size - m, size - m, fill="", outline=ring_col, width=ring_w)

    def create_default_profile_avatar(self, container, size=112, avatar_key="default", *, selected=False):
        """Create a Canvas showing the listener's chosen premade circular profile avatar."""
        avatar = tk.Canvas(
            container, width=size, height=size, bg=container.cget("bg"),
            highlightthickness=0,
        )
        self.draw_profile_avatar(avatar, size, avatar_key=avatar_key, selected=selected)
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
        base_inset = 5
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

            t = cur / 10.0
            raw_eased = ease_out_elastic(t, damping=3.0, frequency=1.65) if tgt > 0 else 1.0 - (1.0 - t) ** 2.4
            color_t = max(0.0, min(1.0, raw_eased))
            inset = max(0, min(base_inset, round(base_inset - 3.0 * raw_eased)))
            cur_bg = blend_colour(rest_bg, hover_bg, color_t)
            cur_bd = blend_colour(BORDER_LINE, ORANGE_ACCENT, color_t)
            cur_title = blend_colour(TEXT_WHITE, ORANGE_HL, color_t * 0.55)

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
                hover_state["job"] = self.after(self._anim_frame_interval(16), apply_frame)

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
                    hover_state["step"] = max(0, target - 1) if target > hover_state["step"] else min(10, target + 1)
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
            set_hover_target(10)

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
        rating_index=None, show_end=True, ratings_mode=False, insert_anim=None,
        evaporate_anim=None,
    ):
        """Render a responsive single-Canvas grid of podcast cards (zero child HWNDs for tear-free scrolling)."""
        if not items_list:
            self.render_empty_message(parent_widget, "No programmes to show yet", "Try another search, or explore all programmes.")
            return
        displayed_items = items_list[:max_count]
        if not single_row and not ratings_mode and len(displayed_items) > PODCASTS_PER_PAGE:
            first_insert = [insert_anim]
            first_evap = [evaporate_anim]
            def _render_paginated(parent, rows, last):
                spec = first_insert[0]
                first_insert[0] = None
                espec = first_evap[0]
                first_evap[0] = None
                self.render_podcast_grid(
                    parent, rows, columns_count, show_play=show_play,
                    show_remove=show_remove, max_count=len(rows), rating_index=rating_index,
                    show_end=show_end and last and len(displayed_items) == len(items_list),
                    insert_anim=spec,
                    evaporate_anim=espec,
                )
            self.paginate_podcasts(parent_widget, displayed_items, _render_paginated)
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

        rounded_pts = rounded_rect_points

        def _grid_fonts():
            # _ui_scale_factor already combines responsive window scaling and _text_scale.
            sf = max(0.75, min(1.75, getattr(self, "_ui_scale_factor", 1.0)))
            return (
                sf,
                self._get_cached_font((DEFAULT_FONT, max(9, round(11 * sf)), "bold")),
                self._get_cached_font((DEFAULT_FONT, max(8, round(9 * sf)))),
                self._get_cached_font((DEFAULT_FONT, max(11, round(13 * sf)))),
                self._get_cached_font((DEFAULT_FONT, max(8, round(9 * sf)), "bold")),
                self._get_cached_font((DEFAULT_FONT, max(12, round(15 * sf)), "bold")),
            )

        f_scale, title_font, meta_font, star_font, btn_font, end_font = _grid_fonts()

        details_txt = translate("Details")
        remove_txt = translate("Remove")
        change_txt = translate("Change rating")
        your_rating_txt = translate("Your rating")
        no_more_txt = translate("No more results")
        hover_bg_col = blend_colour(CARD_BG, SECONDARY_HOVER_BG, 0.55)
        sec_btn_bg = ACTION_BTN_BG
        sec_btn_hover = SECONDARY_HOVER_BG
        sec_btn_outline = blend_colour(BORDER_LINE, TEXT_WHITE, 0.14) if TITLEBAR_DARK_MODE == 0 else BORDER_LINE

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
            nonlocal f_scale, title_font, meta_font, star_font, btn_font, end_font
            if not grid_canvas.winfo_exists():
                return
            if avail_w <= 1:
                avail_w = max(320, self.winfo_width() - 110)
            f_scale, title_font, meta_font, star_font, btn_font, end_font = _grid_fonts()
            size_boost = max(1.0, f_scale)
            base_card_w = (
                min(355, max(280, round(280 + max(0, avail_w - 1100) * 0.025)))
                if ratings_mode else
                min(330, max(255, round(255 + max(0, avail_w - 1100) * 0.025)))
            )
            # Widen cards proportionally when text is scaled up so titles and buttons have breathing room.
            target_card_w = round(base_card_w * (1.0 + (size_boost - 1.0) * 0.60))
            cols = max(2, min(14 if ratings_mode else 16, avail_w // target_card_w))
            gap = round(10 * min(1.35, size_boost))
            card_w = max(190, (avail_w - gap * (cols - 1)) // cols)
            pad_x = round(12 * min(1.35, size_boost))
            cover_sz = max(140, card_w - pad_x * 2 + 4)

            title_lh = title_font.metrics("linespace")
            meta_lh = meta_font.metrics("linespace")
            star_lh = star_font.metrics("linespace")
            btn_pad_y = round(12 * size_boost)
            btn_h = max(round(28 * max(0.95, f_scale)), btn_font.metrics("linespace") + btn_pad_y)
            has_rating_row = ratings_mode or (rating_index is not None)
            rating_block_h = (meta_lh + star_lh + round(14 * size_boost)) if has_rating_row else 0
            text_area_h = (
                title_lh * 2
                + meta_lh * 2
                + rating_block_h
                + btn_h
                + round(34 * size_boost)
            )
            card_h = cover_sz + round(18 * size_boost) + text_area_h

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
                body_tag = f"card_body_{idx}"
                all_tag = f"card_all_{idx}"
                body_tags = (body_tag, all_tag)

                bg_item = grid_canvas.create_polygon(
                    rounded_pts(x0 + 4, y0 + 4, x1 - 4, y1 - 4, 12),
                    smooth=True, fill=CARD_BG, outline=BORDER_LINE, width=1,
                    tags=all_tag,
                )

                cov_x = x0 + (card_w - cover_sz) // 2
                cov_y = y0 + 10
                photo, icon, _ = self._get_cover_photo(
                    grid_canvas, pid, title, category, cover_sz, cover_sz,
                    corner_radius=8, backdrop=CARD_BG,
                )
                grid_canvas._photo_refs.append(photo)
                grid_canvas.create_image(cov_x, cov_y, image=photo, anchor="nw", tags=body_tags)
                if icon is not None:
                    grid_canvas.create_text(
                        cov_x + cover_sz // 2, cov_y + cover_sz // 2,
                        text=icon, fill=TEXT_WHITE,
                        font=self._get_cached_font((DEFAULT_FONT, max(12, cover_sz // 6), "bold")),
                        tags=body_tags,
                    )

                tx = x0 + pad_x
                ty = cov_y + cover_sz + round(11 * size_boost)
                max_tw = max(120, card_w - pad_x * 2)
                # Keep title cleanly within 2 lines so card heights stay uniform.
                disp_title = title if len(title) <= 44 else (title[:42].rstrip() + "…")
                title_item = grid_canvas.create_text(
                    tx, ty, text=disp_title, fill=TEXT_WHITE, font=title_font,
                    anchor="nw", width=max_tw, tags=body_tags,
                )
                tb = grid_canvas.bbox(title_item)
                next_y = (tb[3] if tb else ty + title_lh) + round(5 * size_boost)
                meta_item = grid_canvas.create_text(
                    tx, next_y, text=meta_info, fill=TEXT_GRAY, font=meta_font,
                    anchor="nw", width=max_tw, tags=body_tags,
                )
                mb = grid_canvas.bbox(meta_item)
                next_y = (mb[3] if mb else next_y + meta_lh) + round(4 * size_boost)
                avg_item = grid_canvas.create_text(
                    tx, next_y, text=avg_txt, fill=GOLD_STAR, font=meta_font,
                    anchor="nw", width=max_tw, tags=body_tags,
                )
                ab = grid_canvas.bbox(avg_item)
                next_y = (ab[3] if ab else next_y + meta_lh) + round(5 * size_boost)

                star_items = []
                if r_val is not None:
                    yr_item = grid_canvas.create_text(
                        tx, next_y, text=your_rating_txt, fill=TEXT_GRAY, font=meta_font,
                        anchor="nw", tags=body_tags,
                    )
                    yb = grid_canvas.bbox(yr_item)
                    next_y = (yb[3] if yb else next_y + meta_lh) + round(2 * size_boost)
                    try:
                        filled = max(0, min(5, int(round(float(r_val)))))
                    except (TypeError, ValueError):
                        filled = 0
                    star_step = max(16, round(star_font.measure("★") * 1.18))
                    for s_i in range(5):
                        s_id = grid_canvas.create_text(
                            tx + s_i * star_step, next_y,
                            text="★", fill=GOLD_STAR if s_i < filled else STAR_EMPTY,
                            font=star_font, anchor="nw", tags=body_tags,
                        )
                        star_items.append(s_id)

                card_proxy = _CanvasRectProxy(grid_canvas, x0, y0, card_w, card_h)
                cover_proxy = _CanvasRectProxy(grid_canvas, cov_x, cov_y, cover_sz, cover_sz)
                title_proxy = _CanvasRectProxy(grid_canvas, tx, ty, max_tw, max(24, title_lh))
                grid_canvas._canvas_card_rects[str(pid)] = (card_proxy, cover_proxy, pid, title, category, cover_sz)

                # Bottom pill buttons (measured from font metrics so text never clips or overlaps).
                by1 = y1 - round(11 * size_boost)
                by0 = by1 - btn_h
                btn_gap = round(6 * size_boost)
                btn_px = round(20 * size_boost)
                btn_radius = min(max(8, round(btn_h * 0.28)), btn_h // 2)
                buttons = []

                def add_btn(bx0, bx1, label_s, primary, action):
                    base_c = ORANGE_ACCENT if primary else sec_btn_bg
                    hov_c = ORANGE_HL if primary else sec_btn_hover
                    fg_c = PRIMARY_BTN_FG if primary else ACTION_BTN_FG
                    poly = grid_canvas.create_polygon(
                        rounded_pts(bx0, by0, bx1, by1, btn_radius),
                        smooth=True, fill=base_c,
                        outline="" if primary else sec_btn_outline,
                        width=0 if primary else 1,
                        tags=body_tags,
                    )
                    btn_y_nudge = 0.0 if sys.platform == "win32" else btn_font.metrics("descent") * 0.30
                    lbl = grid_canvas.create_text(
                        (bx0 + bx1) / 2.0, (by0 + by1) / 2.0 + btn_y_nudge,
                        text=label_s, fill=fg_c, font=btn_font, tags=body_tags,
                    )
                    buttons.append({
                        "rect": (bx0, by0, bx1, by1),
                        "poly": poly,
                        "lbl": lbl,
                        "base": base_c,
                        "hover": hov_c,
                        "action": action,
                        "step": 0,
                        "target": 0,
                    })

                right_edge = x1 - pad_x
                if ratings_mode:
                    ch_w = max(84, btn_font.measure(change_txt) + btn_px)
                    rm_w = max(62, btn_font.measure(remove_txt) + btn_px)
                    avail_btns = max(80, right_edge - tx - btn_gap)
                    if ch_w + rm_w > avail_btns:
                        ratio = avail_btns / float(ch_w + rm_w)
                        ch_w = max(54, int(ch_w * ratio))
                        rm_w = max(44, avail_btns - ch_w)
                    add_btn(
                        tx, tx + ch_w, change_txt, False,
                        lambda tid=pid: self.rate_programme(tid, self.show_ratings),
                    )
                    add_btn(
                        right_edge - rm_w, right_edge, remove_txt, False,
                        lambda tid=pid: self.remove_rating(
                            tid, evaporate=lambda done, t_pid=tid: evaporate_card(t_pid, done),
                        ),
                    )
                else:
                    det_w = max(60, btn_font.measure(details_txt) + btn_px)
                    rm_w = max(60, btn_font.measure(remove_txt) + btn_px) if show_remove else 0
                    pw = max(36, round(38 * max(0.95, f_scale))) if show_play else 0
                    # Clamp left-side buttons so they never collide with the right-aligned Play button.
                    left_budget = right_edge - tx - (pw + btn_gap if show_play else 0)
                    if show_remove:
                        need_left = det_w + btn_gap + rm_w
                        if need_left > left_budget and left_budget > 80:
                            ratio = (left_budget - btn_gap) / float(det_w + rm_w)
                            det_w = max(46, int(det_w * ratio))
                            rm_w = max(44, left_budget - btn_gap - det_w)
                    elif det_w > left_budget and left_budget > 46:
                        det_w = left_budget
                    add_btn(
                        tx, tx + det_w, details_txt, False,
                        lambda tid=pid, t=title, c=category, cp=card_proxy, cvp=cover_proxy, tp=title_proxy: (
                            self.open_podcast_detail(tid, t, c, source_card=cp, source_cover=cvp, source_title=tp)
                        ),
                    )
                    if show_remove:
                        rx0 = tx + det_w + btn_gap
                        add_btn(
                            rx0, rx0 + rm_w, remove_txt, False,
                            lambda tid=pid: self.remove_from_history(
                                tid, evaporate=lambda done, t_pid=tid: evaporate_card(t_pid, done),
                            ),
                        )
                    if show_play:
                        px0 = right_edge - pw
                        play_proxy = _CanvasRectProxy(grid_canvas, px0, by0, pw, btn_h)
                        add_btn(
                            px0, right_edge, "▶", True,
                            lambda pp=play_proxy, tid=pid, t=title, c=category, cvp=cover_proxy: (
                                self.play_podcast_to_mini_bar(pp, tid, t, c, cover_widget=cvp)
                            ),
                        )

                genre_info = GENRE_TILE_DETAILS.get(category)
                accent_col = genre_info[0] if genre_info else ORANGE_ACCENT
                state["cards"].append({
                    "pid": pid,
                    "rect": (x0, y0, x1, y1),
                    "cover_rect": (cov_x, cov_y, cover_sz),
                    "proxies": (card_proxy, cover_proxy, title_proxy),
                    "photo": photo,
                    "bg_item": bg_item,
                    "title_item": title_item,
                    "body_tag": body_tag,
                    "all_tag": all_tag,
                    "accent_col": accent_col,
                    "star_items": star_items,
                    "buttons": buttons,
                    "step": 0,
                    "target": 0,
                    "open_action": (
                        lambda tid=pid, t=title, c=category, cp=card_proxy, cvp=cover_proxy, tp=title_proxy:
                        self.open_podcast_detail(tid, t, c, source_card=cp, source_cover=cvp, source_title=tp)
                    ),
                })

            state["cols"] = cols
            state["card_h"] = card_h
            state["gap"] = gap
            state["end_item"] = None
            final_row, used_cols = divmod(total_items, cols)
            if show_end and total_items == len(items_list) and used_cols and (not single_row or final_row == 0):
                ex0 = used_cols * (card_w + gap)
                ex1 = cols * card_w + (cols - 1) * gap
                ey = final_row * (card_h + gap) + card_h // 2
                state["end_item"] = grid_canvas.create_text(
                    (ex0 + ex1) / 2.0, ey, text=no_more_txt, fill="#777b83", font=end_font,
                )

        hover_loop = {"job": None, "evap_job": None}

        def cancel_hover_loop(_event=None):
            for jkey in ("job", "evap_job"):
                if hover_loop[jkey] is not None:
                    try:
                        self.after_cancel(hover_loop[jkey])
                    except tk.TclError:
                        pass
                    hover_loop[jkey] = None

        grid_canvas.bind("<Destroy>", cancel_hover_loop, add="+")

        def evaporate_card(target_pid, on_complete, *, force_callback=False):
            """Dissolve a removed card into ~110 cover-sampled rising particles (1 batched Tcl eval/frame),
            slide all following cards smoothly into place, and update in-place with zero page flicker."""
            card_idx = next(
                (i for i, item in enumerate(state["cards"]) if str(item.get("pid")) == str(target_pid)),
                -1,
            )
            if (
                self._is_reduced_motion()
                or not grid_canvas.winfo_exists()
                or card_idx < 0
                or card_idx >= len(state["cards"])
            ):
                on_complete()
                return

            cancel_hover_loop()
            self._transition_active = True
            state["hovered"] = None
            state["hovered_btn"] = None
            c = state["cards"][card_idx]
            x0, y0, x1, y1 = c["rect"]
            cov_x, cov_y, cov_sz = c["cover_rect"]
            photo_ref = c["photo"]
            bg_item = c["bg_item"]
            grid_canvas.delete(c["body_tag"])
            if state.get("end_item") is not None:
                try:
                    grid_canvas.delete(state["end_item"])
                except tk.TclError:
                    pass
                state["end_item"] = None

            import random as _random
            rng = _random.Random(card_idx * 131 + int(x0 + y0))
            cw_card = max(20.0, x1 - x0)
            ch_card = max(20.0, y1 - y0)

            # Sample real RGB pixels from the podcast's actual cover art so particles match the artwork.
            cover_samples = []
            try:
                pw, ph = photo_ref.width(), photo_ref.height()
                if pw > 8 and ph > 8:
                    for gy in range(5):
                        sy = min(ph - 1, max(1, int((gy + 0.5) * ph / 5.0)))
                        for gx in range(5):
                            sx = min(pw - 1, max(1, int((gx + 0.5) * pw / 5.0)))
                            val = photo_ref.get(sx, sy)
                            if isinstance(val, tuple):
                                r_c, g_c, b_c = val[:3]
                            else:
                                r_c, g_c, b_c = (int(v) for v in str(val).split()[:3])
                            cover_samples.append(f"#{r_c:02x}{g_c:02x}{b_c:02x}")
            except Exception:
                cover_samples = []

            body_palette = (
                blend_colour(CARD_BG, TEXT_WHITE, 0.28),
                blend_colour(CARD_BG, TEXT_WHITE, 0.16),
                TEXT_GRAY,
                c.get("accent_col", ORANGE_ACCENT),
                ORANGE_ACCENT,
                GOLD_STAR,
            )
            if not cover_samples:
                cover_samples = list(body_palette)

            # Precompute a 10-step colour fade ramp per unique hex colour for zero blend math in the frame loop.
            fade_ramps = {}
            def get_ramp(hex_c):
                ramp = fade_ramps.get(hex_c)
                if ramp is None:
                    ramp = tuple(blend_colour(hex_c, bg_col, i / 9.0) for i in range(10))
                    fade_ramps[hex_c] = ramp
                return ramp

            # Spawn ~110 particles: dense fine dust + soft vapour wisps with a natural top-to-bottom / wind-sweep liftoff.
            particles = []
            # 1) ~72 particles sampled across the cover artwork area.
            for idx_p in range(72):
                fx = rng.random()
                fy = rng.random()
                px = cov_x + 4.0 + fx * max(8.0, cov_sz - 8.0)
                py = cov_y + 4.0 + fy * max(8.0, cov_sz - 8.0)
                col = cover_samples[min(len(cover_samples) - 1, int(fy * 5) * 5 + int(fx * 5))] if len(cover_samples) == 25 else rng.choice(cover_samples)
                # Fine specks + soft larger vapour puffs.
                rad = rng.uniform(1.6, 3.2) if (idx_p % 3) else rng.uniform(3.4, 6.2)
                # Natural upward buoyancy + subtle rightward breeze + organic turbulence.
                vx = rng.uniform(4.0, 38.0) + rng.uniform(-14.0, 14.0)
                vy = rng.uniform(-125.0, -45.0)
                phase = rng.uniform(0.0, math.tau)
                freq = rng.uniform(5.0, 9.5)
                amp = rng.uniform(3.0, 9.0)
                # Top-right corners evaporate slightly first, sweeping organically across the card.
                delay = max(0.0, min(0.32, (fy * 0.16) + ((1.0 - fx) * 0.10) + rng.uniform(0.0, 0.08)))
                oid = grid_canvas.create_oval(
                    px - rad, py - rad, px + rad, py + rad,
                    fill=col, outline="", tags="evap_particle",
                )
                particles.append([oid, px, py, rad, get_ramp(col), vx, vy, phase, freq, amp, delay, 0])

            # 2) ~38 particles across the lower text/button body of the card.
            body_top = cov_y + cov_sz
            body_h = max(20.0, y1 - body_top - 6.0)
            for idx_p in range(38):
                fx = rng.random()
                fy = rng.random()
                px = x0 + 8.0 + fx * max(10.0, cw_card - 16.0)
                py = body_top + fy * body_h
                col = rng.choice(body_palette)
                rad = rng.uniform(1.6, 3.0) if (idx_p % 3) else rng.uniform(3.2, 5.6)
                vx = rng.uniform(4.0, 34.0) + rng.uniform(-12.0, 12.0)
                vy = rng.uniform(-110.0, -38.0)
                phase = rng.uniform(0.0, math.tau)
                freq = rng.uniform(5.0, 9.0)
                amp = rng.uniform(2.5, 8.0)
                delay = max(0.0, min(0.36, 0.12 + fy * 0.14 + rng.uniform(0.0, 0.08)))
                oid = grid_canvas.create_oval(
                    px - rad, py - rad, px + rad, py + rad,
                    fill=col, outline="", tags="evap_particle",
                )
                particles.append([oid, px, py, rad, get_ramp(col), vx, vy, phase, freq, amp, delay, 0])

            # Prepare seamless reflow targets: every card after card_idx slides into the previous card's slot.
            reflow_cards = []
            for k in range(card_idx + 1, len(state["cards"])):
                src_r = state["cards"][k]["rect"]
                dst_r = state["cards"][k - 1]["rect"]
                reflow_cards.append([
                    state["cards"][k]["all_tag"],
                    float(dst_r[0] - src_r[0]),
                    float(dst_r[1] - src_r[1]),
                    0.0,  # applied dx
                    0.0,  # applied dy
                ])

            canvas_path = str(grid_canvas)
            tk_eval = grid_canvas.tk.eval
            sin = math.sin
            evap_dur = 0.780
            reflow_start = 0.400  # Start sliding the next cards over while the mist gently dissipates.
            reflow_dur = 0.440
            total_dur = max(evap_dur, reflow_start + reflow_dur) if reflow_cards else evap_dur
            evap_st = {"elapsed": 0.0, "last_t": None, "bg_gone": False}

            def finish_evap():
                hover_loop["evap_job"] = None
                if not grid_canvas.winfo_exists():
                    self._transition_active = False
                    return
                try:
                    grid_canvas.delete("evap_particle")
                    if not evap_st["bg_gone"]:
                        grid_canvas.delete(bg_item)
                    # Snap any sub-pixel remainder so every reflowed card lands pixel-exact in its new slot.
                    for rc in reflow_cards:
                        tag, tot_dx, tot_dy, cur_dx, cur_dy = rc
                        rem_x = tot_dx - cur_dx
                        rem_y = tot_dy - cur_dy
                        if abs(rem_x) > 0.01 or abs(rem_y) > 0.01:
                            grid_canvas.move(tag, rem_x, rem_y)
                except tk.TclError:
                    pass

                # Update the grid in-place (zero page rebuild, zero flicker) whenever cards remain on this page.
                can_update_in_place = (not force_callback) and len(state["cards"]) > 1 and show_end
                if can_update_in_place:
                    # Shift geometry metadata of every card after card_idx to its new slot.
                    for k in range(len(state["cards"]) - 1, card_idx, -1):
                        cur_c = state["cards"][k]
                        prev_c = state["cards"][k - 1]
                        dx = prev_c["rect"][0] - cur_c["rect"][0]
                        dy = prev_c["rect"][1] - cur_c["rect"][1]
                        cur_c["rect"] = prev_c["rect"]
                        cx, cy, csz = cur_c["cover_rect"]
                        cur_c["cover_rect"] = (cx + dx, cy + dy, csz)
                        for b in cur_c["buttons"]:
                            bx0, by0, bx1, by1 = b["rect"]
                            b["rect"] = (bx0 + dx, by0 + dy, bx1 + dx, by1 + dy)
                        for proxy in cur_c.get("proxies", ()):
                            proxy._x += dx
                            proxy._y += dy
                    removed = state["cards"].pop(card_idx)
                    grid_canvas._canvas_card_rects.pop(str(removed.get("pid")), None)
                    for ei, entry in enumerate(card_entries):
                        if str(entry[0]) == str(target_pid):
                            card_entries.pop(ei)
                            break
                    cols_n = max(1, state.get("cols", 4))
                    ch_n = state.get("card_h", 320)
                    gap_n = state.get("gap", 10)
                    rem_count = len(state["cards"])
                    new_rows = max(1, math.ceil(rem_count / cols_n))
                    grid_canvas.configure(height=new_rows * ch_n + max(0, new_rows - 1) * gap_n + 4)
                    updater = getattr(self, "_active_count_updater", None)
                    if updater is not None:
                        try:
                            updater(-1)
                        except tk.TclError:
                            pass
                    self._transition_active = False
                    return

                self._transition_active = False
                on_complete()

            def step_evap():
                hover_loop["evap_job"] = None
                if not grid_canvas.winfo_exists():
                    self._transition_active = False
                    return
                t0 = monotonic()
                dt = 0.016 if evap_st["last_t"] is None else max(0.004, min(0.042, t0 - evap_st["last_t"]))
                evap_st["last_t"] = t0
                evap_st["elapsed"] = min(total_dur, evap_st["elapsed"] + dt)
                el = evap_st["elapsed"]
                p = min(1.0, el / evap_dur)

                cmds = []
                append = cmds.append

                # Dissolve the card silhouette quickly over the first 28% as particles peel off.
                if not evap_st["bg_gone"]:
                    if p >= 0.28:
                        append(f"{canvas_path} delete {bg_item}")
                        evap_st["bg_gone"] = True
                    else:
                        bp = p / 0.28
                        shrink = 4.0 + 16.0 * bp
                        lift_y = -14.0 * bp
                        pts = " ".join(
                            f"{v:.1f}"
                            for v in rounded_pts(x0 + shrink, y0 + shrink + lift_y, x1 - shrink, y1 - shrink + lift_y, 12)
                        )
                        append(f"{canvas_path} coords {bg_item} {pts}")
                        append(
                            f"{canvas_path} itemconfigure {bg_item} "
                            f"-fill {blend_colour(CARD_BG, bg_col, bp)} "
                            f"-outline {blend_colour(ORANGE_ACCENT, bg_col, bp)}"
                        )

                # Update all ~110 particles in one batched Tcl script.
                for part in particles:
                    oid, px, py, rad, ramp, vx, vy, phase, freq, amp, delay, last_ci = part
                    if last_ci == -1:
                        continue
                    local_p = (p - delay) / max(0.18, 1.0 - delay)
                    if local_p <= 0.0:
                        continue
                    if local_p >= 1.0:
                        append(f"{canvas_path} itemconfigure {oid} -state hidden")
                        part[11] = -1
                        continue
                    # Accelerate gently upward like warm vapour while drifting in a soft breeze.
                    ease_y = local_p ** 1.35
                    nx = px + vx * (local_p ** 1.15) + sin(phase + local_p * freq) * amp * local_p
                    ny = py + vy * ease_y
                    nr = max(0.5, rad * (1.0 - local_p * 0.88))
                    append(f"{canvas_path} coords {oid} {nx - nr:.1f} {ny - nr:.1f} {nx + nr:.1f} {ny + nr:.1f}")
                    ci = min(9, int(local_p * 9.5))
                    if ci != last_ci:
                        append(f"{canvas_path} itemconfigure {oid} -fill {ramp[ci]}")
                        part[11] = ci

                # Seamlessly slide all subsequent cards into the vacated positions with a soft elastic settle.
                if reflow_cards and el >= reflow_start:
                    rp = min(1.0, (el - reflow_start) / reflow_dur)
                    reased = ease_out_elastic(rp, damping=5.2, frequency=1.08)
                    for rc in reflow_cards:
                        tag, tot_dx, tot_dy, cur_dx, cur_dy = rc
                        target_dx = tot_dx * reased
                        target_dy = tot_dy * reased
                        step_dx = target_dx - cur_dx
                        step_dy = target_dy - cur_dy
                        if abs(step_dx) >= 0.25 or abs(step_dy) >= 0.25:
                            append(f"{canvas_path} move {tag} {step_dx:.2f} {step_dy:.2f}")
                            rc[3] = target_dx
                            rc[4] = target_dy

                if cmds:
                    try:
                        tk_eval("\n".join(cmds))
                    except tk.TclError:
                        finish_evap()
                        return

                if el < total_dur:
                    spent = (monotonic() - t0) * 1000.0
                    hover_loop["evap_job"] = grid_canvas.after(self._next_frame_delay(spent, 16), step_evap)
                else:
                    finish_evap()

            step_evap()

        def paint_card_hover(c):
            step = c["step"]
            t = step / 10.0
            raw = ease_out_elastic(t, damping=3.0, frequency=1.65) if c["target"] > 0 else 1.0 - (1.0 - t) ** 2.4
            col_t = max(0.0, min(1.0, raw))
            # Symmetrically spring the card border from inset=4 -> 0 overshoot -> settle at 1.5.
            inset = max(0.0, min(4.0, 4.0 - 2.6 * raw))
            x0, y0, x1, y1 = c["rect"]
            grid_canvas.coords(c["bg_item"], *rounded_pts(x0 + inset, y0 + inset, x1 - inset, y1 - inset, 12))
            grid_canvas.itemconfigure(
                c["bg_item"],
                fill=blend_colour(CARD_BG, hover_bg_col, col_t),
                outline=blend_colour(BORDER_LINE, ORANGE_ACCENT, col_t),
            )
            grid_canvas.itemconfigure(c["title_item"], fill=blend_colour(TEXT_WHITE, ORANGE_HL, col_t))

        def paint_btn_hover(b):
            step = b["step"]
            t = step / 10.0
            raw = ease_out_elastic(t, damping=3.0, frequency=1.65) if b["target"] > 0 else 1.0 - (1.0 - t) ** 2.4
            col_t = max(0.0, min(1.0, raw))
            # Symmetrically pop the card button outward around its centered text.
            grow = max(0.0, min(3.5, 2.2 * raw))
            bx0, by0, bx1, by1 = b["rect"]
            grid_canvas.coords(b["poly"], *rounded_pts(bx0 - grow, by0 - grow, bx1 + grow, by1 + grow, 8 + grow * 0.4))
            grid_canvas.itemconfigure(b["poly"], fill=blend_colour(b["base"], b["hover"], col_t))

        def tick_grid_hover():
            hover_loop["job"] = None
            if not grid_canvas.winfo_exists() or getattr(self, "_transition_active", False):
                return
            scrolling = self._is_scrolling()
            any_active = False
            for c in state["cards"]:
                if c["step"] != c["target"]:
                    if scrolling:
                        c["step"] = c["target"]
                    else:
                        c["step"] += 1 if c["target"] > c["step"] else -1
                    paint_card_hover(c)
                    if c["step"] != c["target"]:
                        any_active = True
                for b in c["buttons"]:
                    if b["step"] != b["target"]:
                        if scrolling:
                            b["step"] = b["target"]
                        else:
                            b["step"] += 1 if b["target"] > b["step"] else -1
                        paint_btn_hover(b)
                        if b["step"] != b["target"]:
                            any_active = True
            if any_active:
                hover_loop["job"] = self.after(self._anim_frame_interval(16), tick_grid_hover)

        def set_hover(card_idx, btn_idx):
            prev_c = state["hovered"]
            prev_b = state["hovered_btn"]
            if prev_c == card_idx and prev_b == btn_idx:
                return
            if prev_b is not None:
                pc, pb = prev_b
                if pc < len(state["cards"]) and pb < len(state["cards"][pc]["buttons"]):
                    b = state["cards"][pc]["buttons"][pb]
                    b["target"] = 0
                    if self._is_reduced_motion():
                        b["step"] = 0
                        paint_btn_hover(b)
            if prev_c is not None and prev_c != card_idx and prev_c < len(state["cards"]):
                c = state["cards"][prev_c]
                c["target"] = 0
                if self._is_reduced_motion():
                    c["step"] = 0
                    paint_card_hover(c)
            if card_idx is not None and card_idx < len(state["cards"]):
                c = state["cards"][card_idx]
                c["target"] = 10
                if self._is_reduced_motion():
                    c["step"] = 10
                    paint_card_hover(c)
                if btn_idx is not None and btn_idx < len(c["buttons"]):
                    b = c["buttons"][btn_idx]
                    b["target"] = 10
                    if self._is_reduced_motion():
                        b["step"] = 10
                        paint_btn_hover(b)
                grid_canvas.configure(cursor="hand2")
            else:
                grid_canvas.configure(cursor="")
            state["hovered"] = card_idx
            state["hovered_btn"] = (card_idx, btn_idx) if (card_idx is not None and btn_idx is not None) else None
            if card_idx is not None and card_idx != prev_c and self._is_screen_reader_enabled():
                c_info = state["cards"][card_idx]
                c_title = c_info.get("title") or ""
                c_cat = c_info.get("category") or ""
                if c_title:
                    self.speak_text(f"{c_title}, {c_cat}" if c_cat else c_title)
            if not self._is_reduced_motion() and hover_loop["job"] is None:
                tick_grid_hover()

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
        grid_canvas._on_scale_change = lambda _sf: draw_grid(
            grid_canvas.winfo_width() if grid_canvas.winfo_width() > 1 else state["last_w"]
        )
        draw_grid(init_w)

        if insert_anim and state["cards"] and str(state["cards"][0].get("pid")) == str(insert_anim.get("podcast_id")):
            self._run_grid_insert_animation(grid_canvas, state, insert_anim, star_font, f_scale)
        elif evaporate_anim and state["cards"]:
            evap_pid = evaporate_anim.get("podcast_id")
            evap_return_tab = evaporate_anim.get("return_tab")
            evap_return_fn = evaporate_anim.get("return_fn")
            evap_wait_job = [None]

            def cancel_evap_wait(_e=None):
                if evap_wait_job[0] is not None:
                    try:
                        grid_canvas.after_cancel(evap_wait_job[0])
                    except tk.TclError:
                        pass
                    evap_wait_job[0] = None

            grid_canvas.bind("<Destroy>", cancel_evap_wait, add="+")

            def return_after_evap():
                if not grid_canvas.winfo_exists():
                    return
                def go_back():
                    if not grid_canvas.winfo_exists():
                        return
                    if evap_return_tab == "Programme details":
                        bar_info = getattr(self, "_bottom_bar_info", None)
                        if (
                            bar_info is not None
                            and bar_info[0].winfo_exists()
                            and bar_info[1].winfo_exists()
                            and str(bar_info[2]) == str(evap_pid)
                        ):
                            self.expand_bottom_bar_to_detail(*bar_info)
                            return
                    if evap_return_fn is not None:
                        self.transition_to(evap_return_fn, evap_return_tab, direction=-1)
                evap_wait_job[0] = grid_canvas.after(340, go_back)

            def start_pending_evap():
                evap_wait_job[0] = None
                if not grid_canvas.winfo_exists():
                    return
                if getattr(self, "_transition_active", False):
                    evap_wait_job[0] = grid_canvas.after(20, start_pending_evap)
                    return
                evap_wait_job[0] = grid_canvas.after(
                    180,
                    lambda: evaporate_card(evap_pid, return_after_evap, force_callback=True),
                )

            evap_wait_job[0] = grid_canvas.after(30, start_pending_evap)

    def _run_grid_insert_animation(self, grid_canvas, state, insert_anim, star_font, f_scale):
        """Slide existing cards over, spring the newly added card into slot 0, optionally fill stars 0..N,
        and smoothly transition back to the page the user came from."""
        if not grid_canvas.winfo_exists() or not state["cards"]:
            return
        stars_only = bool(insert_anim.get("stars_only"))
        target_pid = str(insert_anim.get("podcast_id") or "")
        new_card = state["cards"][0]
        if stars_only and target_pid:
            for card_entry in state["cards"]:
                if str(card_entry.get("pid")) == target_pid:
                    new_card = card_entry
                    break
        new_tag = new_card["all_tag"]
        target_rating = insert_anim.get("target_rating")
        return_tab = insert_anim.get("return_tab")
        return_fn = insert_anim.get("return_fn")
        star_items = new_card.get("star_items") or []

        # Prepare the "before" state immediately: for new cards, existing cards sit 1 slot earlier and
        # the new card is hidden above slot 0; for stars-only rating updates, keep all cards in place
        # and only reset the target card's 5 stars to empty before playing the golden wave.
        shifted_cards = []
        drop_offset = -42.0
        if not stars_only:
            for k in range(1, len(state["cards"])):
                dst_r = state["cards"][k]["rect"]
                src_r = state["cards"][k - 1]["rect"]
                back_dx = float(src_r[0] - dst_r[0])
                back_dy = float(src_r[1] - dst_r[1])
                grid_canvas.move(state["cards"][k]["all_tag"], back_dx, back_dy)
                # We will animate each shifted card forward by (-back_dx, -back_dy) back into its real slot k.
                shifted_cards.append([state["cards"][k]["all_tag"], -back_dx, -back_dy, 0.0, 0.0])

            grid_canvas.move(new_tag, 0, drop_offset)
            grid_canvas.itemconfigure(new_tag, state="hidden")
        if target_rating is not None and star_items:
            for s_id in star_items:
                grid_canvas.itemconfigure(s_id, fill=STAR_EMPTY)

        anim_job = [None]
        star_pop_font = self._get_cached_font((DEFAULT_FONT, max(14, round(17 * f_scale)), "bold"))

        def cancel_insert(_event=None):
            if anim_job[0] is not None:
                try:
                    grid_canvas.after_cancel(anim_job[0])
                except tk.TclError:
                    pass
                anim_job[0] = None

        grid_canvas.bind("<Destroy>", cancel_insert, add="+")

        def begin_showcase():
            anim_job[0] = None
            if not grid_canvas.winfo_exists():
                return
            # Wait for the incoming tab slide animation to finish before popping the new card in.
            if getattr(self, "_transition_active", False):
                anim_job[0] = grid_canvas.after(20, begin_showcase)
                return

            self._transition_active = True
            canvas_path = str(grid_canvas)
            tk_eval = grid_canvas.tk.eval
            slide_dur = 0.520
            st = {"elapsed": 0.0, "last_t": None, "new_shown": False, "new_dy": 0.0}

            def finish_and_return():
                anim_job[0] = None
                self._transition_active = False
                if not grid_canvas.winfo_exists():
                    return
                if return_tab == "Programme details":
                    bar_info = getattr(self, "_bottom_bar_info", None)
                    if (
                        bar_info is not None
                        and bar_info[0].winfo_exists()
                        and bar_info[1].winfo_exists()
                        and str(bar_info[2]) == str(new_card.get("pid"))
                    ):
                        # Podcast is currently in the bottom mini-bar: expand from the mini-bar into detail.
                        self.expand_bottom_bar_to_detail(*bar_info)
                        return
                    if new_card.get("open_action") is not None:
                        # Otherwise expand directly from the newly inserted card back into the podcast's detail page.
                        new_card["open_action"]()
                        return
                if return_fn is not None:
                    self.transition_to(return_fn, return_tab, direction=-1)

            def animate_stars(_unused=0):
                """Smooth 60fps overlapped elastic wave lighting up stars 1..target_rating with spring overshoot."""
                anim_job[0] = None
                if not grid_canvas.winfo_exists():
                    self._transition_active = False
                    return
                star_count = min(len(star_items), int(target_rating or 0))
                if star_count <= 0:
                    anim_job[0] = grid_canvas.after(520, finish_and_return)
                    return

                # Measure each target star's exact center & radius from its Canvas bbox so the vector pop
                # overlaps the real glyph cleanly.
                pop_stars = []
                for idx_s in range(star_count):
                    sid = star_items[idx_s]
                    bb = grid_canvas.bbox(sid)
                    if bb:
                        cx = (bb[0] + bb[2]) / 2.0
                        cy = (bb[1] + bb[3]) / 2.0
                        base_r = max(5.5, min(bb[2] - bb[0], bb[3] - bb[1]) * 0.44)
                    else:
                        coords = grid_canvas.coords(sid)
                        cx = (coords[0] if coords else 0) + 7.0
                        cy = (coords[1] if len(coords) > 1 else 0) + 8.0
                        base_r = 6.5
                    poly_id = grid_canvas.create_polygon(
                        cx, cy, cx, cy, cx, cy,
                        fill=GOLD_STAR, outline="", state="hidden", tags="star_pop_poly",
                    )
                    pop_stars.append([sid, poly_id, cx, cy, base_r, False, False])

                stagger = 0.115
                each_dur = 0.360
                total_dur = (star_count - 1) * stagger + each_dur
                s_st = {"elapsed": 0.0, "last_t": None}
                flash_col = blend_colour(GOLD_STAR, "#ffffff", 0.55)
                cos = math.cos
                sin = math.sin
                deg2rad = math.pi / 180.0

                def star_polygon_pts(cx, cy, r_out, rot_deg):
                    r_in = r_out * 0.42
                    pts = []
                    for pt_i in range(10):
                        ang = (-90.0 + rot_deg + pt_i * 36.0) * deg2rad
                        rad = r_out if (pt_i % 2 == 0) else r_in
                        pts.append(cx + rad * cos(ang))
                        pts.append(cy + rad * sin(ang))
                    return pts

                def step_stars():
                    anim_job[0] = None
                    if not grid_canvas.winfo_exists():
                        self._transition_active = False
                        return
                    t0 = monotonic()
                    dt = 0.016 if s_st["last_t"] is None else max(0.004, min(0.042, t0 - s_st["last_t"]))
                    s_st["last_t"] = t0
                    s_st["elapsed"] = min(total_dur, s_st["elapsed"] + dt)
                    el = s_st["elapsed"]

                    for idx_s, ps in enumerate(pop_stars):
                        sid, poly_id, cx, cy, base_r, started_flag, done_flag = ps
                        if done_flag:
                            continue
                        start_t = idx_s * stagger
                        if el < start_t:
                            continue
                        lp = min(1.0, (el - start_t) / each_dur)
                        if not started_flag:
                            grid_canvas.itemconfigure(sid, state="hidden")
                            grid_canvas.itemconfigure(poly_id, state="normal")
                            ps[5] = True
                        if lp >= 1.0:
                            grid_canvas.delete(poly_id)
                            grid_canvas.itemconfigure(sid, fill=GOLD_STAR, state="normal")
                            ps[6] = True
                            continue
                        # Bouncy elastic spring: shoots smoothly past 1.0 (~1.38x peak), wobbles, and settles to 1.0.
                        spring = max(0.05, ease_out_elastic(lp, damping=2.8, frequency=1.75))
                        r_now = base_r * spring
                        # Subtle damped rotational wobble (-16deg -> +6deg -> 0deg) that sells the spring feel.
                        rot = -16.0 * (1.0 - lp) * math.exp(-4.0 * lp) * cos(lp * math.pi * 3.0)
                        # Bright golden glint at the peak of the pop, settling into GOLD_STAR.
                        glint = max(0.0, 1.0 - abs(lp - 0.25) / 0.35)
                        col = blend_colour(GOLD_STAR, flash_col, glint * 0.65)
                        grid_canvas.coords(poly_id, *star_polygon_pts(cx, cy, r_now, rot))
                        grid_canvas.itemconfigure(poly_id, fill=col)

                    if el < total_dur:
                        spent = (monotonic() - t0) * 1000.0
                        anim_job[0] = grid_canvas.after(self._next_frame_delay(spent, 16), step_stars)
                    else:
                        try:
                            grid_canvas.delete("star_pop_poly")
                        except tk.TclError:
                            pass
                        # Hold briefly so the user sees the settled golden stars before transitioning back.
                        anim_job[0] = grid_canvas.after(480, finish_and_return)

                step_stars()

            def step_insert():
                anim_job[0] = None
                if not grid_canvas.winfo_exists():
                    self._transition_active = False
                    return
                t0 = monotonic()
                dt = 0.016 if st["last_t"] is None else max(0.004, min(0.042, t0 - st["last_t"]))
                st["last_t"] = t0
                st["elapsed"] = min(slide_dur, st["elapsed"] + dt)
                p = st["elapsed"] / slide_dur

                cmds = []
                append = cmds.append
                # 1. Slide all existing cards smoothly over by 1 slot.
                if shifted_cards:
                    seased = ease_out_elastic(min(1.0, p / 0.85), damping=5.2, frequency=1.08)
                    for sc in shifted_cards:
                        tag, tot_dx, tot_dy, cur_dx, cur_dy = sc
                        tx_d = tot_dx * seased
                        ty_d = tot_dy * seased
                        dx = tx_d - cur_dx
                        dy = ty_d - cur_dy
                        if abs(dx) >= 0.25 or abs(dy) >= 0.25:
                            append(f"{canvas_path} move {tag} {dx:.2f} {dy:.2f}")
                            sc[3] = tx_d
                            sc[4] = ty_d

                # 2. Spring the new card cleanly into slot 0 with a warm orange highlight border.
                if p >= 0.18:
                    if not st["new_shown"]:
                        append(f"{canvas_path} itemconfigure {new_tag} -state normal")
                        append(f"{canvas_path} itemconfigure {new_card['bg_item']} -outline {ORANGE_ACCENT}")
                        st["new_shown"] = True
                    np = min(1.0, (p - 0.18) / 0.82)
                    neased = ease_out_elastic(np, damping=4.2, frequency=1.30)
                    target_dy = -drop_offset * neased
                    dy_step = target_dy - st["new_dy"]
                    if abs(dy_step) >= 0.25:
                        append(f"{canvas_path} move {new_tag} 0 {dy_step:.2f}")
                        st["new_dy"] = target_dy

                if cmds:
                    try:
                        tk_eval("\n".join(cmds))
                    except tk.TclError:
                        self._transition_active = False
                        return

                if p < 1.0:
                    spent = (monotonic() - t0) * 1000.0
                    anim_job[0] = grid_canvas.after(self._next_frame_delay(spent, 16), step_insert)
                else:
                    # Snap any sub-pixel remainders and restore resting card border.
                    try:
                        for sc in shifted_cards:
                            rem_x = sc[1] - sc[3]
                            rem_y = sc[2] - sc[4]
                            if abs(rem_x) > 0.01 or abs(rem_y) > 0.01:
                                grid_canvas.move(sc[0], rem_x, rem_y)
                        rem_new_y = (-drop_offset) - st["new_dy"]
                        if abs(rem_new_y) > 0.01:
                            grid_canvas.move(new_tag, 0, rem_new_y)
                        grid_canvas.itemconfigure(new_card["bg_item"], outline=BORDER_LINE)
                    except tk.TclError:
                        pass
                    if target_rating is not None and star_items:
                        anim_job[0] = grid_canvas.after(140, lambda: animate_stars(0))
                    else:
                        anim_job[0] = grid_canvas.after(520, finish_and_return)

            if stars_only:
                if target_rating is not None and star_items:
                    anim_job[0] = grid_canvas.after(90, lambda: animate_stars(0))
                else:
                    finish_and_return()
            else:
                step_insert()

        anim_job[0] = grid_canvas.after(30, begin_showcase)

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
