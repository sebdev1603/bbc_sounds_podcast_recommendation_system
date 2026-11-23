"""Window icon/titlebar styling, live UI scaling, app shell, transitions, and bottom mini-bar."""
from collections import deque
import ctypes
from pathlib import Path
import sqlite3
import sys
from time import monotonic
import tkinter as tk
from tkinter import font as tkfont

from last_listened import get_last_listened
from gui_parts.i18n import set_active_language, translate
from gui_parts.theme import (
    BORDER_LINE,
    CARD_BG,
    DARK_BG,
    DEFAULT_FONT,
    INPUT_BG,
    MINI_BAR_BG,
    ORANGE_ACCENT,
    ORANGE_HL,
    PRIMARY_BTN_FG,
    ROOT_PATH,
    SECONDARY_HOVER_BG,
    SECONDARY_HOVER_FG,
    SIDEBAR_BG,
    TEXT_GRAY,
    TEXT_WHITE,
    TITLEBAR_DARK_MODE,
    TITLEBAR_TEXT,
    TOPBAR_BG,
    apply_theme_palette,
    blend_colour,
    ease_out_elastic,
)

# Embedded 64x64, 32x32, and 16x16 BBC Sounds logo PNGs (base64, area-averaged from
# bbc sounds logo.png) so compiled executables always show the exact BBC Sounds icon
# even without external --add-data files.
_EMBEDDED_WINDOW_ICON_PNGS = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAFa0lEQVR42u2bS0wbRxjHd3bXNjbYBvxIHSCyeZwDpGk4VJUKBVIIEn1Q5cAFBbcHqoYLQgIJDkiV4MAJEAKTlLScKiSoRAgtJw4IxCVAisTjAhxSCaQeIH5EwNdvxvbWPGxjIPJjbemv2Z39dj3fb7/5dnY85nie/xflohIEwS2Kol8en9x4jMrFcZwT9S6G5QyQK0DOM/KgTtLS0t5xhBC6A3JUampqEgCHoZ0EIHcA75MAYqRBmI9C7scUANq4rKwssFqtIWWxWKRz6HY4eyq/40ajMaytzWYD9CE6OWBtbQ1CfU5OTmBxcVGyn5ubY3Wh7N1uN6hUKmY/MDAQ9vpHR0eg1+uj8xj0A6AN8Xg8TLRBdN+vhYWFcwBC2QcC6O/vP3WM6uDggJ3n3782AN+o6FoAtra2QK1Wg06nY2E+NjYGx8fHQQHQY/n5+azhBoMBuru7pfpgADY3N6GkpARwtMrOm5mZuTEA7psAQPOB0+mE3t5eKCoqCgmAKjs7GzY2NmB6epr1Zb/9RQBcLhcUFBRAQ0MD7O7uMhhUMQOANoZGQE1NDXOMQggGwN9lcnJyoLy8nEVCU1MTsw8WAfR7aGJcXl4+l0NiBoDZbIb5+XkYGhoCfMmAvb29sAAmJydhamoKTCYTbG9vB42AnZ0dlulnZ2elCPIDjpkuQPvyxMQEdHR0gEajgf39/ZAAaKQ4HA4GjOYOGtrBIoDW19bWsmihdT09PTA+Ph47AOjdbm5uZmpra4OlpaWwSbCzs5PZt7S0nLqzwZIgzQN9fX1gt9uhtbUV1tfX2XViAkBgSJ5VMAAX2QYD4P+OQMVEF+jq6mJhHEzDw8PQ3t4u2dM7F85+cHAQcBKG2dfX17O6UPZUNAFHBUCkY/XL2H/o8f+NAkiIt8FoAiA+XfcaHEeudJ2oAiCEltjXeeoEkWBEIo7Dt0DCA88JWHpBxFEEENBg+fuX6TD1SAkvq1FVvrL6kvvVCvjjUSpoRQJCPHYBLWqvMQM8T3h4/4RI8gRsh9s/bFSDSfF/V4gyAOLrl+f7JGHHCAtbwnknMHSof+w6dIRDpyKXG3XYqAKjInLnP1gEiMxB4nOSBIgDBZY83SbceQCNkcuNOrR7AZCYAEAd4wVQ+pwVGRCvFLQkeIwQBolCSTwAqBRsyMhnt2GmLB3+LDVK+qvUADOlJpj93Ag/3zOzpJWwAKbLbsFKpQFWKzMDlOGtq8iEkU8yWI6QL4AHmTIGgNvP4h0AG8WRi5MgBfAKAaxWJDIA6ZnPS+NwIh8A3uc6fZ7zxPvFvD8qeCKPCMjAsXdjbhr8YNMwfZ+rgUqzmgGRBQCLiofRIgX8UijCi7silgI8talYFMgMgIAABLkCUAZEgCgvALcRwPNiFXN8tNAL4Cd5ARCSAGQNwOID8NznPNWP8gJA4Dd0+te7NAIU8KKQwFOrQi4AeLCk8DD8sRYc91JgpFgDjuIUaMrVygWAgDM7PGQpcZGUkoM7WOZgmSniVBjWy6ILnH0vkN3bYKg5wSQAuQNQYUNelpnhDXOYKlPS8kM9gjGC44EhcafEKIBXpR/B3xUmWKFRIMkEbyoy4PVDA4zeT9BJUcLmBAWY/sIMK3i3V3ACdNWnFXR+tdzIouLZfWOC/jCCEnCcUJWth8d30qHOppX0Leo7mw7qrFr49JYmcX8YufQjM1EjIBIlAcgdgB711q6/MgBPAAD+GgskXNFZH0TwV2QBqvLSoC4vBb7JU0esr/M08BWWKl6MPwD0rZI1mojXWhpHQQpszQGJNwDep4JwahFF5PI6z8ffKjHu1JoecgPXSC6UTAJIArgKAFxpfUD/4CA3KZVK9vf5/wA3Qv98dKvFvgAAAABJRU5ErkJggg==",
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAACJ0lEQVR42s2Wz4sSYRjH592dGUenLXGjy7J76VRQbFGXoHYPkiiBgsycFMXEi6DgRTQEQSg6hscObX/H/g8d3P4FwYMgJMj8UL+9M7Na5thu6/zo8Jl33ocX3s/743l4GUKIQtEp0wUMw+gUzWH0P+F53ogzxoTwA47jNOZyxf4J/G0HgsEgIpHICoIggG7dteOiKN5coF6vYz6fQ9d1szWoVquQZXktXqvVkE6nl31N08y22+1uJzAajZBIJJDL5dYEUqkUstksZrPZUmA6nSKfz6PdbmMwGDgjEI/HzUkVRVkRSCaTkCQJk8lkKTAcDlGpVJY7sbXAeDxGqVRCo9GAqqorAuVy2YwbYr8fQafTQavVQr/f306gUCig1+utkMlkEIvF1uLGEUWj0bV4s9m8uYDvaXg1BOSKMYSOcU2Ap3yTQ/gusxvYxbun/EbJfxKwVkIu/61+gLY/ijzUt4wtCuXTC9aZHbi/x0M6FChBSEchvDkI/RIoMrYoRQcF5EMRvVgEFxSjPT+h5ddXgVMPBMjilhNL4OK1hwK3dgnePwzgwwMez8Ks9wK3WYKzJyy+HrN4te+ugL5ZgMMZFXjpl8AX/wUECk8FOO8FjAwwLuLeDgFLiPcCdnXAVwHpyBJYFKPz033HSvG1BE7uhfD5+R1K2OTjcdhbATv+ewHVbYEdmimP7vJ4TNN0EweiiwLWk2zxULHH1SeZI49S40OBHwQCAe0nDU7DEtMfAP0AAAAASUVORK5CYII=",
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABHklEQVR42qXTP0vDQBzG8cvdVY2VFh1sqBhRcAgRCq4BV83m5uSSZImDvgbfgy8hS6Zky6sIASF/3ojQYspjclZNpbY1Hb7H5fLjwxEIIYSUVdNZ5ZqJecbYO5k9oI5SClmWRdXLhft6pjFfzgGGYSCOY2RZBtu2kSQJ0jSFZVnirCgKmKa5HPA8D2EYCsD3fQRBIIAoipDn+XJAURS4rivSNG3hXlXVv4HfSVWuzvCg0+9O9uhqQO1y6P0ODrco3hyGiU1E46qb4zWAl8seXq8PcK/ufAIOEY2dFcB5l2LUZ+2BuyHD0ynfADjieDzrtAdYFZc2+AZfPV/0EF3t43bYEmjeqAlM/gvUDXYZBvJP20yaB6plWv9hbeKclx9OcXAYViyb6AAAAABJRU5ErkJggg==",
)


