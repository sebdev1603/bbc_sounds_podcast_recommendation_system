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
        self.unbind_all("<MouseWheel>")
        self.current_user = None
        # Reset the login screen visually to default dark theme and 100% text size without changing DB rows.
        self._text_scale = 1.0
        self.set_theme("dark", refresh=False, persist=False)
        self._shell_box = None
        self._shell_bottom_bar = None
        self._shell_bottom_bar_key = None

        # Clear any existing widgets and match the window/titlebar background to DARK_BG.
        for child_widget in self.winfo_children():
            child_widget.destroy()
        self.configure(bg=DARK_BG)
        self.set_windows_titlebar_colour(DARK_BG)

        main_box = tk.Frame(self, bg=DARK_BG)
        main_box.pack(fill="both", expand=True, padx=58, pady=38)

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
            insertbackground=TEXT_WHITE, relief="flat", highlightthickness=0,
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

        def queue_record_paint(event):
            # Debounce resize redraws so dragging the window edge does not rebuild the canvas every pixel.
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

    def expand_login_button_to_home(self, login_button):
        """Coil and launch the rounded Continue button while smoothly revealing and fading in Home."""
        # Sample the button's exact current hover colour, inset, and screen geometry before expanding.
        self.cancel_button_hover(login_button)
        face, hover = getattr(login_button, "_rounded_colours", (ORANGE_ACCENT, ORANGE_HL))
        hover_t = getattr(login_button, "_hover_step", 0) / 12.0
        hover_eased = (
            ease_out_elastic(hover_t, damping=4.8, frequency=1.15)
            if getattr(login_button, "_hover_target", 0) > 0
            else 1.0 - (1.0 - hover_t) ** 3
        )
        start_colour = blend_colour(face, hover, hover_eased)
        start_inset = max(0, min(3, round(3.0 - 2.0 * hover_eased)))
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

        # Capture the clean login screen BEFORE modifying the button, then clear its text.
        self.focus_set()
        login_snap = self._capture_window_snapshot(win_x, win_y, win_w, win_h)
        login_button.configure(text="")
        # Use a dark unique chroma key (#010203) instead of bright magenta so any 1px edge never looks bright/white.
        key_colour = "#010203"

        def strip_dwm_border(top_win):
            """Remove the Windows 11 1px DWM border/rounding on borderless overlay Toplevels."""
            if sys.platform != "win32":
                return
            try:
                hwnd = ctypes.windll.user32.GetParent(top_win.winfo_id()) or top_win.winfo_id()
                # DWMWA_WINDOW_CORNER_PREFERENCE (33) = DWMWCP_DONOTROUND (1)
                # DWMWA_BORDER_COLOR (34) = DWMWA_COLOR_NONE (0xFFFFFFFE)
                for attr, raw_val in ((33, 1), (34, 0xFFFFFFFE)):
                    val = ctypes.c_uint32(raw_val)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        ctypes.c_void_p(hwnd), ctypes.c_int(attr), ctypes.byref(val), ctypes.sizeof(val),
                    )
            except Exception:
                pass

        # Two fixed-size full-window Toplevels kept withdrawn until fully painted so Windows
        # never flashes a default white/grey window frame before the dark canvas appears.
        backdrop_win = None
        pill_win = None
        try:
            backdrop_win = tk.Toplevel(self)
            backdrop_win.withdraw()
            backdrop_win._preserve_during_shell_build = True
            backdrop_win.overrideredirect(True)
            backdrop_win.configure(bg=DARK_BG)
            backdrop_win.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
            backdrop_win.attributes("-transparentcolor", key_colour)
            backdrop_win.transient(self)

            pill_win = tk.Toplevel(self)
            pill_win.withdraw()
            pill_win._preserve_during_shell_build = True
            pill_win.overrideredirect(True)
            pill_win.configure(bg=key_colour)
            pill_win.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")
            pill_win.attributes("-transparentcolor", key_colour)
            pill_win.attributes("-alpha", 1.0)
            pill_win.transient(self)
        except tk.TclError:
            for w in (pill_win, backdrop_win):
                if w is not None:
                    try:
                        w.destroy()
                    except tk.TclError:
                        pass
            self.show_home()
            return

        def make_rounded_shapes(canvas, fill_col, tag):
            return (
                canvas.create_rectangle(0, 0, 0, 0, fill=fill_col, outline="", tags=tag),
                canvas.create_rectangle(0, 0, 0, 0, fill=fill_col, outline="", tags=tag),
                canvas.create_oval(0, 0, 0, 0, fill=fill_col, outline="", tags=tag),
                canvas.create_oval(0, 0, 0, 0, fill=fill_col, outline="", tags=tag),
                canvas.create_oval(0, 0, 0, 0, fill=fill_col, outline="", tags=tag),
                canvas.create_oval(0, 0, 0, 0, fill=fill_col, outline="", tags=tag),
            )

        def set_rounded_shapes(canvas, items, tag, x0, y0, x1, y1, radius, fill_col=None):
            w = max(1, x1 - x0)
            h = max(1, y1 - y0)
            r = max(0, min(radius, w // 2, h // 2))
            if r <= 1:
                canvas.coords(items[0], x0, y0, x1, y1)
                for extra in items[1:]:
                    canvas.coords(extra, 0, 0, 0, 0)
            else:
                d = r * 2
                # Keep corner ovals strictly inside [x0, x1-1] x [y0, y1-1] so Tk's inclusive oval
                # bounds align pixel-for-pixel with the rectangles and leave zero 1px seams.
                ox1 = max(x0, x1 - 1)
                oy1 = max(y0, y1 - 1)
                canvas.coords(items[0], x0 + r, y0, x1 - r, y1)
                canvas.coords(items[1], x0, y0 + r, x1, y1 - r)
                canvas.coords(items[2], x0, y0, x0 + d, y0 + d)
                canvas.coords(items[3], ox1 - d, y0, ox1, y0 + d)
                canvas.coords(items[4], x0, oy1 - d, x0 + d, oy1)
                canvas.coords(items[5], ox1 - d, oy1 - d, ox1, oy1)
            if fill_col is not None:
                canvas.itemconfigure(tag, fill=fill_col)

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
        strip_dwm_border(backdrop_win)
        strip_dwm_border(pill_win)
        backdrop_win.deiconify()
        pill_win.deiconify()
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
                self.after(14, draw_frame)
            else:
                finish()

        # Start after queued idle layout/scaling callbacks finish so the animation runs uninterrupted.
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

        # 1. Three concentric rotating circles of text (matching 1.svg).
        ring_text = "LISTEN · DISCOVER · STREAM · SHARE · BBC SOUND · "
        ring_specs = [
            (outer_r, "#d2d5db", max(11, round(unit * 0.032)), 0.45),
            (mid_r, TEXT_WHITE, max(10, round(unit * 0.028)), -0.60),
            (inner_r, ORANGE_ACCENT, max(9, round(unit * 0.023)), 0.80),
        ]
        ring_items = []
        for radius, colour, font_size, speed in ring_specs:
            step = 360.0 / len(ring_text)
            for idx, char in enumerate(ring_text):
                base_deg = idx * step
                rad = math.radians(base_deg - 90)
                item_id = canvas_obj.create_text(
                    center_x + radius * math.cos(rad),
                    center_y + radius * math.sin(rad),
                    text=char, fill=colour, font=("Arial Black", font_size, "bold"),
                    angle=(-base_deg) % 360,
                )
                ring_items.append((item_id, base_deg, radius, speed))

        # 2. Rotating Vinyl CD / Record in the centre.
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

        label_r = vinyl_r * 0.36
        canvas_obj.create_oval(
            center_x - label_r, center_y - label_r,
            center_x + label_r, center_y + label_r,
            fill=ORANGE_ACCENT, outline=TEXT_WHITE, width=2,
        )
        label_dot_r = label_r * 0.68
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

        # Continuous 360-degree rotation loop for vinyl CD and all 3 text circles.
        state = {"tick": getattr(canvas_obj, "_spin_tick", 0.0)}

        def animate_spin():
            if not canvas_obj.winfo_exists():
                return
            # Advance the shared frame counter (~30 fps) and wrap periodically to avoid float drift.
            state["tick"] = (state["tick"] + 1.0) % 36000.0
            canvas_obj._spin_tick = state["tick"]
            t = state["tick"]

            # Rotate each letter along its concentric ring and keep its angle tangent to the circle.
            for item_id, base_deg, radius, speed in ring_items:
                deg = (base_deg + t * speed) % 360.0
                rad = math.radians(deg - 90.0)
                canvas_obj.coords(
                    item_id,
                    center_x + radius * math.cos(rad),
                    center_y + radius * math.sin(rad),
                )
                canvas_obj.itemconfigure(item_id, angle=(-deg) % 360.0)

            # Rotate the vinyl highlights and specular glints clockwise.
            vinyl_deg = (t * 2.2) % 360.0
            canvas_obj.itemconfigure(sheen_1, start=(25.0 - vinyl_deg) % 360.0)
            canvas_obj.itemconfigure(sheen_2, start=(205.0 - vinyl_deg) % 360.0)
            canvas_obj.itemconfigure(glint_1, start=(35.0 - vinyl_deg) % 360.0)
            canvas_obj.itemconfigure(glint_2, start=(215.0 - vinyl_deg) % 360.0)

            # Orbit the centre label dot and "BBC / SOUNDS" text around the spindle.
            v_rad = math.radians(vinyl_deg - 90.0)
            mx = center_x + label_dot_r * math.cos(v_rad)
            my = center_y + label_dot_r * math.sin(v_rad)
            canvas_obj.coords(label_marker, mx - 3, my - 3, mx + 3, my + 3)

            top_rad = math.radians(vinyl_deg - 90.0)
            bot_rad = math.radians(vinyl_deg + 90.0)
            canvas_obj.coords(
                label_top,
                center_x + label_r * 0.45 * math.cos(top_rad),
                center_y + label_r * 0.45 * math.sin(top_rad),
            )
            canvas_obj.itemconfigure(label_top, angle=(-vinyl_deg) % 360.0)
            canvas_obj.coords(
                label_bottom,
                center_x + label_r * 0.48 * math.cos(bot_rad),
                center_y + label_r * 0.48 * math.sin(bot_rad),
            )
            canvas_obj.itemconfigure(label_bottom, angle=(180.0 - vinyl_deg) % 360.0)

            # Schedule the next rotation frame (~33ms -> 30 fps).
            canvas_obj._spin_job = self.after(33, animate_spin)

        animate_spin()
