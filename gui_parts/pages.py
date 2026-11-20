"""Application pages: Home, Genres/Search, For you, Favourites, History, Ratings, Report, Profile, and Survey."""
import sqlite3
from time import monotonic
import tkinter as tk
from tkinter import messagebox

from gui_parts.theme import (
    BANNER_BG,
    BORDER_LINE,
    CARD_BG,
    DARK_BG,
    DEFAULT_FONT,
    DURATION_RANGES,
    GENRE_LIST,
    GENRE_TILE_DETAILS,
    GOLD_STAR,
    INPUT_BG,
    ORANGE_ACCENT,
    ORANGE_HL,
    PALETTE_SWATCHES,
    PRIMARY_BTN_FG,
    SECONDARY_HOVER_BG,
    SECONDARY_HOVER_FG,
    SELECTED_BG,
    SUBCARD_BG,
    TEXT_GRAY,
    TEXT_LIGHT,
    TEXT_WHITE,
    blend_colour,
    ease_out_elastic,
)


class PagesMixin:
    """Mixin implementing all top-level navigation pages and preference-survey controls."""

    def show_home(self):
        """Render the Home dashboard with stats, report shortcut, recommendations, and recent history."""
        try:
            page = self.build_shell("Home")
            listener_info = self.get_listener_data()
            name_str = self.get_row_field(listener_info, "Username", None) or self.get_row_field(listener_info, "Name", None)
            first_name = str(name_str or "there").split()[0]
            self.render_page_title(page, f"Good to have you back!",
                                   "Settle in and find something worth listening to.")

            favourite_ids = [
                item.strip()
                for item in str(self.get_row_field(listener_info, "FavoritePodcasts", "") or "").split(",")
                if item.strip()
            ]
            with self.get_db_connection() as conn:
                history_counts = conn.execute(
                    "SELECT COUNT(*), COUNT(h.RatingGiven) "
                    "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                    "WHERE h.ListenerID = ?",
                    (self.current_user,),
                ).fetchone()
                history_rows = conn.execute(
                    "SELECT p.PodcastID, p.Title, p.Category, p.AverageLengthMins, "
                    "h.TimesListened, h.RatingGiven "
                    "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                    "WHERE h.ListenerID = ? ORDER BY COALESCE(h.TimesListened, 0) DESC, "
                    "p.Title COLLATE NOCASE LIMIT 8",
                    (self.current_user,),
                ).fetchall()
                favourite_count = 0
                if favourite_ids:
                    placeholders = ",".join("?" for _ in favourite_ids)
                    favourite_count = conn.execute(
                        f"SELECT COUNT(*) FROM podcasts WHERE PodcastID IN ({placeholders})",
                        favourite_ids,
                    ).fetchone()[0]

            stats_pane = tk.Frame(page, bg=DARK_BG)
            stats_pane.pack(fill="x", pady=(4, 12))
            metric_list = [
                (str(history_counts[0]), "programmes in your history"),
                (str(favourite_count), "favourites saved"),
                (str(history_counts[1]), "ratings given"),
            ]
            for idx, (val_str, cap_str) in enumerate(metric_list):
                stats_pane.grid_columnconfigure(idx, weight=1, uniform="stats")
                card_box = self.create_card_frame(stats_pane)
                card_box.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 6, 6))
                self.create_label(card_box, val_str, 23, ORANGE_ACCENT, "bold").pack(anchor="w", padx=16, pady=(12, 0))
                self.create_label(card_box, cap_str, 9, TEXT_GRAY).pack(anchor="w", padx=16, pady=(0, 12))

            report_strip = self.create_card_frame(page, bg=SUBCARD_BG)
            report_strip.pack(fill="x", pady=(0, 10))
            self.create_label(report_strip, "YOUR LISTENING, SUMMARISED", 9, ORANGE_HL, "bold").pack(
                side="left", padx=(16, 8), pady=14
            )
            self.create_label(report_strip, "See your plays, most-listened programme and average rating.", 10, TEXT_GRAY).pack(
                side="left", pady=14
            )
            self.create_button(
                report_strip, "Generate listening report",
                lambda: self.transition_to(self.show_report, "Report"),
                primary=True, compact=True,
            ).pack(side="right", padx=12, pady=8)

            genres_str = str(self.get_row_field(listener_info, "FavoriteGenres", "") or "").replace(",", " · ")
            length_str = self.get_row_field(listener_info, "LengthPreference", "") or ""
            banner_card = self.create_card_frame(page, bg=BANNER_BG)
            banner_card.pack(fill="x", pady=(7, 7))
            banner_text = tk.Frame(banner_card, bg=BANNER_BG)
            banner_text.pack(side="left", fill="both", expand=True, padx=20, pady=19)
            self.create_label(banner_text, "Find your next favourite listen", 17, TEXT_WHITE, "bold").pack(anchor="w")
            hint_msg = "Search thousands of programmes and explore by genre."
            if genres_str:
                hint_msg = "Picked for " + genres_str + (" · " + length_str + " episodes" if length_str else "")
            self.create_label(banner_text, hint_msg, 10, TEXT_GRAY, wraplength=520).pack(anchor="w", pady=(5, 13))
            self.create_button(
                banner_text, "Explore programmes  →",
                lambda: self.transition_to(self.show_search, "Genres"),
                primary=True, compact=True,
            ).pack(anchor="w")
            promo_art = self.render_decorative_panel(banner_card, "1.svg", 0, (150, 138), 155, 138)
            promo_art.pack(side="right", padx=12, pady=10)

            rec_list = self.get_custom_recommendations(8)
            if rec_list:
                self.render_section_title(
                    page, "Made for you", "A match for your favourite genres and episode length.",
                    "See all", lambda: self.transition_to(self.show_recommendations, "For you"),
                )
                self.render_podcast_grid(
                    page, rec_list, columns_count=6, show_play=True,
                    max_count=8, single_row=True,
                )
            elif not self.get_row_field(listener_info, "CompleteSurvey", 0):
                self.render_section_title(page, "Make recommendations personal")
                survey_prompt = self.create_card_frame(page)
                survey_prompt.pack(fill="x", pady=5)
                self.create_label(survey_prompt, "Tell us what you like", 14, TEXT_WHITE, "bold").pack(anchor="w", padx=17, pady=(15, 4))
                self.create_label(survey_prompt, "Choose a few genres and your preferred episode length to get tailored picks.",
                                  10, TEXT_GRAY).pack(anchor="w", padx=17, pady=(0, 12))
                self.create_button(
                    survey_prompt, "Choose your genres  →",
                    lambda: self.transition_to(self.show_preferences, "Profile"),
                    primary=True, compact=True,
                ).pack(anchor="w", padx=17, pady=(0, 15))

            if history_rows:
                self.render_section_title(
                    page, "Pick up where you left off", "Your most played programmes.",
                    "Listening history", lambda: self.transition_to(self.show_history, "History"),
                )
                self.render_podcast_grid(
                    page, history_rows, columns_count=6, show_play=True,
                    max_count=8, single_row=True,
                )
            else:
                self.render_section_title(page, "Explore the catalogue")
                self.render_podcast_grid(
                    page, self.query_podcasts(item_limit=8), columns_count=6,
                    show_play=True, max_count=8, single_row=True,
                )
        except sqlite3.Error as err:
            self.show_db_error("Couldn't load BBC Sounds", err)

    def show_search(self):
        """Render the Genres & Search tab with animated genre cards and live-filtered programmes."""
        page = self.build_shell("Genres")
        self.render_page_title(page, "Browse genres", "Choose a genre below, or use the search bar above.")

        results_pane = tk.Frame(page, bg=DARK_BG)
        last_search = None

        def perform_search_action(_event=None):
            nonlocal last_search
            self.update_search_prompt()
            search_term = self.search_text.get().strip()
            if search_term == last_search:
                return
            self.cancel_pending_render()
            for child in results_pane.winfo_children():
                child.destroy()
            try:
                matching_rows = self.query_podcasts(search_term, item_limit=80, shuffle=True)
                self.create_label(results_pane, f"{len(matching_rows)} programmes", 10, TEXT_GRAY).pack(anchor="w", pady=(8, 6))
                self.render_podcast_grid(
                    results_pane, matching_rows, columns_count=6,
                    show_play=True, max_count=80,
                )
                last_search = search_term
            except sqlite3.Error as err:
                last_search = None
                self.show_db_error("Search failed", err)

        self._live_search_callback = perform_search_action

        self.render_section_title(page, "All genres", "Select a genre to see every matching programme.")
        category_row = tk.Frame(page, bg=DARK_BG)
        category_row.pack(fill="x", pady=(0, 12))
        try:
            with self.get_db_connection() as conn:
                category_rows = conn.execute(
                    "SELECT DISTINCT Category FROM podcasts "
                    "WHERE Category IS NOT NULL AND TRIM(Category) <> '' "
                    "ORDER BY Category COLLATE NOCASE"
                ).fetchall()
            available_categories = {str(row[0]).strip() for row in category_rows}
            all_categories = [name for name in GENRE_LIST if name in available_categories]
            all_categories.extend(sorted(available_categories.difference(all_categories), key=str.casefold))

            columns_count = 4
            for column_idx in range(columns_count):
                category_row.grid_columnconfigure(column_idx, weight=1, uniform="genre")

            for idx, category_name in enumerate(all_categories):
                tile_colour, tile_icon, tile_description = GENRE_TILE_DETAILS.get(
                    category_name,
                    (
                        PALETTE_SWATCHES[idx % len(PALETTE_SWATCHES)],
                        category_name[:1].upper(),
                        f"Explore {category_name.lower()} shows and stories",
                    ),
                )
                category_card = self.create_card_frame(category_row, bg=tile_colour, cursor="hand2")
                category_card._inset = 3
                category_card.grid(
                    row=idx // columns_count, column=idx % columns_count,
                    sticky="nsew", padx=5, pady=5,
                )
                accent_line = tk.Frame(category_card, bg=ORANGE_HL, height=3, cursor="hand2")
                accent_line.pack(fill="x", padx=12, pady=(2, 0))
                card_header = tk.Frame(category_card, bg=tile_colour, cursor="hand2")
                card_header.pack(fill="x", padx=15, pady=(13, 5))
                icon_label = tk.Label(
                    card_header, text=tile_icon, width=3, height=1,
                    font=(DEFAULT_FONT, 14, "bold"), bg="#17181b", fg=TEXT_WHITE,
                    cursor="hand2",
                )
                icon_label.pack(side="left", padx=(0, 10))
                title_label = tk.Label(
                    card_header, text=category_name.upper(), font=(DEFAULT_FONT, 11, "bold"),
                    bg=tile_colour, fg=TEXT_WHITE, anchor="w", cursor="hand2",
                )
                title_label.pack(side="left", fill="x", expand=True)
                description_label = tk.Label(
                    category_card, text=tile_description, font=(DEFAULT_FONT, 9),
                    bg=tile_colour, fg="#f0f0f0", justify="left", anchor="nw",
                    wraplength=225, cursor="hand2",
                )
                description_label.pack(fill="x", padx=15, pady=(3, 12))
                action_label = tk.Label(
                    category_card, text="BROWSE PROGRAMMES  →", font=(DEFAULT_FONT, 8, "bold"),
                    bg=tile_colour, fg="#ffffff", anchor="w", cursor="hand2",
                )
                action_label.pack(fill="x", padx=15, pady=(0, 14))

                hover_colour = blend_colour(tile_colour, "#ffffff", 0.16)
                card_state = {"step": 0, "target": 0, "job": None}
                card_widgets = (
                    category_card, category_card.backdrop, accent_line, card_header, icon_label,
                    title_label, description_label, action_label,
                )

                def cancel_card_hover(state=card_state):
                    if state["job"] is not None:
                        try:
                            self.after_cancel(state["job"])
                        except tk.TclError:
                            pass
                        state["job"] = None

                def apply_card_hover(
                    step,
                    card=category_card,
                    base_col=tile_colour,
                    hi_col=hover_colour,
                    hdr=card_header,
                    ico=icon_label,
                    ttl=title_label,
                    dsc=description_label,
                    act=action_label,
                    state=card_state,
                ):
                    if not card.winfo_exists():
                        return
                    t = step / 12.0
                    # Fluid damped elastic spring on hover; smooth cubic ease-out on leave.
                    eased = ease_out_elastic(t, damping=4.8, frequency=1.15) if state["target"] > 0 else 1.0 - (1.0 - t) ** 3
                    cur_bg = blend_colour(base_col, hi_col, eased)
                    cur_border = blend_colour(BORDER_LINE, ORANGE_HL, eased)
                    cur_ico_bg = blend_colour("#17181b", ORANGE_ACCENT, eased)
                    cur_act_fg = blend_colour("#ffffff", GOLD_STAR, eased)
                    card.set_inset(max(0, min(3, round(3.0 - 2.0 * eased))))
                    card.set_surface(cur_bg, cur_border)
                    hdr.configure(bg=cur_bg)
                    ttl.configure(bg=cur_bg)
                    dsc.configure(bg=cur_bg)
                    act.configure(bg=cur_bg, fg=cur_act_fg)
                    ico.configure(bg=cur_ico_bg)

                def animate_card_hover(target, state=card_state, card=category_card, apply_fn=apply_card_hover):
                    if not card.winfo_exists():
                        return
                    state["target"] = target
                    if state["job"] is not None:
                        return

                    def step_card():
                        state["job"] = None
                        if not card.winfo_exists():
                            return
                        cur = state["step"]
                        tgt = state["target"]
                        if cur == tgt:
                            return
                        cur += 1 if tgt > cur else -1
                        state["step"] = cur
                        apply_fn(cur)
                        if cur != tgt:
                            state["job"] = self.after(16, step_card)

                    step_card()

                def on_card_leave(_event=None, card=category_card, anim_fn=animate_card_hover):
                    if not card.winfo_exists():
                        return
                    hovered = self.winfo_containing(*self.winfo_pointerxy())
                    node = hovered
                    while node is not None:
                        if node is card:
                            return
                        node = node.master
                    anim_fn(0)

                def open_genre(
                    _event=None,
                    card=category_card,
                    name=category_name,
                    icon=tile_icon,
                    desc=tile_description,
                    base_col=tile_colour,
                    hi_col=hover_colour,
                    state=card_state,
                    cancel_fn=cancel_card_hover,
                ):
                    cancel_fn()
                    t = state["step"] / 12.0
                    start_col = blend_colour(base_col, hi_col, 1.0 - (1.0 - t) ** 3)
                    self.expand_genre_in_tab(
                        card, name, icon, desc, start_col,
                        lambda: (self.search_text.set(name), perform_search_action()),
                        programmes_heading, page,
                    )

                for clickable_widget in card_widgets:
                    clickable_widget.bind("<Enter>", lambda _e, anim_fn=animate_card_hover: anim_fn(12))
                    clickable_widget.bind("<Leave>", on_card_leave)
                    clickable_widget.bind("<Button-1>", open_genre)
                category_card.bind("<Destroy>", lambda _e, cancel_fn=cancel_card_hover: cancel_fn())
        except sqlite3.Error as err:
            self.show_db_error("Couldn't load categories", err)

        programmes_heading = self.render_section_title(page, "Programmes")
        results_pane.pack(fill="both", expand=True)
        perform_search_action()

    def expand_genre_in_tab(self, card, genre_name, genre_icon, genre_desc, start_col, apply_filter, heading_widget, page):
        """Expand a clicked genre tile within the Genres content area and scroll to its programmes."""
        canvas_pane, _window = self._page_transition_target
        area_frame = canvas_pane.master
        if getattr(area_frame, "_expanding_genre", False) or not area_frame.winfo_exists() or not card.winfo_exists():
            return
        area_frame._expanding_genre = True

        start_x = card.winfo_rootx() - area_frame.winfo_rootx()
        start_y = card.winfo_rooty() - area_frame.winfo_rooty()
        start_w = max(1, card.winfo_width())
        start_h = max(1, card.winfo_height())
        target_w = max(1, area_frame.winfo_width())
        target_h = max(1, area_frame.winfo_height())

        if target_w <= 1 or target_h <= 1:
            area_frame._expanding_genre = False
            apply_filter()
            return

        expander = tk.Frame(area_frame, bg=start_col, bd=0, highlightthickness=0)
        accent_top = tk.Frame(expander, bg=ORANGE_HL, height=3)
        accent_top.pack(fill="x")
        preview_box = tk.Frame(expander, bg=start_col)
        preview_box.place(relx=0.5, rely=0.5, anchor="center")
        icon_badge = tk.Label(
            preview_box, text=genre_icon, width=3, height=1,
            font=(DEFAULT_FONT, 18, "bold"), bg=ORANGE_ACCENT, fg=TEXT_WHITE,
        )
        icon_badge.pack(pady=(0, 8))
        title_lbl = self.create_label(
            preview_box, genre_name.upper(), 24, TEXT_WHITE, "bold",
            anchor="center", bg=start_col,
        )
        title_lbl.pack()
        desc_lbl = self.create_label(
            preview_box, genre_desc, 11, "#f0f0f0",
            anchor="center", justify="center", bg=start_col,
        )
        desc_lbl.pack(pady=(6, 0))

        expander.place(x=start_x, y=start_y, width=start_w, height=start_h)
        tk.Misc.lift(expander)

        expand_duration = 0.420
        expand_started = monotonic()

        def start_reveal():
            if not expander.winfo_exists() or not area_frame.winfo_exists():
                return
            apply_filter()
            if canvas_pane.winfo_exists() and heading_widget.winfo_exists() and page.winfo_exists():
                self.update_idletasks()
                region = canvas_pane.cget("scrollregion")
                if region:
                    total_h = int(float(region.split()[3]))
                    if total_h > 0:
                        offset = heading_widget.winfo_rooty() - page.winfo_rooty()
                        canvas_pane.yview_moveto(max(0.0, min(1.0, (offset - 12) / total_h)))
            tk.Misc.lift(expander)

            reveal_duration = 0.360
            reveal_started = None

            def draw_reveal():
                nonlocal reveal_started
                if not expander.winfo_exists() or not area_frame.winfo_exists():
                    return
                if reveal_started is None:
                    reveal_started = monotonic()
                progress = min(1.0, (monotonic() - reveal_started) / reveal_duration)
                eased = 1.0 - (1.0 - progress) ** 4
                cur_y = round(-target_h * eased)
                expander.place(x=0, y=cur_y, width=target_w, height=target_h)
                tk.Misc.lift(expander)
                if progress < 1.0:
                    self.after(8, draw_reveal)
                else:
                    expander.destroy()
                    area_frame._expanding_genre = False

            self.after(8, draw_reveal)

        def draw_expand():
            if not expander.winfo_exists() or not area_frame.winfo_exists():
                return
            progress = min(1.0, (monotonic() - expand_started) / expand_duration)
            eased = ease_out_elastic(progress, damping=5.5, frequency=1.05)
            cur_x = max(0, round(start_x * (1.0 - eased)))
            cur_y = max(0, round(start_y * (1.0 - eased)))
            cur_w = max(1, min(target_w, round(start_w + (target_w - start_w) * eased)))
            cur_h = max(1, min(target_h, round(start_h + (target_h - start_h) * eased)))

            if progress > 0.45:
                fade = (progress - 0.45) / 0.55
                cur_bg = blend_colour(start_col, DARK_BG, fade)
                cur_title_fg = blend_colour(TEXT_WHITE, cur_bg, fade)
                cur_desc_fg = blend_colour("#f0f0f0", cur_bg, fade)
                cur_ico_bg = blend_colour(ORANGE_ACCENT, cur_bg, fade)
                cur_ico_fg = blend_colour(TEXT_WHITE, cur_bg, fade)
            else:
                cur_bg = start_col
                cur_title_fg = TEXT_WHITE
                cur_desc_fg = "#f0f0f0"
                cur_ico_bg = ORANGE_ACCENT
                cur_ico_fg = TEXT_WHITE

            expander.configure(bg=cur_bg)
            preview_box.configure(bg=cur_bg)
            title_lbl.configure(bg=cur_bg, fg=cur_title_fg)
            desc_lbl.configure(bg=cur_bg, fg=cur_desc_fg)
            icon_badge.configure(bg=cur_ico_bg, fg=cur_ico_fg)

            expander.place(x=cur_x, y=cur_y, width=cur_w, height=cur_h)
            tk.Misc.lift(expander)

            if progress < 1.0:
                self.after(8, draw_expand)
            else:
                # Hold briefly at full expansion before sliding the curtain up to reveal programmes.
                self.after(120, start_reveal)

        draw_expand()

    def show_recommendations(self):
        """Render the 'For you' recommendations tab based on saved genre and length preferences."""
        page = self.build_shell("For you")
        listener_info = self.get_listener_data()
        genres_val = self.get_row_field(listener_info, "FavoriteGenres", "") or ""
        length_val = self.get_row_field(listener_info, "LengthPreference", "") or ""
        self.render_page_title(page, "Picked for you", "Recommendations use your selected genres and preferred episode length.")
        if not genres_val or not length_val:
            self.render_empty_message(page, "Your listening profile is ready for a few details",
                                      "Choose your favourite genres and episode length to unlock tailored recommendations.")
            self.create_button(
                page, "Set up your preferences  →",
                lambda: self.transition_to(self.show_preferences, "Profile"), primary=True,
            ).pack(anchor="w", pady=7)
            self.render_section_title(page, "Explore the catalogue while you decide")
            self.render_podcast_grid(page, self.query_podcasts(item_limit=8, shuffle=True), show_play=True)
            return
        # Show a 2-column summary card of the listener's active genre and episode-length preferences.
        prefs_bar = tk.Frame(page, bg=DARK_BG)
        prefs_bar.pack(fill="x", pady=(0, 12))
        prefs_bar.grid_columnconfigure(0, weight=2, uniform="for-you-prefs")
        prefs_bar.grid_columnconfigure(1, weight=1, uniform="for-you-prefs")

        genres_card = self.create_card_frame(prefs_bar, bg=SUBCARD_BG)
        genres_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.create_label(genres_card, "YOUR GENRES", 8, TEXT_GRAY, "bold").pack(anchor="w", padx=16, pady=(12, 3))
        formatted_genres = "  ·  ".join(g.strip() for g in str(genres_val).split(",") if g.strip())
        self.create_label(genres_card, formatted_genres, 11, ORANGE_HL, "bold", wraplength=560).pack(
            anchor="w", padx=16, pady=(0, 12)
        )

        length_card = self.create_card_frame(prefs_bar, bg=SUBCARD_BG)
        length_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.create_label(length_card, "EPISODE LENGTH", 8, TEXT_GRAY, "bold").pack(anchor="w", padx=16, pady=(12, 3))
        length_range = DURATION_RANGES.get(length_val)
        length_caption = (
            f"{length_val} episodes ({length_range[0]}–{length_range[1]} min)"
            if length_range else f"{length_val} episodes"
        )
        self.create_label(length_card, length_caption, 11, ORANGE_HL, "bold").pack(
            anchor="w", padx=16, pady=(0, 12)
        )
        # Fetch up to 40 weighted-shuffled recommendations matching those preferences.
        rec_results = self.get_custom_recommendations(40, shuffle=True)
        if rec_results:
            self.render_podcast_grid(page, rec_results, columns_count=6, show_play=True, max_count=40)
        else:
            self.render_empty_message(page, "No exact matches yet", "Try another genre or episode length to see more programmes.")
            self.create_button(
                page, "Edit preferences",
                lambda: self.transition_to(self.show_preferences, "Profile"), compact=True,
            ).pack(anchor="w", pady=8)

    def show_favourites(self):
        """Render the Favourites tab listing saved podcasts."""
        page = self.build_shell("Favourites")
        self.render_page_title(page, "Your favourites", "The programmes you have saved for later.")
        fav_rows = self.fetch_user_favourites()
        if not fav_rows:
            self.render_empty_message(page, "No favourites saved yet", "Open any programme and tap the heart to keep it here.")
            self.create_button(
                page, "Find a programme",
                lambda: self.transition_to(self.show_search, "Genres"), primary=True, compact=True,
            ).pack(anchor="w", pady=6)
            return
        self.render_podcast_grid(
            page, fav_rows, columns_count=6,
            show_play=True, max_count=len(fav_rows),
        )

    def show_history(self):
        """Render the Listening History tab with per-item removal and Clear History controls."""
        page = self.build_shell("History")
        self.render_page_title(page, "Listening history", "A record of what you have played in BBC Sounds.")
        history_rows = self.fetch_user_history()
        if not history_rows:
            self.render_empty_message(page, "Your history is empty", "Play a programme and it will appear here.")
            self.create_button(
                page, "Explore programmes",
                lambda: self.transition_to(self.show_search, "Genres"), primary=True, compact=True,
            ).pack(anchor="w", pady=6)
            return
        control_bar = tk.Frame(page, bg=DARK_BG)
        control_bar.pack(fill="x", pady=(0, 7))
        self.create_label(control_bar, f"{len(history_rows)} programmes", 10, TEXT_GRAY).pack(side="left")
        self.create_button(control_bar, "Clear history", self.clear_history, compact=True).pack(side="right")
        self.render_podcast_grid(
            page, history_rows, columns_count=6,
            show_play=True, show_remove=True, max_count=len(history_rows),
        )

    def show_ratings(self):
        """Render the Ratings tab with paginated rated programme cards."""
        page = self.build_shell("Ratings")
        self.render_page_title(page, "Podcasts you rated", "Every programme you have scored is collected here.")
        rating_rows = self.fetch_user_ratings()
        if not rating_rows:
            self.render_empty_message(page, "No ratings yet", "Listen to a programme, then add a rating from its details page.")
            self.create_button(
                page, "Explore programmes",
                lambda: self.transition_to(self.show_search, "Genres"), primary=True, compact=True,
            ).pack(anchor="w", pady=6)
            return

        summary_bar = self.create_card_frame(page, bg=SUBCARD_BG)
        summary_bar.pack(fill="x", pady=(0, 12))
        self.create_label(summary_bar, str(len(rating_rows)), 24, ORANGE_ACCENT, "bold").pack(
            side="left", padx=(18, 8), pady=12
        )
        self.create_label(summary_bar, "ratings in your library", 10, TEXT_GRAY).pack(side="left", pady=18)
        self.create_label(summary_bar, "Select a programme to update or remove its score.", 10, TEXT_LIGHT).pack(
            side="right", padx=18, pady=18
        )

        self.paginate_podcasts(page, rating_rows, self.render_ratings_page)

    def render_ratings_page(self, parent, rating_rows, last_page):
        """Render one page of 4-column rated podcast cards."""
        ratings_grid = tk.Frame(parent, bg=DARK_BG)
        ratings_grid.pack(fill="x")
        for column_idx in range(4):
            ratings_grid.grid_columnconfigure(column_idx, weight=1, uniform="rating-cards")

        rendered_cards = []
        current_cover_size = [0]
        cover_resize_job = [None]

        def compute_rating_cover_size():
            available_width = ratings_grid.winfo_width()
            if available_width <= 1:
                available_width = max(1, self.winfo_width() - 110)
            col_width = available_width // 4
            return max(160, col_width - 30)

        def refresh_rating_covers():
            cover_resize_job[0] = None
            if not ratings_grid.winfo_exists():
                return
            target_size = current_cover_size[0]
            for card_widget in rendered_cards:
                if not card_widget.winfo_exists():
                    continue
                meta = getattr(card_widget, "_cover_meta", None)
                if not meta or meta[5] == target_size:
                    continue
                cover_box, cover_lbl, pid, title, category, _old_size = meta
                if cover_box.winfo_exists():
                    cover_box.configure(height=target_size)
                self.update_podcast_cover(
                    cover_lbl, pid, title, category, target_size, target_size,
                    corner_radius=8, backdrop=CARD_BG,
                )
                meta[5] = target_size

        def on_ratings_resize(_event=None):
            target_size = compute_rating_cover_size()
            if current_cover_size[0] == 0 or abs(target_size - current_cover_size[0]) >= 2:
                current_cover_size[0] = target_size
                if rendered_cards:
                    if cover_resize_job[0] is not None:
                        try:
                            self.after_cancel(cover_resize_job[0])
                        except tk.TclError:
                            pass
                    cover_resize_job[0] = self.after(50, refresh_rating_covers)

        ratings_grid.bind("<Configure>", on_ratings_resize)

        def render_rating_card(row):
            if current_cover_size[0] == 0:
                current_cover_size[0] = compute_rating_cover_size()
            cover_size = current_cover_size[0]
            card = self.create_card_frame(ratings_grid)
            idx = len(ratings_grid.winfo_children()) - 1
            card.grid(row=idx // 4, column=idx % 4, sticky="nsew", padx=6, pady=6)
            cover_box = tk.Frame(card, bg=CARD_BG, height=cover_size)
            cover_box.pack_propagate(False)
            cover_box.pack(fill="x", padx=9, pady=(9, 0))
            cover = self.generate_podcast_cover(
                cover_box, row[0], row[1], row[2], cover_size, cover_size,
                corner_radius=8, backdrop=CARD_BG,
            )
            cover.pack(fill="both", expand=True)
            card._cover_meta = [cover_box, cover, row[0], row[1], row[2], cover_size]
            rendered_cards.append(card)
            details_pane = tk.Frame(card, bg=CARD_BG)
            details_pane.pack(fill="both", expand=True, padx=13, pady=12)
            self.create_label(details_pane, row[1], 12, TEXT_WHITE, "bold", wraplength=max(180, cover_size - 8)).pack(anchor="w")
            self.create_label(details_pane, str(row[2]), 9, TEXT_GRAY).pack(anchor="w", pady=(4, 0))
            self.create_label(details_pane, self.podcast_average_text(row[0]), 9, GOLD_STAR).pack(anchor="w", pady=(3, 6))
            self.create_label(details_pane, "Your rating", 9, TEXT_GRAY).pack(anchor="w")
            self.create_star_rating_bar(details_pane, row[3], star_size=16, background_col=CARD_BG).pack(
                anchor="w", pady=(5, 10)
            )
            button_row = tk.Frame(details_pane, bg=CARD_BG)
            button_row.pack(fill="x")
            self.create_button(
                button_row, "Change rating", lambda target_id=row[0]: self.rate_programme(target_id, self.show_ratings), compact=True
            ).pack(side="left")
            self.create_button(button_row, "Remove", lambda target_id=row[0]: self.remove_rating(target_id), compact=True).pack(
                side="right"
            )
            final_row, used_columns = divmod(len(rating_rows), 4)
            if last_page and idx == len(rating_rows) - 1 and used_columns:
                self.create_label(
                    ratings_grid, "No more results", 15, "#777b83", "bold", anchor="center",
                ).grid(
                    row=final_row, column=used_columns, columnspan=4 - used_columns,
                    sticky="nsew", padx=6, pady=6,
                )
        self.render_in_batches(rating_rows, render_rating_card)

    def show_genres(self):
        """Render the listener's favourite genres summary and matching programmes."""
        page = self.build_shell("Your genres")
        listener_info = self.get_listener_data()
        user_genres = [g.strip() for g in str(self.get_row_field(listener_info, "FavoriteGenres", "") or "").split(",") if g.strip()]
        self.render_page_title(page, "Your favourite genres", "Programme suggestions are tuned to the genres you choose.")
        if user_genres:
            genre_wrapper = tk.Frame(page, bg=DARK_BG)
            genre_wrapper.pack(fill="x", pady=5)
            for idx, g_item in enumerate(user_genres):
                self.build_genre_tile(genre_wrapper, g_item, idx, selected=True).grid(
                    row=idx // 4, column=idx % 4, sticky="nsew", padx=5, pady=5
                )
                genre_wrapper.grid_columnconfigure(idx % 4, weight=1, uniform="genres")
            self.render_section_title(page, "Episode length", str(self.get_row_field(listener_info, "LengthPreference", "Not selected") or "Not selected"))
            self.create_button(
                page, "Edit preferences",
                lambda: self.transition_to(self.show_preferences, "Profile", direction=1),
                primary=True, compact=True,
            ).pack(anchor="w", pady=7)
            self.render_section_title(page, "Programmes in your genres")
            if user_genres:
                placeholders = ",".join("?" for _ in user_genres)
                with self.get_db_connection() as conn:
                    matched_items = conn.execute(
                        f"SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts WHERE Category IN ({placeholders}) "
                        "ORDER BY Title COLLATE NOCASE LIMIT 12", user_genres,
                    ).fetchall()
                self.render_podcast_grid(page, matched_items, show_play=True, max_count=12)
        else:
            self.render_empty_message(page, "No favourite genres selected", "Choose up to five genres to shape your recommendations.")
            self.create_button(
                page, "Choose genres",
                lambda: self.transition_to(self.show_preferences, "Profile", direction=1), primary=True,
            ).pack(anchor="w", pady=6)

    def show_report(self):
        """Render the Listening Report tab with play totals, top programme, and rated shows."""
        page = self.build_shell("Listening report")
        # Query aggregate play counts, most-played programme, average rating, and rated programmes in one connection.
        with self.get_db_connection() as conn:
            history_summary = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(COALESCE(h.TimesListened, 0)), 0) "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ?",
                (self.current_user,),
            ).fetchone()
            top_programme = conn.execute(
                "SELECT p.PodcastID, p.Title, p.Category, p.AverageLengthMins, "
                "h.TimesListened, h.RatingGiven "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ? ORDER BY COALESCE(h.TimesListened, 0) DESC, "
                "p.Title COLLATE NOCASE LIMIT 1",
                (self.current_user,),
            ).fetchone()
            rating_summary = conn.execute(
                "SELECT COUNT(h.RatingGiven), AVG(h.RatingGiven) "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ?",
                (self.current_user,),
            ).fetchone()
            rating_rows = conn.execute(
                "SELECT p.PodcastID, p.Title, p.Category, h.RatingGiven, h.TimesListened "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ? AND h.RatingGiven IS NOT NULL "
                "ORDER BY p.Title COLLATE NOCASE LIMIT 8",
                (self.current_user,),
            ).fetchall()
        self.render_page_title(page, "Your listening report", "A snapshot of your recent listening activity.")
        total_plays = history_summary[1]
        mean_rating = rating_summary[1]

        # Display 3 equal-width KPI cards: total plays, distinct programmes played, and mean rating.
        stats_grid = tk.Frame(page, bg=DARK_BG)
        stats_grid.pack(fill="x", pady=6)
        stat_cards = [
            (str(total_plays), "total plays"),
            (str(history_summary[0]), "programmes played"),
            ("—" if mean_rating is None else f"{mean_rating:.1f} / 5", "average rating"),
        ]
        for idx, (metric_val, metric_title) in enumerate(stat_cards):
            stats_grid.grid_columnconfigure(idx, weight=1, uniform="report")
            box_item = self.create_card_frame(stats_grid)
            box_item.grid(row=0, column=idx, sticky="ew", padx=5)
            self.create_label(box_item, metric_val, 21, ORANGE_ACCENT, "bold", anchor="center").pack(
                fill="x", padx=16, pady=(13, 2)
            )
            self.create_label(box_item, metric_title, 9, TEXT_GRAY, anchor="center").pack(
                fill="x", padx=16, pady=(0, 13)
            )

        self.render_section_title(page, "Your listening highlights")
        if top_programme:
            highlight_card = self.create_card_frame(page)
            highlight_card.pack(fill="x", pady=5)
            highlight_cover = self.generate_podcast_cover(
                highlight_card, top_programme[0], top_programme[1], top_programme[2], 128, 128,
                corner_radius=8, backdrop=CARD_BG,
            )
            highlight_cover.pack(side="left", padx=12, pady=12)
            highlight_details = tk.Frame(highlight_card, bg=CARD_BG)
            highlight_details.pack(side="left", fill="both", expand=True, pady=16)
            self.create_label(highlight_details, "MOST PLAYED", 8, ORANGE_ACCENT, "bold").pack(anchor="w", pady=(0, 5))
            self.create_label(highlight_details, top_programme[1], 16, TEXT_WHITE, "bold").pack(anchor="w")
            self.create_label(
                highlight_details, f"{top_programme[4] or 0} plays  ·  {top_programme[2]}", 10, TEXT_GRAY,
            ).pack(anchor="w", pady=(5, 0))
            self.create_label(
                highlight_details, self.podcast_average_text(top_programme[0]), 9, GOLD_STAR,
            ).pack(anchor="w", pady=(4, 0))
            self.create_button(
                highlight_card, "▶  Listen again", lambda: self.listen(top_programme[0]),
                primary=True, compact=True,
            ).pack(side="right", padx=18)
        else:
            self.render_empty_message(page, "No listening data yet", "Play a programme to start your personal report.")

        if rating_rows:
            self.render_section_title(page, "Your rated programmes")
            report_programmes = [(row[0], row[1], row[2], None, row[3]) for row in rating_rows]
            self.render_podcast_grid(
                page, report_programmes, columns_count=6,
                max_count=len(report_programmes), rating_index=4,
            )

    def show_profile(self):
        """Render the Profile & Survey tab showing listener info and saved preferences."""
        page = self.build_shell("Profile & survey")
        listener_info = self.get_listener_data()
        self.render_page_title(page, "Profile & survey", "Update your preferences whenever your listening changes.")
        info_card = self.create_card_frame(page)
        info_card.pack(fill="x", pady=(4, 12))
        avatar = self.create_default_profile_avatar(info_card, 112)
        avatar.pack(side="left", padx=(20, 18), pady=18)
        profile_details = tk.Frame(info_card, bg=CARD_BG)
        profile_details.pack(side="left", fill="both", expand=True, pady=20)
        display_name = (
            self.get_row_field(listener_info, "Username", None)
            or self.get_row_field(listener_info, "Name", None)
            or "BBC Sounds listener"
        )
        self.create_label(profile_details, "YOUR PROFILE", 8, ORANGE_HL, "bold").pack(anchor="w", pady=(3, 5))
        self.create_label(profile_details, str(display_name), 19, TEXT_WHITE, "bold").pack(anchor="w")
        self.create_label(profile_details, f"Listener ID  ·  {self.current_user}", 10, TEXT_GRAY).pack(
            anchor="w", pady=(7, 0)
        )

        genres_str = str(self.get_row_field(listener_info, "FavoriteGenres", "") or "")
        length_str = self.get_row_field(listener_info, "LengthPreference", "") or "Not selected"
        survey_done = bool(self.get_row_field(listener_info, "CompleteSurvey", 0))

        self.render_section_title(page, "Listening preferences", "Survey status: " + ("complete" if survey_done else "not completed"))
        pref_card = self.create_card_frame(page)
        pref_card.pack(fill="x", pady=5)
        pref_card.grid_columnconfigure(0, weight=1, uniform="profile-preference")
        pref_card.grid_columnconfigure(1, weight=1, uniform="profile-preference")
        genres_panel = tk.Frame(pref_card, bg=CARD_BG)
        genres_panel.grid(row=0, column=0, sticky="nsew", padx=(18, 12), pady=17)
        length_panel = tk.Frame(pref_card, bg=CARD_BG)
        length_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 18), pady=17)
        self.create_label(genres_panel, "FAVOURITE GENRES", 9, TEXT_GRAY, "bold").pack(anchor="center")
        self.create_label(
            genres_panel, genres_str.replace(",", "  ·  ") if genres_str else "None selected",
            13, TEXT_WHITE, "bold", anchor="center", justify="center", wraplength=480,
        ).pack(fill="x", pady=(6, 0))
        self.create_label(length_panel, "PREFERRED EPISODE LENGTH", 9, TEXT_GRAY, "bold").pack(anchor="center")
        self.create_label(length_panel, length_str, 13, TEXT_WHITE, "bold", anchor="center").pack(fill="x", pady=(6, 0))
        profile_actions = tk.Frame(page, bg=DARK_BG)
        profile_actions.pack(pady=8)
        self.create_button(
            profile_actions, "Edit survey answers",
            lambda: self.transition_to(self.show_preferences, "Profile", direction=1), primary=True,
        ).pack(side="left")
        if survey_done:
            self.create_button(profile_actions, "Reset survey", self.reset_survey, compact=True).pack(side="left", padx=(9, 0))

        # Accessibility settings section for adjusting text size, theme, and resetting defaults.
        self.render_section_title(
            page, "Accessibility settings",
            "Adjust text size and switch between Dark, Light, and High contrast themes.",
        )
        access_card = self.create_card_frame(page)
        access_card.pack(fill="x", pady=5)
        access_row = tk.Frame(access_card, bg=CARD_BG)
        access_row.pack(fill="x", padx=18, pady=16)

        size_info = tk.Frame(access_row, bg=CARD_BG)
        size_info.pack(side="left", fill="x", expand=True)
        self.create_label(size_info, "TEXT SIZE", 9, TEXT_GRAY, "bold").pack(anchor="w")
        size_status_label = self.create_label(size_info, "", 13, TEXT_WHITE, "bold")
        size_status_label.pack(anchor="w", pady=(4, 0))

        size_controls = tk.Frame(access_row, bg=CARD_BG)
        size_controls.pack(side="right")

        # Divider and Theme selector row inside the same Accessibility settings card.
        tk.Frame(access_card, bg=BORDER_LINE, height=1).pack(fill="x", padx=18)
        theme_row = tk.Frame(access_card, bg=CARD_BG)
        theme_row.pack(fill="x", padx=18, pady=16)

        theme_labels = {
            "dark": "Dark  ·  Default",
            "light": "Light",
            "high_contrast": "High contrast",
        }
        active_theme = getattr(self, "_theme_name", "dark")

        theme_info = tk.Frame(theme_row, bg=CARD_BG)
        theme_info.pack(side="left", fill="x", expand=True)
        self.create_label(theme_info, "APPEARANCE THEME", 9, TEXT_GRAY, "bold").pack(anchor="w")
        self.create_label(
            theme_info, theme_labels.get(active_theme, "Dark  ·  Default"), 13, TEXT_WHITE, "bold",
        ).pack(anchor="w", pady=(4, 0))

        theme_controls = tk.Frame(theme_row, bg=CARD_BG)
        theme_controls.pack(side="right")
        for theme_key, theme_caption in (("dark", "Dark"), ("light", "Light"), ("high_contrast", "High contrast")):
            is_selected = active_theme == theme_key
            self.create_button(
                theme_controls,
                theme_caption,
                lambda key=theme_key: self.set_theme(key),
                primary=is_selected,
                compact=True,
            ).pack(side="left", padx=(0 if theme_key == "dark" else 8, 0))

        def format_text_scale_label(scale_val):
            pct = round(scale_val * 100)
            if pct == 100:
                return "100%  ·  Default"
            return f"{pct}%  ·  {'Larger' if pct > 100 else 'Smaller'}"

        def refresh_accessibility_controls():
            scale_val = getattr(self, "_text_scale", 1.0)
            cur_theme = getattr(self, "_theme_name", "dark")
            size_status_label.configure(text=format_text_scale_label(scale_val))
            smaller_btn.configure(state="disabled" if scale_val <= 0.805 else "normal")
            larger_btn.configure(state="disabled" if scale_val >= 1.395 else "normal")
            at_defaults = abs(scale_val - 1.0) < 0.005 and cur_theme == "dark"
            reset_access_btn.configure(state="disabled" if at_defaults else "normal")

        def on_adjust_text(delta):
            self.adjust_text_scale(delta)
            refresh_accessibility_controls()

        def on_reset_accessibility():
            self.reset_accessibility_settings()
            if size_status_label.winfo_exists():
                refresh_accessibility_controls()

        smaller_btn = self.create_button(
            size_controls, "A−  Smaller", lambda: on_adjust_text(-0.10), compact=True,
        )
        smaller_btn.pack(side="left", padx=(0, 8))
        larger_btn = self.create_button(
            size_controls, "A+  Larger", lambda: on_adjust_text(0.10), primary=True, compact=True,
        )
        larger_btn.pack(side="left", padx=(0, 8))
        reset_access_btn = self.create_button(
            size_controls, "Reset accessibility settings", on_reset_accessibility, compact=True,
        )
        reset_access_btn.pack(side="left")
        refresh_accessibility_controls()

    def show_preferences(self):
        """Render the interactive preference survey to pick up to 5 genres and episode length."""
        listener_row = self.get_listener_data()
        saved_genres = [
            item.strip() for item in str(self.get_row_field(listener_row, "FavoriteGenres", "") or "").split(",")
            if item.strip()
        ]
        self.active_genres = list(dict.fromkeys(saved_genres))[:5]
        stored_length = self.get_row_field(listener_row, "LengthPreference", "Medium") or "Medium"
        self.active_length = stored_length if stored_length in DURATION_RANGES else "Medium"
        page = self.build_shell("Your genres")
        self.render_page_title(page, "Build your listening profile", "Choose up to five genres and an episode length.")
        self.create_label(page, "FAVOURITE GENRES", 9, TEXT_GRAY, "bold").pack(anchor="w", pady=(8, 7))
        counter_label = self.create_label(page, "0 / 5 selected", 9, ORANGE_HL)
        counter_label.pack(anchor="e", pady=(0, 4))
        grid_frame = tk.Frame(page, bg=DARK_BG)
        grid_frame.pack(fill="x")
        self.genre_elements = {}
        genre_tiles = []
        for idx, g_name in enumerate(GENRE_LIST):
            tile = self.create_card_frame(grid_frame, cursor="hand2")
            art_cnv = self.create_genre_circle(tile, g_name, idx, 54, CARD_BG)
            art_cnv.pack(pady=(9, 3))
            check_lbl = self.create_label(tile, g_name, 9, TEXT_WHITE, "bold", anchor="center", bg=CARD_BG)
            check_lbl.pack(fill="x", padx=3, pady=(0, 9))
            for sub_widget in (tile, *tile.winfo_children()):
                sub_widget.bind("<Button-1>", lambda _e, name_val=g_name: self.toggle_genre_selection(name_val, counter_label))
            self.genre_elements[g_name] = (tile, check_lbl, art_cnv)
            genre_tiles.append(tile)

        current_genre_columns = [0]

        def reflow_genre_tiles(_event=None):
            available_width = grid_frame.winfo_width()
            if available_width <= 1:
                available_width = max(1, self.winfo_width() - 110)
            column_count = max(3, min(6, available_width // 245))
            if column_count == current_genre_columns[0] and _event is not None:
                return
            current_genre_columns[0] = column_count
            for column_idx in range(6):
                grid_frame.grid_columnconfigure(
                    column_idx, weight=1 if column_idx < column_count else 0,
                    uniform="genre-options" if column_idx < column_count else "",
                )
            for tile_idx, tile_widget in enumerate(genre_tiles):
                tile_widget.grid(
                    row=tile_idx // column_count, column=tile_idx % column_count,
                    sticky="nsew", padx=5, pady=5,
                )

        grid_frame.bind("<Configure>", reflow_genre_tiles)
        reflow_genre_tiles()

        self.update_genre_tile_styles(counter_label)
        self.render_section_title(page, "Episode length", "Pick the average episode length you enjoy most.")
        length_row = tk.Frame(page, bg=DARK_BG)
        length_row.pack(fill="x", pady=(0, 8))
        self.length_buttons = {}
        for choice_val in ("Short", "Medium", "Long"):
            btn = self.create_button(length_row, choice_val + " episodes", lambda val=choice_val: self.set_length_preference(val), compact=False)
            btn.pack(side="left", fill="x", expand=True, padx=5)
            self.length_buttons[choice_val] = btn
        self.update_length_button_styles()
        footer_pane = tk.Frame(page, bg=DARK_BG)
        footer_pane.pack(pady=(15, 18))
        self.create_button(footer_pane, "Save preferences", self.save_user_preferences, primary=True).pack(side="left")
        self.create_button(
            footer_pane, "Cancel",
            lambda: self.transition_to(self.show_home, "Home"), compact=True,
        ).pack(side="left", padx=9)

    def toggle_genre_selection(self, genre_name, counter_lbl):
        """Toggle a genre on or off in active_genres, enforcing the 5-genre cap."""
        if genre_name in self.active_genres:
            self.active_genres.remove(genre_name)
        elif len(self.active_genres) >= 5:
            messagebox.showinfo("Five genre limit", "Choose up to five favourite genres.", parent=self)
            return
        else:
            self.active_genres.append(genre_name)
        self.update_genre_tile_styles(counter_lbl)

    def update_genre_tile_styles(self, counter_lbl=None):
        """Highlight selected genre tiles and update the selected count indicator."""
        if counter_lbl and counter_lbl.winfo_exists():
            counter_lbl.config(text=f"{len(self.active_genres)} / 5 selected")
        for name, (tile, lbl, circle) in getattr(self, "genre_elements", {}).items():
            is_active = name in self.active_genres
            background_color = SELECTED_BG if is_active else CARD_BG
            tile.set_surface(background_color, ORANGE_ACCENT if is_active else BORDER_LINE)
            lbl.configure(bg=background_color, fg=ORANGE_HL if is_active else TEXT_WHITE)
            circle.configure(bg=background_color)
            for child in tile.winfo_children():
                if isinstance(child, tk.Label) and child is not lbl:
                    child.configure(bg=background_color)

    def set_length_preference(self, choice_val):
        """Select the active episode-length preference and refresh button highlights."""
        self.active_length = choice_val
        self.update_length_button_styles()

    def update_length_button_styles(self):
        """Update visual styles for the Short / Medium / Long episode-length buttons."""
        for val_key, button_obj in getattr(self, "length_buttons", {}).items():
            active_flag = val_key == self.active_length
            fg_colour = PRIMARY_BTN_FG if active_flag else TEXT_LIGHT
            button_obj._hover_base_fg = fg_colour
            button_obj._hover_target_fg = PRIMARY_BTN_FG if active_flag else SECONDARY_HOVER_FG
            button_obj.configure(fg=fg_colour)
            self.style_rounded_button(
                button_obj, ORANGE_ACCENT if active_flag else INPUT_BG,
                ORANGE_HL if active_flag else SECONDARY_HOVER_BG,
            )

    def save_user_preferences(self):
        """Persist the selected genres and episode-length preference to SQLite."""
        # Require at least one genre before saving so the For You recommendations query is non-empty.
        if not self.active_genres:
            messagebox.showinfo("Choose a genre", "Select at least one favourite genre to continue.", parent=self)
            return
        try:
            # Mark CompleteSurvey = 1 and store genres as a comma-separated string.
            with self.get_db_connection() as conn:
                conn.execute(
                    "UPDATE listeners SET CompleteSurvey = 1, FavoriteGenres = ?, LengthPreference = ? "
                    "WHERE ListenerID = ?",
                    (",".join(self.active_genres), self.active_length, self.current_user),
                )
            # Navigate straight to the newly personalised "For you" tab.
            self.transition_to(self.show_recommendations, "For you")
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save your preferences", err)

    def reset_survey(self):
        """Clear the listener's saved survey answers and refresh the Profile page."""
        if not messagebox.askyesno("Reset survey", "Clear your favourite genres and episode-length preference?", parent=self):
            return
        try:
            # Reset CompleteSurvey to 0 and clear FavoriteGenres and LengthPreference in SQLite.
            with self.get_db_connection() as conn:
                conn.execute(
                    "UPDATE listeners SET CompleteSurvey = 0, FavoriteGenres = '', LengthPreference = NULL "
                    "WHERE ListenerID = ?", (self.current_user,),
                )
            self.active_genres = []
            self.show_profile()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't reset the survey", err)