class EffectsMixin:
    """Mixin managing native Windows styling, responsive scaling, navigation shell, and transitions."""

    def set_window_icon(self):
        """Find the BBC Sounds logo image (or embedded fallback) and apply it as the window icon."""
        base_dirs = []
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                base_dirs.append(Path(meipass))
            base_dirs.append(Path(sys.executable).resolve().parent)
        else:
            base_dirs.append(ROOT_PATH)

        search_dirs = []
        seen_dirs = set()
        for base in base_dirs:
            for candidate_dir in (
                base,
                *(base / sub for sub in ("assets", "images", "img", "icons", "canva design")),
            ):
                try:
                    resolved = candidate_dir.resolve()
                except OSError:
                    continue
                if resolved not in seen_dirs and resolved.is_dir():
                    seen_dirs.add(resolved)
                    search_dirs.append(resolved)

        def score_file(path):
            name = path.stem.lower()
            ext = path.suffix.lower()
            if "bbc" in name and "sound" in name:
                name_score = 40
            elif "sound" in name or "bbc" in name:
                name_score = 30
            else:
                return -1
            ext_score = {
                ".ico": 10, ".png": 8, ".gif": 6,
                ".webp": 4, ".jpg": 3, ".jpeg": 3, ".bmp": 2,
            }.get(ext, 0)
            return name_score + ext_score

        supported_exts = {".ico", ".png", ".gif", ".webp", ".jpg", ".jpeg", ".bmp"}
        candidates = []
        seen_files = set()
        for folder in search_dirs:
            try:
                for item in folder.iterdir():
                    if item.is_file() and item.suffix.lower() in supported_exts:
                        if score_file(item) < 0:
                            continue
                        resolved_file = item.resolve()
                        if resolved_file not in seen_files:
                            seen_files.add(resolved_file)
                            candidates.append(resolved_file)
            except OSError:
                continue

        candidates.sort(key=score_file, reverse=True)
        applied = False
        for icon_path in candidates:
            if self._apply_clean_window_icon(icon_path):
                applied = True
                break

        if not applied:
            applied = self._apply_embedded_window_icon()

        if applied:
            self._schedule_window_icon_reapply()

    def _apply_embedded_window_icon(self):
        """Apply the built-in base64 BBC Sounds logo so frozen builds keep the titlebar icon."""
        try:
            icons = [
                tk.PhotoImage(master=self, data=b64_png)
                for b64_png in _EMBEDDED_WINDOW_ICON_PNGS
            ]
            self.iconphoto(True, *icons)
            self._window_icons = icons
            return True
        except Exception:
            return False

    def _schedule_window_icon_reapply(self):
        """Re-apply the window icon after initial realization so Windows DWM does not reset it."""
        self.after_idle(self._reapply_window_icon)
        self.after(150, self._reapply_window_icon)

    def _reapply_window_icon(self):
        """Re-apply the stored window icon once the native Windows frame exists."""
        if not self.winfo_exists():
            return
        icons = getattr(self, "_window_icons", None)
        if icons:
            try:
                self.iconphoto(True, *icons)
                return
            except Exception:
                pass
        icon_path = getattr(self, "_window_icon_path", None)
        if icon_path and sys.platform == "win32":
            try:
                self.iconbitmap(default=str(icon_path))
            except Exception:
                pass

    def _apply_clean_window_icon(self, icon_path):
        """Strip outer solid/grey background, crop tight to the logo, and apply crisp icon sizes."""
        ext = icon_path.suffix.lower()
        # Preferred path: Pillow removes outer grey/solid square, crops tight, and resizes cleanly.
        try:
            import io
            from PIL import Image
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            img = Image.open(icon_path).convert("RGBA")
            if max(img.size) > 256:
                img.thumbnail((256, 256), resample)
            w, h = img.size
            px = img.load()
            corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
            opaque_corners = [c for c in corners if c[3] >= 16]
            if opaque_corners:
                bg_r = sum(c[0] for c in opaque_corners) // len(opaque_corners)
                bg_g = sum(c[1] for c in opaque_corners) // len(opaque_corners)
                bg_b = sum(c[2] for c in opaque_corners) // len(opaque_corners)

                def is_bg(rgba):
                    r, g, b, a = rgba
                    if a < 16:
                        return True
                    return abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b) <= 78

                visited = bytearray(w * h)
                queue = deque()
                for x in range(w):
                    for y in (0, h - 1):
                        idx = y * w + x
                        if not visited[idx] and is_bg(px[x, y]):
                            visited[idx] = 1
                            queue.append((x, y))
                for y in range(1, h - 1):
                    for x in (0, w - 1):
                        idx = y * w + x
                        if not visited[idx] and is_bg(px[x, y]):
                            visited[idx] = 1
                            queue.append((x, y))

                while queue:
                    cx, cy = queue.popleft()
                    px[cx, cy] = (0, 0, 0, 0)
                    for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                        if 0 <= nx < w and 0 <= ny < h:
                            nidx = ny * w + nx
                            if not visited[nidx] and is_bg(px[nx, ny]):
                                visited[nidx] = 1
                                queue.append((nx, ny))

            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)
            cw, ch = img.size
            side = max(1, cw, ch)
            square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            square.paste(img, ((side - cw) // 2, (side - ch) // 2), img)

            icons = []
            for sz in (64, 32, 16):
                buf = io.BytesIO()
                square.resize((sz, sz), resample).save(buf, format="PNG")
                icons.append(tk.PhotoImage(master=self, data=buf.getvalue()))
            self.iconphoto(True, *icons)
            self._window_icons = icons
            return True
        except Exception:
            pass

        # Fallback path without Pillow for PNG/GIF: flood-fill border background + crop to tight square.
        if ext in (".png", ".gif"):
            try:
                src = tk.PhotoImage(master=self, file=str(icon_path))
                sw, sh = src.width(), src.height()
                if max(sw, sh) > 128:
                    step = max(1, max(sw, sh) // 128)
                    src = src.subsample(step, step)
                    sw, sh = src.width(), src.height()

                def get_rgb(x, y):
                    if src.transparency_get(x, y):
                        return None
                    val = src.get(x, y)
                    if isinstance(val, tuple):
                        return val[:3]
                    return tuple(int(c) for c in str(val).split()[:3])

                corners = [get_rgb(x, y) for x, y in ((0, 0), (sw - 1, 0), (0, sh - 1), (sw - 1, sh - 1))]
                opaque_corners = [c for c in corners if c is not None]
                bg_mask = bytearray(sw * sh)
                if opaque_corners:
                    bg_r = sum(c[0] for c in opaque_corners) // len(opaque_corners)
                    bg_g = sum(c[1] for c in opaque_corners) // len(opaque_corners)
                    bg_b = sum(c[2] for c in opaque_corners) // len(opaque_corners)

                    def is_tk_bg(x, y):
                        rgb = get_rgb(x, y)
                        if rgb is None:
                            return True
                        return abs(rgb[0] - bg_r) + abs(rgb[1] - bg_g) + abs(rgb[2] - bg_b) <= 78

                    queue = deque()
                    for x in range(sw):
                        for y in (0, sh - 1):
                            idx = y * sw + x
                            if not bg_mask[idx] and is_tk_bg(x, y):
                                bg_mask[idx] = 1
                                queue.append((x, y))
                    for y in range(1, sh - 1):
                        for x in (0, sw - 1):
                            idx = y * sw + x
                            if not bg_mask[idx] and is_tk_bg(x, y):
                                bg_mask[idx] = 1
                                queue.append((x, y))
                    while queue:
                        cx, cy = queue.popleft()
                        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                            if 0 <= nx < sw and 0 <= ny < sh:
                                nidx = ny * sw + nx
                                if not bg_mask[nidx] and is_tk_bg(nx, ny):
                                    bg_mask[nidx] = 1
                                    queue.append((nx, ny))
                else:
                    for y in range(sh):
                        for x in range(sw):
                            if src.transparency_get(x, y):
                                bg_mask[y * sw + x] = 1

                min_x, min_y, max_x, max_y = sw, sh, -1, -1
                for y in range(sh):
                    for x in range(sw):
                        if not bg_mask[y * sw + x]:
                            if x < min_x:
                                min_x = x
                            if y < min_y:
                                min_y = y
                            if x > max_x:
                                max_x = x
                            if y > max_y:
                                max_y = y

                if max_x >= min_x and max_y >= min_y:
                    cw = max_x - min_x + 1
                    ch = max_y - min_y + 1
                    side = max(cw, ch)
                    pad_x = (side - cw) // 2
                    pad_y = (side - ch) // 2
                    icons = []
                    for sz in (32, 16):
                        out = tk.PhotoImage(master=self, width=sz, height=sz)
                        for oy in range(sz):
                            sy_sq = int((oy + 0.5) * side / sz)
                            sy = min_y + sy_sq - pad_y
                            for ox in range(sz):
                                sx_sq = int((ox + 0.5) * side / sz)
                                sx = min_x + sx_sq - pad_x
                                if min_x <= sx <= max_x and min_y <= sy <= max_y and not bg_mask[sy * sw + sx]:
                                    rgb = get_rgb(sx, sy)
                                    if rgb is not None:
                                        out.put(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}", (ox, oy))
                                    else:
                                        out.transparency_set(ox, oy, True)
                                else:
                                    out.transparency_set(ox, oy, True)
                        icons.append(out)
                    self.iconphoto(True, *icons)
                    self._window_icons = icons
                    return True
            except Exception:
                pass

        if ext == ".ico" and sys.platform == "win32":
            try:
                self.iconbitmap(default=str(icon_path))
                self._window_icon_path = icon_path
                return True
            except Exception:
                pass
        return False

    def set_windows_titlebar_colour(self, bg_hex=None, text_hex=None):
        """Apply Windows DWM light/dark mode and custom caption/text/border colours to the titlebar."""
        if sys.platform != "win32":
            return
        if bg_hex is None:
            bg_hex = DARK_BG
        if text_hex is None:
            text_hex = TITLEBAR_TEXT
        dark_mode_flag = int(TITLEBAR_DARK_MODE)
        if getattr(self, "_titlebar_colour", None) == (bg_hex, text_hex, dark_mode_flag):
            return
        try:
            hwnd = getattr(self, "_win_hwnd", None)
            if not hwnd:
                self.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
                self._win_hwnd = hwnd
            dwmapi = ctypes.windll.dwmapi

            def to_colorref(hex_colour):
                r = int(hex_colour[1:3], 16)
                g = int(hex_colour[3:5], 16)
                b = int(hex_colour[5:7], 16)
                return r | (g << 8) | (b << 16)

            for attr, value in (
                (20, dark_mode_flag),
                (19, dark_mode_flag),
                (35, to_colorref(bg_hex)),
                (36, to_colorref(text_hex)),
                (34, to_colorref(bg_hex)),
            ):
                val = ctypes.c_int(value)
                dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd),
                    ctypes.c_int(attr),
                    ctypes.byref(val),
                    ctypes.sizeof(val),
                )
            self._titlebar_colour = (bg_hex, text_hex, dark_mode_flag)
        except Exception:
            pass

    def schedule_interface_scaling(self, event):
        """Track window drags to pause heavy animations and debounce resize-only scaling."""
        if event.widget is not self:
            return
        pos = (event.x, event.y)
        size = (event.width, event.height)
        prev_pos = getattr(self, "_last_win_pos", None)
        prev_size = getattr(self, "_last_win_size", None)
        if prev_pos is not None and (pos != prev_pos or size != prev_size):
            self._window_moving_until = monotonic() + 0.16
        self._last_win_pos = pos
        if size == prev_size:
            return
        self._last_win_size = size
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(60, self.apply_interface_scaling)

    def apply_interface_scaling(self, force=False, target_widget=None):
        """Scale UI fonts, buttons, and wrap widths immediately when the window resizes or text size changes."""
        self._resize_after_id = None
        if not self.winfo_exists():
            return
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        if win_w <= 1 or win_h <= 1:
            return
        width_factor = win_w / 1320
        height_factor = win_h / 850
        # Combine responsive window scaling with the user's accessibility text-size multiplier.
        window_factor = max(0.84, min(1.25, min(width_factor, height_factor)))
        text_scale = getattr(self, "_text_scale", 1.0)
        new_scale_factor = max(0.70, min(1.75, window_factor * text_scale))
        if not force and abs(new_scale_factor - self._ui_scale_factor) < 0.025:
            return
        if force and abs(new_scale_factor - 1.0) < 0.025 and abs(self._ui_scale_factor - 1.0) < 0.025:
            return
        self._ui_scale_factor = new_scale_factor
        root = target_widget if (target_widget is not None and target_widget.winfo_exists()) else self
        self._scale_widget_tree(root, new_scale_factor)
        resize_search = getattr(self, "_resize_search_bar", None)
        if resize_search is not None:
            resize_search()

    def set_text_scale(self, new_scale, persist=True):
        """Set the accessibility text-size multiplier (0.80..1.40), persist per user, and rescale."""
        clamped = round(max(0.80, min(1.40, float(new_scale))), 2)
        if abs(clamped - getattr(self, "_text_scale", 1.0)) < 0.001:
            return
        self._text_scale = clamped
        if persist and self.current_user is not None:
            self.save_user_accessibility(self.current_user, self._text_scale, getattr(self, "_theme_name", "dark"))
        self.apply_interface_scaling(force=True)

    def adjust_text_scale(self, delta):
        """Increase or decrease the accessibility text size by delta (e.g. +0.10 or -0.10)."""
        self.set_text_scale(getattr(self, "_text_scale", 1.0) + delta)

    def set_theme(self, theme_name, refresh=True, persist=True):
        """Switch between 'dark', 'light', and 'high_contrast' themes, save per user, and update titlebar."""
        if theme_name not in ("dark", "light", "high_contrast"):
            theme_name = "dark"
        if getattr(self, "_theme_name", "dark") == theme_name and not refresh:
            return
        self._theme_name = theme_name
        apply_theme_palette(theme_name)
        if persist and self.current_user is not None:
            self.save_user_accessibility(self.current_user, getattr(self, "_text_scale", 1.0), self._theme_name)
        # Clear cached pill buttons and rounded covers so they re-rasterize for the new theme.
        self.button_images.clear()
        self.cover_images.clear()
        self._titlebar_colour = None
        self.configure(bg=DARK_BG)
        if refresh:
            # Tear down the persistent shell so topbar, scrollbar, and mini-bar rebuild in the new theme.
            shell_box = getattr(self, "_shell_box", None)
            if shell_box is not None and shell_box.winfo_exists():
                shell_box.destroy()
            self._shell_box = None
            self._shell_bottom_bar = None
            self._shell_bottom_bar_key = None
            if self.current_user is not None:
                self.set_windows_titlebar_colour(TOPBAR_BG, TITLEBAR_TEXT)
                self.show_profile()
            else:
                self.set_windows_titlebar_colour(DARK_BG, TITLEBAR_TEXT)
                self.show_login()

    def set_language(self, lang_code, refresh=True, persist=True):
        """Switch between English ('en') and Welsh ('cy'), persist per user, and refresh UI."""
        lang = "cy" if str(lang_code or "").lower() == "cy" else "en"
        if getattr(self, "_language", "en") == lang and not refresh:
            return
        self._language = lang
        set_active_language(lang)
        if persist and self.current_user is not None:
            self.save_user_language(self.current_user, lang)
        if refresh:
            shell_box = getattr(self, "_shell_box", None)
            if shell_box is not None and shell_box.winfo_exists():
                shell_box.destroy()
            self._shell_box = None
            self._shell_bottom_bar = None
            self._shell_bottom_bar_key = None
            if self.current_user is not None:
                self.show_profile()
            else:
                self.show_login()

    def _is_reduced_motion(self):
        """Return True when the user enabled Reduced Motion for low-end devices or comfort."""
        return bool(getattr(self, "_reduced_motion", False))

    def _anim_frame_interval(self, base_ms=16):
        """Return target frame interval (ms), keeping interactive animations crisp at 60Hz."""
        return max(16, int(base_ms))

    def _next_frame_delay(self, spent_ms, base_ms=16, min_yield_ms=4):
        """Compute the next timer delay compensating for render time without starving input."""
        clamped_spent = max(0.0, min(60.0, float(spent_ms)))
        return max(min_yield_ms, round(float(base_ms) - clamped_spent))

    def set_reduced_motion(self, enabled, refresh=True, persist=True):
        """Toggle Reduced Motion mode, save per user, and refresh the Settings view if requested."""
        flag = bool(enabled)
        if bool(getattr(self, "_reduced_motion", False)) == flag and not refresh:
            return
        self._reduced_motion = flag
        if persist and self.current_user is not None:
            self.save_user_reduced_motion(self.current_user, flag)
        if refresh and self.current_user is not None:
            self.show_profile()

    def apply_user_accessibility(self, listener_id):
        """Load and apply the signed-in listener's saved text size, theme, language, and motion from database.db."""
        saved_scale, saved_theme = self.load_user_accessibility(listener_id)
        saved_lang = self.load_user_language(listener_id)
        saved_reduced = self.load_user_reduced_motion(listener_id)
        theme_changed = saved_theme != getattr(self, "_theme_name", "dark")
        self._text_scale = saved_scale
        self._theme_name = saved_theme
        self._language = saved_lang
        self._reduced_motion = saved_reduced
        set_active_language(saved_lang)
        if theme_changed:
            apply_theme_palette(saved_theme)
            self.button_images.clear()
            self.cover_images.clear()
            self._titlebar_colour = None

    def reset_accessibility_settings(self):
        """Restore all accessibility settings (text size, theme, language, motion) to defaults and save."""
        theme_changed = getattr(self, "_theme_name", "dark") != "dark"
        lang_changed = getattr(self, "_language", "en") != "en"
        motion_changed = bool(getattr(self, "_reduced_motion", False))
        self._text_scale = 1.0
        self._language = "en"
        self._reduced_motion = False
        set_active_language("en")
        if self.current_user is not None:
            self.save_user_accessibility(self.current_user, 1.0, "dark")
            self.save_user_language(self.current_user, "en")
            self.save_user_reduced_motion(self.current_user, False)
        if theme_changed:
            self.set_theme("dark", refresh=True, persist=False)
            self.apply_interface_scaling(force=True)
        elif lang_changed:
            self.set_language("en", refresh=True, persist=False)
            self.apply_interface_scaling(force=True)
        elif motion_changed and self.current_user is not None:
            self.show_profile()
            self.apply_interface_scaling(force=True)
        else:
            self.apply_interface_scaling(force=True)

    def _scale_widget_tree(self, root_widget, scale_factor):
        """Walk the widget tree and scale point-sized fonts, rounded buttons, and wraplengths."""
        pending_widgets = list(root_widget.winfo_children())
        while pending_widgets:
            widget = pending_widgets.pop()
            if getattr(widget, "_skip_auto_scale", False):
                continue
            pending_widgets.extend(widget.winfo_children())
            try:
                base_font = getattr(widget, "_base_font", None)
                if base_font is None:
                    raw_font = widget.cget("font")
                    if raw_font:
                        actual = self._get_cached_font(raw_font).actual()
                        size_val = int(actual["size"])
                        if size_val > 0:
                            styles = []
                            if actual.get("weight") == "bold":
                                styles.append("bold")
                            if actual.get("slant") == "italic":
                                styles.append("italic")
                            base_font = (actual["family"], size_val, tuple(styles))
                            widget._base_font = base_font
                if base_font is not None:
                    family, base_size, styles = base_font
                    scaled_size = max(7, round(base_size * scale_factor))
                    scaled_font = (family, scaled_size, *styles)
                    if getattr(widget, "_applied_scaled_font", None) != scaled_font:
                        widget._applied_scaled_font = scaled_font
                        widget.configure(font=scaled_font)
                        if hasattr(widget, "_rounded_colours"):
                            self.style_rounded_button(widget, *widget._rounded_colours)
            except (tk.TclError, ValueError, TypeError):
                pass
            try:
                base_wrap = getattr(widget, "_base_wraplength", None)
                if base_wrap is None:
                    raw_wrap = int(widget.cget("wraplength"))
                    if raw_wrap > 0:
                        base_wrap = raw_wrap
                        widget._base_wraplength = base_wrap
                if base_wrap is not None:
                    scaled_wrap = max(60, round(base_wrap * scale_factor))
                    if getattr(widget, "_applied_wraplength", None) != scaled_wrap:
                        widget._applied_wraplength = scaled_wrap
                        widget.configure(wraplength=scaled_wrap)
            except (tk.TclError, ValueError, TypeError):
                pass

    def _sync_scrollregion(self):
        """Ensure the active shell scroll canvas reflects the current page's full height."""
        canvas_pane = getattr(self, "_shell_canvas", None)
        page = getattr(self, "current_page", None)
        if canvas_pane is None or page is None or not canvas_pane.winfo_exists() or not page.winfo_exists():
            return
        try:
            extra_bottom = 96 if getattr(self, "_active_nav_tab", "") != "Programme details" else 0
            w = max(1, canvas_pane.winfo_width(), page.winfo_reqwidth())
            h = max(1, page.winfo_height(), page.winfo_reqheight()) + extra_bottom
            canvas_pane.configure(scrollregion=(0, 0, w, h))
        except tk.TclError:
            pass

    def _finish_transition(self):
        """Mark the active transition complete, sync scrollregion, and resume any queued batch rendering."""
        self._transition_active = False
        self._sync_scrollregion()
        if self._render_queue:
            if self._pending_render_id is not None:
                try:
                    self.after_cancel(self._pending_render_id)
                except tk.TclError:
                    pass
            self._pending_render_id = self.after(1, self._render_next_batch)

    def build_shell(self, active_tab_title):
        """Construct or reuse the persistent top navigation bar, search box, mini-bar, and scroll area."""
        self.cancel_pending_render()
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None
        self._live_search_callback = None

        nav_links = [
            ("Home", self.show_home), ("Genres", self.show_search),
            ("For you", self.show_recommendations), ("Favourites", self.show_favourites),
            ("History", self.show_history), ("Ratings", self.show_ratings),
            ("Report", self.show_report), ("Settings", self.show_profile),
        ]
        profile_tab_active = active_tab_title in ("Your genres", "Profile & survey")
        active_nav_tab = (
            "Settings" if profile_tab_active else
            "Report" if active_tab_title == "Listening report" else active_tab_title
        )
        # Remember the last non-detail page so Programme details' Back button returns there,
        # and only reset shuffled podcast orders when actually switching to a different tab.
        if active_tab_title != "Programme details":
            prev_non_detail = getattr(self, "_last_visited_non_detail_tab", None)
            if prev_non_detail != active_tab_title:
                self._tab_podcast_order_cache = {}
                self._last_visited_non_detail_tab = active_tab_title
            nav_map = dict(nav_links)
            if active_tab_title == "Your genres":
                self._last_non_detail_tab = ("Settings", self.show_genres, "your genres")
            elif active_nav_tab in nav_map:
                self._last_non_detail_tab = (active_nav_tab, nav_map[active_nav_tab], active_nav_tab.lower())

        shell_box = getattr(self, "_shell_box", None)
        reusing_shell = shell_box is not None and shell_box.winfo_exists()

        if reusing_shell:
            # Fast path: keep the topbar, search box, and scroll canvas alive, swapping only the page content.
            for label_text, btn in self._shell_nav_buttons.items():
                selected_flag = label_text == active_nav_tab
                if getattr(btn, "_nav_selected", None) != selected_flag:
                    btn._nav_selected = selected_flag
                    new_fg = PRIMARY_BTN_FG if selected_flag else TEXT_GRAY
                    btn._hover_base_fg = new_fg
                    btn._hover_target_fg = PRIMARY_BTN_FG if selected_flag else SECONDARY_HOVER_FG
                    btn.configure(fg=new_fg)
                    self.style_rounded_button(
                        btn,
                        ORANGE_ACCENT if selected_flag else TOPBAR_BG,
                        ORANGE_HL if selected_flag else SECONDARY_HOVER_BG,
                    )
            self.update_search_prompt()
            canvas_pane = self._shell_canvas
            # Cancel any in-flight horizontal slide animation before preparing the new page.
            previous_frame = getattr(canvas_pane, "_slide_frame", None)
            if previous_frame is not None:
                try:
                    canvas_pane.after_cancel(previous_frame)
                except tk.TclError:
                    pass
                canvas_pane._slide_frame = None
            canvas_pane._leaving_page = False

            # Clean up any prior outgoing page if a new transition interrupted an older one.
            prev_anim_old = getattr(self, "_anim_old_page_info", None)
            if prev_anim_old is not None:
                p_page, p_win = prev_anim_old
                if p_page is not None and p_page.winfo_exists():
                    p_page.destroy()
                if p_win is not None:
                    try:
                        canvas_pane.delete(p_win)
                    except tk.TclError:
                        pass
                self._anim_old_page_info = None

            outgoing_info = getattr(self, "_outgoing_page_info", None)
            self._outgoing_page_info = None
            if outgoing_info is None:
                old_page = self.current_page
                if old_page is not None and old_page.winfo_exists():
                    old_page.destroy()
                old_win = getattr(self, "_shell_canvas_window", None)
                if old_win is not None:
                    try:
                        canvas_pane.delete(old_win)
                    except tk.TclError:
                        pass
                canvas_pane.yview_moveto(0)
            self._active_detail_podcast = None
            self._sync_bottom_bar(
                shell_box,
                show_bar=active_tab_title != "Programme details",
                show_average=not profile_tab_active,
            )
        else:
            outgoing_info = None
            self._outgoing_page_info = None
            # Cold start: clear the login screen and construct the persistent header, search box, and scroll viewport.
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.unbind_all(seq)
            for widget in self.winfo_children():
                if getattr(widget, "_preserve_during_shell_build", False):
                    continue
                widget.destroy()
            self.configure(bg=DARK_BG)
            self.set_windows_titlebar_colour(TOPBAR_BG, TITLEBAR_TEXT)
            shell_box = tk.Frame(self, bg=DARK_BG)
            shell_box.pack(fill="both", expand=True)
            self._shell_box = shell_box
            self._shell_bottom_bar = None
            self._shell_bottom_bar_key = None

            topbar = tk.Frame(shell_box, bg=TOPBAR_BG, height=84)
            topbar.pack(fill="x")
            topbar.pack_propagate(False)
            logo_widget = self.draw_app_logo(topbar, 1.05)
            logo_widget.pack(side="left", padx=(20, 12), pady=22)

            nav_row = tk.Frame(topbar, bg=TOPBAR_BG)
            nav_row.pack(side="left", padx=(4, 10), pady=18)
            self._shell_nav_buttons = {}
            for label_text, handler in nav_links:
                selected_flag = label_text == active_nav_tab
                btn = self.create_button(
                    nav_row, label_text.upper(), lambda go=handler, tab=label_text: self.transition_to(go, tab),
                    compact=True, primary=selected_flag, font=(DEFAULT_FONT, 9, "bold"),
                    face=ORANGE_ACCENT if selected_flag else TOPBAR_BG,
                    fg=PRIMARY_BTN_FG if selected_flag else TEXT_GRAY,
                )
                btn._rounded_padding = (18, 12)
                self.style_rounded_button(
                    btn,
                    ORANGE_ACCENT if selected_flag else TOPBAR_BG,
                    ORANGE_HL if selected_flag else SECONDARY_HOVER_BG,
                )
                btn._nav_selected = selected_flag
                btn.pack(side="left", padx=1)
                self._shell_nav_buttons[label_text] = btn
            sign_out_btn = self.create_button(topbar, "Sign out", self.sign_out_to_login, compact=True)
            sign_out_btn.pack(side="right", padx=(6, 14), pady=20)
            search_container = self.create_card_frame(topbar, bg=INPUT_BG, width=210, height=38)
            search_container.pack(side="right", padx=(6, 10), pady=23)
            search_container.pack_propagate(False)
            self._search_container = search_container

            last_search_size = [210, 38]

            def resize_search_bar(_event=None):
                if not topbar.winfo_exists() or not search_container.winfo_exists():
                    return
                bar_w = topbar.winfo_width()
                if bar_w <= 1:
                    return
                # Calculate remaining space between the nav links and Sign out button.
                used_w = (
                    logo_widget.winfo_reqwidth() + 36
                    + nav_row.winfo_reqwidth() + 20
                    + sign_out_btn.winfo_reqwidth() + 36
                )
                available = bar_w - used_w
                # Grow longer on wider windows (up to 460px) and shrink cleanly on smaller/Linux screens (down to 110px).
                target_w = max(110, min(460, available))
                target_h = max(34, min(44, round(38 * getattr(self, "_ui_scale_factor", 1.0))))
                if abs(target_w - last_search_size[0]) >= 2 or target_h != last_search_size[1]:
                    last_search_size[0] = target_w
                    last_search_size[1] = target_h
                    search_container.configure(width=target_w, height=target_h)

            topbar.bind("<Configure>", resize_search_bar)
            nav_row.bind("<Configure>", resize_search_bar)
            self._resize_search_bar = resize_search_bar
            self.after_idle(resize_search_bar)
            self._search_entry = tk.Entry(
                search_container, textvariable=self.search_text, font=(DEFAULT_FONT, 10),
                bg=INPUT_BG, fg=TEXT_WHITE, insertbackground=TEXT_WHITE, relief="flat",
                bd=0, highlightthickness=0,
            )
            self._search_entry.pack(fill="both", expand=True, padx=10, pady=5)
            self._search_prompt = tk.Label(
                search_container, text=translate("Search programmes..."), font=(DEFAULT_FONT, 10),
                bg=INPUT_BG, fg=TEXT_GRAY, cursor="xterm",
            )
            self._search_prompt.bind("<Button-1>", lambda _event: self._search_entry.focus_set())
            self._search_entry.bind("<FocusIn>", lambda _event: self._search_prompt.place_forget())
            self._search_entry.bind("<FocusOut>", lambda _event: self.update_search_prompt())
            self._search_entry.bind("<KeyRelease>", self.schedule_live_search)
            self.update_search_prompt()
            tk.Frame(shell_box, bg=ORANGE_ACCENT, height=3).pack(fill="x")

            self._active_detail_podcast = None
            self._bottom_bar_info = None
            area_frame = tk.Frame(shell_box, bg=DARK_BG)
            area_frame.pack(fill="both", expand=True)
            self._shell_area_frame = area_frame
            canvas_pane = tk.Canvas(
                area_frame, bg=DARK_BG, highlightthickness=0, borderwidth=0, yscrollincrement=1,
            )
            scroll_bar = tk.Scrollbar(
                area_frame, orient="vertical", command=canvas_pane.yview,
                bg=SIDEBAR_BG, troughcolor=DARK_BG, activebackground=ORANGE_ACCENT,
                bd=0, highlightthickness=0, relief="flat",
            )
            scroll_bar.pack(side="right", fill="y")
            canvas_pane.pack(side="left", fill="both", expand=True)
            canvas_pane.configure(yscrollcommand=scroll_bar.set)
            self._shell_canvas = canvas_pane
            self._shell_scrollbar = scroll_bar
            self.bind_page_scroll(canvas_pane, scroll_bar)

            def resize_content(event):
                cur_page = self.current_page
                cur_win = getattr(self, "_shell_canvas_window", None)
                if cur_page is not None and cur_win is not None and cur_page.winfo_exists():
                    if event.width != cur_page.winfo_width():
                        canvas_pane.itemconfigure(cur_win, width=event.width)

            canvas_pane.bind("<Configure>", resize_content)
            self._sync_bottom_bar(
                shell_box,
                show_bar=active_tab_title != "Programme details",
                show_average=not profile_tab_active,
            )

        content_pane = tk.Frame(canvas_pane, bg=DARK_BG, padx=46, pady=28)
        canvas_w = canvas_pane.winfo_width()
        win_kwargs = {"window": content_pane, "anchor": "nw"}
        if canvas_w > 1:
            win_kwargs["width"] = canvas_w
        if self._tab_transition_direction is not None and canvas_w > 1:
            # Start the incoming page off-screen so it never flashes at (0, 0) before sliding in.
            init_pos = (self._tab_transition_direction * canvas_w, 0)
        else:
            init_pos = (0, 0)
        canvas_window = canvas_pane.create_window(init_pos, **win_kwargs)
        self._shell_canvas_window = canvas_window

        # Extra scrollroom at the bottom lets the last row scroll clear of the floating mini-bar.
        extra_bottom = 96 if active_tab_title != "Programme details" else 0

        def update_scrollregion(event):
            if canvas_pane.winfo_exists() and not getattr(self, "_transition_active", False):
                canvas_pane.configure(scrollregion=(0, 0, event.width, event.height + extra_bottom))

        content_pane.bind("<Configure>", update_scrollregion)
        canvas_pane.after_idle(self._sync_scrollregion)
        self.current_page = content_pane
        self._page_transition_target = (canvas_pane, canvas_window)
        self._tab_order = [label for label, _ in nav_links]
        self._active_nav_tab = active_nav_tab

        if self._tab_transition_direction is not None:
            self.animate_page_entry(
                canvas_pane, canvas_window, self._tab_transition_direction, outgoing_info=outgoing_info,
            )
        elif abs(self._ui_scale_factor - 1.0) >= 0.025 or abs(getattr(self, "_text_scale", 1.0) - 1.0) >= 0.025:
            target = content_pane if reusing_shell else self
            self.after_idle(lambda t=target: self.apply_interface_scaling(force=True, target_widget=t))
        return content_pane

    def _sync_bottom_bar(self, shell, show_bar=True, show_average=True):
        """Show, reuse, or hide the bottom mini-bar without rebuilding it unnecessarily."""
        existing = getattr(self, "_shell_bottom_bar", None)
        if not show_bar or self.current_user is None:
            if existing is not None and existing.winfo_exists():
                existing.destroy()
            self._shell_bottom_bar = None
            self._shell_bottom_bar_key = None
            self._bottom_bar_info = None
            return

        try:
            with self.get_db_connection() as conn:
                recent = get_last_listened(conn, self.current_user)
        except sqlite3.Error:
            recent = None

        if recent is None or recent[0] == self._dismissed_last_listened:
            if existing is not None and existing.winfo_exists():
                existing.destroy()
            self._shell_bottom_bar = None
            self._shell_bottom_bar_key = None
            self._bottom_bar_info = None
            return

        podcast_id, title, category = recent
        avg_text = self.podcast_average_text(podcast_id) if show_average else ""
        bar_key = (podcast_id, title, category, avg_text)
        if existing is not None and existing.winfo_exists() and getattr(self, "_shell_bottom_bar_key", None) == bar_key:
            self._bottom_bar_info = (shell, existing, podcast_id, title, category)
            tk.Misc.lift(existing)
            return

        if existing is not None and existing.winfo_exists():
            existing.destroy()
        self._shell_bottom_bar = None
        self._shell_bottom_bar_key = None
        self._bottom_bar_info = None
        self.add_last_listened_prompt(shell, show_average=show_average, recent=recent)
        self._shell_bottom_bar_key = bar_key

    def _is_busy_transitioning(self):
        """Return True while any page, overlay, genre, or sign-out animation is in progress."""
        if getattr(self, "_transition_active", False) or getattr(self, "_signing_out", False):
            return True
        shell = getattr(self, "_shell_box", None)
        if shell is not None and shell.winfo_exists() and getattr(shell, "_expanding_bar", False):
            return True
        area_frame = getattr(self, "_shell_area_frame", None)
        if area_frame is not None and area_frame.winfo_exists() and getattr(area_frame, "_expanding_genre", False):
            return True
        return False

    def transition_to(self, destination, tab=None, *, direction=None):
        """Animate out of the current page (sliding or shrinking to the mini-bar) and open destination."""
        if self._is_busy_transitioning():
            return
        target = getattr(self, "_page_transition_target", None)
        if not target:
            return
        canvas, window = target
        if not canvas.winfo_exists() or getattr(canvas, "_leaving_page", False):
            return
        current = self._active_nav_tab
        if tab is not None and tab == current and direction is None:
            return
        tab_distance = 1
        if current in self._tab_order and tab in self._tab_order:
            delta = self._tab_order.index(tab) - self._tab_order.index(current)
            tab_distance = max(1, abs(delta))
            if direction is None:
                direction = 1 if delta > 0 else -1
        elif direction is None:
            direction = 1

        canvas._leaving_page = True
        self._transition_active = True
        self.cancel_pending_render()

        if current == "Programme details" and self._active_detail_podcast is not None:
            pid_now, title_now, cat_now = self._active_detail_podcast
            origin = getattr(self, "_detail_hero_origin", None)
            if origin is not None and origin.get("podcast_id") != pid_now:
                origin = None

            back_tab, back_handler, _back_name = getattr(
                self, "_last_non_detail_tab", (None, None, ""),
            )
            # If the user clicked a different tab from Programme details, first shrink back to the
            # page they came from, then smoothly transition to the tab they requested.
            switching_to_other_tab = (
                tab is not None
                and back_tab is not None
                and back_handler is not None
                and tab != back_tab
            )
            shrink_dest = back_handler if switching_to_other_tab else destination
            follow_up = (lambda: self.transition_to(destination, tab)) if switching_to_other_tab else None

            if origin is not None and origin.get("source") == "card":
                self.shrink_detail_to_origin(
                    shrink_dest, origin, restore_scroll=True, on_complete=follow_up,
                )
                return

            if origin is not None and origin.get("source") == "mini_bar":
                self.shrink_detail_to_origin(
                    shrink_dest, origin, restore_scroll=False, on_complete=follow_up,
                )
                return

            recent = None
            try:
                with self.get_db_connection() as conn:
                    recent = get_last_listened(conn, self.current_user)
            except sqlite3.Error:
                recent = None
            if (
                recent is not None
                and recent[0] == pid_now
                and recent[0] != self._dismissed_last_listened
            ):
                self.shrink_detail_to_bottom_bar(
                    shrink_dest, title_now, cat_now, podcast_id=pid_now, on_complete=follow_up,
                )
                return

        if self._is_reduced_motion():
            self._outgoing_page_info = None
            self._tab_transition_direction = None
            self._detail_hero_origin = None
            canvas._leaving_page = False
            self._transition_active = False
            destination()
            self._finish_transition()
            return

        # Slide the current page completely off-screen before building and sliding in the destination page.
        def open_next_page():
            self._outgoing_page_info = None
            self._tab_transition_direction = direction
            self._tab_transition_distance = tab_distance
            try:
                destination()
            finally:
                self._tab_transition_direction = None
                self._tab_transition_distance = 1

        # On Linux/macOS, skip sliding the outgoing heavy widget tree (which triggers per-child X11 repaints)
        # and go straight into a crisp, fast incoming slide.
        if sys.platform != "win32":
            open_next_page()
            return

        self.slide_page(
            canvas, window, -direction * max(1, canvas.winfo_width()), 175, open_next_page,
            frame_ms=self._anim_frame_interval(16),
        )

    def _prerender_initial_batch(self, max_items=2):
        """Render a lightweight initial batch off-screen without overloading slide HWND repaints."""
        rendered = 0
        while self._render_queue and rendered < max_items:
            items_iter, render_item = self._render_queue[0]
            try:
                item = next(items_iter)
            except StopIteration:
                self._render_queue.pop(0)
                continue
            render_item(item)
            rendered += 1

    def animate_page_entry(self, canvas, canvas_window, direction, outgoing_info=None):
        """Slide the new page smoothly into view using 60Hz real-time elastic pacing."""
        self._transition_active = True
        tab_distance = max(1, getattr(self, "_tab_transition_distance", 1))
        max_span = max(1, len(getattr(self, "_tab_order", [])) - 2)
        ratio = min(1.0, (tab_distance - 1) / max_span)
        if sys.platform != "win32":
            entry_ms = 240
            damping = 7.2
            frequency = 0.85
        else:
            entry_ms = round(260 + 40 * ratio)
            damping = 6.6 - 0.8 * ratio
            frequency = 1.00 + 0.12 * ratio

        def finish_entry():
            if canvas.winfo_exists() and canvas_window == getattr(self, "_shell_canvas_window", None):
                try:
                    canvas.coords(canvas_window, 0, 0)
                    if self.current_page is not None and self.current_page.winfo_exists():
                        extra_bottom = 96 if self._active_nav_tab != "Programme details" else 0
                        canvas.configure(
                            scrollregion=(
                                0, 0,
                                self.current_page.winfo_reqwidth(),
                                self.current_page.winfo_reqheight() + extra_bottom,
                            )
                        )
                except tk.TclError:
                    pass
            self._finish_transition()

        def begin_slide():
            if not canvas.winfo_exists() or canvas_window != getattr(self, "_shell_canvas_window", None):
                self._finish_transition()
                return
            try:
                if self._active_nav_tab not in ("Genres", "Home"):
                    self._prerender_initial_batch(2)
                if abs(self._ui_scale_factor - 1.0) >= 0.025 and self.current_page is not None and self.current_page.winfo_exists():
                    self._scale_widget_tree(self.current_page, self._ui_scale_factor)
                width = max(1, canvas.winfo_width())
                canvas.itemconfigure(canvas_window, width=width)
                # Reset vertical scroll and update scrollregion BEFORE frame 0 so the incoming page
                # never slides in clipped at the previous page's scroll offset.
                canvas.update_idletasks()
                if self.current_page is not None and self.current_page.winfo_exists():
                    extra_bottom = 96 if self._active_nav_tab != "Programme details" else 0
                    canvas.configure(
                        scrollregion=(
                            0, 0,
                            max(width, self.current_page.winfo_reqwidth()),
                            self.current_page.winfo_reqheight() + extra_bottom,
                        )
                    )
                canvas.yview_moveto(0)
                slide_offset = min(width, 260) if sys.platform != "win32" else width
                canvas.coords(canvas_window, direction * slide_offset, 0)
                canvas.update_idletasks()
            except tk.TclError:
                self._finish_transition()
                return
            self.slide_page(
                canvas, canvas_window, 0, entry_ms, finish_entry,
                damping=damping, frequency=frequency, frame_ms=16,
            )

        # Start promptly on the next tick so tab switches never feel delayed behind idle work.
        canvas.after(1, begin_slide)

    def slide_page(
        self, canvas, canvas_window, end_x, duration_ms, on_complete=None, *,
        damping=5.4, frequency=1.15, frame_ms=16,
    ):
        """Animate the scrollable content window horizontally to end_x with clamped dt so slow frames never jump."""
        previous_frame = getattr(canvas, "_slide_frame", None)
        if previous_frame is not None:
            try:
                canvas.after_cancel(previous_frame)
            except tk.TclError:
                pass
        try:
            coords = canvas.coords(canvas_window)
        except tk.TclError:
            self._finish_transition()
            return
        start_x = coords[0] if coords else 0
        duration_sec = max(0.08, float(duration_ms) / 1000.0)
        progress = 0.0
        last_t = None
        last_x = round(start_x)
        self._transition_active = True

        def draw_frame():
            nonlocal last_x, progress, last_t
            canvas._slide_frame = None
            if not canvas.winfo_exists() or canvas_window != getattr(self, "_shell_canvas_window", None):
                self._finish_transition()
                return
            frame_t0 = monotonic()
            dt = 0.016 if last_t is None else max(0.004, min(0.042, frame_t0 - last_t))
            last_t = frame_t0
            progress = min(1.0, progress + dt / duration_sec)
            # Outgoing pages accelerate cleanly off-screen; incoming pages settle smoothly (cubic on Linux/macOS, elastic on Windows).
            if end_x:
                eased = progress ** 2.2
            elif sys.platform != "win32":
                eased = 1.0 - (1.0 - progress) ** 3
            else:
                eased = ease_out_elastic(progress, damping=damping, frequency=frequency)
            new_x = round(start_x + (end_x - start_x) * eased)
            if new_x != last_x:
                try:
                    canvas.coords(canvas_window, new_x, 0)
                except tk.TclError:
                    self._finish_transition()
                    return
                last_x = new_x
            if progress < 1.0:
                spent_ms = (monotonic() - frame_t0) * 1000.0
                canvas._slide_frame = canvas.after(self._next_frame_delay(spent_ms, frame_ms), draw_frame)
            elif on_complete:
                # Let Tk paint the final off-screen / resting frame before running on_complete so
                # outgoing pages never cut off early while still partially visible.
                canvas._slide_frame = canvas.after(frame_ms, on_complete)
            else:
                self._finish_transition()

        if not getattr(canvas, "_slide_cleanup_bound", False):
            def cancel_animation(_event):
                frame_id = getattr(canvas, "_slide_frame", None)
                if frame_id is not None:
                    try:
                        canvas.after_cancel(frame_id)
                    except tk.TclError:
                        pass
                self._transition_active = False

            canvas.bind("<Destroy>", cancel_animation, add="+")
            canvas._slide_cleanup_bound = True
        draw_frame()

    def add_last_listened_prompt(self, shell, show_average=True, recent=None):
        """Attach the clickable bottom mini-bar for the user's most recently played podcast."""
        if self.current_user is None:
            return
        if recent is None:
            try:
                with self.get_db_connection() as conn:
                    recent = get_last_listened(conn, self.current_user)
            except sqlite3.Error:
                return
        if recent is None:
            return

        podcast_id, title, category = recent
        if podcast_id == self._dismissed_last_listened:
            return

        footer = self.create_card_frame(shell, bg=MINI_BAR_BG)
        # Float the mini-bar over the scrollable page (leaving space for the right scrollbar)
        # so there is no solid black strip reserved behind or beside it.
        footer.place(relx=0.0, rely=1.0, anchor="sw", x=18, y=-10, relwidth=1.0, width=-52)
        tk.Misc.lift(footer)
        tk.Frame(footer, bg=ORANGE_ACCENT, width=3).pack(side="left", fill="y")
        row = tk.Frame(footer, bg=footer.cget("bg"))
        row.pack(fill="x", padx=10, pady=7)

        def dismiss():
            self._dismissed_last_listened = podcast_id
            self._bottom_bar_info = None
            self._shell_bottom_bar = None
            self._shell_bottom_bar_key = None
            footer.destroy()

        bar_bg = row.cget("bg")
        sim_fade_job = [None]

        def cancel_sim_fade(_event=None):
            if sim_fade_job[0] is not None:
                try:
                    self.after_cancel(sim_fade_job[0])
                except tk.TclError:
                    pass
                sim_fade_job[0] = None

        def show_mini_bar_sim_notice():
            if not sim_notice_label.winfo_exists():
                return
            cancel_sim_fade()
            sim_notice_label.configure(text=translate("Playback is simulated"), fg=TEXT_GRAY)
            fade_steps = 36
            fade_step = [0]

            def step_sim_fade():
                sim_fade_job[0] = None
                if not sim_notice_label.winfo_exists():
                    return
                fade_step[0] += 1
                frac = min(1.0, fade_step[0] / float(fade_steps))
                eased = frac * frac * (3.0 - 2.0 * frac)
                sim_notice_label.configure(fg=blend_colour(TEXT_GRAY, footer.surface, eased))
                if fade_step[0] < fade_steps:
                    sim_fade_job[0] = self.after(40, step_sim_fade)
                else:
                    sim_notice_label.configure(text="")

            # Hold readable for ~1.1s before smoothly fading into the mini-bar background.
            sim_fade_job[0] = self.after(1100, step_sim_fade)

        def play_from_mini_bar():
            if not self.listen(podcast_id, open_detail=False):
                return
            show_mini_bar_sim_notice()

        footer._show_sim_notice = show_mini_bar_sim_notice

        dismiss_btn = self.create_button(row, "Dismiss", dismiss, compact=True)
        dismiss_btn.pack(side="right", padx=(8, 0))
        play_btn = self.create_button(row, "▶  Play", play_from_mini_bar, primary=True, compact=True)
        play_btn.pack(side="right")
        sim_notice_label = tk.Label(
            row,
            text="",
            font=(DEFAULT_FONT, 10, "italic"),
            fg=bar_bg,
            bg=bar_bg,
            anchor="e",
            justify="right",
        )
        sim_notice_label.pack(side="right", padx=(0, 12))
        sim_notice_label.bind("<Destroy>", cancel_sim_fade)

        cover = self.generate_podcast_cover(
            row, podcast_id, title, category, 62, 62,
            corner_radius=10, backdrop=row.cget("bg"),
        )
        cover.pack(side="left", padx=(0, 11))
        details = tk.Frame(row, bg=row.cget("bg"), cursor="hand2", takefocus=True,
                           highlightthickness=1, highlightbackground=row.cget("bg"),
                           highlightcolor=ORANGE_HL)
        details._sync_highlight_bg = True
        details.pack(side="left", fill="both", expand=True, padx=(0, 10))
        title_label = self.create_label(details, title, 13, TEXT_WHITE, "bold", cursor="hand2")
        title_label.pack(fill="x", pady=(6, 1))
        subtitle = f"Last played  ·  {category}" if category else "Last played"
        if show_average:
            subtitle += f"  ·  {self.podcast_average_text(podcast_id)}"
        subtitle_label = self.create_label(details, subtitle, 9, TEXT_GRAY, cursor="hand2")
        subtitle_label.pack(fill="x")
        open_detail = lambda _event=None: self.expand_bottom_bar_to_detail(shell, footer, podcast_id, title, category)
        for widget in (footer, footer.backdrop, row, cover, details, title_label, subtitle_label):
            widget.bind("<Button-1>", open_detail)
        details.bind("<Return>", open_detail)
        details.bind("<space>", open_detail)
        self._attach_podcast_card_hover(
            footer,
            [row, details, title_label, subtitle_label, sim_notice_label, dismiss_btn, play_btn],
            title_label,
            base_bg=bar_bg,
        )
        self._shell_bottom_bar = footer
        self._bottom_bar_info = (shell, footer, podcast_id, title, category)

    def _get_current_page_return_target(self):
        """Return (tab_name, handler_fn) to smoothly navigate back to the currently open page."""
        tab = getattr(self, "_active_nav_tab", "Home") or "Home"
        if tab == "Programme details" and getattr(self, "_active_detail_podcast", None):
            pid = self._active_detail_podcast[0]
            return ("Programme details", lambda target_id=pid: self.show_detail(target_id))
        nav_map = {
            "Home": self.show_home,
            "Genres": self.show_search,
            "For you": self.show_recommendations,
            "Favourites": self.show_favourites,
            "History": self.show_history,
            "Ratings": self.show_ratings,
            "Report": self.show_report,
            "Settings": self.show_profile,
        }
        return (tab, nav_map.get(tab, self.show_home))

    def play_podcast_to_mini_bar(self, source_widget, podcast_id, title="", category="", cover_widget=None):
        """Elastically migrate a podcast's Play button and cover art into the bottom mini-bar."""
        if self._is_busy_transitioning():
            return
        existing_bar = getattr(self, "_shell_bottom_bar", None)
        bar_info = getattr(self, "_bottom_bar_info", None)
        already_in_mini_bar = (
            existing_bar is not None
            and existing_bar.winfo_exists()
            and bar_info is not None
            and str(bar_info[2]) == str(podcast_id)
        )
        return_tab, return_fn = self._get_current_page_return_target()
        listen_res = self.listen(podcast_id, open_detail=False)
        if not listen_res:
            return

        shell = getattr(self, "_shell_box", None)
        if shell is None or not shell.winfo_exists():
            return

        show_avg = getattr(self, "_active_nav_tab", "") != "Settings"
        # First time listening to this podcast: showcase it popping into the top of History, then return here.
        if listen_res == "first_time" and not self._is_reduced_motion() and return_tab != "History":
            self._sync_bottom_bar(shell, show_bar=True, show_average=show_avg)
            self._detail_hero_origin = None
            self._pending_card_insert = {
                "mode": "history",
                "podcast_id": podcast_id,
                "target_rating": None,
                "return_tab": return_tab,
                "return_fn": return_fn,
            }
            self.transition_to(self.show_history, "History")
            return

        if self._is_reduced_motion() or already_in_mini_bar or source_widget is None or not source_widget.winfo_exists():
            self._sync_bottom_bar(shell, show_bar=True, show_average=show_avg)
            bar = getattr(self, "_shell_bottom_bar", None)
            if bar is not None and bar.winfo_exists() and hasattr(bar, "_show_sim_notice"):
                bar._show_sim_notice()
            return

        self._transition_active = True
        self.update_idletasks()
        shell_x = shell.winfo_rootx()
        shell_y = shell.winfo_rooty()
        shell_w = max(1, shell.winfo_width())
        shell_h = max(1, shell.winfo_height())

        start_x = source_widget.winfo_rootx() - shell_x
        start_y = source_widget.winfo_rooty() - shell_y
        start_w = max(28, source_widget.winfo_width())
        start_h = max(24, source_widget.winfo_height())

        existing_bar = getattr(self, "_shell_bottom_bar", None)
        if existing_bar is not None and existing_bar.winfo_exists() and existing_bar.winfo_width() > 1:
            target_x = existing_bar.winfo_x()
            target_y = existing_bar.winfo_y()
            target_w = max(1, existing_bar.winfo_width())
            target_h = max(1, existing_bar.winfo_height())
        else:
            target_x = 18
            target_w = max(1, shell_w - 36)
            target_h = 80
            target_y = max(0, shell_h - 90)

        # Mini-bar cover slot sits 13px from left edge (3px accent + 10px padx) and vertically centred.
        cov_target_x = target_x + 13
        cov_target_y = target_y + max(7, (target_h - 62) // 2)
        if cover_widget is not None and cover_widget.winfo_exists() and cover_widget.winfo_width() > 1:
            cov_start_x = cover_widget.winfo_rootx() - shell_x + max(0, (cover_widget.winfo_width() - 62) // 2)
            cov_start_y = cover_widget.winfo_rooty() - shell_y + max(0, (cover_widget.winfo_height() - 62) // 2)
        else:
            cov_start_x = start_x
            cov_start_y = start_y

        migrator = tk.Frame(shell, bg=ORANGE_ACCENT, bd=0, highlightthickness=1, highlightbackground=ORANGE_HL)
        left_accent = tk.Frame(migrator, bg=ORANGE_ACCENT, width=3)
        left_accent.pack(side="left", fill="y")
        text_box = tk.Frame(migrator, bg=ORANGE_ACCENT)
        text_box.pack(side="left", fill="both", expand=True, padx=(84, 14), pady=8)
        title_lbl = tk.Label(
            text_box, text=str(title or "Programme"),
            font=(DEFAULT_FONT, 12, "bold"), fg=ORANGE_ACCENT, bg=ORANGE_ACCENT, anchor="w",
        )
        title_lbl.pack(fill="x", pady=(6, 1))
        sub_lbl = tk.Label(
            text_box, text=translate(f"Last played  ·  {category}" if category else "Last played"),
            font=(DEFAULT_FONT, 9), fg=ORANGE_ACCENT, bg=ORANGE_ACCENT, anchor="w",
        )
        sub_lbl.pack(fill="x")

        floating_cover = self.generate_podcast_cover(
            shell, podcast_id, title, category, 62, 62,
            corner_radius=10, backdrop=MINI_BAR_BG,
        )

        migrator.place(x=start_x, y=start_y, width=start_w, height=start_h)
        floating_cover.place(x=cov_start_x, y=cov_start_y, width=62, height=62)
        tk.Misc.lift(migrator)
        tk.Misc.lift(floating_cover)

        duration = 0.360
        mig_state = {"progress": 0.0, "last_t": None}
        last_rect = [None]
        last_cov_pos = [None]
        last_bg = [ORANGE_ACCENT]

        def finish_migration():
            for w in (floating_cover, migrator):
                if w is not None and w.winfo_exists():
                    try:
                        w.destroy()
                    except tk.TclError:
                        pass
            if shell.winfo_exists():
                self._sync_bottom_bar(shell, show_bar=True, show_average=show_avg)
                bar = getattr(self, "_shell_bottom_bar", None)
                if bar is not None and bar.winfo_exists() and hasattr(bar, "_show_sim_notice"):
                    bar._show_sim_notice()
            self._finish_transition()

        def draw_migration():
            if not migrator.winfo_exists() or not shell.winfo_exists():
                finish_migration()
                return
            frame_t0 = monotonic()
            dt = 0.016 if mig_state["last_t"] is None else max(0.004, min(0.042, frame_t0 - mig_state["last_t"]))
            mig_state["last_t"] = frame_t0
            mig_state["progress"] = min(1.0, mig_state["progress"] + dt / duration)
            progress = mig_state["progress"]
            # Lively damped elastic spring for both the migrating bar and the flying cover art.
            eased = ease_out_elastic(progress, damping=4.5, frequency=1.30)
            clamped_color = round(max(0.0, min(1.0, 1.0 - (1.0 - progress) ** 3)) * 6) / 6.0

            cur_x = max(0, round(start_x + (target_x - start_x) * eased))
            cur_y = max(0, round(start_y + (target_y - start_y) * eased))
            cur_w = max(1, min(shell_w, round(start_w + (target_w - start_w) * eased)))
            cur_h = max(1, round(start_h + (target_h - start_h) * eased))

            cur_bg = blend_colour(ORANGE_ACCENT, MINI_BAR_BG, clamped_color)
            if cur_bg != last_bg[0]:
                migrator.configure(bg=cur_bg, highlightbackground=blend_colour(ORANGE_HL, ORANGE_ACCENT, clamped_color))
                text_box.configure(bg=cur_bg)
                text_fade = max(0.0, (progress - 0.28) / 0.72)
                title_lbl.configure(bg=cur_bg, fg=blend_colour(cur_bg, TEXT_WHITE, text_fade))
                sub_lbl.configure(bg=cur_bg, fg=blend_colour(cur_bg, TEXT_GRAY, text_fade))
                last_bg[0] = cur_bg

            rect = (cur_x, cur_y, cur_w, cur_h)
            if rect != last_rect[0]:
                migrator.place(x=cur_x, y=cur_y, width=cur_w, height=cur_h)
                last_rect[0] = rect

            if floating_cover.winfo_exists():
                # Gentle upward arc + elastic settle right into the mini-bar's 62x62 cover slot.
                arc_lift = -26.0 * (4.0 * progress * (1.0 - progress))
                cov_x = round(cov_start_x + (cov_target_x - cov_start_x) * eased)
                cov_y = round(cov_start_y + (cov_target_y - cov_start_y) * eased + arc_lift)
                cov_pos = (cov_x, cov_y)
                if cov_pos != last_cov_pos[0]:
                    floating_cover.place(x=cov_x, y=cov_y, width=62, height=62)
                    last_cov_pos[0] = cov_pos

            if progress < 1.0:
                spent_ms = (monotonic() - frame_t0) * 1000.0
                self.after(self._next_frame_delay(spent_ms, 16), draw_migration)
            else:
                finish_migration()

        draw_migration()

    def open_podcast_detail(
        self, podcast_id, title=None, category=None,
        source_card=None, source_cover=None, source_title=None,
    ):
        """Open a podcast's detail page by expanding directly from its card on the page."""
        if self._is_busy_transitioning():
            return
        if title is None or category is None:
            try:
                rec = self.get_single_podcast(podcast_id)
                if rec:
                    title = title if title is not None else rec[1]
                    category = category if category is not None else rec[2]
            except sqlite3.Error:
                pass
        shell = getattr(self, "_shell_box", None)
        has_source = (
            (source_card is not None and source_card.winfo_exists())
            or (source_cover is not None and source_cover.winfo_exists())
        )
        if shell is not None and shell.winfo_exists() and has_source and not self._is_reduced_motion():
            self.expand_card_to_detail(
                shell, source_card, source_cover, podcast_id,
                str(title or "Programme"), category or "",
                title_widget=source_title,
            )
            return
        if self._is_reduced_motion():
            self.show_detail(podcast_id)
            return
        self.transition_to(lambda: self.show_detail(podcast_id), "Programme details", direction=1)

    def expand_card_to_detail(
        self, shell, source_card, source_cover, podcast_id, title, category, title_widget=None,
    ):
        """Seamlessly expand a clicked podcast card and grow its cover art into the detail page."""
        if self._is_busy_transitioning() or not shell.winfo_exists():
            return
        if self._is_reduced_motion():
            self.show_detail(podcast_id)
            return
        canvas, _window = self._page_transition_target
        if not canvas.winfo_exists() or getattr(canvas, "_leaving_page", False):
            return

        area_frame = canvas.master
        shell_w = max(1, shell.winfo_width())
        shell_h = max(1, shell.winfo_height())
        target_y = area_frame.winfo_y()
        sh_rx, sh_ry = shell.winfo_rootx(), shell.winfo_rooty()

        card_w_ref = source_card if (source_card is not None and source_card.winfo_exists()) else source_cover
        if card_w_ref is not None and card_w_ref.winfo_exists() and card_w_ref.winfo_width() > 1:
            raw_x = card_w_ref.winfo_rootx() - sh_rx
            raw_y = card_w_ref.winfo_rooty() - sh_ry
            start_w = max(1, card_w_ref.winfo_width())
            start_h = max(1, card_w_ref.winfo_height())
            start_x = max(0, min(shell_w - 1, raw_x))
            start_y = max(target_y, min(shell_h - 1, raw_y))
            start_h = max(1, min(shell_h - start_y, start_h - max(0, target_y - raw_y)))
        else:
            start_x, start_y, start_w, start_h = 40, target_y + 40, 260, 320

        if source_cover is not None and source_cover.winfo_exists() and source_cover.winfo_width() > 1:
            cw = source_cover.winfo_width()
            ch = source_cover.winfo_height()
            cov_start_sz = max(48, min(cw, ch))
            cov_start_x = (source_cover.winfo_rootx() - sh_rx) + max(0, (cw - cov_start_sz) // 2)
            cov_start_y = max(target_y, source_cover.winfo_rooty() - sh_ry)
        else:
            cov_start_sz = min(140, max(62, min(start_w - 18, start_h - 18)))
            cov_start_x = start_x + 10
            cov_start_y = start_y + 10

        if title_widget is not None and title_widget.winfo_exists() and title_widget.winfo_width() > 1:
            rp_start_x = max(0, title_widget.winfo_rootx() - sh_rx)
            rp_start_y = max(target_y, title_widget.winfo_rooty() - sh_ry)
        else:
            rp_start_x = cov_start_x
            rp_start_y = min(shell_h - 40, cov_start_y + cov_start_sz + 8)

        self._animate_hero_to_detail(
            shell, podcast_id, title, category,
            start_rect=(start_x, start_y, start_w, start_h),
            cov_start_rect=(cov_start_x, cov_start_y, cov_start_sz),
            rp_start_pos=(rp_start_x, rp_start_y),
            start_bg=CARD_BG,
            accent_top_bar=False,
            source_kind="card",
        )

    def expand_bottom_bar_to_detail(self, shell, footer, podcast_id, title, category):
        """Seamlessly expand the bottom mini-bar and grow its cover art into the podcast detail page."""
        if self._is_busy_transitioning() or not shell.winfo_exists():
            return
        if self._is_reduced_motion():
            self.show_detail(podcast_id)
            return
        canvas, _window = self._page_transition_target
        if not canvas.winfo_exists() or getattr(canvas, "_leaving_page", False):
            return

        shell_w = max(1, shell.winfo_width())
        shell_h = max(1, shell.winfo_height())
        if footer is not None and footer.winfo_exists() and footer.winfo_width() > 1 and footer.winfo_height() > 1:
            start_x = footer.winfo_x()
            start_y = footer.winfo_y()
            start_w = max(1, footer.winfo_width())
            start_h = max(1, footer.winfo_height())
        else:
            start_x = 18
            start_w = max(1, shell_w - 36)
            start_h = 80
            start_y = max(0, shell_h - 90)
        cov_start_sz = 62
        cov_start_x = start_x + 13
        cov_start_y = start_y + max(7, (start_h - cov_start_sz) // 2)
        rp_start_x = cov_start_x + cov_start_sz + 11
        rp_start_y = start_y + 12

        self._animate_hero_to_detail(
            shell, podcast_id, title, category,
            start_rect=(start_x, start_y, start_w, start_h),
            cov_start_rect=(cov_start_x, cov_start_y, cov_start_sz),
            rp_start_pos=(rp_start_x, rp_start_y),
            start_bg=MINI_BAR_BG,
            accent_top_bar=True,
            source_kind="mini_bar",
        )

    def _animate_hero_to_detail(
        self, shell, podcast_id, title, category,
        start_rect, cov_start_rect, rp_start_pos, start_bg,
        accent_top_bar=False, source_kind="card",
    ):
        """Shared hero transition engine expanding a source surface + cover + title into the detail page."""
        if self._is_busy_transitioning() or not shell.winfo_exists():
            return
        if self._is_reduced_motion():
            self.show_detail(podcast_id)
            return
        canvas, _window = self._page_transition_target
        if not canvas.winfo_exists() or getattr(canvas, "_leaving_page", False):
            return
        try:
            saved_scroll = canvas.yview()[0]
        except tk.TclError:
            saved_scroll = 0.0
        self._detail_hero_origin = {
            "source": source_kind,
            "podcast_id": podcast_id,
            "title": title,
            "category": category,
            "tab": self._active_nav_tab,
            "scroll_y": saved_scroll,
            "target_rect": start_rect,
            "cov_target_rect": cov_start_rect,
            "rp_target_pos": rp_start_pos,
            "target_bg": start_bg,
            "accent_top_bar": accent_top_bar,
        }
        shell._expanding_bar = True
        canvas._leaving_page = True
        self._transition_active = True
        self.cancel_pending_render()

        area_frame = canvas.master
        shell_w = max(1, shell.winfo_width())
        shell_h = max(1, shell.winfo_height())
        start_x, start_y, start_w, start_h = start_rect
        cov_start_x, cov_start_y, cov_start_sz = cov_start_rect
        rp_start_x, rp_start_y = rp_start_pos
        target_y = area_frame.winfo_y()
        target_w = shell_w
        target_h = max(1, shell_h - target_y)

        # Match detail_view.py's exact cover size, typography, and hero position (using cached geometry when available).
        win_w = max(1024, self.winfo_width())
        win_h = max(700, self.winfo_height())
        detail_scale = max(0.92, min(1.75, min(win_w / 1180, win_h / 760)))
        text_scale = getattr(self, "_text_scale", 1.0)
        font_scale = detail_scale * text_scale
        cov_end_sz = round(max(248, min(420, 285 * detail_scale)))
        hero_gap = round(38 * detail_scale)
        title_wrap = round(max(400, min(720, 500 * detail_scale)))

        geom_key = (target_w, target_h, round(text_scale, 2))
        cached_geom = getattr(self, "_detail_hero_geom", {}).get(geom_key)
        if cached_geom is not None:
            approx_cov_x, approx_cov_y, cov_end_sz, approx_cat_x, approx_cat_y, approx_title_x, approx_title_y = cached_geom
        else:
            approx_cov_x = max(48, round((target_w - 16 - (cov_end_sz + hero_gap + title_wrap)) / 2))
            approx_cov_y = target_y + round(85 + 30 * detail_scale)
            approx_cat_x = approx_cov_x + cov_end_sz + hero_gap + 1
            approx_cat_y = approx_cov_y + 5
            approx_title_x = approx_cat_x
            approx_title_y = approx_cat_y + max(16, round(max(10, round(11 * font_scale)) * 1.45)) + 6

        # Use a single double-buffered tk.Canvas (zero child HWNDs) so background, accent bar, cover art,
        # and title paint atomically in one BitBlt per frame with zero tearing and lively elastic motion.
        is_mini = source_kind == "mini_bar"
        clip_top = target_y
        live_footer = getattr(self, "_shell_bottom_bar", None)
        if is_mini:
            clip_bottom = shell_h
        elif live_footer is not None and live_footer.winfo_exists() and live_footer.winfo_y() > target_y:
            clip_bottom = live_footer.winfo_y()
        else:
            clip_bottom = target_y + max(1, area_frame.winfo_height())

        expander = tk.Canvas(shell, bg=start_bg, bd=0, highlightthickness=0)
        accent_item = (
            expander.create_rectangle(0, 0, max(1, start_w), 3, fill=ORANGE_ACCENT, outline="")
            if accent_top_bar else None
        )

        cat_pt = max(10, round(11 * font_scale))
        title_pt = max(24, round(29 * font_scale))
        cat_font = (DEFAULT_FONT, cat_pt, "bold")
        title_font = (DEFAULT_FONT, title_pt, "bold")
        cat_text = translate(str(category or "Programme")).upper()
        title_text = str(title)
        cat_line_h = max(16, round(cat_pt * 1.45)) + 6

        cat_item = expander.create_text(
            -9999, -9999, text=cat_text, fill=start_bg, font=cat_font, anchor="nw",
        )
        title_item = expander.create_text(
            -9999, -9999, text=title_text, fill=start_bg, font=title_font,
            anchor="nw", width=title_wrap, justify="left",
        )

        if cached_geom is None:
            tb = expander.bbox(title_item)
            req_w = (tb[2] - tb[0]) if tb else title_wrap
            est_rp_w = max(round(460 * detail_scale), min(title_wrap, req_w))
            canvas_inner_w = max(1, target_w - 17)
            approx_cov_x = max(48, round((canvas_inner_w - (cov_end_sz + hero_gap + est_rp_w)) / 2))
            approx_cov_y = target_y + round(85 + 30 * detail_scale)
            approx_cat_x = approx_cov_x + cov_end_sz + hero_gap + 1
            approx_cat_y = approx_cov_y + 5
            approx_title_x = approx_cat_x
            approx_title_y = approx_cat_y + cat_line_h

        photo0, icon0, _bg0 = self._get_cover_photo(
            expander, podcast_id, title, category, cov_start_sz, cov_start_sz,
            corner_radius=8, backdrop=start_bg,
        )
        expander._cur_photo = photo0

        vis_x0 = max(0, round(start_x))
        vis_y0 = max(clip_top, round(start_y))
        vis_x1 = min(shell_w, round(start_x + start_w))
        vis_y1 = min(clip_bottom, round(start_y + start_h))
        expander.place(x=vis_x0, y=vis_y0, width=max(1, vis_x1 - vis_x0), height=max(1, vis_y1 - vis_y0))

        cx0 = cov_start_x + cov_start_sz / 2.0
        cy0 = cov_start_y + cov_start_sz / 2.0
        cx1 = approx_cov_x + cov_end_sz / 2.0
        cy1 = approx_cov_y + cov_end_sz / 2.0

        cover_item = expander.create_image(
            round(cx0 - vis_x0), round(cy0 - vis_y0), image=photo0, anchor="center",
        )
        icon_item = (
            expander.create_text(
                round(cx0 - vis_x0), round(cy0 - vis_y0), text=icon0, fill=TEXT_WHITE,
                font=(DEFAULT_FONT, max(11, cov_start_sz // 6), "bold"), anchor="center",
            )
            if icon0 is not None else None
        )
        tk.Misc.lift(expander)

        # Pre-warm 3 cover sizes (start, mid, end) instead of 6 to avoid startup stutter on low-end devices.
        mid_sz = round((cov_start_sz + cov_end_sz) / 2.0)
        size_steps = tuple(sorted({cov_start_sz, mid_sz, cov_end_sz}))
        cover_cache = {cov_start_sz: (photo0, icon0)}
        for step_sz in size_steps:
            if step_sz not in cover_cache:
                p_img, p_ico, _ = self._get_cover_photo(
                    expander, podcast_id, title, category, step_sz, step_sz,
                    corner_radius=8, backdrop=DARK_BG,
                )
                cover_cache[step_sz] = (p_img, p_ico)

        duration = 0.310 if sys.platform != "win32" else 0.370
        anim_st = {"progress": 0.0, "last_t": None}
        last_bg = [start_bg]
        last_fade_step = [-1]
        last_rect = [None]
        last_cov_sz = [cov_start_sz]
        last_cov_abs = [(cov_start_x, cov_start_y)]
        last_cat_abs = [(rp_start_x, rp_start_y)]
        last_title_abs = [(rp_start_x, rp_start_y + cat_line_h)]

        def cleanup():
            shell._expanding_bar = False
            if expander.winfo_exists():
                try:
                    expander.destroy()
                except tk.TclError:
                    pass
            self._finish_transition()

        def draw_expand():
            if not expander.winfo_exists() or not shell.winfo_exists():
                cleanup()
                return
            frame_start = monotonic()
            dt = 0.016 if anim_st["last_t"] is None else max(0.004, min(0.042, frame_start - anim_st["last_t"]))
            anim_st["last_t"] = frame_start
            anim_st["progress"] = min(1.0, anim_st["progress"] + dt / duration)
            progress = anim_st["progress"]
            # Outer surface expands swiftly and cleanly; cover & title use a juicy elastic spring inside the canvas.
            box_eased = min(1.0, max(0.0, ease_out_elastic(progress, damping=5.2, frequency=1.15)))
            hero_eased = ease_out_elastic(progress, damping=4.3, frequency=1.28)
            smooth_t = 1.0 - (1.0 - progress) ** 3

            cur_x = start_x * (1.0 - box_eased)
            cur_y = start_y + (target_y - start_y) * box_eased
            cur_w = start_w + (target_w - start_w) * box_eased
            cur_h = start_h + (target_h - start_h) * box_eased

            vx0 = max(0, round(cur_x))
            vy0 = max(clip_top, round(cur_y))
            vx1 = min(shell_w, round(cur_x + cur_w))
            vy1 = min(shell_h if progress >= 0.80 else clip_bottom, round(cur_y + cur_h))

            bg_step = round(smooth_t * 6) / 6.0
            cur_bg = blend_colour(start_bg, DARK_BG, bg_step)
            if cur_bg != last_bg[0]:
                expander.configure(bg=cur_bg)
                last_bg[0] = cur_bg

            rect = (vx0, vy0, max(1, vx1 - vx0), max(1, vy1 - vy0))
            if rect != last_rect[0]:
                expander.place(x=rect[0], y=rect[1], width=rect[2], height=rect[3])
                if accent_item is not None:
                    expander.coords(accent_item, 0, 0, rect[2], 3)
                last_rect[0] = rect

            desired_sz = cov_start_sz + (cov_end_sz - cov_start_sz) * max(0.0, min(1.08, hero_eased))
            quant_sz = min(size_steps, key=lambda s: abs(s - desired_sz))
            if quant_sz != last_cov_sz[0]:
                p_img, p_ico = cover_cache[quant_sz]
                expander._cur_photo = p_img
                expander.itemconfigure(cover_item, image=p_img)
                if icon_item is not None and p_ico is not None:
                    expander.itemconfigure(icon_item, font=(DEFAULT_FONT, max(11, quant_sz // 6), "bold"))
                last_cov_sz[0] = quant_sz

            cur_cx = cx0 + (cx1 - cx0) * hero_eased
            cur_cy = cy0 + (cy1 - cy0) * hero_eased
            rel_cx = round(cur_cx) - vx0
            rel_cy = round(cur_cy) - vy0
            expander.coords(cover_item, rel_cx, rel_cy)
            if icon_item is not None:
                expander.coords(icon_item, rel_cx, rel_cy)
            last_cov_abs[0] = (round(cur_cx - quant_sz / 2.0), round(cur_cy - quant_sz / 2.0))

            # Fade the detail-sized title in smoothly once expander is large enough (progress >= 0.30).
            if progress >= 0.30:
                fade_step = min(6, round(((progress - 0.30) / 0.55) * 6))
                if fade_step != last_fade_step[0]:
                    fade = fade_step / 6.0
                    expander.itemconfigure(cat_item, fill=blend_colour(cur_bg, ORANGE_HL, fade))
                    expander.itemconfigure(title_item, fill=blend_colour(cur_bg, TEXT_WHITE, fade))
                    last_fade_step[0] = fade_step
                cat_x = round(rp_start_x + (approx_cat_x - rp_start_x) * hero_eased)
                cat_y = round(rp_start_y + (approx_cat_y - rp_start_y) * hero_eased)
                tit_x = round(rp_start_x + (approx_title_x - rp_start_x) * hero_eased)
                tit_y = round(rp_start_y + cat_line_h + (approx_title_y - (rp_start_y + cat_line_h)) * hero_eased)
                last_cat_abs[0] = (cat_x, cat_y)
                last_title_abs[0] = (tit_x, tit_y)
                expander.coords(cat_item, cat_x - vx0, cat_y - vy0)
                expander.coords(title_item, tit_x - vx0, tit_y - vy0)

            if progress < 1.0:
                spent_ms = (monotonic() - frame_start) * 1000.0
                self.after(self._next_frame_delay(spent_ms, 16), draw_expand)
            else:
                def handoff_to_detail():
                    if not expander.winfo_exists() or not shell.winfo_exists():
                        cleanup()
                        return
                    expander.configure(bg=DARK_BG)
                    expander.place(x=0, y=target_y, width=target_w, height=target_h)
                    expander.itemconfigure(cat_item, fill=ORANGE_HL)
                    expander.itemconfigure(title_item, fill=TEXT_WHITE)

                    self.show_detail(podcast_id)
                    if not expander.winfo_exists() or not shell.winfo_exists():
                        cleanup()
                        return
                    # Lift expander BEFORE update_idletasks so the newly built detail page never flashes on top.
                    tk.Misc.lift(expander)
                    self.update_idletasks()
                    tk.Misc.lift(expander)

                    holder = getattr(self, "_detail_cover_holder", None)
                    dw = getattr(self, "_detail_widgets", {}) or {}
                    cat_lbl = dw.get("category_label")
                    tit_lbl = dw.get("title_label")
                    sh_rx, sh_ry = shell.winfo_rootx(), shell.winfo_rooty()

                    # Measure exact pixel geometry of the real cover, category label, and title label on detail_view.
                    if holder is not None and holder.winfo_exists() and holder.winfo_width() > 1:
                        final_x = holder.winfo_rootx() - sh_rx
                        final_y = holder.winfo_rooty() - sh_ry
                        final_sz = max(cov_start_sz, holder.winfo_width())
                    else:
                        final_x, final_y, final_sz = approx_cov_x, approx_cov_y, cov_end_sz

                    if cat_lbl is not None and cat_lbl.winfo_exists() and cat_lbl.winfo_width() > 1:
                        # Account for tk.Label's 1px default internal padx/pady so text aligns pixel-for-pixel.
                        final_cat_x = cat_lbl.winfo_rootx() - sh_rx + 1
                        final_cat_y = cat_lbl.winfo_rooty() - sh_ry + 1
                        try:
                            expander.itemconfigure(cat_item, font=cat_lbl.cget("font"))
                        except tk.TclError:
                            pass
                    else:
                        final_cat_x, final_cat_y = approx_cat_x, approx_cat_y

                    if tit_lbl is not None and tit_lbl.winfo_exists() and tit_lbl.winfo_width() > 1:
                        final_title_x = tit_lbl.winfo_rootx() - sh_rx + 1
                        final_title_y = tit_lbl.winfo_rooty() - sh_ry + 1
                        try:
                            expander.itemconfigure(
                                title_item,
                                font=tit_lbl.cget("font"),
                                width=max(200, int(tit_lbl.cget("wraplength"))),
                            )
                        except (tk.TclError, ValueError, TypeError):
                            pass
                    else:
                        final_title_x, final_title_y = approx_title_x, approx_title_y

                    geom_cache = getattr(self, "_detail_hero_geom", None)
                    if geom_cache is None:
                        geom_cache = {}
                        self._detail_hero_geom = geom_cache
                    geom_cache[geom_key] = (
                        final_x, final_y, final_sz,
                        final_cat_x, final_cat_y, final_title_x, final_title_y,
                    )

                    if last_cov_sz[0] != final_sz:
                        p_img, p_ico, _ = self._get_cover_photo(
                            expander, podcast_id, title, category, final_sz, final_sz,
                            corner_radius=8, backdrop=DARK_BG,
                        )
                        expander._cur_photo = p_img
                        expander.itemconfigure(cover_item, image=p_img)
                        if icon_item is not None and p_ico is not None:
                            expander.itemconfigure(icon_item, font=(DEFAULT_FONT, max(11, final_sz // 6), "bold"))
                        last_cov_sz[0] = final_sz

                    # Collect exact coordinates of the detail controls so they expand elastically from nowhere
                    # instead of popping in abruptly when expander is dropped.
                    def _rounded_pts(rx0, ry0, rx1, ry1, rad):
                        rad = max(1.0, min(rad, (rx1 - rx0) / 2.0, (ry1 - ry0) / 2.0))
                        return (
                            rx0 + rad, ry0, rx1 - rad, ry0, rx1, ry0, rx1, ry0 + rad,
                            rx1, ry1 - rad, rx1, ry1, rx1 - rad, ry1, rx0 + rad, ry1,
                            rx0, ry1, rx0, ry1 - rad, rx0, ry0 + rad, rx0, ry0,
                        )

                    play_w = dw.get("play_canvas")
                    play_spec = None
                    if play_w is not None and play_w.winfo_exists() and play_w.winfo_width() > 4:
                        psz = min(play_w.winfo_width(), play_w.winfo_height())
                        pcx = (play_w.winfo_rootx() - sh_rx) + play_w.winfo_width() / 2.0
                        pcy = (play_w.winfo_rooty() - sh_ry - target_y) + play_w.winfo_height() / 2.0
                        oval_id = expander.create_oval(pcx, pcy, pcx, pcy, fill=ORANGE_ACCENT, outline="")
                        tri_id = expander.create_polygon(pcx, pcy, pcx, pcy, pcx, pcy, fill="#000000", outline="")
                        play_spec = (oval_id, tri_id, pcx, pcy, psz)

                    pill_specs = []
                    from gui_parts.theme import ACTION_BTN_BG, ACTION_BTN_FG, DIVIDER_LINE, GOLD_STAR, SUBCARD_BG
                    for b_idx, (b_key, is_prim, stagger) in enumerate((
                        ("fav_button", bool(dw.get("fav_primary")), 0.08),
                        ("rate_button", False, 0.16),
                        ("back_btn", False, 0.04),
                    )):
                        btn_w = dw.get(b_key)
                        if btn_w is not None and btn_w.winfo_exists() and btn_w.winfo_width() > 10:
                            y_sh = getattr(btn_w, "_hover_y_shift", 0)
                            h_sz = getattr(btn_w, "_hover_size", None)
                            bw = (h_sz[0] + 2) if h_sz else max(12, btn_w.winfo_width() - 10)
                            bh = (h_sz[1] + 2) if h_sz else max(12, btn_w.winfo_height() - 10 - y_sh * 2)
                            bcx = (btn_w.winfo_rootx() - sh_rx) + btn_w.winfo_width() / 2.0
                            bcy = (btn_w.winfo_rooty() - sh_ry - target_y) + btn_w.winfo_height() / 2.0 - y_sh
                            fill_c = ORANGE_ACCENT if is_prim else (INPUT_BG if b_key == "back_btn" else ACTION_BTN_BG)
                            fg_c = PRIMARY_BTN_FG if is_prim else (TEXT_GRAY if b_key == "back_btn" else ACTION_BTN_FG)
                            poly_id = expander.create_polygon(bcx, bcy, bcx, bcy, smooth=True, fill=fill_c, outline="")
                            txt_id = expander.create_text(
                                bcx, bcy + y_sh, text=btn_w.cget("text"), fill=fill_c,
                                font=btn_w.cget("font"), anchor="center",
                            )
                            pill_specs.append((poly_id, txt_id, bcx, bcy, bw, bh, fill_c, fg_c, stagger))

                    fade_items = []
                    for lbl_key, target_fg in (
                        ("now_playing_lbl", ORANGE_HL),
                        ("meta_label", TEXT_GRAY),
                        ("avg_label", GOLD_STAR),
                        ("listen_label", TEXT_WHITE),
                    ):
                        lw = dw.get(lbl_key)
                        if lw is not None and lw.winfo_exists() and lw.winfo_width() > 2:
                            lx = lw.winfo_rootx() - sh_rx + 1
                            ly = lw.winfo_rooty() - sh_ry - target_y + 1
                            tid = expander.create_text(
                                lx, ly, text=lw.cget("text"), fill=DARK_BG,
                                font=lw.cget("font"), anchor="nw",
                            )
                            fade_items.append((tid, DARK_BG, target_fg, None))

                    for rule_key in ("top_rule", "bottom_rule", "v_divider"):
                        rw = dw.get(rule_key)
                        if rw is not None and rw.winfo_exists() and rw.winfo_width() > 0 and rw.winfo_height() > 0:
                            rx = rw.winfo_rootx() - sh_rx
                            ry = rw.winfo_rooty() - sh_ry - target_y
                            rid = expander.create_rectangle(
                                rx, ry, rx + rw.winfo_width(), ry + rw.winfo_height(),
                                fill=DARK_BG, outline="",
                            )
                            fade_items.append((rid, DARK_BG, DIVIDER_LINE, None))

                    sub_w = dw.get("sub_card")
                    if sub_w is not None and sub_w.winfo_exists() and sub_w.winfo_width() > 20:
                        sx0 = sub_w.winfo_rootx() - sh_rx + 1
                        sy0 = sub_w.winfo_rooty() - sh_ry - target_y + 1
                        sx1 = sx0 + sub_w.winfo_width() - 2
                        sy1 = sy0 + sub_w.winfo_height() - 2
                        sid = expander.create_polygon(
                            *_rounded_pts(sx0, sy0, sx1, sy1, 12),
                            smooth=True, fill=DARK_BG, outline=DARK_BG,
                        )
                        fade_items.append((sid, DARK_BG, SUBCARD_BG, BORDER_LINE))
                        for sub_key, sub_fg in (
                            ("listening_heading", ORANGE_HL),
                            ("summary_label", dw.get("summary_color", TEXT_WHITE)),
                            ("rating_caption", TEXT_GRAY),
                        ):
                            sw = dw.get(sub_key)
                            if sw is not None and sw.winfo_exists() and sw.winfo_width() > 2:
                                slx = sw.winfo_rootx() - sh_rx + 1
                                sly = sw.winfo_rooty() - sh_ry - target_y + 1
                                stid = expander.create_text(
                                    slx, sly, text=sw.cget("text"), fill=DARK_BG,
                                    font=sw.cget("font"), anchor="nw",
                                )
                                fade_items.append((stid, DARK_BG, sub_fg, None))
                        sc_w = dw.get("star_canvas")
                        sc_st = dw.get("star_state")
                        if sc_w is not None and sc_w.winfo_exists() and sc_st is not None:
                            import math as _m
                            from gui_parts.theme import STAR_EMPTY
                            sc_x0 = sc_w.winfo_rootx() - sh_rx
                            sc_y0 = sc_w.winfo_rooty() - sh_ry - target_y
                            s_sz = sc_st["size"]
                            s_gap = sc_st["gap"]
                            s_active = sc_st["score"]
                            r_out = s_sz * 0.46
                            r_in = s_sz * 0.20
                            scy = sc_y0 + s_sz / 2.0
                            for s_i in range(1, 6):
                                scx = sc_x0 + (s_i - 1) * (s_sz + s_gap) + s_sz / 2.0
                                pts = []
                                for pt_i in range(10):
                                    ang = _m.radians(-90 + pt_i * 36)
                                    rad = r_out if pt_i % 2 == 0 else r_in
                                    pts.extend((scx + rad * _m.cos(ang), scy + rad * _m.sin(ang)))
                                star_id = expander.create_polygon(pts, fill=DARK_BG, outline="")
                                fade_items.append((star_id, DARK_BG, GOLD_STAR if s_i <= s_active else STAR_EMPTY, None))

                    from_x, from_y = last_cov_abs[0]
                    from_cat_x, from_cat_y = last_cat_abs[0]
                    from_tit_x, from_tit_y = last_title_abs[0]
                    bloom_dur = 0.290
                    bloom_st = {"progress": 0.0, "last_t": None}

                    def draw_bloom():
                        if not expander.winfo_exists() or not shell.winfo_exists():
                            cleanup()
                            return
                        f_t0 = monotonic()
                        dt = 0.016 if bloom_st["last_t"] is None else max(0.004, min(0.042, f_t0 - bloom_st["last_t"]))
                        bloom_st["last_t"] = f_t0
                        bloom_st["progress"] = min(1.0, bloom_st["progress"] + dt / bloom_dur)
                        bp = bloom_st["progress"]

                        # 1. Pixel-perfectly align cover, category, and title during the first 30% of the bloom.
                        ap = min(1.0, bp / 0.30)
                        ae = 1.0 - (1.0 - ap) ** 2
                        sx = round(from_x + (final_x - from_x) * ae + final_sz / 2.0)
                        sy = round(from_y + (final_y - from_y) * ae + final_sz / 2.0) - target_y
                        expander.coords(cover_item, sx, sy)
                        if icon_item is not None:
                            expander.coords(icon_item, sx, sy)
                        cx_t = round(from_cat_x + (final_cat_x - from_cat_x) * ae)
                        cy_t = round(from_cat_y + (final_cat_y - from_cat_y) * ae) - target_y
                        tx_t = round(from_tit_x + (final_title_x - from_tit_x) * ae)
                        ty_t = round(from_tit_y + (final_title_y - from_tit_y) * ae) - target_y
                        expander.coords(cat_item, cx_t, cy_t)
                        expander.coords(title_item, tx_t, ty_t)

                        # 2. Expand the circular Play button elastically from 0 -> full size.
                        if play_spec is not None:
                            oval_id, tri_id, pcx, pcy, psz = play_spec
                            pe = max(0.0, ease_out_elastic(bp, damping=3.8, frequency=1.45))
                            rad = max(0.5, ((psz / 2.0) - 5.0) * pe)
                            expander.coords(oval_id, pcx - rad, pcy - rad, pcx + rad, pcy + rad)
                            ts = max(0.0, pe)
                            s_pts = (
                                pcx + (-psz * 0.11) * ts, pcy + (-psz * 0.24) * ts,
                                pcx + (-psz * 0.11) * ts, pcy + (psz * 0.24) * ts,
                                pcx + (psz * 0.26) * ts, pcy,
                            )
                            expander.coords(tri_id, *s_pts)

                        # 3. Expand each pill button elastically from nowhere (0x0 center -> full rounded pill).
                        for poly_id, txt_id, bcx, bcy, bw, bh, fill_c, fg_c, stag in pill_specs:
                            lp = max(0.0, min(1.0, (bp - stag) / max(0.20, 1.0 - stag)))
                            if lp <= 0.0:
                                continue
                            pe = max(0.0, ease_out_elastic(lp, damping=3.8, frequency=1.45))
                            hw = max(1.0, (bw / 2.0) * pe)
                            hh = max(1.0, (bh / 2.0) * pe)
                            expander.coords(poly_id, *_rounded_pts(bcx - hw, bcy - hh, bcx + hw, bcy + hh, 10.0 * min(1.0, pe)))
                            tf = max(0.0, min(1.0, (lp - 0.30) / 0.55))
                            expander.itemconfigure(txt_id, fill=blend_colour(fill_c, fg_c, tf))

                        # 4. Smoothly fade in metadata, divider rules, and bottom listening card (including border & text).
                        fp = min(1.0, bp / 0.80)
                        for fid, c0, c1, out_c in fade_items:
                            if out_c is not None:
                                expander.itemconfigure(
                                    fid,
                                    fill=blend_colour(c0, c1, fp),
                                    outline=blend_colour(c0, out_c, fp),
                                )
                            else:
                                expander.itemconfigure(fid, fill=blend_colour(c0, c1, fp))

                        if bp < 1.0:
                            spent = (monotonic() - f_t0) * 1000.0
                            self.after(self._next_frame_delay(spent, 16), draw_bloom)
                        else:
                            cleanup()

                    draw_bloom()

                self.after(1, handoff_to_detail)

        draw_expand()

    def shrink_detail_to_bottom_bar(self, destination, title, category, podcast_id=None, on_complete=None):
        """Shrink the podcast detail view down into the destination tab's bottom mini-bar."""
        shell = getattr(self, "_shell_box", None)
        shell_w = max(1, shell.winfo_width()) if (shell is not None and shell.winfo_exists()) else max(1, self.winfo_width())
        shell_h = max(1, shell.winfo_height()) if (shell is not None and shell.winfo_exists()) else max(1, self.winfo_height())
        if podcast_id is None and self._active_detail_podcast is not None:
            podcast_id = self._active_detail_podcast[0]
        start_x = 18
        start_w = max(1, shell_w - 36)
        start_h = 80
        start_y = max(0, shell_h - 90)
        cov_sz = 62
        cov_x = start_x + 13
        cov_y = start_y + max(7, (start_h - cov_sz) // 2)
        origin = {
            "source": "mini_bar",
            "podcast_id": podcast_id,
            "title": title,
            "category": category,
            "tab": None,
            "scroll_y": 0.0,
            "target_rect": (start_x, start_y, start_w, start_h),
            "cov_target_rect": (cov_x, cov_y, cov_sz),
            "rp_target_pos": (cov_x + cov_sz + 11, start_y + 12),
            "target_bg": MINI_BAR_BG,
            "accent_top_bar": True,
        }
        self.shrink_detail_to_origin(destination, origin, restore_scroll=False, on_complete=on_complete)

    def shrink_detail_to_origin(self, destination, origin, restore_scroll=False, on_complete=None):
        """Reverse hero transition: shrink the detail view + cover art back into its source card or mini-bar."""
        shell = getattr(self, "_shell_box", None)
        canvas, _window = self._page_transition_target
        if shell is None or not shell.winfo_exists() or not canvas.winfo_exists():
            self._tab_transition_direction = None
            self._detail_hero_origin = None
            self._finish_transition()
            destination()
            if on_complete is not None:
                self.after(16, on_complete)
            return

        area_frame = canvas.master
        shell_w = max(1, shell.winfo_width())
        shell_h = max(1, shell.winfo_height())
        start_x = 0
        start_y = area_frame.winfo_y()
        start_w = shell_w
        start_h = max(1, shell_h - start_y)

        if start_w <= 1 or start_h <= 1:
            self._tab_transition_direction = None
            self._detail_hero_origin = None
            self._finish_transition()
            destination()
            return

        # Measure exact current detail cover and title/category coordinates before rebuilding destination.
        shell.update_idletasks()
        sh_rx, sh_ry = shell.winfo_rootx(), shell.winfo_rooty()
        holder = getattr(self, "_detail_cover_holder", None)
        rp_widget = getattr(self, "_detail_right_pane", None)
        win_w = max(1024, self.winfo_width())
        win_h = max(700, self.winfo_height())
        detail_scale = max(0.92, min(1.75, min(win_w / 1180, win_h / 760)))
        text_scale = getattr(self, "_text_scale", 1.0)
        font_scale = detail_scale * text_scale
        title_wrap = round(max(400, min(720, 500 * detail_scale)))

        if holder is not None and holder.winfo_exists() and holder.winfo_width() > 1:
            cov_start_x = holder.winfo_rootx() - sh_rx
            cov_start_y = holder.winfo_rooty() - sh_ry
            cov_start_sz = max(62, holder.winfo_width())
        else:
            cov_start_sz = round(max(248, min(420, 285 * detail_scale)))
            cov_start_x = max(48, round((shell_w - cov_start_sz - 460) / 2))
            cov_start_y = start_y + round(85 + 30 * detail_scale)

        if rp_widget is not None and rp_widget.winfo_exists() and rp_widget.winfo_width() > 1:
            rp_start_x = rp_widget.winfo_rootx() - sh_rx
            rp_start_y = rp_widget.winfo_rooty() - sh_ry
        else:
            rp_start_x = cov_start_x + cov_start_sz + round(38 * detail_scale)
            rp_start_y = cov_start_y + 4

        podcast_id = origin.get("podcast_id")
        title = str(origin.get("title") or "Programme")
        category = origin.get("category") or ""
        target_bg = origin.get("target_bg") or CARD_BG
        accent_top_bar = bool(origin.get("accent_top_bar"))
        target_box = list(origin.get("target_rect", (18, max(start_y, shell_h - 90), max(1, shell_w - 36), 80)))
        cov_target = list(origin.get("cov_target_rect", (target_box[0] + 13, target_box[1] + 9, 62)))
        rp_target = list(origin.get("rp_target_pos", (cov_target[0] + cov_target[2] + 11, target_box[1] + 12)))

        # Build one double-buffered tk.Canvas (zero child HWNDs) so the shrinking card, cover art, and title
        # paint atomically in one BitBlt per frame with zero stutter and lively elastic motion.
        shell._expanding_bar = True
        self._tab_transition_direction = None
        self._transition_active = True
        self._detail_hero_origin = None
        is_mini = origin.get("source") == "mini_bar"

        shrinker = tk.Canvas(shell, bg=DARK_BG, bd=0, highlightthickness=0)
        accent_item = (
            shrinker.create_rectangle(0, 0, start_w, 3, fill=ORANGE_ACCENT, outline="")
            if accent_top_bar else None
        )

        shrink_cat_pt = max(9, round(10 * min(1.25, font_scale)))
        shrink_title_pt = max(14, round(18 * min(1.25, font_scale)))
        cat_line_h = max(14, round(shrink_cat_pt * 1.45)) + 4
        cat_item = shrinker.create_text(
            rp_start_x - start_x, rp_start_y - start_y,
            text=translate(str(category or "Programme")).upper(),
            fill=ORANGE_HL, font=(DEFAULT_FONT, shrink_cat_pt, "bold"), anchor="nw",
        )
        title_item = shrinker.create_text(
            rp_start_x - start_x, rp_start_y - start_y + cat_line_h,
            text=title, fill=TEXT_WHITE, font=(DEFAULT_FONT, shrink_title_pt, "bold"),
            anchor="nw", width=min(title_wrap, 360), justify="left",
        )

        photo0, icon0, _bg0 = self._get_cover_photo(
            shrinker, podcast_id, title, category, cov_start_sz, cov_start_sz,
            corner_radius=8, backdrop=DARK_BG,
        )
        shrinker._cur_photo = photo0
        cx0 = cov_start_x + cov_start_sz / 2.0
        cy0 = cov_start_y + cov_start_sz / 2.0
        cover_item = shrinker.create_image(
            round(cx0 - start_x), round(cy0 - start_y), image=photo0, anchor="center",
        )
        icon_item = (
            shrinker.create_text(
                round(cx0 - start_x), round(cy0 - start_y), text=icon0, fill=TEXT_WHITE,
                font=(DEFAULT_FONT, max(11, cov_start_sz // 6), "bold"), anchor="center",
            )
            if icon0 is not None else None
        )

        shrinker.place(x=start_x, y=start_y, width=start_w, height=start_h)
        tk.Misc.lift(shrinker)

        # Build the destination page underneath while fully covered by shrinker.
        destination()
        if not shell.winfo_exists() or not shrinker.winfo_exists():
            self._finish_transition()
            return

        # Pre-render the visible batch of cards underneath shrinker BEFORE animation starts so grid pages
        # (For you, Favourites, History, Ratings, Search) are already populated rather than blank during shrink.
        self._prerender_initial_batch(6)
        saved_scroll = float(origin.get("scroll_y") or 0.0)
        new_target = getattr(self, "_page_transition_target", None)
        if restore_scroll and saved_scroll > 0.0 and new_target:
            self._prerender_initial_batch(6)
        if new_target:
            new_canvas, _new_win = new_target
            if new_canvas.winfo_exists():
                try:
                    new_canvas.update_idletasks()
                    if self.current_page is not None and self.current_page.winfo_exists():
                        new_canvas.configure(
                            scrollregion=(0, 0, self.current_page.winfo_reqwidth(), self.current_page.winfo_reqheight())
                        )
                    if restore_scroll and saved_scroll > 0.0:
                        new_canvas.yview_moveto(saved_scroll)
                except tk.TclError:
                    pass

        shell.update_idletasks()
        tk.Misc.lift(shrinker)
        sh_rx, sh_ry = shell.winfo_rootx(), shell.winfo_rooty()

        # Visible clip region: card returns stay inside the scroll area (never over the mini-bar);
        # mini-bar returns may travel down into the footer.
        new_area = getattr(self, "_shell_area_frame", None)
        if new_area is None or not new_area.winfo_exists():
            new_area = area_frame
        if is_mini:
            clip_top, clip_bottom = start_y, shell_h
        else:
            clip_top = new_area.winfo_y()
            dest_footer = getattr(self, "_shell_bottom_bar", None)
            if dest_footer is not None and dest_footer.winfo_exists() and dest_footer.winfo_y() > clip_top:
                clip_bottom = dest_footer.winfo_y()
            else:
                clip_bottom = clip_top + max(1, new_area.winfo_height())

        if is_mini:
            dest_footer = getattr(self, "_shell_bottom_bar", None)
            if dest_footer is not None and dest_footer.winfo_exists() and dest_footer.winfo_width() > 1 and dest_footer.winfo_height() > 1:
                fx = dest_footer.winfo_x()
                fy = dest_footer.winfo_y()
                fw = dest_footer.winfo_width()
                fh = dest_footer.winfo_height()
                target_box[:] = [fx, fy, fw, fh]
                cov_target[:] = [fx + 13, fy + max(7, (fh - 62) // 2), 62]
                rp_target[:] = [fx + 13 + 62 + 11, fy + 12]
        else:
            live = self._find_live_podcast_card(podcast_id, target_box, sh_rx, sh_ry)
            if live is not None:
                card_rect, cover_rect = live
                dx = card_rect[0] - target_box[0]
                dy = card_rect[1] - target_box[1]
                target_box[:] = list(card_rect)
                cov_target[:] = list(cover_rect)
                rp_target[:] = [rp_target[0] + dx, rp_target[1] + dy]

        end_x, end_y, end_w, end_h = target_box
        cov_end_x, cov_end_y, cov_end_sz = cov_target
        rp_end_x, rp_end_y = rp_target
        cx1 = cov_end_x + cov_end_sz / 2.0
        cy1 = cov_end_y + cov_end_sz / 2.0

        # Pre-warm 3 cover sizes (start, mid, end) with constant target_bg backdrop for snappy low-end performance.
        mid_sz = round((cov_start_sz + cov_end_sz) / 2.0)
        size_steps = tuple(sorted({cov_start_sz, mid_sz, cov_end_sz}))
        cover_cache = {cov_start_sz: (photo0, icon0)}
        for step_sz in size_steps:
            if step_sz not in cover_cache:
                p_img, p_ico, _ = self._get_cover_photo(
                    shrinker, podcast_id, title, category, step_sz, step_sz,
                    corner_radius=8, backdrop=target_bg,
                )
                cover_cache[step_sz] = (p_img, p_ico)

        duration = 0.290 if sys.platform != "win32" else 0.360
        frame_ms = 16
        anim_st = {"progress": 0.0, "last_t": None}
        last_bg = [DARK_BG]
        last_fade_step = [-1]
        preview_hidden = [False]
        shrinker_hidden = [False]
        last_rect = [None]
        last_cov_sz = [cov_start_sz]

        def cleanup():
            if shell.winfo_exists():
                shell._expanding_bar = False
            if shrinker.winfo_exists():
                try:
                    shrinker.destroy()
                except tk.TclError:
                    pass
            if on_complete is not None and shell.winfo_exists():
                # Skip background batch rendering for the intermediate page since we immediately slide to the next tab.
                self._transition_active = False
                self.after(16, on_complete)
            else:
                self._finish_transition()

        def draw_shrink():
            if not shrinker.winfo_exists() or not shell.winfo_exists():
                cleanup()
                return
            frame_start = monotonic()
            dt = 0.016 if anim_st["last_t"] is None else max(0.004, min(0.042, frame_start - anim_st["last_t"]))
            anim_st["last_t"] = frame_start
            anim_st["progress"] = min(1.0, anim_st["progress"] + dt / duration)
            progress = anim_st["progress"]
            # Outer card surface contracts smoothly (no re-covering underlying cards or mini-bar);
            # cover art inside the canvas uses a juicy elastic spring for tactile snap-back.
            box_eased = 1.0 - (1.0 - progress) ** 3.4
            hero_eased = ease_out_elastic(progress, damping=4.5, frequency=1.25)

            bg_step = round(box_eased * 6) / 6.0
            cur_bg = blend_colour(DARK_BG, target_bg, bg_step)

            cur_x = start_x + (end_x - start_x) * box_eased
            cur_y = start_y + (end_y - start_y) * box_eased
            cur_w = start_w + (end_w - start_w) * box_eased
            cur_h = start_h + (end_h - start_h) * box_eased

            vis_x0 = max(0, round(cur_x))
            vis_y0 = max(clip_top, round(cur_y))
            vis_x1 = min(shell_w, round(cur_x + cur_w))
            vis_y1 = min(clip_bottom, round(cur_y + cur_h))

            if vis_x1 - vis_x0 < 1 or vis_y1 - vis_y0 < 1:
                if not shrinker_hidden[0]:
                    shrinker.place_forget()
                    shrinker_hidden[0] = True
            else:
                if shrinker_hidden[0]:
                    shrinker_hidden[0] = False
                    last_rect[0] = None
                rect = (vis_x0, vis_y0, vis_x1 - vis_x0, vis_y1 - vis_y0)
                if rect != last_rect[0]:
                    shrinker.place(x=rect[0], y=rect[1], width=rect[2], height=rect[3])
                    if accent_item is not None:
                        shrinker.coords(accent_item, 0, 0, rect[2], 3)
                    last_rect[0] = rect

            if cur_bg != last_bg[0]:
                shrinker.configure(bg=cur_bg)
                last_bg[0] = cur_bg

            desired_sz = cov_start_sz + (cov_end_sz - cov_start_sz) * max(0.0, min(1.06, hero_eased))
            quant_sz = min(size_steps, key=lambda s: abs(s - desired_sz))
            if quant_sz != last_cov_sz[0]:
                p_img, p_ico = cover_cache[quant_sz]
                shrinker._cur_photo = p_img
                shrinker.itemconfigure(cover_item, image=p_img)
                if icon_item is not None and p_ico is not None:
                    shrinker.itemconfigure(icon_item, font=(DEFAULT_FONT, max(11, quant_sz // 6), "bold"))
                last_cov_sz[0] = quant_sz

            rel_cx = round(cx0 + (cx1 - cx0) * hero_eased) - vis_x0
            rel_cy = round(cy0 + (cy1 - cy0) * hero_eased) - vis_y0
            shrinker.coords(cover_item, rel_cx, rel_cy)
            if icon_item is not None:
                shrinker.coords(icon_item, rel_cx, rel_cy)

            if not preview_hidden[0]:
                if progress >= 0.35:
                    shrinker.delete(cat_item, title_item)
                    preview_hidden[0] = True
                else:
                    fade_step = round((progress / 0.35) * 4)
                    if fade_step != last_fade_step[0]:
                        fade = fade_step / 4.0
                        shrinker.itemconfigure(cat_item, fill=blend_colour(ORANGE_HL, cur_bg, fade))
                        shrinker.itemconfigure(title_item, fill=blend_colour(TEXT_WHITE, cur_bg, fade))
                        last_fade_step[0] = fade_step
                    rx = round(rp_start_x + (rp_end_x - rp_start_x) * hero_eased) - vis_x0
                    ry = round(rp_start_y + (rp_end_y - rp_start_y) * hero_eased) - vis_y0
                    shrinker.coords(cat_item, rx, ry)
                    shrinker.coords(title_item, rx, ry + cat_line_h)

            if progress < 1.0:
                spent_ms = (monotonic() - frame_start) * 1000.0
                self.after(self._next_frame_delay(spent_ms, frame_ms), draw_shrink)
            else:
                cleanup()

        self.update_idletasks()
        draw_shrink()

    def _find_live_podcast_card(self, podcast_id, near_rect, sh_rx, sh_ry):
        """Locate a rendered podcast card for podcast_id on the current page (closest to near_rect)."""
        page = getattr(self, "current_page", None)
        if page is None or not page.winfo_exists():
            return None
        best = None
        best_dist = None
        stack = [page]
        target_str = str(podcast_id)
        while stack:
            widget = stack.pop()
            canvas_cards = getattr(widget, "_canvas_card_rects", None)
            if canvas_cards is not None and target_str in canvas_cards:
                card_proxy, cover_proxy, _pid, _t, _c, csz = canvas_cards[target_str]
                try:
                    if card_proxy.winfo_ismapped() and cover_proxy.winfo_exists():
                        cx = card_proxy.winfo_rootx() - sh_rx
                        cy = card_proxy.winfo_rooty() - sh_ry
                        card_rect = (cx, cy, card_proxy.winfo_width(), card_proxy.winfo_height())
                        cover_rect = (
                            cover_proxy.winfo_rootx() - sh_rx,
                            cover_proxy.winfo_rooty() - sh_ry,
                            csz,
                        )
                        dist = abs(cx - near_rect[0]) + abs(cy - near_rect[1])
                        if best_dist is None or dist < best_dist:
                            best, best_dist = (card_rect, cover_rect), dist
                except tk.TclError:
                    pass
                continue
            meta = getattr(widget, "_cover_meta", None)
            if meta is not None and str(meta[2]) == target_str:
                cover = meta[1]
                try:
                    if widget.winfo_ismapped() and cover.winfo_exists() and cover.winfo_width() > 1:
                        cx = widget.winfo_rootx() - sh_rx
                        cy = widget.winfo_rooty() - sh_ry
                        card_rect = (cx, cy, widget.winfo_width(), widget.winfo_height())
                        cw, ch = cover.winfo_width(), cover.winfo_height()
                        csz = max(48, min(cw, ch))
                        cover_rect = (
                            cover.winfo_rootx() - sh_rx + max(0, (cw - csz) // 2),
                            cover.winfo_rooty() - sh_ry + max(0, (ch - csz) // 2),
                            csz,
                        )
                        dist = abs(cx - near_rect[0]) + abs(cy - near_rect[1])
                        if best_dist is None or dist < best_dist:
                            best, best_dist = (card_rect, cover_rect), dist
                except tk.TclError:
                    pass
                continue
            try:
                stack.extend(widget.winfo_children())
            except tk.TclError:
                pass
        return best

    def _is_scrolling(self):
        """Return True while the user is actively scrolling so hover animations don't stutter frames."""
        return monotonic() < getattr(self, "_scroll_priority_until", 0.0)

    def bind_page_scroll(self, canvas, scrollbar):
        """Coalesced 60Hz smooth scrolling with continuous velocity across wheel notches and touchpads."""
        import math as _math
        fraction = 0.0
        pending_frame = None
        target = None
        float_pos = None
        last_tick = None
        pending_touchpad = 0.0
        cached_max = [0]

        def cancel_animation():
            nonlocal pending_frame, target, float_pos, last_tick, pending_touchpad
            if pending_frame is not None:
                try:
                    canvas.after_cancel(pending_frame)
                except tk.TclError:
                    pass
                pending_frame = None
            target = None
            float_pos = None
            last_tick = None
            pending_touchpad = 0.0

        def refresh_max_scroll():
            try:
                page = getattr(self, "current_page", None)
                extra_bottom = 96 if getattr(self, "_active_nav_tab", "") != "Programme details" else 0
                region = canvas.cget("scrollregion")
                bottom = int(float(region.split()[3])) if region else 0
                if page is not None and page.winfo_exists():
                    needed = max(page.winfo_height(), page.winfo_reqheight()) + extra_bottom
                    if needed > bottom + 2 or bottom <= 1:
                        self._sync_scrollregion()
                        region = canvas.cget("scrollregion")
                        bottom = int(float(region.split()[3])) if region else needed
                cached_max[0] = max(0, bottom - canvas.winfo_height())
                return cached_max[0]
            except (tk.TclError, ValueError, IndexError):
                pass
            cached_max[0] = 0
            return 0

        def drag_scrollbar(*args):
            cancel_animation()
            self._scroll_priority_until = monotonic() + 0.160
            canvas.yview(*args)

        def step_scroll():
            nonlocal pending_frame, target, float_pos, last_tick, pending_touchpad
            pending_frame = None
            if not canvas.winfo_exists():
                cancel_animation()
                return
            frame_t0 = monotonic()
            self._scroll_priority_until = frame_t0 + 0.140

            # Flush coalesced high-frequency precision touchpad deltas once per frame.
            if pending_touchpad:
                pixels = int(pending_touchpad)
                pending_touchpad -= pixels
                if pixels:
                    canvas.yview_scroll(pixels, "units")
                if abs(pending_touchpad) >= 1.0:
                    spent_ms = (monotonic() - frame_t0) * 1000.0
                    pending_frame = canvas.after(self._next_frame_delay(spent_ms, 16), step_scroll)
                return

            if target is None:
                return

            dt = 0.016 if last_tick is None else max(0.004, min(0.050, frame_t0 - last_tick))
            last_tick = frame_t0
            cur_int = round(canvas.canvasy(0))
            if float_pos is None:
                float_pos = float(cur_int)

            # Continuous exponential smoothing keeps velocity fluid across rapid wheel notches.
            factor = 1.0 - _math.exp(-dt / 0.052)
            float_pos += (target - float_pos) * factor
            if abs(target - float_pos) < 0.75:
                float_pos = float(target)

            next_int = round(float_pos)
            delta = next_int - cur_int
            if delta:
                canvas.yview_scroll(delta, "units")

            if next_int != target:
                spent_ms = (monotonic() - frame_t0) * 1000.0
                pending_frame = canvas.after(self._next_frame_delay(spent_ms, 16), step_scroll)
            else:
                target = None
                float_pos = None
                last_tick = None

        def handle_scroll_step(step_px, *, is_precision=False):
            nonlocal target, float_pos, last_tick, pending_frame, pending_touchpad
            if not canvas.winfo_exists():
                return "break"
            now = monotonic()
            self._scroll_priority_until = now + 0.160

            if self._is_reduced_motion():
                cancel_animation()
                px = round(step_px)
                if px:
                    canvas.yview_scroll(px, "units")
                return "break"

            if is_precision:
                target = None
                float_pos = None
                last_tick = None
                pending_touchpad += step_px
                if pending_frame is None:
                    pending_frame = canvas.after(1, step_scroll)
                return "break"

            pending_touchpad = 0.0
            maximum = refresh_max_scroll()
            if maximum <= 0:
                return "break"
            current = round(canvas.canvasy(0))
            base = target if (target is not None and (target - current) * step_px >= 0) else current
            new_target = max(0, min(maximum, base + round(step_px)))
            # Cap lookahead distance so fast wheel spins stay snappy and never drift far ahead.
            new_target = max(current - 260, min(current + 260, new_target))
            new_target = max(0, min(maximum, new_target))
            if new_target != current or target is not None:
                target = new_target
                if float_pos is None:
                    float_pos = float(current)
                if pending_frame is None:
                    last_tick = now
                    pending_frame = canvas.after(1, step_scroll)
            return "break"

        def on_wheel(event):
            if not event.delta or not canvas.winfo_exists():
                return "break"
            if sys.platform == "darwin":
                # macOS delivers small pixel/line deltas directly (typically ±1..±10).
                return handle_scroll_step(-event.delta * 18.0, is_precision=abs(event.delta) <= 2)
            # Precision touchpad (sub-120 deltas): coalesce into the frame loop instead of 240Hz moves.
            if event.delta % 120:
                return handle_scroll_step(-event.delta * 48.0 / 120.0, is_precision=True)
            return handle_scroll_step(-event.delta * 56.0 / 120.0, is_precision=False)

        def on_linux_button(event):
            # Linux X11/XWayland mouse wheel fires Button-4 (up) and Button-5 (down).
            step_px = -56.0 if event.num == 4 else 56.0
            return handle_scroll_step(step_px, is_precision=False)

        scrollbar.configure(command=drag_scrollbar)
        canvas.bind_all("<MouseWheel>", on_wheel)
        canvas.bind_all("<Button-4>", on_linux_button)
        canvas.bind_all("<Button-5>", on_linux_button)
        canvas.bind("<Destroy>", lambda _event: cancel_animation(), add="+")

    def schedule_live_search(self, _event=None):
        """Refresh results shortly after the user pauses typing in the header search."""
        self.update_search_prompt()
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(180, self.apply_live_search)

    def update_search_prompt(self):
        """Show or hide the placeholder prompt inside the header search box."""
        if self._search_prompt is None or not self._search_prompt.winfo_exists():
            return
        if self.search_text.get() or self.focus_get() == self._search_entry:
            self._search_prompt.place_forget()
        else:
            self._search_prompt.place(x=9, rely=0.5, anchor="w")

    def apply_live_search(self):
        """Invoke the active page's search callback, or open the Genres/Search tab."""
        self._search_after_id = None
        if self._live_search_callback is not None:
            self._live_search_callback()
            return
        self.show_search()
        if self._search_entry is not None:
            self._search_entry.focus_set()
            self._search_entry.icursor(tk.END)
