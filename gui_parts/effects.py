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
from gui_parts.theme import (
    BORDER_LINE,
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
            from PIL import Image, ImageTk
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

            icons = [
                ImageTk.PhotoImage(square.resize((sz, sz), resample), master=self)
                for sz in (64, 32, 16)
            ]
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
        """Debounce window resize events before applying live UI scaling."""
        if event.widget is not self:
            return
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

    def apply_user_accessibility(self, listener_id):
        """Load and apply the signed-in listener's saved text size and theme from database.db."""
        saved_scale, saved_theme = self.load_user_accessibility(listener_id)
        theme_changed = saved_theme != getattr(self, "_theme_name", "dark")
        self._text_scale = saved_scale
        self._theme_name = saved_theme
        if theme_changed:
            apply_theme_palette(saved_theme)
            self.button_images.clear()
            self.cover_images.clear()
            self._titlebar_colour = None

    def reset_accessibility_settings(self):
        """Restore all accessibility settings (text size and theme) to defaults and save to database.db."""
        theme_changed = getattr(self, "_theme_name", "dark") != "dark"
        self._text_scale = 1.0
        if self.current_user is not None:
            self.save_user_accessibility(self.current_user, 1.0, "dark")
        if theme_changed:
            self.set_theme("dark", refresh=True, persist=False)
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

    def _finish_transition(self):
        """Mark the active transition complete and immediately resume any queued batch rendering."""
        self._transition_active = False
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
            ("Report", self.show_report), ("Profile", self.show_profile),
        ]
        profile_tab_active = active_tab_title in ("Your genres", "Profile & survey")
        active_nav_tab = (
            "Profile" if profile_tab_active else
            "Report" if active_tab_title == "Listening report" else active_tab_title
        )

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
            self.unbind_all("<MouseWheel>")
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
            logo_widget = self.draw_app_logo(topbar, 1.1)
            logo_widget.pack(side="left", padx=(26, 18), pady=22)

            nav_row = tk.Frame(topbar, bg=TOPBAR_BG)
            nav_row.pack(side="left", padx=(12, 16), pady=18)
            self._shell_nav_buttons = {}
            for label_text, handler in nav_links:
                selected_flag = label_text == active_nav_tab
                btn = self.create_button(
                    nav_row, label_text.upper(), lambda go=handler, tab=label_text: self.transition_to(go, tab),
                    compact=True, primary=selected_flag, font=(DEFAULT_FONT, 9, "bold"),
                    face=ORANGE_ACCENT if selected_flag else TOPBAR_BG,
                    fg=PRIMARY_BTN_FG if selected_flag else TEXT_GRAY,
                )
                btn._nav_selected = selected_flag
                btn.pack(side="left", padx=1)
                self._shell_nav_buttons[label_text] = btn
            sign_out_btn = self.create_button(topbar, "Sign out", self.show_login, compact=True)
            sign_out_btn.pack(side="right", padx=(6, 14), pady=20)
            search_container = self.create_card_frame(topbar, bg=INPUT_BG, width=230, height=38)
            search_container.pack(side="right", padx=(8, 12), pady=23)
            search_container.pack_propagate(False)
            self._search_container = search_container

            last_search_size = [230, 38]

            def resize_search_bar(_event=None):
                if not topbar.winfo_exists() or not search_container.winfo_exists():
                    return
                bar_w = topbar.winfo_width()
                if bar_w <= 1:
                    return
                # Calculate remaining space between the nav links and Sign out button.
                used_w = (
                    logo_widget.winfo_reqwidth() + 44
                    + nav_row.winfo_reqwidth() + 28
                    + sign_out_btn.winfo_reqwidth() + 44
                )
                available = bar_w - used_w
                # Grow longer on wider windows (up to 480px) and shrink cleanly on smaller windows (down to 135px).
                target_w = max(135, min(480, available))
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
                highlightthickness=0,
            )
            self._search_entry.pack(fill="both", expand=True, padx=10, pady=5)
            self._search_prompt = tk.Label(
                search_container, text="Search programmes...", font=(DEFAULT_FONT, 10),
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
            scroll_bar = tk.Scrollbar(area_frame, orient="vertical", command=canvas_pane.yview,
                                      bg=SIDEBAR_BG, troughcolor=DARK_BG, activebackground=ORANGE_ACCENT)
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

        def update_scrollregion(event):
            if canvas_pane.winfo_exists() and not getattr(self, "_transition_active", False):
                canvas_pane.configure(scrollregion=(0, 0, event.width, event.height))

        content_pane.bind("<Configure>", update_scrollregion)
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
            return

        if existing is not None and existing.winfo_exists():
            existing.destroy()
        self._shell_bottom_bar = None
        self._shell_bottom_bar_key = None
        self._bottom_bar_info = None
        self.add_last_listened_prompt(shell, show_average=show_average, recent=recent)
        self._shell_bottom_bar_key = bar_key

    def transition_to(self, destination, tab=None, *, direction=None):
        """Animate out of the current page (sliding or shrinking to the mini-bar) and open destination."""
        canvas, window = self._page_transition_target
        if getattr(canvas, "_leaving_page", False):
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
            recent = None
            try:
                with self.get_db_connection() as conn:
                    recent = get_last_listened(conn, self.current_user)
            except sqlite3.Error:
                recent = None
            if (
                recent is not None
                and recent[0] == self._active_detail_podcast[0]
                and recent[0] != self._dismissed_last_listened
            ):
                self.shrink_detail_to_bottom_bar(
                    destination, self._active_detail_podcast[1], self._active_detail_podcast[2],
                )
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

        self.slide_page(
            canvas, window, -direction * max(1, canvas.winfo_width()), 12, open_next_page,
            frame_ms=10, complete_delay_ms=16,
        )

    def _prerender_initial_batch(self, max_items=6):
        """Render the first visible row of queued cards off-screen so pages slide in already populated."""
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
        """Slide the new page into view across guaranteed frames so it never cuts mid-transition."""
        self._transition_active = True
        tab_distance = max(1, getattr(self, "_tab_transition_distance", 1))
        max_span = max(1, len(getattr(self, "_tab_order", [])) - 2)
        ratio = min(1.0, (tab_distance - 1) / max_span)
        # Smooth, seamless frame-stepped elastic slide: 18 frames for adjacent tabs up to 28 for Home <-> Profile.
        # Kept within ~2%..8% overshoot so far-away jumps feel clearly elastic without cutting off page content.
        entry_frames = round(18 + 10 * ratio)
        damping = 6.8 - 1.8 * ratio
        frequency = 0.95 + 0.30 * ratio

        def finish_entry():
            if canvas.winfo_exists():
                canvas.coords(canvas_window, 0, 0)
                canvas.yview_moveto(0)
                if self.current_page is not None and self.current_page.winfo_exists():
                    canvas.configure(
                        scrollregion=(0, 0, self.current_page.winfo_reqwidth(), self.current_page.winfo_reqheight())
                    )
            self._finish_transition()

        def begin_slide():
            if not canvas.winfo_exists():
                self._finish_transition()
                return
            # Pre-render the first row of cards off-screen so the page glides in looking complete.
            self._prerender_initial_batch(6)
            if abs(self._ui_scale_factor - 1.0) >= 0.025 and self.current_page is not None and self.current_page.winfo_exists():
                self._scale_widget_tree(self.current_page, self._ui_scale_factor)
            width = max(1, canvas.winfo_width())
            canvas.itemconfigure(canvas_window, width=width)
            canvas.coords(canvas_window, direction * width, 0)
            canvas.update_idletasks()
            self.slide_page(
                canvas, canvas_window, 0, entry_frames, finish_entry,
                damping=damping, frequency=frequency, frame_ms=12, complete_delay_ms=16,
            )

        # Wait one idle tick so the destination page finishes building off-screen before sliding in.
        canvas.after_idle(begin_slide)

    def slide_page(
        self, canvas, canvas_window, end_x, total_frames, on_complete=None, *,
        damping=5.4, frequency=1.15, frame_ms=10, complete_delay_ms=10,
    ):
        """Step through every frame (1..total_frames) so the slide finishes completely without cutting."""
        previous_frame = getattr(canvas, "_slide_frame", None)
        if previous_frame is not None:
            try:
                canvas.after_cancel(previous_frame)
            except tk.TclError:
                pass
        coords = canvas.coords(canvas_window)
        start_x = coords[0] if coords else 0
        total_frames = max(1, int(total_frames))
        step = 0
        last_x = round(start_x)
        self._transition_active = True

        def draw_frame():
            nonlocal last_x, step
            canvas._slide_frame = None
            if not canvas.winfo_exists():
                self._transition_active = False
                return
            step += 1
            progress = min(1.0, step / float(total_frames))
            # Outgoing pages accelerate cleanly off-screen; incoming pages stretch and settle elastically.
            eased = progress ** 3 if end_x else ease_out_elastic(progress, damping=damping, frequency=frequency)
            new_x = round(start_x + (end_x - start_x) * eased)
            if new_x != last_x:
                canvas.coords(canvas_window, new_x, 0)
                last_x = new_x
            if step < total_frames:
                canvas._slide_frame = canvas.after(frame_ms, draw_frame)
            elif on_complete:
                # Hold briefly after the final frame paints before handing off to the next page.
                canvas._slide_frame = canvas.after(complete_delay_ms, on_complete)
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
        area_frame = getattr(self, "_shell_area_frame", None)
        if area_frame is not None and area_frame.winfo_exists() and area_frame.master is shell:
            footer.pack(side="bottom", fill="x", padx=18, pady=(4, 10), before=area_frame)
        else:
            footer.pack(side="bottom", fill="x", padx=18, pady=(4, 10))
        tk.Frame(footer, bg=ORANGE_ACCENT, width=3).pack(side="left", fill="y")
        row = tk.Frame(footer, bg=footer.cget("bg"))
        row.pack(fill="x", padx=10, pady=7)

        def dismiss():
            self._dismissed_last_listened = podcast_id
            self._bottom_bar_info = None
            self._shell_bottom_bar = None
            self._shell_bottom_bar_key = None
            footer.destroy()

        self.create_button(row, "Dismiss", dismiss, compact=True).pack(side="right", padx=(8, 0))
        self.create_button(
            row, "▶  Play", lambda: self.listen(podcast_id), primary=True, compact=True,
        ).pack(side="right")

        cover = self.generate_podcast_cover(
            row, podcast_id, title, category, 62, 62,
            corner_radius=10, backdrop=row.cget("bg"),
        )
        cover.pack(side="left", padx=(0, 11))
        details = tk.Frame(row, bg=row.cget("bg"), cursor="hand2", takefocus=True,
                           highlightthickness=1, highlightbackground=row.cget("bg"),
                           highlightcolor=ORANGE_HL)
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
        self._shell_bottom_bar = footer
        self._bottom_bar_info = (shell, footer, podcast_id, title, category)

    def expand_bottom_bar_to_detail(self, shell, footer, podcast_id, title, category):
        """Expand the bottom mini-bar smoothly upward to open the podcast detail page."""
        if getattr(shell, "_expanding_bar", False):
            return
        canvas, _window = self._page_transition_target
        if getattr(canvas, "_leaving_page", False):
            return
        shell._expanding_bar = True
        canvas._leaving_page = True
        self._transition_active = True
        self.cancel_pending_render()

        area_frame = canvas.master
        start_x = footer.winfo_x()
        start_y = footer.winfo_y()
        start_w = max(1, footer.winfo_width())
        start_h = max(1, footer.winfo_height())
        target_y = area_frame.winfo_y()
        target_w = max(1, shell.winfo_width())
        target_h = max(1, shell.winfo_height() - target_y)

        start_bg = MINI_BAR_BG
        expander = tk.Frame(shell, bg=start_bg, bd=0, highlightthickness=0)
        accent_top = tk.Frame(expander, bg=ORANGE_ACCENT, height=3)
        accent_top.pack(fill="x")
        preview_box = tk.Frame(expander, bg=start_bg)
        preview_box.place(relx=0.5, rely=0.5, anchor="center")
        preview_cat = self.create_label(
            preview_box, str(category or "Programme").upper(), 10, ORANGE_HL, "bold",
            anchor="center", bg=start_bg,
        )
        preview_cat.pack()
        preview_title = self.create_label(
            preview_box, title, 22, TEXT_WHITE, "bold",
            anchor="center", justify="center", bg=start_bg,
        )
        preview_title.pack(pady=(6, 0))
        expander.place(x=start_x, y=start_y, width=start_w, height=start_h)
        tk.Misc.lift(expander)

        duration = 0.420
        started = monotonic()
        last_bg = start_bg

        def draw_expand():
            nonlocal last_bg
            if not expander.winfo_exists() or not shell.winfo_exists():
                shell._expanding_bar = False
                self._finish_transition()
                return
            progress = min(1.0, (monotonic() - started) / duration)
            eased = ease_out_elastic(progress, damping=5.5, frequency=1.05)
            cur_x = max(0, round(start_x * (1.0 - eased)))
            cur_y = max(target_y, round(start_y + (target_y - start_y) * eased))
            cur_w = max(1, min(target_w, round(start_w + (target_w - start_w) * eased)))
            cur_h = max(1, round(start_h + (target_h - start_h) * eased))
            cur_bg = blend_colour(start_bg, DARK_BG, progress)
            if cur_bg != last_bg:
                expander.configure(bg=cur_bg)
                preview_box.configure(bg=cur_bg)
                preview_cat.configure(bg=cur_bg)
                preview_title.configure(bg=cur_bg)
                last_bg = cur_bg
            expander.place(x=cur_x, y=cur_y, width=cur_w, height=cur_h)
            if progress < 1.0:
                self.after(8, draw_expand)
            else:
                def start_detail_reveal():
                    if not expander.winfo_exists() or not shell.winfo_exists():
                        shell._expanding_bar = False
                        self._finish_transition()
                        return
                    # Build the detail page underneath the overlay, then glide the curtain upward to reveal it.
                    self.show_detail(podcast_id)
                    if not expander.winfo_exists() or not shell.winfo_exists():
                        shell._expanding_bar = False
                        self._finish_transition()
                        return
                    tk.Misc.lift(expander)
                    reveal_frames = 18
                    reveal_step = 0

                    def draw_detail_reveal():
                        nonlocal reveal_step
                        if not expander.winfo_exists() or not shell.winfo_exists():
                            shell._expanding_bar = False
                            self._finish_transition()
                            return
                        reveal_step += 1
                        r_prog = min(1.0, reveal_step / float(reveal_frames))
                        r_eased = 1.0 - (1.0 - r_prog) ** 3
                        cur_top = round(target_y - target_h * r_eased)
                        expander.place(x=0, y=cur_top, width=target_w, height=target_h)
                        tk.Misc.lift(expander)
                        if reveal_step < reveal_frames:
                            self.after(10, draw_detail_reveal)
                        else:
                            shell._expanding_bar = False
                            expander.destroy()
                            self._finish_transition()

                    self.after(10, draw_detail_reveal)

                self.after(80, start_detail_reveal)

        draw_expand()

    def shrink_detail_to_bottom_bar(self, destination, title, category):
        """Shrink the podcast detail view down into the destination tab's bottom mini-bar."""
        canvas, _window = self._page_transition_target
        area_frame = canvas.master
        win_w = max(1, self.winfo_width())
        win_h = max(1, self.winfo_height())
        start_x = area_frame.winfo_rootx() - self.winfo_rootx()
        start_y = area_frame.winfo_rooty() - self.winfo_rooty()
        start_w = max(1, area_frame.winfo_width())
        start_h = max(1, win_h - start_y)

        if start_w <= 1 or start_h <= 1:
            self._tab_transition_direction = None
            self._finish_transition()
            destination()
            return

        target_box = [18, max(start_y, win_h - 90), max(1, win_w - 36), 80]

        self._tab_transition_direction = None
        self._transition_active = True
        destination()
        if not self.winfo_exists():
            self._transition_active = False
            return

        target_bg = MINI_BAR_BG
        shrinker = tk.Frame(self, bg=DARK_BG, bd=0, highlightthickness=0)
        accent_top = tk.Frame(shrinker, bg=ORANGE_ACCENT, height=3)
        accent_top.pack(fill="x")
        preview_box = tk.Frame(shrinker, bg=DARK_BG)
        preview_box.place(relx=0.5, rely=0.5, anchor="center")
        preview_cat = self.create_label(
            preview_box, str(category or "Programme").upper(), 10, ORANGE_HL, "bold",
            anchor="center", bg=DARK_BG,
        )
        preview_cat.pack()
        preview_title = self.create_label(
            preview_box, title, 22, TEXT_WHITE, "bold",
            anchor="center", justify="center", bg=DARK_BG,
        )
        preview_title.pack(pady=(6, 0))

        shrinker.place(x=start_x, y=start_y, width=start_w, height=start_h)
        tk.Misc.lift(shrinker)

        duration = 0.440
        started = None
        last_bg = DARK_BG

        def draw_shrink():
            nonlocal last_bg, started
            if not shrinker.winfo_exists() or not self.winfo_exists():
                self._finish_transition()
                return
            if started is None:
                started = monotonic()
            if self._bottom_bar_info is not None:
                dest_footer = self._bottom_bar_info[1]
                if dest_footer.winfo_exists() and dest_footer.winfo_width() > 1 and dest_footer.winfo_height() > 1:
                    target_box[0] = dest_footer.winfo_rootx() - self.winfo_rootx()
                    target_box[1] = dest_footer.winfo_rooty() - self.winfo_rooty()
                    target_box[2] = dest_footer.winfo_width()
                    target_box[3] = dest_footer.winfo_height()
            target_x, target_y, target_w, target_h = target_box
            progress = min(1.0, (monotonic() - started) / duration)
            eased = ease_out_elastic(progress, damping=5.2, frequency=1.10)
            cur_x = round(start_x + (target_x - start_x) * eased)
            cur_y = round(start_y + (target_y - start_y) * eased)
            cur_w = max(1, round(start_w + (target_w - start_w) * eased))
            cur_h = max(1, round(start_h + (target_h - start_h) * eased))
            cur_bg = blend_colour(DARK_BG, target_bg, progress)

            if cur_bg != last_bg or progress > 0.55:
                shrinker.configure(bg=cur_bg)
                preview_box.configure(bg=cur_bg)
                if progress > 0.55:
                    fade = (progress - 0.55) / 0.45
                    cat_fg = blend_colour(ORANGE_HL, cur_bg, fade)
                    title_fg = blend_colour(TEXT_WHITE, cur_bg, fade)
                    accent_bg = blend_colour(ORANGE_ACCENT, cur_bg, fade)
                else:
                    cat_fg = ORANGE_HL
                    title_fg = TEXT_WHITE
                    accent_bg = ORANGE_ACCENT
                accent_top.configure(bg=accent_bg)
                preview_cat.configure(bg=cur_bg, fg=cat_fg)
                preview_title.configure(bg=cur_bg, fg=title_fg)
                last_bg = cur_bg

            shrinker.place(x=cur_x, y=cur_y, width=cur_w, height=cur_h)

            if progress < 1.0:
                self.after(8, draw_shrink)
            else:
                shrinker.destroy()
                self._finish_transition()

        self.after(8, draw_shrink)

    def bind_page_scroll(self, canvas, scrollbar):
        """Ease wheel detents briefly and keep direct scrolling responsive."""
        fraction = 0.0
        pending_frame = None
        target = None

        def cancel_animation():
            nonlocal pending_frame, target
            if pending_frame is not None:
                canvas.after_cancel(pending_frame)
                pending_frame = None
            target = None

        def drag_scrollbar(*args):
            cancel_animation()
            self._scroll_priority_until = monotonic() + 0.080
            canvas.yview(*args)

        def draw_frame(start, started):
            nonlocal pending_frame, target
            pending_frame = None
            progress = min(1.0, (monotonic() - started) / 0.165)
            position = round(start + (target - start) * (1 - (1 - progress) ** 4))
            canvas.yview_scroll(position - round(canvas.canvasy(0)), "units")
            if progress < 1 and position != target:
                pending_frame = canvas.after(8, draw_frame, start, started)
            else:
                target = None

        def on_wheel(event):
            nonlocal fraction, target
            if not event.delta:
                return "break"
            self._scroll_priority_until = monotonic() + 0.080
            if event.delta % 120:
                cancel_animation()
                fraction -= event.delta * 48 / 120
                pixels = int(fraction)
                fraction -= pixels
                if pixels:
                    canvas.yview_scroll(pixels, "units")
                return "break"

            current = round(canvas.canvasy(0))
            distance = -event.delta * 48 // 120
            queued = target - current if target is not None else 0
            cancel_animation()
            if queued * distance > 0:
                distance += queued
            region = canvas.cget("scrollregion")
            if region:
                bottom = int(float(region.split()[3]))
                maximum = max(0, bottom - canvas.winfo_height())
                target = max(0, min(maximum, current + max(-144, min(144, distance))))
                if target != current:
                    draw_frame(current, monotonic())
                else:
                    target = None
            return "break"

        scrollbar.configure(command=drag_scrollbar)
        canvas.bind_all("<MouseWheel>", on_wheel)
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
