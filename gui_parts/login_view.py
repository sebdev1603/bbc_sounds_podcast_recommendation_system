"""Login screen, button-to-home expansion transition, and spinning vinyl turntable visual."""
import math
import sqlite3
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

    def expand_login_button_to_home(self, login_button):
        """Expand the rounded Continue button to fill the window, then lift a curtain to reveal Home."""
        # Sample the button's exact current hover colour, inset, and screen geometry before expanding.
        self.cancel_button_hover(login_button)
        face, hover = getattr(login_button, "_rounded_colours", (ORANGE_ACCENT, ORANGE_HL))
        hover_t = getattr(login_button, "_hover_step", 0) / 12.0
        hover_eased = ease_out_elastic(hover_t, damping=4.8, frequency=1.15) if getattr(login_button, "_hover_target", 0) > 0 else 1.0 - (1.0 - hover_t) ** 3
        start_colour = blend_colour(face, hover, hover_eased)
        start_inset = max(0, min(3, round(3.0 - 2.0 * hover_eased)))
        button_bg = login_button.cget("bg")
        button_font = login_button.cget("font")

        start_x = login_button.winfo_rootx() - self.winfo_rootx() + start_inset
        start_y = login_button.winfo_rooty() - self.winfo_rooty() + start_inset
        start_w = max(1, login_button.winfo_width() - start_inset * 2)
        start_h = max(1, login_button.winfo_height() - start_inset * 2)
        target_w = max(1, self.winfo_width())
        target_h = max(1, self.winfo_height())

        if start_w <= 1 or start_h <= 1:
            self.show_home()
            return

        # Overlay Canvas that morphs from the rounded orange pill into a full-window dark backdrop.
        start_radius = min(10, start_h // 2, start_w // 2)
        expander = tk.Canvas(self, bg=button_bg, bd=0, highlightthickness=0)
        text_item = expander.create_text(
            start_w / 2, start_h / 2, text="Continue  →",
            fill=TEXT_WHITE, font=button_font,
        )

        def draw_rounded_fill(w, h, radius, fill_colour):
            # Redraw the pill silhouette using two overlapping rectangles and four corner ovals.
            expander.delete("pill")
            r = min(radius, w // 2, h // 2)
            if r <= 1:
                expander.create_rectangle(0, 0, w, h, fill=fill_colour, outline="", tags="pill")
            else:
                d = r * 2
                expander.create_rectangle(r, 0, w - r, h, fill=fill_colour, outline="", tags="pill")
                expander.create_rectangle(0, r, w, h - r, fill=fill_colour, outline="", tags="pill")
                expander.create_oval(0, 0, d, d, fill=fill_colour, outline="", tags="pill")
                expander.create_oval(w - d, 0, w, d, fill=fill_colour, outline="", tags="pill")
                expander.create_oval(0, h - d, d, h, fill=fill_colour, outline="", tags="pill")
                expander.create_oval(w - d, h - d, w, h, fill=fill_colour, outline="", tags="pill")
            expander.tag_raise(text_item)

        def reveal_home():
            # Phase 2: build the Home page underneath, then slide a dark curtain upward to uncover it.
            if not self.winfo_exists():
                return
            win_w = max(1, self.winfo_width())
            win_h = max(1, self.winfo_height())
            self.show_home()
            if not self.winfo_exists():
                return

            curtain = tk.Frame(self, bg=DARK_BG, bd=0, highlightthickness=0)
            accent = tk.Frame(curtain, bg=ORANGE_ACCENT, height=3)
            accent.pack(side="bottom", fill="x")
            curtain.place(x=0, y=0, width=win_w, height=win_h)
            curtain.lift()

            reveal_duration = 0.420
            reveal_started = None

            def draw_reveal():
                nonlocal reveal_started
                if not curtain.winfo_exists() or not self.winfo_exists():
                    return
                if reveal_started is None:
                    reveal_started = monotonic()
                # Smooth quartic ease-out lifts the curtain seamlessly while fading its orange edge.
                progress = min(1.0, (monotonic() - reveal_started) / reveal_duration)
                eased = 1.0 - (1.0 - progress) ** 4
                cur_y = round(-win_h * eased)
                if progress > 0.70:
                    fade = (progress - 0.70) / 0.30
                    accent.configure(bg=blend_colour(ORANGE_ACCENT, DARK_BG, fade))
                curtain.place(x=0, y=cur_y, width=win_w, height=win_h)
                curtain.lift()
                if progress < 1.0:
                    self.after(8, draw_reveal)
                else:
                    curtain.destroy()

            self.after(8, draw_reveal)

        expand_duration = 0.520
        expand_started = monotonic()

        def draw_expand():
            # Phase 1: fluid elastic ease-in-out gives a gentle pull before blooming to fill the window.
            if not expander.winfo_exists() or not self.winfo_exists():
                return
            progress = min(1.0, (monotonic() - expand_started) / expand_duration)
            eased = ease_in_out_back(progress, overshoot=0.65)

            cur_x = max(0, round(start_x * (1.0 - eased)))
            cur_y = max(0, round(start_y * (1.0 - eased)))
            cur_w = max(1, min(target_w, round(start_w + (target_w - start_w) * eased)))
            cur_h = max(1, min(target_h, round(start_h + (target_h - start_h) * eased)))
            cur_r = round(start_radius * max(0.0, 1.0 - progress / 0.35))

            if progress < 0.45:
                cur_bg = blend_colour(start_colour, ORANGE_ACCENT, progress / 0.45)
            else:
                t = (progress - 0.45) / 0.55
                smooth_t = t * t * (3.0 - 2.0 * t)
                cur_bg = blend_colour(ORANGE_ACCENT, DARK_BG, smooth_t)

            if cur_r <= 1:
                expander.configure(bg=cur_bg)
            draw_rounded_fill(cur_w, cur_h, cur_r, cur_bg)

            # Fade out the "Continue ->" label during the first 42% of the expansion.
            if progress < 0.42:
                text_fade = progress / 0.42
                expander.coords(text_item, cur_w / 2, cur_h / 2)
                expander.itemconfigure(
                    text_item,
                    state="normal",
                    fill=blend_colour(TEXT_WHITE, cur_bg, text_fade),
                )
            else:
                expander.itemconfigure(text_item, state="hidden")

            expander.place(x=cur_x, y=cur_y, width=cur_w, height=cur_h)
            # Canvas.lift() aliases tag_raise(); call tk.Misc.lift() to raise the widget above siblings.
            tk.Misc.lift(expander)

            if progress < 1.0:
                self.after(8, draw_expand)
            else:
                # Pause briefly at full-screen dark fill before lifting the Home curtain.
                self.after(120, reveal_home)

        draw_expand()

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
