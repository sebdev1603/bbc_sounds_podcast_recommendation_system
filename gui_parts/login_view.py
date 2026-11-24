"""Login screen, button-to-home expansion transition, and spinning vinyl turntable visual."""
import ctypes
import math
import sqlite3
import sys
from time import monotonic
import tkinter as tk

from gui_parts.theme import (
    DARK_BG,
    DEFAULT_FONT,
    INPUT_BG,
    ORANGE_ACCENT,
    ORANGE_HL,
    TEXT_GRAY,
    TEXT_WHITE,
    blend_colour,
    ease_in_out_back,
    ease_out_elastic,
    format_user_id,
)


class LoginViewMixin:
    """Mixin implementing the sign-in page and its animated transitions."""

    def show_login(self, error_message=""):
        """Render the sign-in screen with listener ID authentication and spinning vinyl art."""
        # Cancel any background rendering, search timers, and mouse-wheel hooks from a prior session.
        self.cancel_pending_render()
        self._dismissed_last_listened = None
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None
        self._live_search_callback = None
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(seq)
        self.current_user = None
        self._armed_easter_egg = None
        for attr in ("_snake_window", "_memory_window", "_flappy_window"):
            egg_win = getattr(self, attr, None)
            if egg_win is not None and egg_win.winfo_exists():
                try:
                    egg_win.destroy()
                except tk.TclError:
                    pass
            setattr(self, attr, None)
        # Reset the login screen visually to default dark theme, English, and 100% text size without changing DB rows.
        self._text_scale = 1.0
        self.set_language("en", refresh=False, persist=False)
        self.set_theme("dark", refresh=False, persist=False)
        self._shell_box = None
        self._shell_bottom_bar = None
        self._shell_bottom_bar_key = None

        # Clear any existing widgets and match the window/titlebar background to DARK_BG.
        for child_widget in self.winfo_children():
            if getattr(child_widget, "_preserve_during_shell_build", False):
                continue
            child_widget.destroy()
        self.configure(bg=DARK_BG)
        self.set_windows_titlebar_colour(DARK_BG)

        main_box = tk.Frame(self, bg=DARK_BG)
        main_box.pack(fill="both", expand=True, padx=58, pady=38)
        self._login_main_box = main_box

        # Header row with the BBC Sounds logo on the left and tagline on the right.
        top_header = tk.Frame(main_box, bg=DARK_BG)
        top_header.pack(fill="x")
        self.draw_app_logo(top_header, 1.25).pack(side="left")
        self.create_label(top_header, "PODCASTS · RADIO · MUSIC", 9, TEXT_GRAY, "bold").pack(side="right")

        # Two-column split: hero copy + sign-in card on the left, animated vinyl turntable on the right.
        content_split = tk.Frame(main_box, bg=DARK_BG)
        content_split.pack(fill="both", expand=True, pady=(36, 0))

        left_side = tk.Frame(content_split, bg=DARK_BG)
        left_side.pack(side="left", fill="both", expand=True, padx=(0, 30))
        self.create_label(left_side, "YOUR NEXT LISTEN\nIS WAITING", 37, TEXT_WHITE, "bold", justify="left").pack(
            anchor="w", pady=(46, 13)
        )
        self.create_label(
            left_side,
            "Find programmes that fit your mood.\nDiscover new voices, stories and ideas.",
            14, TEXT_GRAY, justify="left",
        ).pack(anchor="w", pady=(0, 30))

        # Rounded sign-in card containing the listener ID input field, error label, and Continue button.
        login_panel = self.create_card_frame(left_side)
        login_panel.pack(anchor="w", fill="x", padx=(0, 8), pady=(2, 0))
        self.create_label(login_panel, "Welcome back", 18, TEXT_WHITE, "bold").pack(anchor="w", padx=20, pady=(19, 4))
        self.create_label(login_panel, "Enter your listener ID to continue.", 10, TEXT_GRAY).pack(anchor="w", padx=20)

        id_var = tk.StringVar()
        input_panel = self.create_card_frame(login_panel, bg=INPUT_BG)
        input_panel.pack(fill="x", padx=20, pady=(15, 10))
        text_entry = tk.Entry(
            input_panel, textvariable=id_var, font=(DEFAULT_FONT, 13), bg=INPUT_BG, fg=TEXT_WHITE,
            disabledbackground=INPUT_BG, disabledforeground=TEXT_WHITE,
            insertbackground=TEXT_WHITE, relief="flat", bd=0, highlightthickness=0,
        )
        text_entry.pack(fill="x", padx=12, pady=5, ipady=4)

        status_label = self.create_label(login_panel, error_message, 10, "#ff9868", wraplength=390)
        status_label.pack(anchor="w", padx=20, pady=(0, 4))

        def handle_login(_event=None):
            # Ignore duplicate clicks or Enter presses while the transition animation is already running.
            if getattr(login_button, "_expanding_login", False):
                return
            username_input = id_var.get().strip()
            if not username_input:
                status_label.config(text="Enter your listener ID to continue.")
                return
            try:
                # Verify the entered listener ID exists in SQLite.
                with self.get_db_connection() as conn:
                    found_record = conn.execute(
                        "SELECT ListenerID, CompleteSurvey FROM listeners WHERE ListenerID = ?",
                        (format_user_id(username_input),),
                    ).fetchone()
                if found_record:
                    self.current_user = found_record[0]
                    if not found_record["CompleteSurvey"]:
                        self.active_genres = []
                        self.active_length = "Medium"
                    # Load this listener's saved theme and text size before animating into Home.
                    self.apply_user_accessibility(self.current_user)
                    # Lock the form, stop the vinyl spin loop, and expand the Continue button into Home.
                    login_button._expanding_login = True
                    text_entry.configure(state="disabled")
                    cancel_record_jobs()
                    self.expand_login_button_to_home(login_button)
                else:
                    status_label.config(text="We couldn't find that listener ID. Check it and try again.")
            except sqlite3.Error as err:
                status_label.config(text="Couldn't open the project database: " + str(err))

        login_button = self.create_button(login_panel, "Continue  →", handle_login, primary=True)
        login_button.configure(highlightthickness=0, takefocus=0)
        login_button.pack(anchor="w", padx=20, pady=(5, 20))
        self._login_button = login_button
        text_entry.bind("<Return>", handle_login)
        text_entry.focus_set()

        # Right-hand canvas hosting the rotating BBC Sounds vinyl turntable graphic.
        right_side = tk.Frame(content_split, bg=DARK_BG, width=460)
        right_side.pack(side="right", fill="both", expand=True, padx=(16, 0))
        disc_canvas = tk.Canvas(right_side, bg=DARK_BG, highlightthickness=0)
        disc_canvas.pack(fill="both", expand=True)

        def cancel_record_jobs(_event=None):
            # Cleanly cancel pending repaint and spin animation callbacks on exit or destroy.
            for attr in ("_paint_job", "_spin_job"):
                job = getattr(disc_canvas, attr, None)
                if job is not None:
                    try:
                        self.after_cancel(job)
                    except tk.TclError:
                        pass
                    setattr(disc_canvas, attr, None)

        self._login_disc_canvas = disc_canvas

        last_disc_size = [None]

        def queue_record_paint(event):
            # Debounce resize redraws and ignore move-only Configure events with unchanged size.
            if getattr(self, "_signing_out", False):
                return
            size = (event.width, event.height)
            if size == last_disc_size[0]:
                return
            last_disc_size[0] = size
            pending = getattr(disc_canvas, "_paint_job", None)
            if pending is not None:
                self.after_cancel(pending)
            disc_canvas._paint_job = self.after(80, paint_record, event)

        def paint_record(event):
            disc_canvas._paint_job = None
            if disc_canvas.winfo_exists():
                self.paint_vinyl_record(event)

        disc_canvas.bind("<Configure>", queue_record_paint)
        disc_canvas.bind("<Destroy>", cancel_record_jobs)
        if not getattr(self, "_signing_out", False):
            self.after_idle(lambda: self.apply_interface_scaling(force=True))

    def _capture_window_snapshot(self, win_x, win_y, win_w, win_h):
        """Capture the current login window client area as a Tk PhotoImage via Windows BitBlt."""
        if sys.platform != "win32" or win_w <= 1 or win_h <= 1:
            return None
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            vp = ctypes.c_void_p
            user32.GetDC.restype = vp
            user32.GetDC.argtypes = [vp]
            user32.ReleaseDC.argtypes = [vp, vp]
            gdi32.CreateCompatibleDC.restype = vp
            gdi32.CreateCompatibleDC.argtypes = [vp]
            gdi32.CreateCompatibleBitmap.restype = vp
            gdi32.CreateCompatibleBitmap.argtypes = [vp, ctypes.c_int, ctypes.c_int]
            gdi32.SelectObject.restype = vp
            gdi32.SelectObject.argtypes = [vp, vp]
            gdi32.BitBlt.argtypes = [
                vp, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                vp, ctypes.c_int, ctypes.c_int, ctypes.c_uint32,
            ]
            gdi32.GetDIBits.argtypes = [vp, vp, ctypes.c_uint, ctypes.c_uint, vp, vp, ctypes.c_uint]
            gdi32.DeleteObject.argtypes = [vp]
            gdi32.DeleteDC.argtypes = [vp]

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", ctypes.c_uint32),
                    ("biWidth", ctypes.c_int32),
                    ("biHeight", ctypes.c_int32),
                    ("biPlanes", ctypes.c_uint16),
                    ("biBitCount", ctypes.c_uint16),
                    ("biCompression", ctypes.c_uint32),
                    ("biSizeImage", ctypes.c_uint32),
                    ("biXPelsPerMeter", ctypes.c_int32),
                    ("biYPelsPerMeter", ctypes.c_int32),
                    ("biClrUsed", ctypes.c_uint32),
                    ("biClrImportant", ctypes.c_uint32),
                ]

            sdc = user32.GetDC(None)
            if not sdc:
                return None
            mdc = gdi32.CreateCompatibleDC(sdc)
            bmp = gdi32.CreateCompatibleBitmap(sdc, win_w, win_h)
            old = gdi32.SelectObject(mdc, bmp)
            try:
                ok = gdi32.BitBlt(mdc, 0, 0, win_w, win_h, sdc, win_x, win_y, 0x00CC0020)
                if not ok:
                    return None
                bih = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), win_w, -win_h, 1, 32, 0, 0, 0, 0, 0, 0)
                buf = ctypes.create_string_buffer(win_w * win_h * 4)
                lines = gdi32.GetDIBits(mdc, bmp, 0, win_h, buf, ctypes.byref(bih), 0)
                if lines <= 0:
                    return None
            finally:
                gdi32.SelectObject(mdc, old)
                gdi32.DeleteObject(bmp)
                gdi32.DeleteDC(mdc)
                user32.ReleaseDC(None, sdc)

            raw = buf.raw
            rgb = bytearray(win_w * win_h * 3)
            rgb[0::3] = raw[2::4]
            rgb[1::3] = raw[1::4]
            rgb[2::3] = raw[0::4]
            header = f"P6\n{win_w} {win_h}\n255\n".encode("ascii")
            return tk.PhotoImage(master=self, data=header + bytes(rgb), format="PPM")
        except Exception:
            return None

    @staticmethod
    def _make_rounded_shapes(canvas, fill_col, tag):
        """Create 2 rectangles + 4 corner ovals forming a crisp pixel-aligned rounded pill."""
        return (
            canvas.create_rectangle(0, 0, 0, 0, fill=fill_col, outline="", tags=tag),
            canvas.create_rectangle(0, 0, 0, 0, fill=fill_col, outline="", tags=tag),
            *(canvas.create_oval(0, 0, 0, 0, fill=fill_col, outline="", tags=tag) for _ in range(4)),
        )

    @staticmethod
    def _set_rounded_shapes(canvas, items, tag, x0, y0, x1, y1, radius, fill_col=None):
        """Update the 6-primitive rounded pill geometry and optional fill colour."""
        w, h = max(1, x1 - x0), max(1, y1 - y0)
        r = max(0, min(radius, w // 2, h // 2))
        if r <= 1:
            canvas.coords(items[0], x0, y0, x1, y1)
            for extra in items[1:]:
                canvas.coords(extra, 0, 0, 0, 0)
        else:
            d = r * 2
            ox1, oy1 = max(x0, x1 - 1), max(y0, y1 - 1)
            canvas.coords(items[0], x0 + r, y0, x1 - r, y1)
            canvas.coords(items[1], x0, y0 + r, x1, y1 - r)
            canvas.coords(items[2], x0, y0, x0 + d, y0 + d)
            canvas.coords(items[3], ox1 - d, y0, ox1, y0 + d)
            canvas.coords(items[4], x0, oy1 - d, x0 + d, oy1)
            canvas.coords(items[5], ox1 - d, oy1 - d, ox1, oy1)
        if fill_col is not None:
            canvas.itemconfigure(tag, fill=fill_col)

    def _create_overlay_pair(self, win_x, win_y, win_w, win_h, key_colour, pill_alpha):
        """Create two withdrawn borderless chroma-key Toplevels aligned over the main window."""
        wins = []
        try:
            for bg_col, alpha in ((DARK_BG, None), (key_colour, pill_alpha)):
                top = tk.Toplevel(self)
                top.withdraw()
                top._preserve_during_shell_build = True
                top.overrideredirect(True)
                top.configure(bg=bg_col)
                top.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
                top.attributes("-transparentcolor", key_colour)
                if alpha is not None:
                    top.attributes("-alpha", alpha)
                top.transient(self)
                wins.append(top)
            return wins[0], wins[1]
        except tk.TclError:
            for w in wins:
                try:
                    w.destroy()
                except tk.TclError:
                    pass
            return None, None

    @staticmethod
    def _strip_dwm_border(top_win):
        """Disable Windows 11 DWM non-client border, shadow, and corner rounding on an overlay Toplevel."""
        if sys.platform != "win32":
            return
        try:
            wid = top_win.winfo_id()
            hwnd = ctypes.windll.user32.GetAncestor(wid, 2) or wid
            # DWMWA_NCRENDERING_POLICY (2) = DWMNCRP_DISABLED (1)
            # DWMWA_WINDOW_CORNER_PREFERENCE (33) = DWMWCP_DONOTROUND (1)
            # DWMWA_BORDER_COLOR (34) = DWMWA_COLOR_NONE (0xFFFFFFFE)
            for attr, raw_val in ((2, 1), (33, 1), (34, 0xFFFFFFFE)):
                val = ctypes.c_uint32(raw_val)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd), ctypes.c_int(attr), ctypes.byref(val), ctypes.sizeof(val),
                )
        except Exception:
            pass

    def _expand_login_in_window(self, start_x, start_y, start_w, start_h, start_colour):
        """Expand the Continue button directly over the untouched login UI, then lift the curtain to reveal Home."""
        win_w = max(1, self.winfo_width())
        win_h = max(1, self.winfo_height())
        if win_w <= 1 or win_h <= 1 or self._is_reduced_motion():
            self.show_home()
            return

        # Place the expanding surface ONLY over the Continue button so the login UI stays completely untouched around it.
        overlay = tk.Frame(self, bg=start_colour, bd=0, highlightthickness=0)
        overlay._preserve_during_shell_build = True
        overlay.place(x=start_x, y=start_y, width=start_w, height=start_h)
        tk.Misc.lift(overlay)
        overlay.update_idletasks()

        self._transition_active = True
        coil_w = max(24.0, start_w * 0.84)
        coil_h = max(18.0, start_h * 0.82)
        coil_x = start_x + (start_w - coil_w) / 2.0
        coil_y = start_y + (start_h - coil_h) / 2.0
        charged_col = blend_colour(start_colour, ORANGE_HL, 0.85)

        total_dur = 0.600  # 0..0.18 coil -> 0.18..0.60 expand -> subtle loading pulse + build Home -> 0.60..1.00 lift curtain.
        windup_end = 0.18
        expand_end = 0.60
        anim_st = {"progress": 0.0, "last_t": None}
        last_bg = [start_colour]
        last_rect = [None]
        home_built = [False]
        spinner_state = {"canvas": None, "arc": None, "angle": 0.0, "job": None}

        def stop_spinner():
            if spinner_state["job"] is not None:
                try:
                    self.after_cancel(spinner_state["job"])
                except tk.TclError:
                    pass
                spinner_state["job"] = None

        def finish():
            stop_spinner()
            if overlay.winfo_exists():
                try:
                    tk.Misc.lower(overlay)
                    self.update_idletasks()
                    overlay.destroy()
                except tk.TclError:
                    pass
            self._finish_transition()

        def spin_loader():
            spinner_state["job"] = None
            sc = spinner_state["canvas"]
            if sc is None or not sc.winfo_exists():
                return
            spinner_state["angle"] = (spinner_state["angle"] - 14.0) % 360.0
            try:
                sc.itemconfigure(spinner_state["arc"], start=spinner_state["angle"])
            except tk.TclError:
                return
            spinner_state["job"] = self.after(16, spin_loader)

        def draw_frame():
            if not overlay.winfo_exists() or not self.winfo_exists():
                finish()
                return
            t0 = monotonic()
            dt = 0.016 if anim_st["last_t"] is None else max(0.004, min(0.036, t0 - anim_st["last_t"]))
            anim_st["last_t"] = t0
            anim_st["progress"] = min(1.0, anim_st["progress"] + dt / total_dur)
            p = anim_st["progress"]

            if p < windup_end:
                u = p / windup_end
                e = 1.0 - (1.0 - u) ** 2
                cx = round(start_x + (coil_x - start_x) * e)
                cy = round(start_y + (coil_y - start_y) * e)
                cw = max(1, round(start_w + (coil_w - start_w) * e))
                ch = max(1, round(start_h + (coil_h - start_h) * e))
                cur_bg = blend_colour(start_colour, charged_col, e)
                rect = (cx, cy, cw, ch)
                if rect != last_rect[0]:
                    overlay.place(x=cx, y=cy, width=cw, height=ch)
                    last_rect[0] = rect
                if cur_bg != last_bg[0]:
                    overlay.configure(bg=cur_bg)
                    last_bg[0] = cur_bg
            elif p < expand_end:
                u = (p - windup_end) / (expand_end - windup_end)
                e = 1.0 - (1.0 - u) ** 3
                cx = round(coil_x * (1.0 - e))
                cy = round(coil_y * (1.0 - e))
                cw = max(1, min(win_w, round(coil_w + (win_w - coil_w) * e)))
                ch = max(1, min(win_h, round(coil_h + (win_h - coil_h) * e)))
                cur_bg = blend_colour(charged_col, DARK_BG, min(1.0, u / 0.88))
                rect = (cx, cy, cw, ch)
                if rect != last_rect[0]:
                    overlay.place(x=cx, y=cy, width=cw, height=ch)
                    last_rect[0] = rect
                if cur_bg != last_bg[0]:
                    overlay.configure(bg=cur_bg)
                    last_bg[0] = cur_bg
            else:
                if not home_built[0]:
                    home_built[0] = True
                    overlay.configure(bg=DARK_BG)
                    overlay.place(x=0, y=0, width=win_w, height=win_h)
                    tk.Frame(overlay, bg=ORANGE_ACCENT, height=3).pack(side="bottom", fill="x")
                    # Subtle centered loading ring + caption shown while Home builds underneath.
                    loader_box = tk.Frame(overlay, bg=DARK_BG)
                    loader_box.place(relx=0.5, rely=0.5, anchor="center")
                    spin_cvs = tk.Canvas(loader_box, width=44, height=44, bg=DARK_BG, bd=0, highlightthickness=0)
                    spin_cvs.pack()
                    spin_cvs.create_oval(5, 5, 39, 39, outline=blend_colour(DARK_BG, "#ffffff", 0.14), width=3)
                    arc_id = spin_cvs.create_arc(
                        5, 5, 39, 39, start=90, extent=105, style="arc", outline=ORANGE_ACCENT, width=3,
                    )
                    tk.Label(
                        loader_box, text="Loading...", font=(DEFAULT_FONT, 10),
                        fg=TEXT_GRAY, bg=DARK_BG,
                    ).pack(pady=(10, 0))
                    spinner_state["canvas"] = spin_cvs
                    spinner_state["arc"] = arc_id
                    overlay.update_idletasks()
                    spin_loader()

                    def _build_and_reveal():
                        if not self.winfo_exists() or not overlay.winfo_exists():
                            finish()
                            return
                        self.show_home()
                        if not self.winfo_exists() or not overlay.winfo_exists():
                            finish()
                            return
                        tk.Misc.lift(overlay)
                        self.update_idletasks()
                        tk.Misc.lift(overlay)
                        anim_st["last_t"] = monotonic()
                        self.after(16, draw_frame)

                    # Yield briefly so the loading spinner visibly paints before Home builds.
                    self.after(24, _build_and_reveal)
                    return

                u = (p - expand_end) / (1.0 - expand_end)
                e = 1.0 - (1.0 - u) ** 3.2
                new_y = round(-win_h * e)
                rect = (0, new_y, win_w, win_h)
                if rect != last_rect[0]:
                    overlay.place(x=0, y=new_y, width=win_w, height=win_h)
                    last_rect[0] = rect

            if p < 1.0:
                spent = (monotonic() - t0) * 1000.0
                self.after(self._next_frame_delay(spent, 16), draw_frame)
            else:
                finish()

        self.after(1, draw_frame)

    def _sign_out_in_window(self):
        """Shrink an overlay directly into the Continue button while revealing the live login UI around it."""
        win_w = max(1, self.winfo_width())
        win_h = max(1, self.winfo_height())
        if win_w <= 1 or win_h <= 1 or self._is_reduced_motion():
            self._signing_out = False
            self.show_login()
            return

        start_col = blend_colour(DARK_BG, "#ffffff", 0.06)
        overlay = tk.Frame(self, bg=start_col, bd=0, highlightthickness=2, highlightbackground=ORANGE_ACCENT)
        overlay._preserve_during_shell_build = True
        overlay.place(x=0, y=0, width=win_w, height=win_h)
        tk.Misc.lift(overlay)
        overlay.update_idletasks()

        self._transition_active = True
        self.show_login()
        if not self.winfo_exists() or not overlay.winfo_exists():
            self._signing_out = False
            self._transition_active = False
            if overlay.winfo_exists():
                overlay.destroy()
            return
        self.apply_interface_scaling(force=True)
        tk.Misc.lift(overlay)
        self.update_idletasks()
        tk.Misc.lift(overlay)

        target_btn = getattr(self, "_login_button", None)
        if target_btn is not None and target_btn.winfo_exists() and target_btn.winfo_width() > 1:
            y_sh = getattr(target_btn, "_hover_y_shift", 0)
            h_sz = getattr(target_btn, "_hover_size", None)
            end_w = (h_sz[0] + 2) if h_sz else max(12, target_btn.winfo_width() - 10)
            end_h = (h_sz[1] + 2) if h_sz else max(12, target_btn.winfo_height() - 10 - y_sh * 2)
            end_x = (target_btn.winfo_rootx() - self.winfo_rootx()) + (target_btn.winfo_width() - end_w) / 2.0
            end_y = (target_btn.winfo_rooty() - self.winfo_rooty()) + (target_btn.winfo_height() - end_h) / 2.0 - y_sh
        else:
            end_x, end_y, end_w, end_h = 80.0, win_h / 2.0, 160.0, 44.0

        impact_col = blend_colour(ORANGE_ACCENT, ORANGE_HL, 0.75)
        squash_w = max(24.0, end_w * 0.78)
        squash_h = max(18.0, end_h * 0.76)
        squash_x = end_x + (end_w - squash_w) / 2.0
        squash_y = end_y + (end_h - squash_h) / 2.0

        total_dur = 0.500  # 0..0.64 contract while revealing live login screen -> 0.64..1.00 elastic spring settle.
        shrink_end = 0.64
        anim_st = {"progress": 0.0, "last_t": None}
        last_bg = [start_col]
        last_rect = [None]

        def finish():
            if overlay.winfo_exists():
                try:
                    tk.Misc.lower(overlay)
                    self.update_idletasks()
                    overlay.destroy()
                except tk.TclError:
                    pass
            self._signing_out = False
            self._finish_transition()
            disc = getattr(self, "_login_disc_canvas", None)
            if disc is not None and disc.winfo_exists():
                def _start_vinyl():
                    if not disc.winfo_exists():
                        return
                    resume = getattr(disc, "_resume_spin", None)
                    if resume is not None:
                        resume()
                    else:
                        class _PaintEvt:
                            widget = disc
                            width = max(240, disc.winfo_width())
                            height = max(240, disc.winfo_height())
                        self.paint_vinyl_record(_PaintEvt())
                self.after(16, _start_vinyl)

        def draw_frame():
            if not overlay.winfo_exists() or not self.winfo_exists():
                finish()
                return
            t0 = monotonic()
            dt = 0.016 if anim_st["last_t"] is None else max(0.004, min(0.036, t0 - anim_st["last_t"]))
            anim_st["last_t"] = t0
            anim_st["progress"] = min(1.0, anim_st["progress"] + dt / total_dur)
            p = anim_st["progress"]

            if p < shrink_end:
                u = p / shrink_end
                e = 4.0 * u ** 3 if u < 0.5 else 1.0 - ((-2.0 * u + 2.0) ** 3) / 2.0
                cx = round(squash_x * e)
                cy = round(squash_y * e)
                cw = max(1, round(win_w + (squash_w - win_w) * e))
                ch = max(1, round(win_h + (squash_h - win_h) * e))
                cur_bg = blend_colour(start_col, impact_col, min(1.0, u / 0.88))
            else:
                u = (p - shrink_end) / (1.0 - shrink_end)
                sp = ease_out_elastic(u, damping=3.4, frequency=1.55)
                cw = max(12, round(squash_w + (end_w - squash_w) * sp))
                ch = max(12, round(squash_h + (end_h - squash_h) * sp))
                cx = round(end_x + (end_w - cw) / 2.0)
                cy = round(end_y + (end_h - ch) / 2.0)
                cur_bg = blend_colour(impact_col, ORANGE_ACCENT, min(1.0, u / 0.70))

            # Shrink the overlay widget itself so the real login screen is progressively revealed all around it.
            rect = (cx, cy, cw, ch)
            if rect != last_rect[0]:
                overlay.place(x=cx, y=cy, width=cw, height=ch)
                last_rect[0] = rect
            if cur_bg != last_bg[0]:
                overlay.configure(bg=cur_bg, highlightbackground=cur_bg if p >= shrink_end else ORANGE_ACCENT)
                last_bg[0] = cur_bg

            if p < 1.0:
                spent = (monotonic() - t0) * 1000.0
                self.after(self._next_frame_delay(spent, 16), draw_frame)
            else:
                finish()

        self.after(1, draw_frame)

    def expand_login_button_to_home(self, login_button):
        """Coil and launch the rounded Continue button while smoothly revealing and fading in Home."""
        # Sample the button's exact current hover colour, inset, and screen geometry before expanding.
        self.cancel_button_hover(login_button)
        if self._is_reduced_motion():
            self.show_home()
            return
        face, hover = getattr(login_button, "_rounded_colours", (ORANGE_ACCENT, ORANGE_HL))
        hover_t = getattr(login_button, "_hover_step", 0) / 10.0
        hover_eased = (
            ease_out_elastic(hover_t, damping=3.0, frequency=1.65)
            if getattr(login_button, "_hover_target", 0) > 0
            else 1.0 - (1.0 - hover_t) ** 2.4
        )
        start_colour = blend_colour(face, hover, max(0.0, min(1.0, hover_eased)))
        start_inset = max(0, min(5, round(5.0 - 3.0 * hover_eased)))
        button_bg = login_button.cget("bg")

        win_x = self.winfo_rootx()
        win_y = self.winfo_rooty()
        win_w = max(1, self.winfo_width())
        win_h = max(1, self.winfo_height())

        raw_bx = login_button.winfo_rootx() - win_x
        raw_by = login_button.winfo_rooty() - win_y
        raw_bw = max(1, login_button.winfo_width())
        raw_bh = max(1, login_button.winfo_height())

        start_x = raw_bx + start_inset
        start_y = raw_by + start_inset
        start_w = max(1, raw_bw - start_inset * 2)
        start_h = max(1, raw_bh - start_inset * 2)

        if start_w <= 1 or start_h <= 1:
            self.show_home()
            return

        # On Linux (Wayland/X11) and macOS, -transparentcolor Toplevels are unsupported; use the fast in-window overlay.
        if sys.platform != "win32":
            self._expand_login_in_window(start_x, start_y, start_w, start_h, start_colour)
            return

        # Capture the clean login screen BEFORE modifying the button, then clear its text.
        self.focus_set()
        login_snap = self._capture_window_snapshot(win_x, win_y, win_w, win_h)
        login_button.configure(text="")
        # Use a dark unique chroma key (#010203) instead of bright magenta so any 1px edge never looks bright/white.
        key_colour = "#010203"

        backdrop_win, pill_win = self._create_overlay_pair(win_x, win_y, win_w, win_h, key_colour, 1.0)
        if backdrop_win is None:
            self.show_home()
            return

        make_rounded_shapes = self._make_rounded_shapes
        set_rounded_shapes = self._set_rounded_shapes

        backdrop_canvas = tk.Canvas(backdrop_win, bg=DARK_BG, bd=0, highlightthickness=0)
        backdrop_canvas.pack(fill="both", expand=True)
        if login_snap is not None:
            backdrop_canvas._snap_ref = login_snap
            backdrop_canvas.create_image(0, 0, image=login_snap, anchor="nw")
            # Cover the static button and any border margin on the snapshot with card background.
            backdrop_canvas.create_rectangle(
                raw_bx - 4, raw_by - 4, raw_bx + raw_bw + 4, raw_by + raw_bh + 4,
                fill=button_bg, outline="",
            )
        cutout_items = make_rounded_shapes(backdrop_canvas, key_colour, "cutout")
        backdrop_canvas.itemconfigure("cutout", state="hidden")
        cutout_visible = [False]

        pill_canvas = tk.Canvas(pill_win, bg=key_colour, bd=0, highlightthickness=0)
        pill_canvas.pack(fill="both", expand=True)
        pill_items = make_rounded_shapes(pill_canvas, start_colour, "pill")

        start_r = min(10, start_h // 2, start_w // 2)
        set_rounded_shapes(
            pill_canvas, pill_items, "pill",
            start_x, start_y, start_x + start_w, start_y + start_h, start_r,
        )

        # Layout both canvases while still withdrawn, strip Windows 11 DWM border, then reveal.
        backdrop_win.update_idletasks()
        pill_win.update_idletasks()
        self._strip_dwm_border(backdrop_win)
        self._strip_dwm_border(pill_win)
        backdrop_win.deiconify()
        pill_win.deiconify()
        self._strip_dwm_border(backdrop_win)
        self._strip_dwm_border(pill_win)
        backdrop_win.lift()
        pill_win.lift()
        try:
            self.update()
        except tk.TclError:
            pass

        # Build Home once underneath the fully opaque login backdrop (batch card rendering paused).
        self._transition_active = True
        self.show_home()
        if not self.winfo_exists():
            self._transition_active = False
            for w in (pill_win, backdrop_win):
                if w.winfo_exists():
                    w.destroy()
            return
        self.update_idletasks()
        backdrop_win.lift()
        pill_win.lift()

        # Pre-compute the compressed "coiled spring" rectangle around the button's centre for the
        # elastic anticipation wind-up before launching into the full window.
        coil_w = max(24, round(start_w * 0.80))
        coil_h = max(18, round(start_h * 0.78))
        coil_x = start_x + (start_w - coil_w) // 2
        coil_y = start_y + (start_h - coil_h) // 2
        charged_colour = blend_colour(start_colour, ORANGE_HL, 0.85)

        total_duration = 0.720  # ~0.19s elastic wind-up coil + ~0.53s rounded launch and Home fade-in.
        max_step = 1.0 / 24.0  # Cap per-frame progress so slow frames never cause visible jumps.
        windup_end = 0.26  # First 26%: button visibly compresses & brightens, getting ready to launch.
        fade_start = 0.34  # Begin fading Home in right as the rounded button rockets outward.
        state = {"progress": 0.0, "last_t": None}
        last_rect = [None]
        last_bg = [start_colour]

        def finish():
            for w in (pill_win, backdrop_win):
                if w is not None and w.winfo_exists():
                    try:
                        w.destroy()
                    except tk.TclError:
                        pass
            self._finish_transition()

        def draw_frame():
            if not pill_win.winfo_exists() or not backdrop_win.winfo_exists() or not self.winfo_exists():
                finish()
                return

            now = monotonic()
            if state["last_t"] is None:
                delta = max_step * 0.5
            else:
                delta = min(max_step, (now - state["last_t"]) / total_duration)
            state["last_t"] = now
            state["progress"] = min(1.0, state["progress"] + delta)
            progress = state["progress"]

            if progress < windup_end:
                # Phase 1: Elastic anticipation — rounded button compresses inward and brightens.
                u = progress / windup_end
                coil_t = 1.0 - (1.0 - u) ** 2
                cur_x = round(start_x + (coil_x - start_x) * coil_t)
                cur_y = round(start_y + (coil_y - start_y) * coil_t)
                cur_w = max(1, round(start_w + (coil_w - start_w) * coil_t))
                cur_h = max(1, round(start_h + (coil_h - start_h) * coil_t))
                cur_r = start_r
                cur_bg = blend_colour(start_colour, charged_colour, coil_t)
            else:
                # Phase 2: Rounded elastic launch — expands smoothly while keeping rounded corners
                # until the final 12% where corners gently settle flush with the window edges.
                t = (progress - windup_end) / (1.0 - windup_end)
                launch_eased = 1.0 - (1.0 - t) ** 3
                cur_x = round(coil_x * (1.0 - launch_eased))
                cur_y = round(coil_y * (1.0 - launch_eased))
                cur_w = max(1, min(win_w, round(coil_w + (win_w - coil_w) * launch_eased)))
                cur_h = max(1, min(win_h, round(coil_h + (win_h - coil_h) * launch_eased)))
                if t < 0.88:
                    cur_r = round(start_r + 8 * min(1.0, t / 0.30))
                else:
                    cur_r = round((start_r + 8) * max(0.0, (1.0 - t) / 0.12))

                if t <= 0.65:
                    cp = min(1.0, t / 0.60)
                    cur_bg = blend_colour(charged_colour, DARK_BG, cp * cp * (3.0 - 2.0 * cp))
                else:
                    cur_bg = last_bg[0]

                if not cutout_visible[0]:
                    backdrop_canvas.itemconfigure("cutout", state="normal")
                    cutout_visible[0] = True

            x0, y0, x1, y1 = cur_x, cur_y, cur_x + cur_w, cur_y + cur_h
            rect_key = (x0, y0, x1, y1, cur_r)
            fill_update = cur_bg if cur_bg != last_bg[0] else None
            if rect_key != last_rect[0] or fill_update is not None:
                set_rounded_shapes(pill_canvas, pill_items, "pill", x0, y0, x1, y1, cur_r, fill_update)
                if cutout_visible[0] and rect_key != last_rect[0]:
                    set_rounded_shapes(backdrop_canvas, cutout_items, "cutout", x0, y0, x1, y1, cur_r)
                last_rect[0] = rect_key
                if fill_update is not None:
                    last_bg[0] = fill_update

            if progress >= fade_start:
                fade_p = min(1.0, (progress - fade_start) / (1.0 - fade_start))
                fade_eased = fade_p * fade_p * (3.0 - 2.0 * fade_p)
                try:
                    pill_win.attributes("-alpha", max(0.0, 1.0 - fade_eased))
                except tk.TclError:
                    finish()
                    return

            if progress < 1.0:
                spent_ms = (monotonic() - now) * 1000.0
                self.after(self._next_frame_delay(spent_ms, 16), draw_frame)
            else:
                finish()

        # Start after queued idle layout/scaling callbacks finish so the animation runs uninterrupted.
        self.after(16, draw_frame)

    def sign_out_to_login(self):
        """Shrink the current page smoothly back into the rounded Continue button on the login screen."""
        if getattr(self, "_signing_out", False) or getattr(self, "_transition_active", False):
            return
        self._signing_out = True
        self.focus_set()

        win_x = self.winfo_rootx()
        win_y = self.winfo_rooty()
        win_w = max(1, self.winfo_width())
        win_h = max(1, self.winfo_height())

        if win_w <= 1 or win_h <= 1 or self._is_reduced_motion():
            self._signing_out = False
            self.show_login()
            return

        if sys.platform != "win32":
            self._sign_out_in_window()
            return

        # Capture the live current page BEFORE switching to the login screen underneath.
        page_snap = self._capture_window_snapshot(win_x, win_y, win_w, win_h)
        key_colour = "#010203"

        page_win, pill_win = self._create_overlay_pair(win_x, win_y, win_w, win_h, key_colour, 0.0)
        if page_win is None:
            self._signing_out = False
            self.show_login()
            return

        page_canvas = tk.Canvas(page_win, bg=DARK_BG, bd=0, highlightthickness=0)
        page_canvas.pack(fill="both", expand=True)
        if page_snap is not None:
            page_canvas._snap_ref = page_snap
            page_canvas.create_image(0, 0, image=page_snap, anchor="nw")

        # 4 outer chroma-key rectangles + 4 inverse-corner polygons clip page_snap to a rounded box.
        outer_masks = tuple(
            page_canvas.create_rectangle(0, 0, 0, 0, fill=key_colour, outline="")
            for _ in range(4)
        )
        corner_masks = tuple(
            page_canvas.create_polygon(0, 0, 0, 0, 0, 0, fill=key_colour, outline="")
            for _ in range(4)
        )

        # Pre-compute smooth quarter-circle steps (5 segments per corner) for fast, seamless rounded clipping.
        arc_steps = tuple(
            (math.cos(math.radians(a)), math.sin(math.radians(a)))
            for a in (0, 18, 36, 54, 72, 90)
        )

        def update_page_clip(x0, y0, x1, y1, radius):
            # Inset the clipped page snapshot 1-2px strictly inside pill_win's rounded boundary so
            # bright pixels from page_snap can never poke past the pill's rounded corners.
            lx = max(0, x0 + 1)
            ly = max(0, y0 + 1)
            rx = min(win_w, max(lx, x1 - 2))
            by = min(win_h, max(ly, y1 - 2))
            page_canvas.coords(outer_masks[0], 0, 0, win_w, ly)
            page_canvas.coords(outer_masks[1], 0, by, win_w, win_h)
            page_canvas.coords(outer_masks[2], 0, ly, lx, by)
            page_canvas.coords(outer_masks[3], rx, ly, win_w, by)

            r = max(0, min(radius + 1, (rx - lx) // 2, (by - ly) // 2))
            if r <= 1:
                for cm in corner_masks:
                    page_canvas.coords(cm, 0, 0, 0, 0, 0, 0)
                return

            # Top-left, top-right, bottom-left, bottom-right inverse rounded corner masks with 2px outer overlap.
            tl = [lx - 2, ly - 2]
            for c, s in arc_steps:
                tl.extend((lx + r - r * s, ly + r - r * c))
            tr = [rx + 2, ly - 2]
            for c, s in arc_steps:
                tr.extend((rx - r + r * c, ly + r - r * s))
            bl = [lx - 2, by + 2]
            for c, s in arc_steps:
                bl.extend((lx + r - r * c, by - r + r * s))
            br = [rx + 2, by + 2]
            for c, s in arc_steps:
                br.extend((rx - r + r * s, by - r + r * c))
            page_canvas.coords(corner_masks[0], *tl)
            page_canvas.coords(corner_masks[1], *tr)
            page_canvas.coords(corner_masks[2], *bl)
            page_canvas.coords(corner_masks[3], *br)

        pill_canvas = tk.Canvas(pill_win, bg=key_colour, bd=0, highlightthickness=0)
        pill_canvas.pack(fill="both", expand=True)
        pill_items = self._make_rounded_shapes(pill_canvas, DARK_BG, "pill")

        def set_pill_shapes(x0, y0, x1, y1, radius, fill_col=None):
            self._set_rounded_shapes(pill_canvas, pill_items, "pill", x0, y0, x1, y1, radius, fill_col)

        # Reveal the full-window page snapshot BEFORE switching to the login screen underneath.
        page_win.update_idletasks()
        pill_win.update_idletasks()
        self._strip_dwm_border(page_win)
        self._strip_dwm_border(pill_win)
        page_win.deiconify()
        pill_win.deiconify()
        self._strip_dwm_border(page_win)
        self._strip_dwm_border(pill_win)
        page_win.lift()
        pill_win.lift()
        try:
            self.update()
        except tk.TclError:
            pass

        # Build the login screen underneath while covered by page_win, and measure the Continue button.
        self._transition_active = True
        self.show_login()
        if not self.winfo_exists():
            self._signing_out = False
            self._transition_active = False
            for w in (pill_win, page_win):
                if w.winfo_exists():
                    w.destroy()
            return
        self.apply_interface_scaling(force=True)
        self.update_idletasks()
        # Paint the login vinyl graphic statically right now while still hidden behind page_win
        # (its spin loop stays paused until finish() so it never steals FPS during the transition).
        disc_canvas = getattr(self, "_login_disc_canvas", None)
        if disc_canvas is not None and disc_canvas.winfo_exists():
            class _StaticPaintEvent:
                widget = disc_canvas
                width = disc_canvas.winfo_width()
                height = disc_canvas.winfo_height()
            self.paint_vinyl_record(_StaticPaintEvent())
            self.update_idletasks()
        page_win.lift()
        pill_win.lift()

        target_btn = getattr(self, "_login_button", None)
        if target_btn is None or not target_btn.winfo_exists():
            self._signing_out = False
            self._finish_transition()
            for w in (pill_win, page_win):
                if w.winfo_exists():
                    w.destroy()
            return

        end_inset = 3
        end_x = target_btn.winfo_rootx() - win_x + end_inset
        end_y = target_btn.winfo_rooty() - win_y + end_inset
        end_w = max(1, target_btn.winfo_width() - end_inset * 2)
        end_h = max(1, target_btn.winfo_height() - end_inset * 2)
        end_r = min(10, end_h // 2, end_w // 2)

        # Temporarily mask the real Continue button with its card background so its full-size edges
        # never peek out behind the squashed/bouncing pill during the elastic rebound.
        btn_cover = tk.Frame(target_btn.master, bg=target_btn.cget("bg"), bd=0, highlightthickness=0)
        btn_cover.place(
            x=target_btn.winfo_x() - 2,
            y=target_btn.winfo_y() - 2,
            width=target_btn.winfo_width() + 4,
            height=target_btn.winfo_height() + 4,
        )
        btn_cover.lift()
        self.update_idletasks()
        page_win.lift()
        pill_win.lift()

        # Deeply compressed impact target when the shrinking page snaps into the Continue button,
        # followed by a lively damped elastic spring rebound that overshoots and settles cleanly.
        squash_w = max(24, round(end_w * 0.72))
        squash_h = max(18, round(end_h * 0.70))
        squash_x = end_x + (end_w - squash_w) // 2
        squash_y = end_y + (end_h - squash_h) // 2
        impact_colour = blend_colour(ORANGE_ACCENT, ORANGE_HL, 0.85)

        total_duration = 0.680  # ~0.39s snappy shrink into button + ~0.29s lively elastic spring bounce.
        max_step = 1.0 / 20.0
        shrink_end = 0.58
        state = {"progress": 0.0, "last_t": None}
        last_rect = [None]
        last_bg = [DARK_BG]
        last_alpha = [0.0]
        page_hidden = [False]
        btn_revealed = [False]

        def finish():
            for w in (pill_win, page_win, btn_cover):
                if w is not None and w.winfo_exists():
                    try:
                        w.destroy()
                    except tk.TclError:
                        pass
            self._signing_out = False
            self._finish_transition()
            disc = getattr(self, "_login_disc_canvas", None)
            if disc is not None and disc.winfo_exists():
                resume = getattr(disc, "_resume_spin", None)
                if resume is not None:
                    resume()
                else:
                    class _PaintEvt:
                        widget = disc
                        width = max(240, disc.winfo_width())
                        height = max(240, disc.winfo_height())
                    self.paint_vinyl_record(_PaintEvt())

        def draw_frame():
            if not pill_win.winfo_exists() or not page_win.winfo_exists() or not self.winfo_exists():
                finish()
                return

            now = monotonic()
            if state["last_t"] is None:
                delta = 0.014
            else:
                delta = min(max_step, (now - state["last_t"]) / total_duration)
            state["last_t"] = now
            state["progress"] = min(1.0, state["progress"] + delta)
            progress = state["progress"]

            if progress < shrink_end:
                # Phase 1: Pull the entire current page inward into the compressed Continue button.
                t = progress / shrink_end
                # Smooth cubic ease-in-out gathers momentum as it collapses into the button.
                eased = (
                    4.0 * t ** 3
                    if t < 0.5
                    else 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0
                )
                cur_x = round(squash_x * eased)
                cur_y = round(squash_y * eased)
                cur_w = max(1, round(win_w + (squash_w - win_w) * eased))
                cur_h = max(1, round(win_h + (squash_h - win_h) * eased))
                # Corners round in smoothly during the first 15%, then settle to end_r.
                if t < 0.15:
                    cur_r = round((end_r + 8) * (t / 0.15))
                else:
                    cur_r = round((end_r + 8) - 8 * ((t - 0.15) / 0.85))

                # Fade the pill overlay in smoothly over the shrinking page toward bright impact orange.
                fade_p = min(1.0, t / 0.82)
                fade_eased = fade_p * fade_p * (3.0 - 2.0 * fade_p)
                cur_bg = blend_colour(DARK_BG, impact_colour, fade_eased)
                alpha = fade_eased
                # Hide page_win the instant pill_win is fully opaque so no snapshot edges can ever show.
                if alpha >= 0.99 and not page_hidden[0]:
                    page_win.withdraw()
                    page_hidden[0] = True
            else:
                # Phase 2: Lively damped elastic spring bounce from compressed impact into the Continue button.
                if not page_hidden[0]:
                    page_win.withdraw()
                    page_hidden[0] = True
                u = (progress - shrink_end) / (1.0 - shrink_end)
                spring = ease_out_elastic(u, damping=3.2, frequency=1.55)
                cur_w = max(1, round(squash_w + (end_w - squash_w) * spring))
                cur_h = max(1, round(squash_h + (end_h - squash_h) * spring))
                cur_x = end_x + (end_w - cur_w) // 2
                cur_y = end_y + (end_h - cur_h) // 2
                cur_r = min(end_r, cur_h // 2, cur_w // 2)
                cur_bg = blend_colour(impact_colour, ORANGE_ACCENT, min(1.0, u / 0.65))
                # Uncover the real Continue button right as the spring settles, then fade seamlessly into its label.
                if u >= 0.72:
                    if not btn_revealed[0] and btn_cover.winfo_exists():
                        btn_cover.destroy()
                        btn_revealed[0] = True
                    alpha = max(0.0, 1.0 - (u - 0.72) / 0.28)
                else:
                    alpha = 1.0

            x0, y0, x1, y1 = cur_x, cur_y, cur_x + cur_w, cur_y + cur_h
            rect_key = (x0, y0, x1, y1, cur_r)
            fill_update = cur_bg if cur_bg != last_bg[0] else None
            if rect_key != last_rect[0] or fill_update is not None:
                set_pill_shapes(x0, y0, x1, y1, cur_r, fill_update)
                if not page_hidden[0] and rect_key != last_rect[0]:
                    update_page_clip(x0, y0, x1, y1, cur_r)
                last_rect[0] = rect_key
                if fill_update is not None:
                    last_bg[0] = fill_update

            if abs(alpha - last_alpha[0]) >= 0.008 or (alpha in (0.0, 1.0) and alpha != last_alpha[0]):
                try:
                    pill_win.attributes("-alpha", alpha)
                    last_alpha[0] = alpha
                except tk.TclError:
                    finish()
                    return

            if progress < 1.0:
                spent_ms = (monotonic() - now) * 1000.0
                self.after(self._next_frame_delay(spent_ms, 16), draw_frame)
            else:
                finish()

        self.after(16, draw_frame)

    def paint_vinyl_record(self, event):
        """Draw and continuously rotate the 3 concentric text circles, vinyl disc, and tonearm."""
        canvas_obj = event.widget
        prev_spin = getattr(canvas_obj, "_spin_job", None)
        if prev_spin is not None:
            try:
                self.after_cancel(prev_spin)
            except tk.TclError:
                pass
            canvas_obj._spin_job = None

        canvas_obj.delete("all")
        w, h = max(240, event.width), max(240, event.height)
        unit = min(w, h)
        # Position toward the top-right, matching 1.svg's hero composition.
        center_x = w * 0.52
        center_y = max(unit * 0.48, min(h * 0.45, unit * 0.50))
        outer_r = unit * 0.43
        mid_r = outer_r * 0.82
        inner_r = outer_r * 0.65
        vinyl_r = outer_r * 0.50

        # 1. Three concentric rotating circles of text + centre vinyl disc.
        # On Windows, render both the rings and the vinyl disc via GDI+ (SmoothingModeAntiAlias +
        # TextRenderingHintAntiAlias) into a reusable PhotoImage so curves and letters have zero jitter.
        ring_text = "LISTEN · DISCOVER · STREAM · SHARE · BBC SOUND · "
        ring_specs = [
            (outer_r, "#d2d5db", max(11, round(unit * 0.032)), 0.45),
            (mid_r, TEXT_WHITE, max(10, round(unit * 0.028)), -0.60),
            (inner_r, ORANGE_ACCENT, max(9, round(unit * 0.023)), 0.80),
        ]
        ring_items = []
        gdi_rings = self._create_gdiplus_ring_renderer(
            canvas_obj, center_x, center_y, outer_r, vinyl_r, ring_text, ring_specs,
        )
        if gdi_rings is None:
            gdi_rings = self._create_pillow_ring_renderer(
                canvas_obj, center_x, center_y, outer_r, vinyl_r, ring_text, ring_specs,
            )
        sheen_1 = sheen_2 = glint_1 = glint_2 = None
        label_marker = label_top = label_bottom = None
        label_r = vinyl_r * 0.36
        label_dot_r = label_r * 0.68
        if gdi_rings is None:
            letter_slot = 0
            for radius, colour, font_size, speed in ring_specs:
                step = 360.0 / len(ring_text)
                for idx, char in enumerate(ring_text):
                    if char == " ":
                        continue
                    base_deg = idx * step
                    rad = math.radians(base_deg - 90)
                    init_ang = (-base_deg) % 360.0
                    item_id = canvas_obj.create_text(
                        center_x + radius * math.cos(rad),
                        center_y + radius * math.sin(rad),
                        text=char, fill=colour, font=(DEFAULT_FONT, font_size, "bold"),
                        angle=init_ang,
                    )
                    ring_items.append([item_id, base_deg, radius, speed, letter_slot % 3])
                    letter_slot += 1

            # 2. Fallback Tk Canvas Vinyl CD / Record in the centre (non-Windows).
            canvas_obj.create_oval(
                center_x - vinyl_r, center_y - vinyl_r,
                center_x + vinyl_r, center_y + vinyl_r,
                fill="#111215", outline="#2e3138", width=2,
            )
            sheen_1 = canvas_obj.create_arc(
                center_x - vinyl_r + 3, center_y - vinyl_r + 3,
                center_x + vinyl_r - 3, center_y + vinyl_r - 3,
                start=25, extent=38, fill="#24272e", outline="", style="pieslice",
            )
            sheen_2 = canvas_obj.create_arc(
                center_x - vinyl_r + 3, center_y - vinyl_r + 3,
                center_x + vinyl_r - 3, center_y + vinyl_r - 3,
                start=205, extent=38, fill="#24272e", outline="", style="pieslice",
            )
            glint_1 = canvas_obj.create_arc(
                center_x - vinyl_r * 0.84, center_y - vinyl_r * 0.84,
                center_x + vinyl_r * 0.84, center_y + vinyl_r * 0.84,
                start=35, extent=18, outline="#555a66", width=2, style="arc",
            )
            glint_2 = canvas_obj.create_arc(
                center_x - vinyl_r * 0.68, center_y - vinyl_r * 0.68,
                center_x + vinyl_r * 0.68, center_y + vinyl_r * 0.68,
                start=215, extent=20, outline="#4a4f5a", width=2, style="arc",
            )
            for frac, stroke in ((0.92, "#292c33"), (0.81, "#1e2026"), (0.70, "#2c2f36"), (0.58, "#1e2026"), (0.47, "#2a2d34")):
                gr = vinyl_r * frac
                canvas_obj.create_oval(center_x - gr, center_y - gr, center_x + gr, center_y + gr, outline=stroke, width=1)

            canvas_obj.create_oval(
                center_x - label_r, center_y - label_r,
                center_x + label_r, center_y + label_r,
                fill=ORANGE_ACCENT, outline=TEXT_WHITE, width=2,
            )
            label_marker = canvas_obj.create_oval(
                center_x - 3, center_y - label_dot_r - 3,
                center_x + 3, center_y - label_dot_r + 3,
                fill="#111111", outline="",
            )
            label_top = canvas_obj.create_text(
                center_x, center_y - label_r * 0.45,
                text="BBC", fill=TEXT_WHITE, font=(DEFAULT_FONT, max(7, round(label_r * 0.28)), "bold"),
            )
            label_bottom = canvas_obj.create_text(
                center_x, center_y + label_r * 0.48,
                text="SOUNDS", fill="#111111", font=(DEFAULT_FONT, max(6, round(label_r * 0.20)), "bold"),
            )
            spindle_r = max(5, vinyl_r * 0.08)
            canvas_obj.create_oval(
                center_x - spindle_r, center_y - spindle_r,
                center_x + spindle_r, center_y + spindle_r,
                fill="#111111", outline=TEXT_WHITE, width=2,
            )

        # 3. Turntable tonearm resting on the top-right of the spinning vinyl (as in 1.svg).
        pivot_x = center_x + vinyl_r * 1.06
        pivot_y = center_y - vinyl_r * 0.92
        base_r = max(14, vinyl_r * 0.20)
        canvas_obj.create_oval(
            pivot_x - base_r, pivot_y - base_r,
            pivot_x + base_r, pivot_y + base_r,
            fill="#2b2e35", outline="#7c808b", width=2,
        )
        canvas_obj.create_oval(
            pivot_x - base_r * 0.55, pivot_y - base_r * 0.55,
            pivot_x + base_r * 0.55, pivot_y + base_r * 0.55,
            fill="#565b66", outline="#c7cbd4", width=1,
        )
        cw_x = pivot_x + base_r * 0.55
        cw_y = pivot_y - base_r * 0.72
        canvas_obj.create_line(pivot_x, pivot_y, cw_x, cw_y, fill="#aeb3bd", width=max(5, round(vinyl_r * 0.06)), capstyle="round")
        elbow_x = pivot_x - vinyl_r * 0.10
        elbow_y = pivot_y + vinyl_r * 0.74
        tip_x = center_x + vinyl_r * 0.60
        tip_y = center_y + vinyl_r * 0.18
        canvas_obj.create_line(
            pivot_x, pivot_y, elbow_x, elbow_y, tip_x, tip_y,
            fill="#c6cad2", width=max(4, round(vinyl_r * 0.045)), smooth=True, capstyle="round",
        )
        head_x = tip_x - vinyl_r * 0.09
        head_y = tip_y + vinyl_r * 0.08
        canvas_obj.create_line(
            tip_x, tip_y, head_x, head_y,
            fill="#1f2126", width=max(8, round(vinyl_r * 0.09)), capstyle="butt",
        )
        canvas_obj.create_oval(
            head_x - 3, head_y - 3, head_x + 3, head_y + 3,
            fill=ORANGE_ACCENT, outline="",
        )

        # Continuous time-based rotation loop that adapts its frame rate on lower-end devices
        # and pauses automatically while dragging/resizing or when Reduced Motion is enabled.
        normal_tick_speed = 30.0
        state = {
            "tick": getattr(canvas_obj, "_spin_tick", 0.0),
            "last_t": None,
            "frame_n": 0,
            "velocity": normal_tick_speed,
        }
        scratch = {
            "active": False,
            "last_angle": 0.0,
            "last_time": 0.0,
            "last_render": 0.0,
            "velocity": 0.0,
        }
        grab_r = outer_r * 1.08
        vinyl_deg_per_tick = 2.2
        canvas_path = str(canvas_obj)
        tk_eval = canvas_obj.tk.eval
        cos = math.cos
        sin = math.sin
        atan2 = math.atan2
        hypot = math.hypot
        degrees = math.degrees
        deg2rad = math.pi / 180.0
        top_r = label_r * 0.45
        bot_r = label_r * 0.48
        # Use ~30fps on Linux/macOS or Canvas fallback so the turntable looks smooth while staying light on CPU.
        spin_base_ms = 22 if sys.platform == "win32" else 33

        def render_frame_at(t, force_all_angles=False):
            if not canvas_obj.winfo_exists():
                return False
            bucket = state["frame_n"] % 6
            state["frame_n"] += 1

            if gdi_rings is not None:
                gdi_rings(t)
                return True

            cmds = []
            append = cmds.append
            # Lightweight Canvas fallback: stagger expensive FreeType -angle updates across 6 buckets
            # unless actively scratching.
            for item_id, base_deg, radius, speed, slot in ring_items:
                deg = (base_deg + t * speed) % 360.0
                rad = (deg - 90.0) * deg2rad
                append(f"{canvas_path} coords {item_id} {center_x + radius * cos(rad):.1f} {center_y + radius * sin(rad):.1f}")
                if force_all_angles or ((slot == bucket % 3) and (bucket < 3)):
                    append(f"{canvas_path} itemconfigure {item_id} -angle {(-deg) % 360.0:.1f}")

            # Rotate the vinyl highlights and specular glints clockwise.
            vinyl_deg = (t * vinyl_deg_per_tick) % 360.0
            append(f"{canvas_path} itemconfigure {sheen_1} -start {(25.0 - vinyl_deg) % 360.0:.1f}")
            append(f"{canvas_path} itemconfigure {sheen_2} -start {(205.0 - vinyl_deg) % 360.0:.1f}")
            append(f"{canvas_path} itemconfigure {glint_1} -start {(35.0 - vinyl_deg) % 360.0:.1f}")
            append(f"{canvas_path} itemconfigure {glint_2} -start {(215.0 - vinyl_deg) % 360.0:.1f}")

            # Orbit the centre label dot and "BBC / SOUNDS" text.
            v_rad = (vinyl_deg - 90.0) * deg2rad
            cv, sv = cos(v_rad), sin(v_rad)
            mx = center_x + label_dot_r * cv
            my = center_y + label_dot_r * sv
            append(f"{canvas_path} coords {label_marker} {mx - 3:.1f} {my - 3:.1f} {mx + 3:.1f} {my + 3:.1f}")
            append(f"{canvas_path} coords {label_top} {center_x + top_r * cv:.1f} {center_y + top_r * sv:.1f}")
            append(f"{canvas_path} coords {label_bottom} {center_x - bot_r * cv:.1f} {center_y - bot_r * sv:.1f}")
            append(f"{canvas_path} itemconfigure {label_top} -angle {(-vinyl_deg) % 360.0:.1f}")
            append(f"{canvas_path} itemconfigure {label_bottom} -angle {(180.0 - vinyl_deg) % 360.0:.1f}")

            try:
                tk_eval("\n".join(cmds))
            except tk.TclError:
                return False
            return True

        def _on_vinyl_press(evt):
            if getattr(self, "_signing_out", False):
                return
            dx = evt.x - center_x
            dy = evt.y - center_y
            if hypot(dx, dy) > grab_r:
                return
            now_t = monotonic()
            scratch["active"] = True
            scratch["last_angle"] = degrees(atan2(dy, dx))
            scratch["last_time"] = now_t
            scratch["velocity"] = 0.0
            state["velocity"] = 0.0
            try:
                canvas_obj.configure(cursor="hand2")
            except tk.TclError:
                pass

        def _on_vinyl_drag(evt):
            if not scratch["active"] or getattr(self, "_signing_out", False):
                return
            dx = evt.x - center_x
            dy = evt.y - center_y
            now_t = monotonic()
            # Ignore tiny jitter right over the spindle centre so atan2 never flips 180 degrees.
            if hypot(dx, dy) < 4.0:
                scratch["last_time"] = now_t
                return
            angle = degrees(atan2(dy, dx))
            delta_deg = (angle - scratch["last_angle"] + 180.0) % 360.0 - 180.0
            scratch["last_angle"] = angle

            delta_tick = delta_deg / vinyl_deg_per_tick
            state["tick"] = (state["tick"] + delta_tick) % 36000.0
            canvas_obj._spin_tick = state["tick"]

            dt_drag = max(0.004, now_t - scratch["last_time"])
            scratch["last_time"] = now_t
            inst_vel = max(-450.0, min(450.0, delta_tick / dt_drag))
            scratch["velocity"] = scratch["velocity"] * 0.45 + inst_vel * 0.55

            # Cap synchronous drag redraws to ~60fps so high-polling mice stay buttery smooth.
            if (now_t - scratch["last_render"]) >= 0.014:
                scratch["last_render"] = now_t
                render_frame_at(state["tick"], force_all_angles=True)

        def _on_vinyl_release(evt):
            if not scratch["active"]:
                return
            now_t = monotonic()
            scratch["active"] = False
            # If the user held the vinyl still before releasing, spin back up smoothly from rest.
            if (now_t - scratch["last_time"]) > 0.08:
                state["velocity"] = 0.0
            else:
                state["velocity"] = max(-450.0, min(450.0, scratch["velocity"]))
            state["last_t"] = now_t
            render_frame_at(state["tick"], force_all_angles=True)
            dx = evt.x - center_x
            dy = evt.y - center_y
            try:
                canvas_obj.configure(cursor="hand2" if hypot(dx, dy) <= grab_r else "")
            except tk.TclError:
                pass

        def _on_vinyl_hover(evt):
            if scratch["active"] or getattr(self, "_signing_out", False):
                return
            dx = evt.x - center_x
            dy = evt.y - center_y
            want = "hand2" if hypot(dx, dy) <= grab_r else ""
            try:
                if canvas_obj.cget("cursor") != want:
                    canvas_obj.configure(cursor=want)
            except tk.TclError:
                pass

        def _on_vinyl_leave(_evt):
            if scratch["active"]:
                return
            try:
                if canvas_obj.cget("cursor"):
                    canvas_obj.configure(cursor="")
            except tk.TclError:
                pass

        canvas_obj.bind("<ButtonPress-1>", _on_vinyl_press)
        canvas_obj.bind("<B1-Motion>", _on_vinyl_drag)
        canvas_obj.bind("<ButtonRelease-1>", _on_vinyl_release)
        canvas_obj.bind("<Motion>", _on_vinyl_hover)
        canvas_obj.bind("<Leave>", _on_vinyl_leave)

        def animate_spin():
            canvas_obj._spin_job = None
            if not canvas_obj.winfo_exists():
                return
            if getattr(self, "_signing_out", False):
                scratch["active"] = False
                state["last_t"] = None
                return
            now = monotonic()
            if now < getattr(self, "_window_moving_until", 0.0):
                state["last_t"] = None
                canvas_obj._spin_job = self.after(50, animate_spin)
                return

            if scratch["active"]:
                # While the user holds/scratches the record, keep the loop alive without auto-spinning.
                state["last_t"] = now
                if (now - scratch["last_render"]) >= 0.014:
                    scratch["last_render"] = now
                    render_frame_at(state["tick"], force_all_angles=True)
                canvas_obj._spin_job = self.after(spin_base_ms, animate_spin)
                return

            # Advance in real elapsed time and smoothly recover motor speed after a DJ scratch release.
            dt = (spin_base_ms / 1000.0) if state["last_t"] is None else max(0.004, min(0.060, now - state["last_t"]))
            state["last_t"] = now
            state["velocity"] += (normal_tick_speed - state["velocity"]) * min(1.0, dt * 4.5)
            state["tick"] = (state["tick"] + dt * state["velocity"]) % 36000.0
            canvas_obj._spin_tick = state["tick"]

            if not render_frame_at(state["tick"]):
                return

            # Adapt frame delay so typing/clicks stay responsive even on lower-end CPUs.
            spent_ms = (monotonic() - now) * 1000.0
            delay_ms = self._next_frame_delay(spent_ms, base_ms=spin_base_ms, min_yield_ms=10)
            canvas_obj._spin_job = self.after(delay_ms, animate_spin)

        canvas_obj._resume_spin = animate_spin
        if not getattr(self, "_signing_out", False):
            animate_spin()
        elif gdi_rings is not None:
            gdi_rings(state["tick"])

    def _create_pillow_ring_renderer(self, canvas_obj, center_x, center_y, outer_r, vinyl_r, ring_text, ring_specs):
        """Cross-platform Pillow renderer: pre-renders cropped L-mode text rings + vinyl once, outputs PPM (no ImageTk needed)."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            from gui_parts.theme import ROOT_PATH
        except Exception:
            return None

        try:
            pad = max(22, round(ring_specs[0][2] * 2.1))
            size = int(math.ceil((outer_r + pad) * 2))
            if size < 64 or size > 1100:
                return None

            # Locate bundled BBC Reith Sans Bold (or any system sans-serif TTF/OTF) for crisp ring letters.
            font_path = None
            reith_dir = ROOT_PATH / "BBCReithSans"
            if reith_dir.is_dir():
                for candidate in sorted(reith_dir.rglob("*.ttf")):
                    n = candidate.stem.lower()
                    if "sans" in n and ("bd" in n or "bold" in n) and "it" not in n and "cd" not in n:
                        font_path = str(candidate)
                        break
            if font_path is None:
                from pathlib import Path as _Path
                for sys_font in (
                    "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf",
                    "/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf",
                    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf",
                    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/System/Library/Fonts/Helvetica.ttc",
                ):
                    if _Path(sys_font).is_file():
                        font_path = sys_font
                        break

            def load_font(pt_size):
                px = max(10, round(pt_size * 1.33))
                if font_path:
                    try:
                        return ImageFont.truetype(font_path, px)
                    except OSError:
                        pass
                return ImageFont.load_default()

            def parse_rgb(hex_col):
                c = str(hex_col).lstrip("#")
                if len(c) != 6:
                    return (255, 255, 255)
                return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

            bg_rgb = parse_rgb(canvas_obj.cget("bg"))
            resample_rot = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
            resample_aa = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

            # Pre-render each solid-colour text ring ONCE into a cropped 1-channel L-mode alpha mask (4x faster to rotate than RGBA).
            step = 360.0 / len(ring_text)
            ring_layers = []
            for radius, colour, font_size, speed in ring_specs:
                ring_pad = max(18, round(font_size * 1.9))
                layer_sz = min(size, max(64, int(math.ceil((radius + ring_pad) * 2))))
                l_half = layer_sz / 2.0
                mask_layer = Image.new("L", (layer_sz, layer_sz), 0)
                fnt = load_font(font_size)
                glyph_box = max(32, round(font_size * 3.0))
                g_half = glyph_box // 2
                for idx, ch in enumerate(ring_text):
                    if ch == " ":
                        continue
                    base_deg = idx * step
                    glyph = Image.new("L", (glyph_box, glyph_box), 0)
                    gd = ImageDraw.Draw(glyph)
                    gd.text((g_half, g_half), ch, fill=255, font=fnt, anchor="mm")
                    rot_g = glyph.rotate(-base_deg, resample=resample_aa, expand=False)
                    rad = math.radians(base_deg - 90.0)
                    gx = round(l_half + radius * math.cos(rad) - g_half)
                    gy = round(l_half + radius * math.sin(rad) - g_half)
                    mask_layer.paste(255, (gx, gy), rot_g)
                off = (size - layer_sz) // 2
                ring_layers.append((mask_layer, parse_rgb(colour), off, speed))

            # Pre-render the anti-aliased vinyl disc ONCE at 2x resolution, cropped tightly around vinyl_r.
            v_sz = min(size, max(64, int(math.ceil((vinyl_r + 6) * 2))))
            v_off = (size - v_sz) // 2
            s2 = v_sz * 2
            h2 = s2 / 2.0
            vr2 = vinyl_r * 2.0
            vinyl_hi = Image.new("RGBA", (s2, s2), (0, 0, 0, 0))
            vd = ImageDraw.Draw(vinyl_hi)
            vd.ellipse((h2 - vr2, h2 - vr2, h2 + vr2, h2 + vr2), fill=(17, 18, 21, 255), outline=(46, 49, 56, 255), width=4)
            vd.pieslice((h2 - vr2 + 6, h2 - vr2 + 6, h2 + vr2 - 6, h2 + vr2 - 6), start=-63, end=-25, fill=(36, 39, 46, 255))
            vd.pieslice((h2 - vr2 + 6, h2 - vr2 + 6, h2 + vr2 - 6, h2 + vr2 - 6), start=117, end=155, fill=(36, 39, 46, 255))
            for frac, col_hex in ((0.92, "#292c33"), (0.81, "#1e2026"), (0.70, "#2c2f36"), (0.58, "#1e2026"), (0.47, "#2a2d34")):
                gr = vr2 * frac
                vd.ellipse((h2 - gr, h2 - gr, h2 + gr, h2 + gr), outline=parse_rgb(col_hex) + (255,), width=2)
            lr2 = vr2 * 0.36
            vd.ellipse((h2 - lr2, h2 - lr2, h2 + lr2, h2 + lr2), fill=parse_rgb(ORANGE_ACCENT) + (255,), outline=parse_rgb(TEXT_WHITE) + (255,), width=4)
            dot_r2 = lr2 * 0.68
            vd.ellipse((h2 - 6, h2 - dot_r2 - 6, h2 + 6, h2 - dot_r2 + 6), fill=(17, 17, 17, 255))
            bbc_f = load_font(max(7, round(vinyl_r * 0.36 * 0.28)) * 2)
            snd_f = load_font(max(6, round(vinyl_r * 0.36 * 0.20)) * 2)
            vd.text((h2, h2 - lr2 * 0.45), "BBC", fill=parse_rgb(TEXT_WHITE) + (255,), font=bbc_f, anchor="mm")
            vd.text((h2, h2 + lr2 * 0.48), "SOUNDS", fill=(17, 17, 17, 255), font=snd_f, anchor="mm")
            sp2 = max(10.0, vr2 * 0.08)
            vd.ellipse((h2 - sp2, h2 - sp2, h2 + sp2, h2 + sp2), fill=(17, 17, 17, 255), outline=parse_rgb(TEXT_WHITE) + (255,), width=4)
            vinyl_rgba = vinyl_hi.resize((v_sz, v_sz), resample_aa)
            vinyl_rgb = vinyl_rgba.convert("RGB")
            vinyl_alpha = vinyl_rgba.getchannel("A")

            base_bg = Image.new("RGB", (size, size), bg_rgb)
            ppm_header = f"P6\n{size} {size}\n255\n".encode("ascii")
            photo = tk.PhotoImage(master=self, data=ppm_header + base_bg.tobytes(), format="PPM")
            canvas_obj._ring_photo = photo
            canvas_obj.create_image(center_x, center_y, image=photo, anchor="center")

            def render_frame(t):
                if not canvas_obj.winfo_exists():
                    return
                frame = base_bg.copy()
                for mask_layer, rgb_col, off, speed in ring_layers:
                    ang = -(t * speed) % 360.0
                    rot_m = mask_layer.rotate(ang, resample=resample_rot, expand=False)
                    frame.paste(rgb_col, (off, off), rot_m)
                v_ang = -(t * 2.2) % 360.0
                v_rot = vinyl_rgb.rotate(v_ang, resample=resample_rot, expand=False, fillcolor=bg_rgb)
                frame.paste(v_rot, (v_off, v_off), vinyl_alpha)
                photo.configure(data=ppm_header + frame.tobytes())

            render_frame(0.0)
            return render_frame
        except Exception:
            return None

    def _create_gdiplus_ring_renderer(self, canvas_obj, center_x, center_y, outer_r, vinyl_r, ring_text, ring_specs):
        """Build a Windows GDI+ sub-pixel anti-aliased renderer for the 3 rotating text rings and vinyl disc."""
        import sys
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            gdiplus = ctypes.windll.gdiplus
            if not getattr(self, "_gdiplus_vinyl_token", None):
                class _GdiplusStartupInput(ctypes.Structure):
                    _fields_ = [
                        ("GdiplusVersion", ctypes.c_uint32),
                        ("DebugEventCallback", ctypes.c_void_p),
                        ("SuppressBackgroundThread", ctypes.c_int),
                        ("SuppressExternalCodecs", ctypes.c_int),
                    ]
                token = ctypes.c_void_p()
                if gdiplus.GdiplusStartup(ctypes.byref(token), ctypes.byref(_GdiplusStartupInput(1, None, 0, 0)), None) != 0:
                    return None
                self._gdiplus_vinyl_token = token

            # Ensure bitmap dimension is a multiple of 4 so 24bppRGB stride is 4-byte aligned.
            pad = max(24, round(ring_specs[0][2] * 2.2))
            size = ((int(math.ceil((outer_r + pad) * 2)) + 3) // 4) * 4
            if size < 64 or size > 1200:
                return None

            def swapped_argb(hex_col):
                c = str(hex_col).lstrip("#")
                if len(c) != 6:
                    return 0xFFFFFFFF
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                # Swap R and B so GDI+ PixelFormat24bppRGB ([B, G, R] in memory) produces exact PPM [R, G, B].
                return 0xFF000000 | (b << 16) | (g << 8) | r

            bg_argb = ctypes.c_uint32(swapped_argb(canvas_obj.cget("bg")))
            stride = size * 3
            buf = (ctypes.c_ubyte * (stride * size))()
            bmp = ctypes.c_void_p()
            if gdiplus.GdipCreateBitmapFromScan0(size, size, stride, 0x00021808, buf, ctypes.byref(bmp)) != 0:
                return None
            gfx = ctypes.c_void_p()
            if gdiplus.GdipGetImageGraphicsContext(bmp, ctypes.byref(gfx)) != 0:
                gdiplus.GdipDisposeImage(bmp)
                return None
            gdiplus.GdipSetSmoothingMode(gfx, 4)        # SmoothingModeAntiAlias
            gdiplus.GdipSetTextRenderingHint(gfx, 4)    # TextRenderingHintAntiAlias (sub-pixel, no grid-fitting)

            fam = ctypes.c_void_p()
            for fam_name in (DEFAULT_FONT, "Segoe UI", "Arial"):
                if gdiplus.GdipCreateFontFamilyFromName(fam_name, None, ctypes.byref(fam)) == 0 and fam.value:
                    break
            if not fam.value:
                gdiplus.GdipDeleteGraphics(gfx)
                gdiplus.GdipDisposeImage(bmp)
                return None

            fmt = ctypes.c_void_p()
            gdiplus.GdipCreateStringFormat(0, 0, ctypes.byref(fmt))
            gdiplus.GdipSetStringFormatAlign(fmt, 1)      # Center
            gdiplus.GdipSetStringFormatLineAlign(fmt, 1)  # Center

            class _RectF(ctypes.Structure):
                _fields_ = [("X", ctypes.c_float), ("Y", ctypes.c_float), ("W", ctypes.c_float), ("H", ctypes.c_float)]

            char_rect = _RectF(-26.0, -26.0, 52.0, 52.0)
            label_rect = _RectF(-60.0, -24.0, 120.0, 48.0)
            step = 360.0 / len(ring_text)
            chars = tuple((idx * step, ch) for idx, ch in enumerate(ring_text) if ch != " ")

            c_float = ctypes.c_float
            fonts_to_free = []
            brushes_to_free = []
            pens_to_free = []

            def make_brush(hex_col):
                br = ctypes.c_void_p()
                gdiplus.GdipCreateSolidFill(ctypes.c_uint32(swapped_argb(hex_col)), ctypes.byref(br))
                brushes_to_free.append(br)
                return br

            def make_pen(hex_col, width_px):
                pen = ctypes.c_void_p()
                gdiplus.GdipCreatePen1(ctypes.c_uint32(swapped_argb(hex_col)), c_float(float(width_px)), 2, ctypes.byref(pen))
                pens_to_free.append(pen)
                return pen

            def make_font(pt_size):
                fnt = ctypes.c_void_p()
                gdiplus.GdipCreateFont(fam, c_float(max(9.0, pt_size * 1.33)), 1, 2, ctypes.byref(fnt))
                fonts_to_free.append(fnt)
                return fnt

            prepared_rings = []
            for radius, colour, font_size, speed in ring_specs:
                prepared_rings.append((c_float(-float(radius)), speed, make_font(font_size), make_brush(colour)))

            # Pre-create brushes, pens, and fonts for the anti-aliased centre vinyl disc.
            half_f = size / 2.0
            disc_br = make_brush("#111215")
            disc_pen = make_pen("#2e3138", 2.0)
            sheen_br = make_brush("#24272e")
            glint1_pen = make_pen("#555a66", 2.0)
            glint2_pen = make_pen("#4a4f5a", 2.0)
            groove_specs = tuple(
                (c_float(half_f - vinyl_r * f), c_float(half_f - vinyl_r * f),
                 c_float(vinyl_r * f * 2.0), c_float(vinyl_r * f * 2.0), make_pen(col, 1.0))
                for f, col in ((0.92, "#292c33"), (0.81, "#1e2026"), (0.70, "#2c2f36"), (0.58, "#1e2026"), (0.47, "#2a2d34"))
            )
            label_r = vinyl_r * 0.36
            label_dot_r = label_r * 0.68
            spindle_r = max(5.0, vinyl_r * 0.08)
            label_br = make_brush(ORANGE_ACCENT)
            white_pen = make_pen(TEXT_WHITE, 2.0)
            white_br = make_brush(TEXT_WHITE)
            dark_br = make_brush("#111111")
            bbc_font = make_font(max(7, round(label_r * 0.28)))
            sounds_font = make_font(max(6, round(label_r * 0.20)))

            disc_xy = c_float(half_f - vinyl_r)
            disc_d = c_float(vinyl_r * 2.0)
            sheen_xy = c_float(half_f - vinyl_r + 3.0)
            sheen_d = c_float((vinyl_r - 3.0) * 2.0)
            g1_xy = c_float(half_f - vinyl_r * 0.84)
            g1_d = c_float(vinyl_r * 0.84 * 2.0)
            g2_xy = c_float(half_f - vinyl_r * 0.68)
            g2_d = c_float(vinyl_r * 0.68 * 2.0)
            lbl_xy = c_float(half_f - label_r)
            lbl_d = c_float(label_r * 2.0)
            sp_xy = c_float(half_f - spindle_r)
            sp_d = c_float(spindle_r * 2.0)
            dot_x = c_float(-3.0)
            dot_y = c_float(-label_dot_r - 3.0)
            dot_d = c_float(6.0)
            top_neg_y = c_float(-label_r * 0.45)
            bot_neg_y = c_float(-label_r * 0.48)
            sw_38 = c_float(38.0)
            sw_18 = c_float(18.0)
            sw_20 = c_float(20.0)
            deg_180 = c_float(180.0)

            header = f"P6\n{size} {size}\n255\n".encode("ascii")
            half = c_float(half_f)
            zero = c_float(0.0)
            rect_ref = ctypes.byref(char_rect)
            lbl_rect_ref = ctypes.byref(label_rect)

            gdi_clear = gdiplus.GdipGraphicsClear
            gdi_reset = gdiplus.GdipResetWorldTransform
            gdi_trans = gdiplus.GdipTranslateWorldTransform
            gdi_rot = gdiplus.GdipRotateWorldTransform
            gdi_draw = gdiplus.GdipDrawString
            gdi_fill_ell = gdiplus.GdipFillEllipse
            gdi_draw_ell = gdiplus.GdipDrawEllipse
            gdi_fill_pie = gdiplus.GdipFillPie
            gdi_draw_arc = gdiplus.GdipDrawArc

            # Paint initial frame into a single reusable PhotoImage placed behind the tonearm.
            gdi_clear(gfx, bg_argb)
            photo = tk.PhotoImage(data=header + bytes(buf))
            canvas_obj._ring_photo = photo
            canvas_obj.create_image(center_x, center_y, image=photo, anchor="center")

            alive = [True]

            def cleanup_gdi(_event=None):
                if not alive[0]:
                    return
                alive[0] = False
                for fnt in fonts_to_free:
                    if fnt.value:
                        gdiplus.GdipDeleteFont(fnt)
                for br in brushes_to_free:
                    if br.value:
                        gdiplus.GdipDeleteBrush(br)
                for pen in pens_to_free:
                    if pen.value:
                        gdiplus.GdipDeletePen(pen)
                if fmt.value:
                    gdiplus.GdipDeleteStringFormat(fmt)
                if fam.value:
                    gdiplus.GdipDeleteFontFamily(fam)
                if gfx.value:
                    gdiplus.GdipDeleteGraphics(gfx)
                if bmp.value:
                    gdiplus.GdipDisposeImage(bmp)

            canvas_obj.bind("<Destroy>", cleanup_gdi, add="+")

            def render_frame(t):
                if not alive[0]:
                    return
                gdi_clear(gfx, bg_argb)
                # 1. Three rotating anti-aliased text rings.
                for neg_r, speed, fnt, br in prepared_rings:
                    offset = t * speed
                    for base_deg, ch in chars:
                        gdi_reset(gfx)
                        gdi_trans(gfx, half, half, 0)
                        gdi_rot(gfx, c_float(base_deg + offset), 0)
                        gdi_trans(gfx, zero, neg_r, 0)
                        gdi_draw(gfx, ch, 1, fnt, rect_ref, fmt, br)

                # 2. Anti-aliased vinyl disc, rotating specular sheens/glints, grooves, and centre label.
                gdi_reset(gfx)
                vinyl_deg = (t * 2.2) % 360.0
                gdi_fill_ell(gfx, disc_br, disc_xy, disc_xy, disc_d, disc_d)
                gdi_fill_pie(gfx, sheen_br, sheen_xy, sheen_xy, sheen_d, sheen_d, c_float(vinyl_deg - 63.0), sw_38)
                gdi_fill_pie(gfx, sheen_br, sheen_xy, sheen_xy, sheen_d, sheen_d, c_float(vinyl_deg + 117.0), sw_38)
                gdi_draw_arc(gfx, glint1_pen, g1_xy, g1_xy, g1_d, g1_d, c_float(vinyl_deg - 53.0), sw_18)
                gdi_draw_arc(gfx, glint2_pen, g2_xy, g2_xy, g2_d, g2_d, c_float(vinyl_deg + 125.0), sw_20)
                gdi_draw_ell(gfx, disc_pen, disc_xy, disc_xy, disc_d, disc_d)
                for gx, gy, gw, gh, gpen in groove_specs:
                    gdi_draw_ell(gfx, gpen, gx, gy, gw, gh)

                gdi_fill_ell(gfx, label_br, lbl_xy, lbl_xy, lbl_d, lbl_d)
                gdi_draw_ell(gfx, white_pen, lbl_xy, lbl_xy, lbl_d, lbl_d)

                # Rotating marker dot + "BBC" and "SOUNDS" on the orange label.
                gdi_trans(gfx, half, half, 0)
                gdi_rot(gfx, c_float(vinyl_deg), 0)
                gdi_fill_ell(gfx, dark_br, dot_x, dot_y, dot_d, dot_d)
                gdi_trans(gfx, zero, top_neg_y, 0)
                gdi_draw(gfx, "BBC", 3, bbc_font, lbl_rect_ref, fmt, white_br)

                gdi_reset(gfx)
                gdi_trans(gfx, half, half, 0)
                gdi_rot(gfx, c_float(vinyl_deg + 180.0), 0)
                gdi_trans(gfx, zero, bot_neg_y, 0)
                gdi_draw(gfx, "SOUNDS", 6, sounds_font, lbl_rect_ref, fmt, dark_br)

                # Centre spindle.
                gdi_reset(gfx)
                gdi_fill_ell(gfx, dark_br, sp_xy, sp_xy, sp_d, sp_d)
                gdi_draw_ell(gfx, white_pen, sp_xy, sp_xy, sp_d, sp_d)

                photo.configure(data=header + bytes(buf))

            return render_frame
        except Exception:
            return None
