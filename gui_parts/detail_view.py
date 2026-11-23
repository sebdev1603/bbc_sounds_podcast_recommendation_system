"""Podcast detail view, playback simulation, star-picker rating dialog, and library actions."""
import ctypes
import math
import sqlite3
import sys
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
    TITLEBAR_DARK_MODE,
    TITLEBAR_TEXT,
    blend_colour,
    ease_out_elastic,
)


class DetailViewMixin:
    """Mixin implementing the podcast detail screen and play/rate/favourite/history actions."""

    def show_detail(self, podcast_id, *, show_simulated_notice=False):
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

            page = self.build_shell("Programme details")
            self._active_detail_podcast = (podcast_id, podcast_rec[1], podcast_rec[2])
            back_tab, back_handler, back_name = getattr(
                self, "_last_non_detail_tab", ("Genres", self.show_search, "genres"),
            )
            back_row = tk.Frame(page, bg=DARK_BG)
            back_row.pack(fill="x", pady=(2, 12))
            self.create_button(
                back_row, f"←  Back to {back_name}",
                lambda: self.transition_to(back_handler, back_tab, direction=-1), compact=True,
            ).pack(side="left")
            self.create_label(back_row, "NOW PLAYING", 9, ORANGE_HL, "bold").pack(side="right", pady=8)

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
            avg_label = self.create_label(right_pane, self.podcast_average_text(podcast_id), 11, GOLD_STAR)
            avg_label.pack(anchor="w", pady=(5, 0))

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
                play_canvas.create_oval(inset, inset, size - inset, size - inset, fill=colour, outline="")
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

            bottom_rule = tk.Frame(detail_column, bg=DIVIDER_LINE, height=2)
            bottom_rule.pack(fill="x", pady=(0, 22))

            sub_card = self.create_card_frame(detail_column, bg=SUBCARD_BG)
            sub_card.pack(fill="x", padx=28, pady=(0, 8))
            listening_heading = self.create_label(sub_card, "YOUR LISTENING", 8, ORANGE_HL, "bold")
            listening_heading.pack(anchor="w", padx=18, pady=(13, 5))
            play_count = (history_record[0] or 0) if history_record else 0
            given_rating = int(history_record[1]) if (history_record and history_record[1] is not None) else 0
            if play_count:
                summary_text = f"{play_count} {'play' if play_count == 1 else 'plays'}"
                summary_color = TEXT_WHITE
            else:
                summary_text = "You haven't listened to this podcast yet."
                summary_color = TEXT_GRAY
            summary_label = self.create_label(sub_card, summary_text, 11, summary_color)
            summary_label.pack(anchor="w", padx=18, pady=(0, 8))

            # Read-only 5-star polygon display aligned with the personal rating label.
            rating_row = tk.Frame(sub_card, bg=SUBCARD_BG)
            rating_row.pack(anchor="w", padx=18, pady=(0, 14))
            rating_caption = self.create_label(
                rating_row,
                "Your rating:",
                10, TEXT_GRAY, "bold", bg=SUBCARD_BG,
            )
            rating_caption.pack(side="left", padx=(0, 10))

            star_state = {"size": 22, "gap": 4, "score": given_rating}
            star_canvas = tk.Canvas(
                rating_row,
                width=5 * star_state["size"] + 4 * star_state["gap"],
                height=star_state["size"],
                bg=SUBCARD_BG,
                bd=0,
                highlightthickness=0,
            )
            star_canvas.pack(side="left", pady=(1, 0))

            def draw_inline_stars():
                if not star_canvas.winfo_exists():
                    return
                active = star_state["score"]
                size = star_state["size"]
                gap = star_state["gap"]
                total_w = 5 * size + 4 * gap
                star_canvas.configure(width=total_w, height=size)
                star_canvas.delete("all")
                r_out = size * 0.46
                r_in = size * 0.20
                cy = size / 2
                for star_idx in range(1, 6):
                    cx = (star_idx - 1) * (size + gap) + size / 2
                    pts = []
                    for pt_i in range(10):
                        ang = math.radians(-90 + pt_i * 36)
                        rad = r_out if pt_i % 2 == 0 else r_in
                        pts.extend((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
                    star_canvas.create_polygon(
                        pts,
                        fill=GOLD_STAR if star_idx <= active else STAR_EMPTY,
                        outline="",
                    )

            draw_inline_stars()

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
                avg_label.configure(font=(DEFAULT_FONT, max(11, round(12 * font_scale))))
                listen_label.configure(font=(DEFAULT_FONT, max(13, round(14 * font_scale)), "bold"))
                sim_notice_label.configure(font=(DEFAULT_FONT, max(9, round(10 * font_scale)), "italic"))
                listening_heading.configure(font=(DEFAULT_FONT, max(8, round(9 * font_scale)), "bold"))
                summary_label.configure(font=(DEFAULT_FONT, max(11, round(12 * font_scale))))
                rating_caption.configure(font=(DEFAULT_FONT, max(9, round(10 * font_scale)), "bold"))
                star_state["size"] = max(20, round(22 * font_scale))
                star_state["gap"] = max(3, round(4 * font_scale))
                draw_inline_stars()
                action_font_size = max(10, round(11 * font_scale))
                fav_button.pack_configure(pady=(0, round(8 * scale)))
                for btn, face_col, hover_col in action_buttons:
                    btn._rounded_padding = (round(28 * scale), round(14 * scale))
                    btn.configure(font=(DEFAULT_FONT, action_font_size, "bold"))
                    self.style_rounded_button(btn, face_col, hover_col)

            def schedule_detail_scale(_event=None):
                if resize_job[0] is not None:
                    self.after_cancel(resize_job[0])
                resize_job[0] = self.after(60, apply_detail_scale)

            detail_column.bind("<Configure>", schedule_detail_scale)
            apply_detail_scale()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't load programme", err)

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
                if existing_entry:
                    # Increment the existing play counter safely even if TimesListened was NULL.
                    conn.execute(
                        "UPDATE listening_history SET TimesListened = COALESCE(TimesListened, 0) + 1 "
                        "WHERE ListenerID = ? AND PodcastID = ?", (self.current_user, podcast_id),
                    )
                else:
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
                self.show_detail(podcast_id, show_simulated_notice=True)
            return True
        except sqlite3.Error as err:
            self.show_db_error("Couldn't update listening history", err)
            return False

    def save_programme_rating(self, podcast_id, new_score, callback_func=None):
        """Persist a 1-5 rating for the active listener and refresh the current view."""
        try:
            with self.get_db_connection() as conn:
                # Update the listener's rating in place, or insert a row if one doesn't exist yet.
                prior_record = conn.execute(
                    "SELECT 1 FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
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
                self.show_detail(podcast_id)
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save your rating", err)

    def rate_programme(self, podcast_id, callback_func=None, *, on_unplayed=None):
        """Open a dark interactive 5-star picker dialog to rate or update a programme's score."""
        existing_dlg = getattr(self, "_active_rating_dialog", None)
        if existing_dlg is not None and existing_dlg.winfo_exists():
            try:
                existing_dlg.lift()
                existing_dlg.focus_force()
            except tk.TclError:
                pass
            return
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
            self._active_rating_dialog = dialog
            dialog.title(dialog_title)
            dialog.configure(bg=DARK_BG)
            dialog.resizable(False, False)
            dialog.transient(self)
            dialog.grab_set()

            # Style the popup dialog's Windows titlebar to match the active theme.
            if sys.platform == "win32":
                try:
                    dialog.update_idletasks()
                    dlg_hwnd = ctypes.windll.user32.GetParent(dialog.winfo_id()) or dialog.winfo_id()

                    def _to_colorref(hex_col):
                        return int(hex_col[1:3], 16) | (int(hex_col[3:5], 16) << 8) | (int(hex_col[5:7], 16) << 16)

                    for attr, value in (
                        (20, int(TITLEBAR_DARK_MODE)),
                        (19, int(TITLEBAR_DARK_MODE)),
                        (35, _to_colorref(DARK_BG)),
                        (36, _to_colorref(TITLEBAR_TEXT)),
                        (34, _to_colorref(DARK_BG)),
                    ):
                        val = ctypes.c_int(value)
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            ctypes.c_void_p(dlg_hwnd), ctypes.c_int(attr), ctypes.byref(val), ctypes.sizeof(val),
                        )
                except Exception:
                    pass

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
                dialog.destroy()
                self.save_programme_rating(podcast_id, chosen, callback_func=callback_func)

            btn_row = tk.Frame(body, bg=DARK_BG)
            btn_row.pack()
            self.create_button(btn_row, "Save rating", confirm_rating, primary=True, compact=True).pack(side="left", padx=(0, 8))
            self.create_button(btn_row, "Cancel", dialog.destroy, compact=True).pack(side="left")

            dialog.update_idletasks()
            dw, dh = dialog.winfo_reqwidth(), dialog.winfo_reqheight()
            px = self.winfo_rootx() + (self.winfo_width() - dw) // 2
            py = self.winfo_rooty() + (self.winfo_height() - dh) // 2
            dialog.geometry(f"+{max(0, px)}+{max(0, py)}")
            dialog.bind("<Return>", lambda _e: confirm_rating())
            dialog.bind("<Escape>", lambda _e: dialog.destroy())
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save your rating", err)

    def remove_rating(self, podcast_id):
        """Clear the active listener's rating for a podcast and reload the Ratings page."""
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
                if target_str in id_tokens:
                    id_tokens.remove(target_str)
                else:
                    id_tokens.append(target_str)
                conn.execute(
                    "UPDATE listeners SET FavoritePodcasts = ? WHERE ListenerID = ?",
                    (",".join(id_tokens), self.current_user),
                )
            self.show_detail(podcast_id)
        except sqlite3.Error as err:
            self.show_db_error("Couldn't update favourites", err)

    def remove_from_history(self, podcast_id):
        """Delete one programme from the listener's listening history."""
        if not messagebox.askyesno("Remove from history", "Remove this programme from your listening history?", parent=self):
            return
        try:
            # Delete only the matching (ListenerID, PodcastID) row from listening_history.
            with self.get_db_connection() as conn:
                conn.execute(
                    "DELETE FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                )
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
