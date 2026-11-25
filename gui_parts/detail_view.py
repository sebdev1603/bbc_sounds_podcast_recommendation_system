"""Podcast detail view, playback simulation, star-picker rating dialog, and library actions."""
import math
import sqlite3
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

from last_listened import record_last_listened
from gui_parts.i18n import translate
from gui_parts.theme import (
    ACTION_BTN_BG,
    ACTION_BTN_FG,
    BORDER_LINE,
    DARK_BG,
    DEFAULT_FONT,
    DIVIDER_LINE,
    GOLD_STAR,
    ORANGE_ACCENT,
    ORANGE_HL,
    PRIMARY_BTN_FG,
    SECONDARY_HOVER_BG,
    STAR_EMPTY,
    SUBCARD_BG,
    TEXT_GRAY,
    TEXT_WHITE,
    apply_windows_titlebar_theme,
    blend_colour,
    center_toplevel,
    ease_out_elastic,
    rounded_rect_points,
)


class DetailViewMixin:
    """Mixin implementing the podcast detail screen and play/rate/favourite/history actions."""

    def _draw_detail_skeleton_outlines(
        self, canvas, width, height, *, skip_hero_cover_title=False, skip_play_button=False,
    ):
        """Draw subtle, pixel-aligned wireframe outlines matching the podcast details page layout."""
        col = blend_colour(DARK_BG, BORDER_LINE, 0.72)
        soft_col = blend_colour(DARK_BG, BORDER_LINE, 0.45)
        items = []  # (item_id, center_x, center_y, is_line, base_stroke)

        def add_box(x0, y0, x1, y1, r=8, stroke=None, w_px=1.0):
            c = stroke or col
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            if r > 1 and (x1 - x0) > 6 and (y1 - y0) > 6:
                iid = canvas.create_polygon(
                    *rounded_rect_points(x0, y0, x1, y1, r),
                    smooth=True, fill="", outline=c, width=w_px,
                )
            else:
                iid = canvas.create_rectangle(x0, y0, x1, y1, fill="", outline=c, width=w_px)
            items.append((iid, cx, cy, False, c))

        def add_line(x0, y0, x1, y1, stroke=None, w_px=1.0):
            c = stroke or soft_col
            iid = canvas.create_line(x0, y0, x1, y1, fill=c, width=w_px)
            items.append((iid, (x0 + x1) / 2.0, (y0 + y1) / 2.0, True, c))

        win_w = max(1024, self.winfo_width() if self.winfo_exists() else width)
        win_h = max(700, self.winfo_height() if self.winfo_exists() else height)
        scale = max(0.92, min(1.75, min(win_w / 1180.0, win_h / 760.0)))
        cover_sz = round(max(248, min(420, 285 * scale)))
        play_sz = round(max(74, min(124, 82 * scale)))

        # Exact build_shell (padx=46, pady=28) + detail_column (padx=56) alignment.
        pad_x, pad_y = 46, 28
        col_x0 = pad_x + 56
        col_x1 = max(col_x0 + 480, width - pad_x - 56)

        # 1. Back button pill + NOW PLAYING badge.
        add_box(pad_x + 5, pad_y + 7, pad_x + 138, pad_y + 40, r=10)
        add_box(width - pad_x - 89, pad_y + 13, width - pad_x, pad_y + 32, r=4, stroke=soft_col)

        # 2. Top rule.
        y = pad_y + 61
        add_line(col_x0, y, col_x1, y, stroke=soft_col, w_px=1.5)
        y += round(32 * scale)

        # 3. Hero section (cover art + right pane metadata & controls).
        hero_gap = round(38 * scale)
        listen_w = round(101 * scale)
        btn_gap = round(22 * scale)
        right_w = play_sz + round(14 * scale) + listen_w + btn_gap * 2 + 215
        hero_total_w = cover_sz + hero_gap + right_w
        hero_x0 = max(col_x0, round((width - hero_total_w) / 2.0))
        if not skip_hero_cover_title:
            add_box(hero_x0, y, hero_x0 + cover_sz, y + cover_sz, r=8)

        rx = hero_x0 + cover_sz + hero_gap
        ry = y + 4
        if not skip_hero_cover_title:
            add_box(rx, ry, rx + 76, ry + 18, r=4, stroke=soft_col)
            add_box(rx, ry + 32, rx + min(right_w, 290), ry + 78, r=6)
        add_box(rx, ry + 104, rx + 218, ry + 124, r=4, stroke=soft_col)

        # Controls row: rounded-square Play button, Listen now, vertical divider, and 2 action pills.
        cy = ry + 124 + round(26 * scale)
        if not skip_play_button:
            add_box(rx + 6, cy + 6, rx + play_sz - 6, cy + play_sz - 6, r=round(play_sz * 0.22))
        lx = rx + play_sz + round(14 * scale)
        add_box(lx, cy + play_sz // 2 - 12, lx + listen_w, cy + play_sz // 2 + 12, r=5, stroke=soft_col)
        vx = lx + listen_w + btn_gap
        add_line(vx, cy + 7, vx, cy + play_sz - 7, stroke=soft_col, w_px=1.5)
        ax = vx + btn_gap
        add_box(ax + 5, cy - 4, ax + 196, cy + 37, r=10)
        add_box(ax + 5, cy + 56, ax + 224, cy + 97, r=10)

        # 4. Bottom rule.
        y = max(y + cover_sz, cy + play_sz) + round(34 * scale)
        add_line(col_x0, y, col_x1, y, stroke=soft_col, w_px=1.5)
        y += 20

        # 5. Side-by-side cards: Your Listening (left) + Listener Ratings bar chart (right).
        cards_x0 = col_x0 + 28
        cards_x1 = col_x1 - 28
        cards_gap = 20
        half_w = max(200, (cards_x1 - cards_x0 - cards_gap) // 2)
        card_h = 184

        # Left card: Your Listening
        add_box(cards_x0, y, cards_x0 + half_w, y + card_h, r=12)
        add_box(cards_x0 + 18, y + 14, cards_x0 + 124, y + 27, r=4, stroke=soft_col)
        add_box(cards_x0 + 18, y + 38, cards_x0 + min(half_w - 28, 210), y + 56, r=5, stroke=soft_col)
        add_box(cards_x0 + 18, y + 72, cards_x0 + 102, y + 88, r=4, stroke=soft_col)
        for s_i in range(5):
            sx = cards_x0 + 114 + s_i * 26
            add_box(sx, y + 70, sx + 20, y + 90, r=5, stroke=soft_col)

        # Right card: Listener Ratings + 5 horizontal bar outlines matching Matplotlib plot area
        rc_x0 = cards_x0 + half_w + cards_gap
        add_box(rc_x0, y, rc_x0 + half_w, y + card_h, r=12)
        add_box(rc_x0 + 16, y + 14, rc_x0 + 132, y + 27, r=4, stroke=soft_col)
        add_box(rc_x0 + 16, y + 34, rc_x0 + min(half_w - 28, 220), y + 48, r=4, stroke=soft_col)
        ch_x0, ch_w = rc_x0 + 10, half_w - 20
        bar_x0 = ch_x0 + round(ch_w * 0.14)
        bar_x1 = ch_x0 + round(ch_w * 0.88)
        for b_i in range(5):
            by = y + 72 + b_i * 20
            add_box(ch_x0 + 8, by, bar_x0 - 8, by + 11, r=3, stroke=soft_col)
            add_box(bar_x0, by, bar_x1, by + 11, r=3, stroke=soft_col)

        # 6. Full-width bottom Programme Details card (Region, Downloads, Award, Download pill).
        y += card_h + 14
        info_h = 108
        add_box(cards_x0, y, cards_x1, y + info_h, r=12)
        add_box(cards_x0 + 18, y + 14, cards_x0 + 148, y + 26, r=4, stroke=soft_col)
        meta_zone_w = max(240, (cards_x1 - cards_x0) - 200)
        col_step = meta_zone_w // 3
        for c_i in range(3):
            mx = cards_x0 + 18 + c_i * col_step
            add_box(mx, y + 40, mx + 84, y + 52, r=3, stroke=soft_col)
            add_box(mx, y + 60, mx + 126, y + 78, r=5)
        add_box(cards_x1 - 161, y + 47, cards_x1 - 23, y + 88, r=10)
        return items

    def _start_skeleton_glare(self, canvas, skeleton_items, width, height, *, delay_ms=250):
        """Run a subtle periodic diagonal glare sweep across wireframe outlines once loading exceeds 1s."""
        glare_col = blend_colour(BORDER_LINE, TEXT_WHITE, 0.55)
        span = max(1.0, float(width) + float(height) * 0.45)
        norm_items = [
            (iid, (cx + cy * 0.45) / span, is_line, base_c)
            for iid, cx, cy, is_line, base_c in skeleton_items
        ]
        state = {"job": None, "sweeping": False, "sweep_t0": 0.0, "active": True}
        sweep_dur = 0.65
        rest_ms = 1150

        def cancel_glare(_event=None):
            state["active"] = False
            if state["job"] is not None:
                try:
                    self.after_cancel(state["job"])
                except tk.TclError:
                    pass
                state["job"] = None

        def step_sweep():
            state["job"] = None
            if not state["active"] or not canvas.winfo_exists():
                return
            now = time.monotonic()
            if not state["sweeping"]:
                state["sweeping"] = True
                state["sweep_t0"] = now
            p = (now - state["sweep_t0"]) / sweep_dur
            if p >= 1.0:
                state["sweeping"] = False
                for iid, _pos, is_line, base_c in norm_items:
                    try:
                        canvas.itemconfigure(iid, fill=base_c) if is_line else canvas.itemconfigure(iid, outline=base_c)
                    except tk.TclError:
                        return
                state["job"] = self.after(rest_ms, step_sweep)
                return

            # Glare band travels diagonally from -0.18 to 1.18 with a soft cosine falloff.
            wave_x = -0.18 + 1.36 * p
            band_w = 0.22
            for iid, pos, is_line, base_c in norm_items:
                dist = abs(pos - wave_x)
                glow = (0.5 * (1.0 + math.cos(math.pi * dist / band_w))) if dist < band_w else 0.0
                c = blend_colour(base_c, glare_col, glow * 0.85) if glow > 0.01 else base_c
                try:
                    canvas.itemconfigure(iid, fill=c) if is_line else canvas.itemconfigure(iid, outline=c)
                except tk.TclError:
                    return
            state["job"] = self.after(22, step_sweep)

        canvas.bind("<Destroy>", cancel_glare, add="+")
        state["job"] = self.after(delay_ms, step_sweep)
        return cancel_glare

    def _preload_detail_backend(self, done_flag):
        """Warm up Matplotlib in a background thread so slow first-loads never freeze the skeleton timer."""
        try:
            import matplotlib.backends.backend_agg  # noqa: F401
            import matplotlib.figure  # noqa: F401
        except Exception:
            pass
        finally:
            done_flag[0] = True

    def show_detail_with_skeleton(self, podcast_id):
        """Load the details page; show subtle wireframe outlines only if loading exceeds 0.75s (glare after 1s)."""
        if "matplotlib.backends.backend_agg" in sys.modules:
            self.show_detail(podcast_id)
            return

        done_flag = [False]
        threading.Thread(target=self._preload_detail_backend, args=(done_flag,), daemon=True).start()
        t0 = time.monotonic()
        skel_state = {"shown": False, "cancel_glare": None}

        def poll_ready():
            if not self.winfo_exists():
                return
            if done_flag[0]:
                if skel_state["cancel_glare"] is not None:
                    skel_state["cancel_glare"]()
                self.show_detail(podcast_id)
                return
            elapsed = time.monotonic() - t0
            if elapsed >= 0.75 and not skel_state["shown"]:
                skel_state["shown"] = True
                page = self.build_shell("Programme details")
                sw = max(900, self.winfo_width() - 20)
                sh = max(640, self.winfo_height() - 100)
                sc = tk.Canvas(page, bg=DARK_BG, bd=0, highlightthickness=0, width=sw, height=sh)
                sc.pack(fill="both", expand=True)
                items = self._draw_detail_skeleton_outlines(sc, sw, sh, skip_hero_cover_title=False)
                sc.update_idletasks()
                rem_glare_ms = max(0, round((1.0 - elapsed) * 1000.0))
                skel_state["cancel_glare"] = self._start_skeleton_glare(sc, items, sw, sh, delay_ms=rem_glare_ms)
            self.after(25, poll_ready)

        self.after(10, poll_ready)

    def show_detail(self, podcast_id, *, show_simulated_notice=False, show_download_notice=False, animate_rating=False):
        """Render the responsive podcast view page with rounded art, animated play button, and actions."""
        try:
            podcast_rec = self.get_single_podcast(podcast_id)
            if not podcast_rec:
                messagebox.showinfo("Programme unavailable", "This programme is no longer in the catalogue.", parent=self)
                return

            with self.get_db_connection() as conn:
                history_record = conn.execute(
                    "SELECT TimesListened, RatingGiven FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                ).fetchone()
                rating_rows = conn.execute(
                    "SELECT RatingGiven, COUNT(*) FROM listening_history "
                    "WHERE PodcastID = ? AND RatingGiven BETWEEN 1 AND 5 GROUP BY RatingGiven",
                    (podcast_id,),
                ).fetchall()
                extra_rec = conn.execute(
                    "SELECT BBCRegion, DownloadCount, AwardWinner, ReleaseFrequency FROM podcasts WHERE PodcastID = ?",
                    (podcast_id,),
                ).fetchone()
            rating_counts = {star: 0 for star in (5, 4, 3, 2, 1)}
            for star_val, cnt in rating_rows:
                s = int(round(float(star_val)))
                if s in rating_counts:
                    rating_counts[s] += int(cnt)
            total_ratings = sum(rating_counts.values())
            region_text = str(extra_rec[0]).strip() if (extra_rec and extra_rec[0]) else "UK-wide"
            download_state = {"count": int(extra_rec[1]) if (extra_rec and extra_rec[1] is not None) else 0}
            is_award_winner = bool(extra_rec and str(extra_rec[2] or "").strip().lower() in ("yes", "1", "true"))
            release_freq_text = str(extra_rec[3]).strip() if (extra_rec and extra_rec[3]) else "Not listed"

            # If rebuilding Programme details in place, keep the old page visible while the new
            # detail layout, cover art, and Matplotlib chart render off-screen so nothing flashes blank.
            defer_rebuild = (
                getattr(self, "_active_nav_tab", None) == "Programme details"
                and not getattr(self, "_defer_old_page_destroy", False)
            )
            deferred_detail_old = None
            if defer_rebuild:
                self._deferred_old_page = None
                self._defer_old_page_destroy = True
            try:
                page = self.build_shell("Programme details")
            finally:
                if defer_rebuild:
                    self._defer_old_page_destroy = False
                    deferred_detail_old = getattr(self, "_deferred_old_page", None)
                    self._deferred_old_page = None
            self._active_detail_podcast = (podcast_id, podcast_rec[1], podcast_rec[2])
            back_tab, back_handler, back_name = getattr(
                self, "_last_non_detail_tab", ("Genres", self.show_search, "genres"),
            )
            back_row = tk.Frame(page, bg=DARK_BG)
            back_row.pack(fill="x", pady=(2, 12))
            back_btn = self.create_button(
                back_row, f"←  Back to {back_name}",
                lambda: self.transition_to(back_handler, back_tab, direction=-1), compact=True,
            )
            back_btn.pack(side="left")
            now_playing_lbl = self.create_label(back_row, "NOW PLAYING", 9, ORANGE_HL, "bold")
            now_playing_lbl.pack(side="right", pady=8)

            # Centered content column framed by top and bottom rules, matching 5.svg.
            detail_column = tk.Frame(page, bg=DARK_BG)
            detail_column._skip_auto_scale = True
            detail_column.pack(fill="x", padx=56)

            top_rule = tk.Frame(detail_column, bg=DIVIDER_LINE, height=2)
            top_rule.pack(fill="x", pady=(4, 34))

            hero_box = tk.Frame(detail_column, bg=DARK_BG)
            hero_box.pack(anchor="center", pady=(0, 34))

            cover_holder = tk.Frame(hero_box, bg=DARK_BG)
            cover_holder.pack(side="left", anchor="n", padx=(0, 38))
            self._detail_cover_holder = cover_holder

            right_pane = tk.Frame(hero_box, bg=DARK_BG)
            right_pane.pack(side="left", anchor="n", pady=(4, 0))
            self._detail_right_pane = right_pane

            category_label = self.create_label(right_pane, str(podcast_rec[2] or "Programme").upper(), 10, ORANGE_HL, "bold")
            category_label.pack(anchor="w")
            title_label = self.create_label(right_pane, podcast_rec[1], 28, TEXT_WHITE, "bold", wraplength=520)
            title_label.pack(anchor="w", pady=(6, 6))
            length_text = "Episode length not listed" if podcast_rec[3] is None else f"{podcast_rec[3]} minutes"
            meta_label = self.create_label(right_pane, f"BBC SOUNDS  ·  {length_text}", 11, TEXT_GRAY)
            meta_label.pack(anchor="w")

            controls_row = tk.Frame(right_pane, bg=DARK_BG)
            controls_row.pack(anchor="w", pady=(26, 0))

            play_canvas = tk.Canvas(controls_row, width=76, height=76, bg=DARK_BG, highlightthickness=0, cursor="hand2")
            play_canvas.pack(side="left", padx=(0, 14))
            play_canvas.bind("<Button-1>", lambda _event: self.listen(podcast_id))

            listen_label = self.create_label(controls_row, "Listen now", 13, TEXT_WHITE, "bold", cursor="hand2")
            listen_label.pack(side="left", padx=(0, 22))
            listen_label.bind("<Button-1>", lambda _event: self.listen(podcast_id))

            play_state = {"size": 76, "step": 0, "target": 0, "job": None}

            def draw_play_button():
                if not play_canvas.winfo_exists():
                    return
                size = play_state["size"]
                t = play_state["step"] / 10.0
                # Lively damped elastic spring stretches the play circle and settles seamlessly.
                eased = ease_out_elastic(t, damping=3.0, frequency=1.65) if play_state["target"] > 0 else 1.0 - (1.0 - t) ** 2.4
                inset = max(0.5, 6.0 - 4.0 * eased)
                col_t = max(0.0, min(1.0, eased))
                colour = blend_colour(ORANGE_ACCENT, ORANGE_HL, col_t)
                play_canvas.delete("all")
                sq_x0, sq_y0 = inset, inset
                sq_x1, sq_y1 = size - inset, size - inset
                sq_r = max(6.0, min((sq_x1 - sq_x0) * 0.24, (sq_x1 - sq_x0) / 2.0))
                sq_pts = (
                    sq_x0 + sq_r, sq_y0, sq_x1 - sq_r, sq_y0, sq_x1, sq_y0, sq_x1, sq_y0 + sq_r,
                    sq_x1, sq_y1 - sq_r, sq_x1, sq_y1, sq_x1 - sq_r, sq_y1, sq_x0 + sq_r, sq_y1,
                    sq_x0, sq_y1, sq_x0, sq_y1 - sq_r, sq_x0, sq_y0 + sq_r, sq_x0, sq_y0,
                )
                play_canvas.create_polygon(*sq_pts, smooth=True, fill=colour, outline="")
                tri_scale = 1.0 + 0.10 * eased
                cx, cy = size * 0.50, size * 0.50
                pts = [
                    (size * 0.39, size * 0.26),
                    (size * 0.39, size * 0.74),
                    (size * 0.76, size * 0.50),
                ]
                scaled_pts = []
                for px, py in pts:
                    scaled_pts.extend((cx + (px - cx) * tri_scale, cy + (py - cy) * tri_scale))
                play_canvas.create_polygon(*scaled_pts, fill="#000000", outline="")
                if listen_label.winfo_exists():
                    listen_label.configure(fg=blend_colour(TEXT_WHITE, ORANGE_HL, col_t))

            def animate_play_hover(target):
                play_state["target"] = target
                if self._is_reduced_motion():
                    cancel_play_hover()
                    if play_state["step"] != target:
                        play_state["step"] = target
                        draw_play_button()
                    return
                if play_state["job"] is not None:
                    return

                def step_play():
                    play_state["job"] = None
                    if not play_canvas.winfo_exists():
                        return
                    if play_state["step"] == play_state["target"]:
                        return
                    play_state["step"] += 1 if play_state["target"] > play_state["step"] else -1
                    draw_play_button()
                    if play_state["step"] != play_state["target"]:
                        play_state["job"] = self.after(self._anim_frame_interval(16), step_play)

                step_play()

            def cancel_play_hover(_event=None):
                if play_state["job"] is not None:
                    try:
                        self.after_cancel(play_state["job"])
                    except tk.TclError:
                        pass
                    play_state["job"] = None

            for play_widget in (play_canvas, listen_label):
                play_widget.bind("<Enter>", lambda _e: animate_play_hover(10))
                play_widget.bind("<Leave>", lambda _e: animate_play_hover(0))
            play_canvas.bind("<Destroy>", cancel_play_hover)

            v_divider = tk.Frame(controls_row, bg=DIVIDER_LINE, width=2, height=62)
            v_divider.pack(side="left", padx=(0, 22))

            actions_box = tk.Frame(controls_row, bg=DARK_BG)
            actions_box.pack(side="left")
            is_fav = self.check_if_favourited(podcast_id)
            fav_button = self.create_button(
                actions_box,
                "♥  Remove from favourites" if is_fav else "♥  Save to favourites",
                lambda: self.toggle_favourite(podcast_id),
                primary=is_fav,
                compact=True,
                face=ORANGE_ACCENT if is_fav else ACTION_BTN_BG,
                fg=PRIMARY_BTN_FG if is_fav else ACTION_BTN_FG,
            )
            fav_button.pack(anchor="w", pady=(0, 8))
            rate_button = self.create_button(
                actions_box,
                "★  Rate this programme",
                lambda: self.rate_programme(
                    podcast_id,
                    on_unplayed=lambda: show_detail_notice(
                        "You can't rate this programme until you've listened to it."
                    ),
                ),
                compact=True,
                face=ACTION_BTN_BG,
                fg=ACTION_BTN_FG,
            )
            rate_button.pack(anchor="w")
            action_buttons = [
                (fav_button, ORANGE_ACCENT if is_fav else ACTION_BTN_BG, ORANGE_HL if is_fav else SECONDARY_HOVER_BG),
                (rate_button, ACTION_BTN_BG, SECONDARY_HOVER_BG),
            ]

            # Subtle background notice for simulated playback or unplayed rating feedback that slowly fades away.
            sim_notice_label = tk.Label(
                right_pane,
                text="",
                font=(DEFAULT_FONT, 10, "italic"),
                fg=DARK_BG,
                bg=DARK_BG,
                anchor="w",
                justify="left",
                wraplength=360,
            )
            sim_notice_label.pack(anchor="w", pady=(12, 0))
            sim_fade_job = [None]

            def cancel_sim_fade(_event=None):
                if sim_fade_job[0] is not None:
                    try:
                        self.after_cancel(sim_fade_job[0])
                    except tk.TclError:
                        pass
                    sim_fade_job[0] = None

            def show_detail_notice(message, hold_ms=1100):
                if not sim_notice_label.winfo_exists():
                    return
                cancel_sim_fade()
                sim_notice_label.configure(text=translate(message), fg=TEXT_GRAY)
                fade_steps = 36
                fade_step = [0]

                def step_sim_fade():
                    sim_fade_job[0] = None
                    if not sim_notice_label.winfo_exists():
                        return
                    fade_step[0] += 1
                    frac = min(1.0, fade_step[0] / float(fade_steps))
                    eased = frac * frac * (3.0 - 2.0 * frac)
                    sim_notice_label.configure(fg=blend_colour(TEXT_GRAY, DARK_BG, eased))
                    if fade_step[0] < fade_steps:
                        sim_fade_job[0] = self.after(40, step_sim_fade)
                    else:
                        sim_notice_label.configure(text="")

                # Hold readable before slowly fading into the background over ~1.45s.
                sim_fade_job[0] = self.after(hold_ms, step_sim_fade)

            sim_notice_label.bind("<Destroy>", cancel_sim_fade)

            if show_simulated_notice:
                show_detail_notice("Playback is simulated")
            elif show_download_notice:
                show_detail_notice("Download is simulated")

            bottom_rule = tk.Frame(detail_column, bg=DIVIDER_LINE, height=2)
            bottom_rule.pack(fill="x", pady=(0, 18))

            bottom_cards = tk.Frame(detail_column, bg=DARK_BG)
            bottom_cards.pack(fill="x", padx=28, pady=(0, 14))
            bottom_cards.grid_columnconfigure(0, weight=1, uniform="detail-bottom")
            bottom_cards.grid_columnconfigure(1, weight=1, uniform="detail-bottom")

            sub_card = self.create_card_frame(bottom_cards, bg=SUBCARD_BG)
            sub_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
            listening_heading = self.create_label(sub_card, "YOUR LISTENING", 8, ORANGE_HL, "bold")
            listening_heading.pack(anchor="w", padx=18, pady=(13, 8))
            play_count_box = [(history_record[0] or 0) if history_record else 0]
            play_count = play_count_box[0]
            given_rating = int(history_record[1]) if (history_record and history_record[1] is not None) else 0

            listening_body = tk.Frame(sub_card, bg=SUBCARD_BG)
            listening_body.pack(fill="both", expand=True, padx=18, pady=(0, 14))

            # Unified play-count stat row filling the upper half of the card cleanly.
            plays_row = tk.Frame(listening_body, bg=SUBCARD_BG)
            plays_row.pack(fill="x", pady=(4, 10))
            if play_count:
                summary_text = f"{play_count} {'play' if play_count == 1 else 'plays'}"
                summary_color = TEXT_WHITE
                summary_label = self.create_label(plays_row, summary_text, 18, summary_color, "bold", bg=SUBCARD_BG)
            else:
                summary_text = "You haven't listened to this podcast yet."
                summary_color = TEXT_GRAY
                summary_label = self.create_label(plays_row, summary_text, 12, summary_color, bg=SUBCARD_BG)
            summary_label.pack(anchor="w", pady=(2, 2))

            tk.Frame(listening_body, bg=DIVIDER_LINE, height=1).pack(fill="x", pady=(2, 12))

            # Personal rating header + larger 5-star polygon display filling the lower half of the card.
            rating_header = tk.Frame(listening_body, bg=SUBCARD_BG)
            rating_header.pack(fill="x", pady=(0, 4))
            rating_caption = self.create_label(
                rating_header,
                "YOUR RATING",
                9, TEXT_GRAY, "bold", bg=SUBCARD_BG,
            )
            rating_caption.pack(side="left")
            rating_score_text = f"{given_rating} / 5" if given_rating > 0 else "Not rated"
            rating_score_label = self.create_label(
                rating_header,
                rating_score_text,
                10, GOLD_STAR if given_rating > 0 else TEXT_GRAY, "bold", bg=SUBCARD_BG,
            )
            rating_score_label.pack(side="right")

            rating_row = tk.Frame(listening_body, bg=SUBCARD_BG)
            rating_row.pack(fill="x", pady=(0, 2))

            star_state = {
                "size": 30, "gap": 8, "score": given_rating,
                "animating": bool(animate_rating and given_rating > 0 and not self._is_reduced_motion()),
                "anim_job": None,
            }
            star_pad = max(7, round(star_state["size"] * 0.28))
            star_canvas = tk.Canvas(
                rating_row,
                width=5 * star_state["size"] + 4 * star_state["gap"] + star_pad * 2,
                height=star_state["size"] + star_pad * 2,
                bg=SUBCARD_BG,
                bd=0,
                highlightthickness=0,
            )
            star_canvas.pack(anchor="w")

            def _star_pts(cx, cy, r_out, rot_deg=0.0):
                r_in = r_out * 0.43
                pts = []
                for pt_i in range(10):
                    ang = math.radians(-90.0 + rot_deg + pt_i * 36.0)
                    rad = r_out if pt_i % 2 == 0 else r_in
                    pts.extend((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
                return pts

            def cancel_star_anim(_event=None):
                if star_state["anim_job"] is not None:
                    try:
                        self.after_cancel(star_state["anim_job"])
                    except tk.TclError:
                        pass
                    star_state["anim_job"] = None
                star_state["animating"] = False

            star_canvas.bind("<Destroy>", cancel_star_anim, add="+")

            def draw_inline_stars(force_empty=False):
                if not star_canvas.winfo_exists():
                    return
                active = 0 if (force_empty or star_state["animating"]) else star_state["score"]
                size = star_state["size"]
                gap = star_state["gap"]
                pad = max(6, round(size * 0.28))
                total_w = 5 * size + 4 * gap + pad * 2
                total_h = size + pad * 2
                star_canvas.configure(width=total_w, height=total_h)
                star_canvas.delete("all")
                r_out = size * 0.46
                cy = total_h / 2.0
                ids = []
                for star_idx in range(1, 6):
                    cx = pad + (star_idx - 1) * (size + gap) + size / 2.0
                    pid_star = star_canvas.create_polygon(
                        _star_pts(cx, cy, r_out),
                        fill=GOLD_STAR if star_idx <= active else STAR_EMPTY,
                        outline="",
                    )
                    ids.append((pid_star, cx, cy, r_out))
                star_state["items"] = ids

            def animate_detail_stars():
                star_state["anim_job"] = None
                if not star_canvas.winfo_exists():
                    return
                target_n = min(5, max(0, int(star_state["score"] or 0)))
                if target_n <= 0:
                    star_state["animating"] = False
                    draw_inline_stars()
                    return
                draw_inline_stars(force_empty=True)
                items = star_state.get("items") or []
                if len(items) < target_n:
                    star_state["animating"] = False
                    draw_inline_stars()
                    return

                stagger = 0.105
                each_dur = 0.360
                total_dur = (target_n - 1) * stagger + each_dur
                flash_col = blend_colour(GOLD_STAR, "#ffffff", 0.55)
                anim_st = {"elapsed": 0.0, "last_t": None}

                def step_detail_stars():
                    star_state["anim_job"] = None
                    if not star_canvas.winfo_exists():
                        return
                    t0 = time.monotonic()
                    dt = 0.016 if anim_st["last_t"] is None else max(0.004, min(0.042, t0 - anim_st["last_t"]))
                    anim_st["last_t"] = t0
                    anim_st["elapsed"] = min(total_dur, anim_st["elapsed"] + dt)
                    el = anim_st["elapsed"]

                    for idx_s in range(target_n):
                        start_t = idx_s * stagger
                        if el < start_t:
                            continue
                        lp = min(1.0, (el - start_t) / each_dur)
                        pid_star, cx, cy, base_r = items[idx_s]
                        if lp >= 1.0:
                            star_canvas.coords(pid_star, *_star_pts(cx, cy, base_r, 0.0))
                            star_canvas.itemconfigure(pid_star, fill=GOLD_STAR)
                            continue
                        spring = max(0.08, ease_out_elastic(lp, damping=2.8, frequency=1.75))
                        r_now = base_r * spring
                        rot = -16.0 * (1.0 - lp) * math.exp(-4.0 * lp) * math.cos(lp * math.pi * 3.0)
                        glint = max(0.0, 1.0 - abs(lp - 0.25) / 0.35)
                        col = blend_colour(GOLD_STAR, flash_col, glint * 0.65)
                        star_canvas.coords(pid_star, *_star_pts(cx, cy, r_now, rot))
                        star_canvas.itemconfigure(pid_star, fill=col)

                    if el < total_dur:
                        spent = (time.monotonic() - t0) * 1000.0
                        star_state["anim_job"] = self.after(self._next_frame_delay(spent, 16), step_detail_stars)
                    else:
                        star_state["animating"] = False
                        draw_inline_stars()

                step_detail_stars()

            draw_inline_stars()
            if star_state["animating"]:
                star_state["anim_job"] = self.after(60, animate_detail_stars)

            # Compact community rating breakdown card placed beside Your Listening.
            ratings_card = self.create_card_frame(bottom_cards, bg=SUBCARD_BG)
            ratings_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
            ratings_heading = self.create_label(ratings_card, "LISTENER RATINGS", 8, ORANGE_HL, "bold")
            ratings_heading.pack(anchor="w", padx=16, pady=(12, 2))
            ratings_sub_text = (
                f"{total_ratings} {'rating' if total_ratings == 1 else 'ratings'}  ·  {self.podcast_average_text(podcast_id)}"
                if total_ratings else "No listener ratings yet."
            )
            ratings_sub_color = TEXT_WHITE if total_ratings else TEXT_GRAY
            ratings_sub = self.create_label(ratings_card, ratings_sub_text, 9, ratings_sub_color)
            ratings_sub.pack(anchor="w", padx=16, pady=(0, 4))

            ratings_chart_widget = self._render_ratings_bar_chart(ratings_card, rating_counts)

            # Bottom programme metadata card: Region, Download count, Award status, and simulated Download toggle.
            is_downloaded = self.check_if_downloaded(podcast_id)
            info_card = self.create_card_frame(detail_column, bg=SUBCARD_BG)
            info_card.pack(fill="x", padx=28, pady=(0, 22))
            info_heading = self.create_label(info_card, "PROGRAMME DETAILS", 8, ORANGE_HL, "bold", bg=SUBCARD_BG)
            info_heading.pack(anchor="w", padx=18, pady=(12, 6))

            info_grid = tk.Frame(info_card, bg=SUBCARD_BG)
            info_grid.pack(fill="x", padx=18, pady=(0, 14))
            for col_i in range(4):
                info_grid.grid_columnconfigure(col_i, weight=1, uniform="podcast-meta")
            info_grid.grid_columnconfigure(4, weight=0)

            meta_captions = []
            meta_values = []
            award_text = "★  Award Winner" if is_award_winner else "No"
            award_color = GOLD_STAR if is_award_winner else TEXT_GRAY
            for col_i, (cap_txt, val_txt, val_col) in enumerate((
                ("NEW EPISODES", release_freq_text, TEXT_WHITE),
                ("BBC REGION", region_text, TEXT_WHITE),
                ("DOWNLOADS", f"{download_state['count']:,}", TEXT_WHITE),
                ("AWARD WINNER", award_text, award_color),
            )):
                cell = tk.Frame(info_grid, bg=SUBCARD_BG)
                cell.grid(row=0, column=col_i, sticky="w", padx=(0, 12))
                cap_lbl = self.create_label(cell, cap_txt, 8, TEXT_GRAY, "bold", bg=SUBCARD_BG)
                cap_lbl.pack(anchor="w")
                val_lbl = self.create_label(cell, val_txt, 12, val_col, "bold", bg=SUBCARD_BG)
                val_lbl.pack(anchor="w", pady=(3, 0))
                meta_captions.append(cap_lbl)
                meta_values.append((val_lbl, val_col))

            download_button = self.create_button(
                info_grid,
                "×  Remove download" if is_downloaded else "      Download",
                lambda: self.toggle_download(podcast_id),
                primary=not is_downloaded,
                compact=True,
                face=ACTION_BTN_BG if is_downloaded else ORANGE_ACCENT,
                fg=ACTION_BTN_FG if is_downloaded else PRIMARY_BTN_FG,
            )
            if not is_downloaded:
                download_button._icon_kind = "cloud"
            download_button.grid(row=0, column=4, sticky="e", padx=(12, 0))
            action_buttons.append((
                download_button,
                ACTION_BTN_BG if is_downloaded else ORANGE_ACCENT,
                SECONDARY_HOVER_BG if is_downloaded else ORANGE_HL,
            ))

            last_layout = {"cover": 0}
            resize_job = [None]

            def apply_detail_scale():
                resize_job[0] = None
                if not detail_column.winfo_exists():
                    return
                win_w = max(1024, self.winfo_width())
                win_h = max(700, self.winfo_height())
                scale = max(0.92, min(1.75, min(win_w / 1180, win_h / 760)))
                cover_size = round(max(248, min(420, 285 * scale)))
                if abs(cover_size - last_layout["cover"]) < 6:
                    return
                last_layout["cover"] = cover_size
                play_size = round(max(74, min(124, 82 * scale)))
                # Apply the user's accessibility text-size multiplier to detail-page typography.
                font_scale = scale * getattr(self, "_text_scale", 1.0)

                for child in cover_holder.winfo_children():
                    child.destroy()
                cover_art = self.generate_podcast_cover(
                    cover_holder, podcast_id, podcast_rec[1], podcast_rec[2],
                    cover_size, cover_size,
                    corner_radius=8, backdrop=DARK_BG,
                )
                cover_art.pack()
                self._detail_cover_art = cover_art
                self._detail_cover_size = cover_size

                play_state["size"] = play_size
                play_canvas.configure(width=play_size, height=play_size)
                draw_play_button()

                v_divider.configure(height=round(play_size * 0.86))
                cover_holder.pack_configure(padx=(0, round(38 * scale)))
                top_rule.pack_configure(pady=(4, round(30 * scale)))
                hero_box.pack_configure(pady=(0, round(30 * scale)))
                controls_row.pack_configure(pady=(round(26 * scale), 0))
                play_canvas.pack_configure(padx=(0, round(14 * scale)))
                listen_label.pack_configure(padx=(0, round(22 * scale)))
                v_divider.pack_configure(padx=(0, round(22 * scale)))

                category_label.configure(font=(DEFAULT_FONT, max(10, round(11 * font_scale)), "bold"))
                title_label.configure(
                    font=(DEFAULT_FONT, max(24, round(29 * font_scale)), "bold"),
                    wraplength=round(max(400, min(720, 500 * scale))),
                )
                meta_label.configure(font=(DEFAULT_FONT, max(11, round(12 * font_scale))))
                listen_label.configure(font=(DEFAULT_FONT, max(13, round(14 * font_scale)), "bold"))
                sim_notice_label.configure(font=(DEFAULT_FONT, max(9, round(10 * font_scale)), "italic"))
                listening_heading.configure(font=(DEFAULT_FONT, max(8, round(9 * font_scale)), "bold"))
                if play_count_box[0]:
                    summary_label.configure(font=(DEFAULT_FONT, max(16, round(18 * font_scale)), "bold"))
                else:
                    summary_label.configure(font=(DEFAULT_FONT, max(11, round(12 * font_scale))))
                rating_caption.configure(font=(DEFAULT_FONT, max(8, round(9 * font_scale)), "bold"))
                rating_score_label.configure(font=(DEFAULT_FONT, max(10, round(11 * font_scale)), "bold"))
                star_state["size"] = max(26, round(30 * font_scale))
                star_state["gap"] = max(6, round(8 * font_scale))
                draw_inline_stars()
                ratings_heading.configure(font=(DEFAULT_FONT, max(8, round(9 * font_scale)), "bold"))
                ratings_sub.configure(font=(DEFAULT_FONT, max(10, round(11 * font_scale))))
                info_heading.configure(font=(DEFAULT_FONT, max(8, round(9 * font_scale)), "bold"))
                for cap_lbl in meta_captions:
                    cap_lbl.configure(font=(DEFAULT_FONT, max(8, round(8 * font_scale)), "bold"))
                for val_lbl, _vc in meta_values:
                    val_lbl.configure(font=(DEFAULT_FONT, max(11, round(12 * font_scale)), "bold"))
                action_font_size = max(10, round(11 * font_scale))
                fav_button.pack_configure(pady=(0, round(8 * scale)))
                for btn, face_col, hover_col in action_buttons:
                    btn._rounded_padding = (round(28 * scale), round(14 * scale))
                    btn.configure(font=(DEFAULT_FONT, action_font_size, "bold"))
                    self.style_rounded_button(btn, face_col, hover_col)
                dw_live = getattr(self, "_detail_widgets", None) or {}
                ch_live = dw_live.get("ratings_chart_widget")
                if ch_live is not None and ch_live.winfo_exists() and callable(getattr(ch_live, "_rerender_chart", None)):
                    ch_live._rerender_chart()

            def schedule_detail_scale(_event=None):
                if resize_job[0] is not None:
                    self.after_cancel(resize_job[0])
                resize_job[0] = self.after(60, apply_detail_scale)

            detail_column.bind("<Configure>", schedule_detail_scale)
            apply_detail_scale()

            if defer_rebuild:
                # Swap the freshly built detail page into view atomically and drop the old page.
                new_target = getattr(self, "_page_transition_target", None)
                if new_target:
                    new_cvs, new_win = new_target
                    if new_cvs.winfo_exists():
                        try:
                            new_cvs.coords(new_win, 0, 0)
                            new_cvs.update_idletasks()
                        except tk.TclError:
                            pass
                if deferred_detail_old is not None:
                    o_page, o_win = deferred_detail_old
                    if o_page is not None and o_page.winfo_exists():
                        try:
                            o_page.destroy()
                        except tk.TclError:
                            pass
                    if o_win is not None and new_target and new_target[0].winfo_exists():
                        try:
                            new_target[0].delete(o_win)
                        except tk.TclError:
                            pass

            live_chart_ref = [ratings_chart_widget]

            def update_live_listen(new_play_count):
                if not summary_label.winfo_exists():
                    return
                play_count_box[0] = int(new_play_count or 0)
                cnt = play_count_box[0]
                win_w = max(1024, self.winfo_width())
                win_h = max(700, self.winfo_height())
                sc = max(0.92, min(1.75, min(win_w / 1180, win_h / 760)))
                f_sc = sc * getattr(self, "_text_scale", 1.0)
                summary_label.configure(
                    text=translate(f"{cnt} {'play' if cnt == 1 else 'plays'}"),
                    fg=TEXT_WHITE,
                    font=(DEFAULT_FONT, max(16, round(18 * f_sc)), "bold"),
                )
                show_detail_notice("Playback is simulated")

            def update_live_rating(new_score, animate=True):
                if not star_canvas.winfo_exists():
                    return
                cancel_star_anim()
                score_int = int(new_score)
                star_state["score"] = score_int
                if rating_score_label.winfo_exists():
                    rating_score_label.configure(
                        text=f"{score_int} / 5" if score_int > 0 else translate("Not rated"),
                        fg=GOLD_STAR if score_int > 0 else TEXT_GRAY,
                    )
                if animate and score_int > 0 and not self._is_reduced_motion():
                    star_state["animating"] = True
                    star_state["anim_job"] = self.after(40, animate_detail_stars)
                else:
                    star_state["animating"] = False
                    draw_inline_stars()
                # Refresh community rating summary and bar chart in place without rebuilding the page.
                try:
                    with self.get_db_connection() as conn:
                        r_rows = conn.execute(
                            "SELECT RatingGiven, COUNT(*) FROM listening_history "
                            "WHERE PodcastID = ? AND RatingGiven BETWEEN 1 AND 5 GROUP BY RatingGiven",
                            (podcast_id,),
                        ).fetchall()
                    new_counts = {s: 0 for s in (5, 4, 3, 2, 1)}
                    for sv, c_val in r_rows:
                        si = int(round(float(sv)))
                        if si in new_counts:
                            new_counts[si] += int(c_val)
                    new_total = sum(new_counts.values())
                    if ratings_sub.winfo_exists():
                        sub_txt = (
                            f"{new_total} {'rating' if new_total == 1 else 'ratings'}  ·  {self.podcast_average_text(podcast_id)}"
                            if new_total else "No listener ratings yet."
                        )
                        ratings_sub.configure(
                            text=translate(sub_txt),
                            fg=TEXT_WHITE if new_total else TEXT_GRAY,
                        )
                    if ratings_card.winfo_exists():
                        old_chart = live_chart_ref[0]
                        if old_chart is not None and old_chart.winfo_exists():
                            old_chart.destroy()
                        live_chart_ref[0] = self._render_ratings_bar_chart(ratings_card, new_counts)
                        if isinstance(getattr(self, "_detail_widgets", None), dict):
                            self._detail_widgets["ratings_chart_widget"] = live_chart_ref[0]
                except sqlite3.Error:
                    pass

            self._detail_widgets = {
                "podcast_id": podcast_id,
                "on_live_listen": update_live_listen,
                "on_live_rating": update_live_rating,
                "back_btn": back_btn,
                "now_playing_lbl": now_playing_lbl,
                "top_rule": top_rule,
                "bottom_rule": bottom_rule,
                "category_label": category_label,
                "title_label": title_label,
                "meta_label": meta_label,
                "play_canvas": play_canvas,
                "listen_label": listen_label,
                "v_divider": v_divider,
                "fav_button": fav_button,
                "fav_primary": is_fav,
                "rate_button": rate_button,
                "sub_card": sub_card,
                "listening_heading": listening_heading,
                "summary_label": summary_label,
                "summary_color": summary_color,
                "rating_caption": rating_caption,
                "star_canvas": star_canvas,
                "star_state": star_state,
                "ratings_card": ratings_card,
                "ratings_heading": ratings_heading,
                "ratings_sub": ratings_sub,
                "ratings_sub_color": ratings_sub_color,
                "ratings_chart_widget": ratings_chart_widget,
                "ratings_counts": rating_counts,
                "info_card": info_card,
                "info_texts": [
                    (info_heading, ORANGE_HL),
                    *((c_lbl, TEXT_GRAY) for c_lbl in meta_captions),
                    *meta_values,
                ],
                "download_button": download_button,
                "download_primary": not is_downloaded,
            }
        except sqlite3.Error as err:
            self.show_db_error("Couldn't load programme", err)

    def _render_ratings_bar_chart(self, parent_card, rating_counts):
        """Render a responsive themed horizontal Matplotlib bar chart of 5-to-1 star listener rating counts."""
        try:
            import io
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure
        except Exception:
            self.create_label(
                parent_card, "Install matplotlib to view the star rating chart.", 9, TEXT_GRAY,
            ).pack(anchor="w", padx=16, pady=(0, 10))
            return None

        stars = [5, 4, 3, 2, 1]
        labels = [f"{s} ★" for s in stars]
        counts = [rating_counts.get(s, 0) for s in stars]
        max_count = max(counts) if counts else 0
        max_digits = max(1, len(str(max_count)))
        track_col = blend_colour(SUBCARD_BG, TEXT_WHITE, 0.08)

        chart_widget = tk.Canvas(
            parent_card, bg=SUBCARD_BG, bd=0, highlightthickness=0, width=1, height=110,
        )
        chart_widget.pack(fill="both", expand=True, padx=14, pady=(2, 12))
        chart_img_id = chart_widget.create_image(0, 0, anchor="center")

        render_state = {"key": None, "job": None}

        def render_for_size(avail_w, avail_h=None):
            render_state["job"] = None
            if not chart_widget.winfo_exists() or not parent_card.winfo_exists():
                return
            w_px = max(180, min(1400, int(avail_w)))
            win_h = max(600, self.winfo_height())
            text_scale = max(0.80, min(1.40, getattr(self, "_text_scale", 1.0)))
            target_h = round(min(w_px * 0.30, win_h * 0.24) * max(0.95, text_scale))
            h_px = max(96, min(260, target_h))
            if avail_h is not None and avail_h > h_px:
                h_px = min(260, int(avail_h))
            size_key = (w_px, h_px, round(text_scale, 2))
            if render_state["key"] is not None:
                prev_w, prev_h, prev_ts = render_state["key"]
                if abs(w_px - prev_w) < 6 and abs(h_px - prev_h) < 4 and prev_ts == size_key[2]:
                    return
            render_state["key"] = size_key
            dpi = 96

            fig = Figure(figsize=(w_px / dpi, h_px / dpi), dpi=dpi, facecolor=SUBCARD_BG)
            ax = fig.add_subplot(111)
            ax.set_facecolor(SUBCARD_BG)

            # Scale typography and margins smoothly with chart height and accessibility text scale.
            lbl_pt = max(8.0, min(14.0, (h_px / 110.0) * 8.5 * max(0.95, text_scale)))
            left_px = max(36.0, lbl_pt * 4.4)
            left_frac = max(0.06, min(0.24, left_px / w_px))
            right_px = max(22.0, 14.0 + max_digits * (lbl_pt * 0.95))
            right_frac = max(0.76, min(0.96, 1.0 - right_px / w_px))

            x_cap = max(1.0, float(max_count))
            ax.barh(labels, [x_cap] * 5, height=0.50, color=track_col, edgecolor="none", zorder=1)
            bars = ax.barh(labels, counts, height=0.50, color=ORANGE_ACCENT, edgecolor="none", zorder=2)

            ax.invert_yaxis()
            ax.set_xlim(0, x_cap)
            ax.set_ylim(4.65, -0.65)
            ax.set_xticks([])
            ax.tick_params(axis="y", length=0, pad=6, colors=TEXT_WHITE, labelsize=lbl_pt)
            for tick_lbl in ax.get_yticklabels():
                tick_lbl.set_fontweight("bold")
            for spine in ax.spines.values():
                spine.set_visible(False)

            for bar, cnt in zip(bars, counts):
                y_mid = bar.get_y() + bar.get_height() / 2.0
                ax.annotate(
                    str(cnt),
                    xy=(x_cap, y_mid),
                    xytext=(6, 0),
                    textcoords="offset points",
                    va="center", ha="left",
                    color=TEXT_WHITE if cnt > 0 else TEXT_GRAY,
                    fontsize=lbl_pt, fontweight="bold" if cnt > 0 else "normal",
                    annotation_clip=False,
                )

            fig.subplots_adjust(left=left_frac, right=right_frac, top=0.96, bottom=0.04)

            buf = io.BytesIO()
            FigureCanvasAgg(fig).print_png(buf)
            fig.clear()
            photo = tk.PhotoImage(master=self, data=buf.getvalue(), format="png")
            chart_widget._chart_photo = photo
            if chart_widget.winfo_reqheight() != h_px:
                chart_widget.configure(height=h_px)
            cur_cw = max(w_px, chart_widget.winfo_width())
            cur_ch = max(h_px, chart_widget.winfo_height())
            chart_widget.coords(chart_img_id, cur_cw / 2.0, cur_ch / 2.0)
            chart_widget.itemconfigure(chart_img_id, image=photo)
            self._sync_scrollregion()

        def schedule_chart_render(avail_w):
            if not chart_widget.winfo_exists():
                return
            if avail_w < 140:
                return
            if render_state["job"] is not None:
                try:
                    self.after_cancel(render_state["job"])
                except tk.TclError:
                    pass
            render_state["job"] = self.after(45, lambda w=avail_w: render_for_size(w))

        def on_chart_resize(event):
            if not chart_widget.winfo_exists():
                return
            if event.width > 1 and event.height > 1:
                chart_widget.coords(chart_img_id, event.width / 2.0, event.height / 2.0)
            schedule_chart_render(event.width)

        def cancel_chart_job(_event=None):
            if render_state["job"] is not None:
                try:
                    self.after_cancel(render_state["job"])
                except tk.TclError:
                    pass
                render_state["job"] = None

        chart_widget._rerender_chart = lambda: schedule_chart_render(
            chart_widget.winfo_width() if chart_widget.winfo_width() > 140 else max(240, parent_card.winfo_width() - 28)
        )
        chart_widget.bind("<Configure>", on_chart_resize, add="+")
        chart_widget.bind("<Destroy>", cancel_chart_job, add="+")

        # Initial render using the estimated half-column width so the chart is immediately well-proportioned.
        est_w = max(240, round((max(900, self.winfo_width()) - 280) / 2.0) - 28)
        render_for_size(est_w)
        return chart_widget

    def listen(self, podcast_id, *, open_detail=True):
        """Simulate playing a podcast, increment TimesListened, and update last-listened recency."""
        if open_detail and self._is_busy_transitioning():
            return False
        try:
            with self.get_db_connection() as conn:
                # Check if this listener already has a listening_history row for this podcast.
                existing_entry = conn.execute(
                    "SELECT TimesListened FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                ).fetchone()
                is_first_listen = (existing_entry is None) or (not (existing_entry[0] or 0))
                if existing_entry:
                    # Increment the existing play counter safely even if TimesListened was NULL.
                    new_play_count = int(existing_entry[0] or 0) + 1
                    conn.execute(
                        "UPDATE listening_history SET TimesListened = COALESCE(TimesListened, 0) + 1 "
                        "WHERE ListenerID = ? AND PodcastID = ?", (self.current_user, podcast_id),
                    )
                else:
                    new_play_count = 1
                    # Create a new listening_history record starting at 1 play.
                    conn.execute(
                        "INSERT INTO listening_history (PodcastID, ListenerID, TimesListened) VALUES (?, ?, 1)",
                        (podcast_id, self.current_user),
                    )
                # Update recency tables in the same transaction so the bottom mini-bar reflects this play.
                record_last_listened(conn, self.current_user, podcast_id)
            # Clear any prior dismissal so the newly played podcast appears in the mini-bar.
            self._dismissed_last_listened = None
            if open_detail:
                # Going back after pressing Listen now should shrink the podcast down into the mini-bar.
                self._detail_hero_origin = None
                if is_first_listen and not self._is_reduced_motion():
                    self._pending_card_insert = {
                        "mode": "history",
                        "podcast_id": podcast_id,
                        "target_rating": None,
                        "return_tab": "Programme details",
                        "return_fn": lambda pid=podcast_id: self.show_detail(pid, show_simulated_notice=True),
                    }
                    self.transition_to(self.show_history, "History")
                    return "first_time"
                dw = getattr(self, "_detail_widgets", None) or {}
                if (
                    getattr(self, "_active_nav_tab", None) == "Programme details"
                    and str(dw.get("podcast_id")) == str(podcast_id)
                    and callable(dw.get("on_live_listen"))
                ):
                    dw["on_live_listen"](new_play_count)
                else:
                    self.show_detail(podcast_id, show_simulated_notice=True)
            return "first_time" if is_first_listen else True
        except sqlite3.Error as err:
            self.show_db_error("Couldn't update listening history", err)
            return False

    def save_programme_rating(self, podcast_id, new_score, callback_func=None):
        """Persist a 1-5 rating for the active listener and animate the stars on the details page."""
        try:
            with self.get_db_connection() as conn:
                # Update the listener's rating in place, or insert a row if one doesn't exist yet.
                prior_record = conn.execute(
                    "SELECT RatingGiven FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                ).fetchone()
                if prior_record:
                    conn.execute(
                        "UPDATE listening_history SET RatingGiven = ? WHERE ListenerID = ? AND PodcastID = ?",
                        (new_score, self.current_user, podcast_id),
                    )
                else:
                    conn.execute(
                        "INSERT INTO listening_history (PodcastID, ListenerID, TimesListened, RatingGiven) "
                        "VALUES (?, ?, 0, ?)", (podcast_id, self.current_user, new_score),
                    )
            # Invalidate the cached community rating averages so the new score is reflected immediately.
            self._podcast_averages = None
            if callback_func:
                callback_func()
            else:
                dw = getattr(self, "_detail_widgets", None) or {}
                if (
                    getattr(self, "_active_nav_tab", None) == "Programme details"
                    and str(dw.get("podcast_id")) == str(podcast_id)
                    and callable(dw.get("on_live_rating"))
                ):
                    dw["on_live_rating"](new_score, animate=not self._is_reduced_motion())
                else:
                    self.show_detail(podcast_id, animate_rating=not self._is_reduced_motion())
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save your rating", err)

    def rate_programme(self, podcast_id, callback_func=None, *, on_unplayed=None):
        """Open a dark interactive 5-star picker dialog to rate or update a programme's score."""
        existing_dlg = getattr(self, "_active_rating_dialog", None)
        if existing_dlg is not None:
            try:
                if existing_dlg.winfo_exists():
                    existing_dlg.deiconify()
                    existing_dlg.lift()
                    existing_dlg.focus_set()
                    return
            except tk.TclError:
                pass
            self._active_rating_dialog = None
        dialog = None
        try:
            with self.get_db_connection() as conn:
                prior_record = conn.execute(
                    "SELECT TimesListened, RatingGiven FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                ).fetchone()
            if not prior_record or (not prior_record[0] and prior_record[1] is None):
                if on_unplayed is not None:
                    on_unplayed()
                return

            initial_score = int(prior_record[1]) if prior_record[1] is not None else 5
            dialog_title = "Rate this programme" if prior_record[1] is None else "Update your rating"

            dialog = tk.Toplevel(self)
            dialog.withdraw()
            self._active_rating_dialog = dialog
            dialog.title(dialog_title)
            dialog.configure(bg=DARK_BG)
            dialog.resizable(False, False)
            try:
                dialog.transient(self)
            except tk.TclError:
                pass

            def close_dialog(_event=None):
                if getattr(self, "_active_rating_dialog", None) is dialog:
                    self._active_rating_dialog = None
                try:
                    dialog.grab_release()
                except tk.TclError:
                    pass
                try:
                    if dialog.winfo_exists():
                        dialog.destroy()
                except tk.TclError:
                    pass

            dialog.protocol("WM_DELETE_WINDOW", close_dialog)

            body = tk.Frame(dialog, bg=DARK_BG, padx=28, pady=22)
            body.pack(fill="both", expand=True)
            self.create_label(body, dialog_title, 15, TEXT_WHITE, "bold", anchor="center").pack()
            self.create_label(body, "Select a star rating from 1 to 5.", 10, TEXT_GRAY, anchor="center").pack(pady=(4, 14))

            selected = {"score": initial_score}
            stars_frame = tk.Frame(body, bg=DARK_BG)
            stars_frame.pack(pady=(0, 8))
            score_lbl = self.create_label(body, f"{initial_score} / 5", 11, GOLD_STAR, "bold", anchor="center")
            score_lbl.pack(pady=(0, 16))
            dlg_stars = []

            def paint_dlg_stars(score):
                for idx, lbl in enumerate(dlg_stars, start=1):
                    lbl.configure(fg=GOLD_STAR if idx <= score else STAR_EMPTY)
                score_lbl.configure(text=f"{score} / 5")

            def select_dlg_star(score):
                selected["score"] = score
                paint_dlg_stars(score)

            for star_idx in range(1, 6):
                star_lbl = tk.Label(
                    stars_frame, text="★", font=(DEFAULT_FONT, 30, "bold"),
                    bg=DARK_BG, fg=GOLD_STAR if star_idx <= initial_score else STAR_EMPTY,
                    cursor="hand2", bd=0, padx=4,
                )
                star_lbl.pack(side="left")
                star_lbl.bind("<Enter>", lambda _e, s=star_idx: paint_dlg_stars(s))
                star_lbl.bind("<Button-1>", lambda _e, s=star_idx: select_dlg_star(s))
                dlg_stars.append(star_lbl)
            stars_frame.bind("<Leave>", lambda _e: paint_dlg_stars(selected["score"]))

            def confirm_rating():
                chosen = selected["score"]
                close_dialog()
                self.save_programme_rating(podcast_id, chosen, callback_func=callback_func)

            btn_row = tk.Frame(body, bg=DARK_BG)
            btn_row.pack()
            self.create_button(btn_row, "Save rating", confirm_rating, primary=True, compact=True).pack(side="left", padx=(0, 8))
            self.create_button(btn_row, "Cancel", close_dialog, compact=True).pack(side="left")

            apply_windows_titlebar_theme(dialog)
            center_toplevel(dialog, self, min_w=260, min_h=180, set_size=True)
            dialog.bind("<Return>", lambda _e: confirm_rating())
            dialog.bind("<Escape>", close_dialog)

            dialog.deiconify()
            dialog.lift()
            dialog.focus_set()

            # Acquire modal grab only after the WM has actually mapped the dialog; calling
            # grab_set() immediately on Linux (X11/Wayland) or slower hardware raises
            # TclError ("grab failed: window not viewable") and prevents the popup from appearing.
            def _acquire_grab(attempts_left=20):
                try:
                    if not dialog.winfo_exists():
                        return
                    if not dialog.winfo_viewable():
                        if attempts_left > 0:
                            dialog.after(25, _acquire_grab, attempts_left - 1)
                        return
                    dialog.grab_set()
                    dialog.lift()
                    dialog.focus_set()
                except tk.TclError:
                    if attempts_left > 0:
                        try:
                            if dialog.winfo_exists():
                                dialog.after(25, _acquire_grab, attempts_left - 1)
                        except tk.TclError:
                            pass

            dialog.after(10, _acquire_grab)
        except sqlite3.Error as err:
            if dialog is not None:
                try:
                    dialog.destroy()
                except tk.TclError:
                    pass
                if getattr(self, "_active_rating_dialog", None) is dialog:
                    self._active_rating_dialog = None
            self.show_db_error("Couldn't save your rating", err)
        except tk.TclError:
            if dialog is not None:
                try:
                    dialog.destroy()
                except tk.TclError:
                    pass
                if getattr(self, "_active_rating_dialog", None) is dialog:
                    self._active_rating_dialog = None

    def remove_rating(self, podcast_id, evaporate=None):
        """Clear the active listener's rating for a podcast, evaporating its card before reloading."""
        if not messagebox.askyesno("Remove rating", "Remove your rating for this programme?", parent=self):
            return
        try:
            # Set RatingGiven to NULL rather than deleting the row so play counts are preserved.
            with self.get_db_connection() as conn:
                conn.execute(
                    "UPDATE listening_history SET RatingGiven = NULL WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                )
            # Clear cached average ratings so community scores recalculate on next render.
            self._podcast_averages = None
            if evaporate is not None:
                evaporate(self.show_ratings)
            else:
                self.show_ratings()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't remove your rating", err)

    def toggle_favourite(self, podcast_id):
        """Add or remove a podcast from the active listener's FavoritePodcasts CSV."""
        if self._is_busy_transitioning():
            return
        try:
            with self.get_db_connection() as conn:
                # Read the current comma-separated list of favourited PodcastIDs.
                record = conn.execute(
                    "SELECT FavoritePodcasts FROM listeners WHERE ListenerID = ?", (self.current_user,)
                ).fetchone()
                current_str = str((record[0] if record else "") or "")
                id_tokens = [item.strip() for item in current_str.split(",") if item.strip()]
                target_str = str(podcast_id)
                # Toggle membership: remove if already saved, otherwise append.
                was_added = target_str not in id_tokens
                if was_added:
                    id_tokens.append(target_str)
                else:
                    id_tokens.remove(target_str)
                conn.execute(
                    "UPDATE listeners SET FavoritePodcasts = ? WHERE ListenerID = ?",
                    (",".join(id_tokens), self.current_user),
                )
            if not self._is_reduced_motion():
                self._detail_hero_origin = None
                if was_added:
                    self._pending_card_insert = {
                        "mode": "favourites",
                        "podcast_id": podcast_id,
                        "target_rating": None,
                        "return_tab": "Programme details",
                        "return_fn": lambda pid=podcast_id: self.show_detail(pid),
                    }
                else:
                    self._pending_card_evaporate = {
                        "mode": "favourites",
                        "podcast_id": podcast_id,
                        "return_tab": "Programme details",
                        "return_fn": lambda pid=podcast_id: self.show_detail(pid),
                    }
                self.transition_to(self.show_favourites, "Favourites")
                return
            self.show_detail(podcast_id)
        except sqlite3.Error as err:
            self.show_db_error("Couldn't update favourites", err)

    def toggle_download(self, podcast_id):
        """Toggle a simulated download for the active listener, updating DownloadCount and animating Downloads."""
        if self._is_busy_transitioning() or self.current_user is None:
            return
        try:
            with self.get_db_connection() as conn:
                self._ensure_downloads_table(conn)
                existing = conn.execute(
                    "SELECT 1 FROM user_downloads WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                ).fetchone()
                was_added = existing is None
                if was_added:
                    conn.execute(
                        "INSERT INTO user_downloads (ListenerID, PodcastID, DownloadedAt) VALUES (?, ?, ?)",
                        (self.current_user, podcast_id, time.time()),
                    )
                    conn.execute(
                        "UPDATE podcasts SET DownloadCount = COALESCE(DownloadCount, 0) + 1 WHERE PodcastID = ?",
                        (podcast_id,),
                    )
                else:
                    conn.execute(
                        "DELETE FROM user_downloads WHERE ListenerID = ? AND PodcastID = ?",
                        (self.current_user, podcast_id),
                    )
                    conn.execute(
                        "UPDATE podcasts SET DownloadCount = MAX(0, COALESCE(DownloadCount, 0) - 1) WHERE PodcastID = ?",
                        (podcast_id,),
                    )
            if not self._is_reduced_motion():
                self._detail_hero_origin = None
                anim_payload = {
                    "mode": "downloads",
                    "podcast_id": podcast_id,
                    "return_tab": "Programme details",
                    "return_fn": lambda pid=podcast_id, added=was_added: self.show_detail(pid, show_download_notice=added),
                }
                if was_added:
                    anim_payload["target_rating"] = None
                    self._pending_card_insert = anim_payload
                else:
                    self._pending_card_evaporate = anim_payload
                self.transition_to(self.show_downloads, "Downloads")
                return
            self.show_detail(podcast_id, show_download_notice=was_added)
        except sqlite3.Error as err:
            self.show_db_error("Couldn't update downloads", err)

    def remove_from_history(self, podcast_id, evaporate=None):
        """Delete one programme from the listener's listening history, evaporating its card first."""
        if not messagebox.askyesno("Remove from history", "Remove this programme from your listening history?", parent=self):
            return
        try:
            # Delete only the matching (ListenerID, PodcastID) row from listening_history.
            with self.get_db_connection() as conn:
                conn.execute(
                    "DELETE FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                )
            if evaporate is not None:
                evaporate(self.show_history)
            else:
                self.show_history()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't remove programme", err)

    def clear_history(self):
        """Delete all listening history entries for the active listener."""
        if not messagebox.askyesno("Clear listening history", "Remove all programmes from your listening history?", parent=self):
            return
        try:
            # Remove every listening_history record belonging to the current listener.
            with self.get_db_connection() as conn:
                conn.execute("DELETE FROM listening_history WHERE ListenerID = ?", (self.current_user,))
            self.show_history()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't clear listening history", err)
