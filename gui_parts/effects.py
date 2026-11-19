"""Window icon/titlebar styling, live UI scaling, app shell, transitions, and bottom mini-bar."""
from collections import deque
import ctypes
import sqlite3
import sys
from time import monotonic
import tkinter as tk
from tkinter import font as tkfont

from last_listened import get_last_listened
from gui_parts.theme import (
    DARK_BG,
    DEFAULT_FONT,
    INPUT_BG,
    ORANGE_ACCENT,
    ORANGE_HL,
    ROOT_PATH,
    SIDEBAR_BG,
    TEXT_GRAY,
    TEXT_WHITE,
    blend_colour,
)


class EffectsMixin:
    """Mixin managing native Windows styling, responsive scaling, navigation shell, and transitions."""

    def set_window_icon(self):
        """Find the BBC Sounds logo image in the project folder and apply it as the window icon."""
        search_dirs = [ROOT_PATH]
        for sub in ("assets", "images", "img", "icons", "canva design"):
            candidate_dir = ROOT_PATH / sub
            if candidate_dir.is_dir():
                search_dirs.append(candidate_dir)

        def score_file(path):
            name = path.stem.lower()
            ext = path.suffix.lower()
            if "bbc" in name and "sound" in name:
                name_score = 40
            elif "sound" in name or "bbc" in name:
                name_score = 30
            elif "logo" in name or "icon" in name:
                name_score = 20
            else:
                name_score = 5
            ext_score = {
                ".ico": 10, ".png": 8, ".gif": 6,
                ".webp": 4, ".jpg": 3, ".jpeg": 3, ".bmp": 2,
            }.get(ext, 0)
            return name_score + ext_score

        supported_exts = {".ico", ".png", ".gif", ".webp", ".jpg", ".jpeg", ".bmp"}
        candidates = []
        for folder in search_dirs:
            try:
                for item in folder.iterdir():
                    if item.is_file() and item.suffix.lower() in supported_exts:
                        candidates.append(item)
            except OSError:
                continue

        candidates.sort(key=score_file, reverse=True)
        for icon_path in candidates:
            if self._apply_clean_window_icon(icon_path):
                return

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

    def set_windows_titlebar_colour(self, bg_hex=DARK_BG, text_hex=TEXT_WHITE):
        """Apply Windows DWM dark mode and custom caption/text/border colours to the titlebar."""
        if sys.platform != "win32":
            return
        if getattr(self, "_titlebar_colour", None) == (bg_hex, text_hex):
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
                (20, 1),
                (19, 1),
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
            self._titlebar_colour = (bg_hex, text_hex)
        except Exception:
            pass

    def schedule_interface_scaling(self, event):
        """Debounce window resize events before applying live UI scaling."""
        if event.widget is not self:
            return
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(60, self.apply_interface_scaling)

    def apply_interface_scaling(self, force=False):
        """Scale UI fonts, buttons, and wrap widths immediately when the window resizes."""
        self._resize_after_id = None
        if not self.winfo_exists():
            return
        win_w = self.winfo_width()
        win_h = self.winfo_height()
        if win_w <= 1 or win_h <= 1:
            return
        width_factor = win_w / 1320
        height_factor = win_h / 850
        new_scale_factor = max(0.84, min(1.25, min(width_factor, height_factor)))
        if not force and abs(new_scale_factor - self._ui_scale_factor) < 0.025:
            return
        self._ui_scale_factor = new_scale_factor
        self._scale_widget_tree(self, new_scale_factor)

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
                        actual = tkfont.Font(root=self, font=raw_font).actual()
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

    def build_shell(self, active_tab_title):
        """Construct the persistent top navigation bar, search box, optional mini-bar, and scroll area."""
        self.cancel_pending_render()
        self._podcast_averages = None
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None
        self._live_search_callback = None
        self.unbind_all("<MouseWheel>")
        for widget in self.winfo_children():
            widget.destroy()
        self.configure(bg=DARK_BG)
        self.set_windows_titlebar_colour("#080808")
        shell_box = tk.Frame(self, bg=DARK_BG)
        shell_box.pack(fill="both", expand=True)

        topbar = tk.Frame(shell_box, bg="#080808", height=84)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self.draw_app_logo(topbar, 1.1).pack(side="left", padx=30, pady=22)

        nav_links = [
            ("Home", self.show_home), ("Genres", self.show_search),
            ("For you", self.show_recommendations), ("Favourites", self.show_favourites),
            ("History", self.show_history), ("Ratings", self.show_ratings),
            ("Report", self.show_report), ("Profile", self.show_profile),
        ]
        nav_row = tk.Frame(topbar, bg="#080808")
        nav_row.pack(side="left", padx=35, pady=18)
        profile_tab_active = active_tab_title in ("Your genres", "Profile & survey")
        for label_text, handler in nav_links:
            selected_flag = label_text == active_tab_title or (label_text == "Report" and active_tab_title == "Listening report") or (
                label_text == "Profile" and profile_tab_active
            )
            self.create_button(
                nav_row, label_text.upper(), lambda go=handler, tab=label_text: self.transition_to(go, tab),
                compact=True, primary=selected_flag, font=(DEFAULT_FONT, 9, "bold"),
                face=ORANGE_ACCENT if selected_flag else "#080808",
                fg=TEXT_WHITE if selected_flag else TEXT_GRAY,
            ).pack(side="left", padx=1)
        self.create_button(topbar, "Sign out", self.show_login, compact=True).pack(side="right", padx=(6, 9), pady=20)
        search_container = self.create_card_frame(topbar, bg=INPUT_BG, width=230, height=38)
        search_container.pack(side="right", padx=(0, 14), pady=23)
        search_container.pack_propagate(False)
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
        if active_tab_title != "Programme details":
            self.add_last_listened_prompt(shell_box, show_average=not profile_tab_active)
        area_frame = tk.Frame(shell_box, bg=DARK_BG)
        area_frame.pack(fill="both", expand=True)
        canvas_pane = tk.Canvas(
            area_frame, bg=DARK_BG, highlightthickness=0, borderwidth=0, yscrollincrement=1,
        )
        scroll_bar = tk.Scrollbar(area_frame, orient="vertical", command=canvas_pane.yview,
                                  bg=SIDEBAR_BG, troughcolor=DARK_BG, activebackground=ORANGE_ACCENT)
        scroll_bar.pack(side="right", fill="y")
        canvas_pane.pack(side="left", fill="both", expand=True)
        canvas_pane.configure(yscrollcommand=scroll_bar.set)
        content_pane = tk.Frame(canvas_pane, bg=DARK_BG, padx=46, pady=28)
        canvas_window = canvas_pane.create_window((0, 0), window=content_pane, anchor="nw")
        content_pane.bind(
            "<Configure>", lambda event: canvas_pane.configure(scrollregion=(0, 0, event.width, event.height)),
        )

        def resize_content(event):
            if event.width != content_pane.winfo_width():
                canvas_pane.itemconfigure(canvas_window, width=event.width)

        canvas_pane.bind("<Configure>", resize_content)
        self.bind_page_scroll(canvas_pane, scroll_bar)
        self.current_page = content_pane
        self._page_transition_target = (canvas_pane, canvas_window)
        self._tab_order = [label for label, _ in nav_links]
        self._active_nav_tab = (
            "Profile" if profile_tab_active else
            "Report" if active_tab_title == "Listening report" else active_tab_title
        )
        if self._tab_transition_direction is not None:
            self.animate_page_entry(canvas_pane, canvas_window, self._tab_transition_direction)
        self.after_idle(lambda: self.apply_interface_scaling(force=True))
        return content_pane

    def transition_to(self, destination, tab=None, *, direction=None):
        """Animate out of the current page (sliding or shrinking to the mini-bar) and open destination."""
        canvas, window = self._page_transition_target
        if getattr(canvas, "_leaving_page", False):
            return
        current = self._active_nav_tab
        if tab is not None and tab == current and direction is None:
            return
        if direction is None:
            if current in self._tab_order and tab in self._tab_order:
                direction = 1 if self._tab_order.index(tab) > self._tab_order.index(current) else -1
            else:
                direction = 1
        canvas._leaving_page = True
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

        def open_next_page():
            self._tab_transition_direction = direction
            try:
                destination()
            finally:
                self._tab_transition_direction = None

        self.slide_page(canvas, window, -direction * canvas.winfo_width(), 210, open_next_page)

    def animate_page_entry(self, canvas, canvas_window, direction):
        """Slide a newly built page horizontally into view from the given direction."""
        canvas.itemconfigure(canvas_window, state="hidden")

        def reveal_page():
            if not canvas.winfo_exists():
                return
            canvas.itemconfigure(canvas_window, state="normal")
            self.slide_page(canvas, canvas_window, 0, 285)

        def start_entry(event):
            canvas.unbind("<Configure>", configure_binding)
            canvas.itemconfigure(canvas_window, width=event.width)
            canvas.coords(canvas_window, direction * event.width, 0)
            canvas.after_idle(reveal_page)

        configure_binding = canvas.bind("<Configure>", start_entry, add="+")

    def slide_page(self, canvas, canvas_window, end_x, duration_ms, on_complete=None):
        """Animate the scrollable content window horizontally to end_x."""
        previous_frame = getattr(canvas, "_slide_frame", None)
        if previous_frame is not None:
            canvas.after_cancel(previous_frame)
        start_x = canvas.coords(canvas_window)[0]
        started = monotonic()

        def draw_frame():
            canvas._slide_frame = None
            progress = min(1.0, (monotonic() - started) * 1000 / duration_ms)
            eased = progress ** 2 if end_x else 1 - (1 - progress) ** 3
            canvas.coords(canvas_window, round(start_x + (end_x - start_x) * eased), 0)
            if progress < 1:
                canvas._slide_frame = canvas.after(15, draw_frame)
            elif on_complete:
                on_complete()

        if not getattr(canvas, "_slide_cleanup_bound", False):
            def cancel_animation(_event):
                if canvas._slide_frame is not None:
                    canvas.after_cancel(canvas._slide_frame)

            canvas.bind("<Destroy>", cancel_animation, add="+")
            canvas._slide_cleanup_bound = True
        draw_frame()

    def add_last_listened_prompt(self, shell, show_average=True):
        """Attach the clickable bottom mini-bar for the user's most recently played podcast."""
        if self.current_user is None:
            return
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

        footer = self.create_card_frame(shell, bg="#262228")
        footer.pack(side="bottom", fill="x", padx=18, pady=(4, 10))
        tk.Frame(footer, bg=ORANGE_ACCENT, width=3).pack(side="left", fill="y")
        row = tk.Frame(footer, bg=footer.cget("bg"))
        row.pack(fill="x", padx=10, pady=7)

        def dismiss():
            self._dismissed_last_listened = podcast_id
            self._bottom_bar_info = None
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
        self.cancel_pending_render()

        area_frame = canvas.master
        start_x = footer.winfo_x()
        start_y = footer.winfo_y()
        start_w = max(1, footer.winfo_width())
        start_h = max(1, footer.winfo_height())
        target_y = area_frame.winfo_y()
        target_w = max(1, shell.winfo_width())
        target_h = max(1, shell.winfo_height() - target_y)

        start_bg = "#262228"
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

        duration = 0.240
        started = monotonic()

        def draw_expand():
            if not expander.winfo_exists() or not shell.winfo_exists():
                return
            progress = min(1.0, (monotonic() - started) / duration)
            eased = 1.0 - (1.0 - progress) ** 3
            cur_x = round(start_x * (1.0 - eased))
            cur_y = round(start_y + (target_y - start_y) * eased)
            cur_w = round(start_w + (target_w - start_w) * eased)
            cur_h = round(start_h + (target_h - start_h) * eased)
            cur_bg = blend_colour(start_bg, DARK_BG, eased)
            expander.configure(bg=cur_bg)
            preview_box.configure(bg=cur_bg)
            preview_cat.configure(bg=cur_bg)
            preview_title.configure(bg=cur_bg)
            expander.place(x=cur_x, y=cur_y, width=cur_w, height=cur_h)
            tk.Misc.lift(expander)
            if progress < 1.0:
                self.after(15, draw_expand)
            else:
                self.show_detail(podcast_id)

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
            destination()
            return

        target_box = [18, max(start_y, win_h - 90), max(1, win_w - 36), 80]

        self._tab_transition_direction = None
        destination()
        if not self.winfo_exists():
            return

        target_bg = "#262228"
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

        duration = 0.260
        started = monotonic()

        def draw_shrink():
            if not shrinker.winfo_exists() or not self.winfo_exists():
                return
            if self._bottom_bar_info is not None:
                dest_footer = self._bottom_bar_info[1]
                if dest_footer.winfo_exists() and dest_footer.winfo_width() > 1 and dest_footer.winfo_height() > 1:
                    target_box[0] = dest_footer.winfo_rootx() - self.winfo_rootx()
                    target_box[1] = dest_footer.winfo_rooty() - self.winfo_rooty()
                    target_box[2] = dest_footer.winfo_width()
                    target_box[3] = dest_footer.winfo_height()
            target_x, target_y, target_w, target_h = target_box
            progress = min(1.0, (monotonic() - started) / duration)
            eased = 1.0 - (1.0 - progress) ** 3
            cur_x = round(start_x + (target_x - start_x) * eased)
            cur_y = round(start_y + (target_y - start_y) * eased)
            cur_w = max(1, round(start_w + (target_w - start_w) * eased))
            cur_h = max(1, round(start_h + (target_h - start_h) * eased))
            cur_bg = blend_colour(DARK_BG, target_bg, eased)

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

            shrinker.place(x=cur_x, y=cur_y, width=cur_w, height=cur_h)
            tk.Misc.lift(shrinker)

            if progress < 1.0:
                self.after(12, draw_shrink)
            else:
                shrinker.destroy()

        self.after(12, draw_shrink)

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
            progress = min(1.0, (monotonic() - started) / 0.065)
            position = round(start + (target - start) * (1 - (1 - progress) ** 2))
            canvas.yview_scroll(position - round(canvas.canvasy(0)), "units")
            if progress < 1 and position != target:
                pending_frame = canvas.after(10, draw_frame, start, started)
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
