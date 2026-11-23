"""Application pages: Home, Genres/Search, For you, Favourites, History, Ratings, Report, Profile, and Survey."""
import sqlite3
import sys
from time import monotonic
import tkinter as tk
from tkinter import messagebox

from gui_parts.i18n import translate
from gui_parts.theme import (
    BANNER_BG,
    BORDER_LINE,
    CARD_BG,
    DARK_BG,
    DEFAULT_FONT,
    DURATION_RANGES,
    GENRE_GRADIENTS,
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
            name_str = self.get_row_field(listener_info, "Name", None) or self.get_row_field(listener_info, "Username", None)
            clean_name = str(name_str or "").strip()
            greeting = f"Good to have you back, {clean_name}!" if clean_name else "Good to have you back!"
            self.render_page_title(page, greeting,
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
                    "p.Title COLLATE NOCASE LIMIT 16",
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
            self.create_label(banner_text, hint_msg, 10, TEXT_GRAY, wraplength=520).pack(anchor="w", pady=(5, 0))
            self.create_button(
                banner_card, "Explore programmes  →",
                lambda: self.transition_to(self.show_search, "Genres"),
                primary=True, compact=True,
            ).pack(side="right", padx=18, pady=12)

            rec_list = self.get_custom_recommendations(16)
            if rec_list:
                self.render_section_title(
                    page, "Made for you", "A match for your favourite genres and episode length.",
                    "See all", lambda: self.transition_to(self.show_recommendations, "For you"),
                )
                self.render_podcast_grid(
                    page, rec_list, columns_count=6, show_play=True,
                    max_count=16, single_row=True,
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
                    lambda: self.transition_to(self.show_preferences, "Settings"),
                    primary=True, compact=True,
                ).pack(anchor="w", padx=17, pady=(0, 15))

            if history_rows:
                self.render_section_title(
                    page, "Pick up where you left off", "Your most played programmes.",
                    "Listening history", lambda: self.transition_to(self.show_history, "History"),
                )
                self.render_podcast_grid(
                    page, history_rows, columns_count=6, show_play=True,
                    max_count=16, single_row=True,
                )
            else:
                self.render_section_title(page, "Explore the catalogue")
                self.render_podcast_grid(
                    page, self.query_podcasts(item_limit=16), columns_count=6,
                    show_play=True, max_count=16, single_row=True,
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
                normalized_q = " ".join(search_term.lower().split())
                egg_specs = {
                    "snake": (
                        "BBC Sounds Snake",
                        "Activate the easter egg, then click all three letters of \"BBC\" (B, B, and C) in the top-left logo within 2 seconds to launch Snake.",
                        "Activated! Click all three letters of \"BBC\" (B, B, and C) in the top-left logo within 2 seconds to launch Snake.",
                    ),
                    "memory": (
                        "BBC Sounds Card Match",
                        "Activate the easter egg, then click all three letters of \"BBC\" (B, B, and C) in the top-left logo within 2 seconds to launch Card Match.",
                        "Activated! Click all three letters of \"BBC\" (B, B, and C) in the top-left logo within 2 seconds to launch Card Match.",
                    ),
                    "flappy": (
                        "BBC Sounds Flappy Bird",
                        "Activate the easter egg, then click all three letters of \"BBC\" (B, B, and C) in the top-left logo within 2 seconds to launch Flappy Bird.",
                        "Activated! Click all three letters of \"BBC\" (B, B, and C) in the top-left logo within 2 seconds to launch Flappy Bird.",
                    ),
                }
                egg_key = (
                    "snake" if normalized_q in ("snake game", "snake")
                    else "memory" if normalized_q in ("match cards", "card match", "memory", "memory game", "matching cards")
                    else "flappy" if normalized_q in ("flappy bird", "flappy", "flappy game")
                    else None
                )
                if egg_key is not None:
                    egg_title, desc_idle, desc_armed = egg_specs[egg_key]
                    egg_card = self.create_card_frame(results_pane, bg=BANNER_BG)
                    egg_card.pack(fill="x", pady=(10, 12))
                    tk.Frame(egg_card, bg=ORANGE_ACCENT, width=4).pack(side="left", fill="y")
                    egg_body = tk.Frame(egg_card, bg=BANNER_BG)
                    egg_body.pack(side="left", fill="both", expand=True, padx=18, pady=16)
                    self.create_label(egg_body, "SECRET EASTER EGG", 8, ORANGE_HL, "bold", bg=BANNER_BG).pack(anchor="w")
                    self.create_label(
                        egg_body, egg_title, 15, TEXT_WHITE, "bold", bg=BANNER_BG,
                    ).pack(anchor="w", pady=(4, 6))
                    already_armed = getattr(self, "_armed_easter_egg", None) == egg_key
                    egg_desc = self.create_label(
                        egg_body,
                        desc_armed if already_armed else desc_idle,
                        10, TEXT_LIGHT, bg=BANNER_BG, wraplength=620,
                    )
                    egg_desc.pack(anchor="w")

                    def activate_egg(target_key=egg_key, armed_text=desc_armed):
                        self._armed_easter_egg = target_key
                        if egg_btn.winfo_exists():
                            egg_btn.configure(text=translate("Easter egg activated ✓"), state="disabled")
                            self.style_rounded_button(egg_btn, INPUT_BG, BORDER_LINE)
                        if egg_desc.winfo_exists():
                            egg_desc.configure(text=translate(armed_text))

                    egg_btn = self.create_button(
                        egg_card,
                        "Easter egg activated ✓" if already_armed else "Activate easter egg",
                        activate_egg,
                        primary=not already_armed,
                        compact=True,
                    )
                    if already_armed:
                        egg_btn.configure(state="disabled")
                    egg_btn.pack(side="right", padx=18, pady=16)
                    last_search = search_term
                    return

                order_cache = getattr(self, "_tab_podcast_order_cache", None)
                if order_cache is None:
                    order_cache = {}
                    self._tab_podcast_order_cache = order_cache
                search_cache_key = ("search", self.current_user, search_term)
                matching_rows = order_cache.get(search_cache_key)
                if matching_rows is None:
                    matching_rows = self.query_podcasts(search_term, item_limit=80, shuffle=True)
                    order_cache[search_cache_key] = matching_rows
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

            import math as _math
            grad_cache = getattr(self, "_genre_grad_cache", None)
            if grad_cache is None:
                from collections import OrderedDict
                grad_cache = OrderedDict()
                self._genre_grad_cache = grad_cache

            def make_gradient_card_photo(width, height, top_hex, bot_hex, border_hex, bg_hex, inset=3):
                """Rasterize and cache a smooth vertical-gradient rounded card as a PPM PhotoImage."""
                w = max(16, int(width))
                h = max(16, int(height))
                cache_key = (w, h, top_hex, bot_hex, border_hex, bg_hex, inset)
                cached = grad_cache.get(cache_key)
                if cached is not None:
                    grad_cache.move_to_end(cache_key)
                    return cached

                m = 1 + inset
                left, top = m, m
                right, bottom = max(left + 4, w - 1 - inset), max(top + 4, h - 1 - inset)
                cw, ch = right - left, bottom - top
                r = min(12, cw // 2, ch // 2)

                bg_b = bytes.fromhex(bg_hex[1:])
                bd_b = bytes.fromhex(border_hex[1:])
                t_rgb = tuple(int(top_hex[p:p + 2], 16) for p in (1, 3, 5))
                b_rgb = tuple(int(bot_hex[p:p + 2], 16) for p in (1, 3, 5))

                pixels = bytearray(f"P6\n{w} {h}\n255\n".encode("ascii"))
                full_bg_row = bg_b * w
                denom = max(1, ch - 1)
                for y in range(h):
                    if y < top or y >= bottom:
                        pixels.extend(full_bg_row)
                        continue
                    ly = y - top
                    frac = ly / denom
                    fill_b = bytes((
                        round(t_rgb[0] + (b_rgb[0] - t_rgb[0]) * frac),
                        round(t_rgb[1] + (b_rgb[1] - t_rgb[1]) * frac),
                        round(t_rgb[2] + (b_rgb[2] - t_rgb[2]) * frac),
                    ))
                    if ly < r:
                        dy = r - ly
                        dx = r - _math.isqrt(max(0, r * r - dy * dy))
                    elif ly >= ch - r:
                        dy = ly - (ch - r - 1)
                        dx = r - _math.isqrt(max(0, r * r - dy * dy))
                    else:
                        dx = 0
                    x0 = left + dx
                    x1 = right - dx
                    if x1 <= x0:
                        pixels.extend(full_bg_row)
                        continue
                    row = bytearray(full_bg_row)
                    if ly == 0 or ly == ch - 1:
                        row[x0 * 3:x1 * 3] = bd_b * (x1 - x0)
                    else:
                        row[x0 * 3:(x0 + 1) * 3] = bd_b
                        if x1 - x0 > 2:
                            row[(x0 + 1) * 3:(x1 - 1) * 3] = fill_b * (x1 - x0 - 2)
                        row[(x1 - 1) * 3:x1 * 3] = bd_b
                    pixels.extend(row)
                photo = tk.PhotoImage(master=self, data=bytes(pixels), format="PPM")
                grad_cache[cache_key] = photo
                if len(grad_cache) > 192:
                    grad_cache.popitem(last=False)
                return photo

            is_light_mode = getattr(self, "_theme_name", "dark") == "light"
            card_title_fg = "#ffffff"
            card_desc_fg = "#f4f6f9" if is_light_mode else "#f0f0f0"
            card_act_hover_fg = "#fff1a8" if is_light_mode else GOLD_STAR

            for idx, category_name in enumerate(all_categories):
                tile_colour, tile_icon, tile_description = GENRE_TILE_DETAILS.get(
                    category_name,
                    (
                        PALETTE_SWATCHES[idx % len(PALETTE_SWATCHES)],
                        category_name[:1].upper(),
                        f"Explore {category_name.lower()} shows and stories",
                    ),
                )
                top_col, bot_col, accent_col = GENRE_GRADIENTS.get(
                    category_name,
                    (
                        blend_colour(tile_colour, "#ffffff", 0.14),
                        blend_colour(tile_colour, "#000000", 0.45),
                        ORANGE_HL,
                    ),
                )
                if is_light_mode:
                    # Lift dark gradients into richer, brighter mid-tones that pop cleanly on a light page.
                    top_col = blend_colour(top_col, accent_col, 0.24)
                    bot_col = blend_colour(bot_col, top_col, 0.42)
                    ico_base_bg = "#ffffff"
                    ico_hover_bg = blend_colour("#ffffff", accent_col, 0.22)
                    ico_txt_fg = blend_colour(bot_col, "#000000", 0.25)
                    border_base = blend_colour(bot_col, BORDER_LINE, 0.35)
                else:
                    ico_base_bg = "#17181b"
                    ico_hover_bg = accent_col
                    ico_txt_fg = "#ffffff"
                    border_base = BORDER_LINE

                card_canvas = tk.Canvas(
                    category_row, bg=DARK_BG, height=166, bd=0,
                    highlightthickness=0, cursor="hand2",
                )
                card_canvas.grid(
                    row=idx // columns_count, column=idx % columns_count,
                    sticky="nsew", padx=5, pady=5,
                )

                bg_item = card_canvas.create_image(0, 0, anchor="nw")
                accent_item = card_canvas.create_rectangle(0, 0, 0, 0, fill=accent_col, outline="")
                ico_bg_item = card_canvas.create_rectangle(0, 0, 0, 0, fill=ico_base_bg, outline="")
                ico_txt_item = card_canvas.create_text(
                    0, 0, text=tile_icon, fill=ico_txt_fg,
                    font=(DEFAULT_FONT, 14, "bold"), anchor="center",
                )
                title_item = card_canvas.create_text(
                    0, 0, text=translate(category_name.upper()), fill=card_title_fg,
                    font=(DEFAULT_FONT, 11, "bold"), anchor="w",
                )
                desc_item = card_canvas.create_text(
                    0, 0, text=translate(tile_description), fill=card_desc_fg,
                    font=(DEFAULT_FONT, 9), anchor="nw", justify="left", width=225,
                )
                act_item = card_canvas.create_text(
                    0, 0, text=translate("BROWSE PROGRAMMES  →"), fill="#ffffff",
                    font=(DEFAULT_FONT, 8, "bold"), anchor="sw",
                )

                hi_top = blend_colour(top_col, "#ffffff", 0.14 if is_light_mode else 0.16)
                hi_bot = blend_colour(bot_col, "#ffffff", 0.14 if is_light_mode else 0.16)
                card_state = {"step": 0, "target": 0, "job": None, "cfg_job": None, "w": 0, "h": 0, "cache": {}}

                def paint_gradient_card(
                    cvs=card_canvas,
                    state=card_state,
                    t_base=top_col,
                    b_base=bot_col,
                    t_hi=hi_top,
                    b_hi=hi_bot,
                    acc=accent_col,
                    ib_base=ico_base_bg,
                    ib_hi=ico_hover_bg,
                    bd_base=border_base,
                    act_hi=card_act_hover_fg,
                    bi=bg_item,
                    ai=accent_item,
                    ib=ico_bg_item,
                    it=ico_txt_item,
                    ti=title_item,
                    di=desc_item,
                    acti=act_item,
                ):
                    if not cvs.winfo_exists():
                        return
                    w = cvs.winfo_width()
                    h = cvs.winfo_height()
                    if w <= 4 or h <= 4:
                        return
                    if w != state["w"] or h != state["h"]:
                        state["w"] = w
                        state["h"] = h
                        state["cache"].clear()

                    step = state["step"]
                    t = step / 10.0
                    raw_eased = ease_out_elastic(t, damping=3.0, frequency=1.65) if state["target"] > 0 else 1.0 - (1.0 - t) ** 2.4
                    # Quantize colour blend to 4 shared levels while preserving full elastic pop-out overshoot for inset.
                    level = max(0, min(3, round(max(0.0, min(1.0, raw_eased)) * 3.0)))
                    eased = level / 3.0
                    inset = max(0, min(5, round(5.0 - 3.0 * raw_eased)))
                    cur_top = blend_colour(t_base, t_hi, eased)
                    cur_bot = blend_colour(b_base, b_hi, eased)
                    cur_border = blend_colour(bd_base, acc, eased)
                    cur_ico_bg = blend_colour(ib_base, ib_hi, eased)
                    cur_act_fg = blend_colour("#ffffff", act_hi, eased)

                    cache_key = (level, inset)
                    photo = state["cache"].get(cache_key)
                    if photo is None:
                        photo = make_gradient_card_photo(w, h, cur_top, cur_bot, cur_border, DARK_BG, inset=inset)
                        state["cache"][cache_key] = photo
                    cvs._grad_img = photo
                    cvs.itemconfigure(bi, image=photo)

                    m = 1 + inset
                    cvs.coords(ai, m + 12, m + 3, max(m + 14, w - m - 12), m + 6)
                    cvs.coords(ib, m + 15, m + 18, m + 53, m + 50)
                    cvs.itemconfigure(ib, fill=cur_ico_bg)
                    cvs.coords(it, m + 34, m + 34)
                    cvs.coords(ti, m + 65, m + 34)
                    cvs.coords(di, m + 15, m + 62)
                    cvs.itemconfigure(di, width=max(120, w - 2 * m - 30))
                    cvs.coords(acti, m + 15, h - m - 14)
                    cvs.itemconfigure(acti, fill=cur_act_fg)

                def cancel_card_hover(state=card_state):
                    for jkey in ("job", "cfg_job"):
                        if state[jkey] is not None:
                            try:
                                self.after_cancel(state[jkey])
                            except tk.TclError:
                                pass
                            state[jkey] = None

                def schedule_card_paint(_event=None, state=card_state, cvs=card_canvas, paint_fn=paint_gradient_card):
                    # First paint runs immediately; subsequent resizes debounce 45ms to avoid rasterizing on every pixel.
                    if state["w"] == 0:
                        paint_fn()
                        return
                    if state["cfg_job"] is not None:
                        try:
                            self.after_cancel(state["cfg_job"])
                        except tk.TclError:
                            pass
                    state["cfg_job"] = self.after(45, lambda: (state.__setitem__("cfg_job", None), paint_fn()))

                def animate_card_hover(target, state=card_state, cvs=card_canvas, paint_fn=paint_gradient_card):
                    if not cvs.winfo_exists():
                        return
                    state["target"] = target
                    if self._is_reduced_motion():
                        if state["job"] is not None:
                            try:
                                self.after_cancel(state["job"])
                            except tk.TclError:
                                pass
                            state["job"] = None
                        if state["step"] != target:
                            state["step"] = target
                            paint_fn()
                        return
                    if state["job"] is not None:
                        return

                    def step_card():
                        state["job"] = None
                        if not cvs.winfo_exists() or getattr(self, "_transition_active", False):
                            return
                        if state["target"] > 0 and self._is_scrolling():
                            return
                        cur = state["step"]
                        tgt = state["target"]
                        if cur == tgt:
                            return
                        cur += 1 if tgt > cur else -1
                        state["step"] = cur
                        paint_fn()
                        if cur != tgt:
                            state["job"] = self.after(self._anim_frame_interval(16), step_card)

                    step_card()

                def open_genre(
                    _event=None,
                    card=card_canvas,
                    name=category_name,
                    icon=tile_icon,
                    desc=tile_description,
                    base_col=top_col,
                    hi_col=hi_top,
                    state=card_state,
                    cancel_fn=cancel_card_hover,
                ):
                    cancel_fn()
                    t = state["step"] / 10.0
                    start_col = blend_colour(base_col, hi_col, 1.0 - (1.0 - t) ** 2)
                    self.expand_genre_in_tab(
                        card, name, icon, desc, start_col,
                        lambda: (self.search_text.set(name), perform_search_action()),
                        programmes_heading, page,
                    )

                card_canvas.bind("<Configure>", schedule_card_paint)
                card_canvas.bind("<Enter>", lambda _e, anim_fn=animate_card_hover: anim_fn(10))
                card_canvas.bind("<Leave>", lambda _e, anim_fn=animate_card_hover: anim_fn(0))
                card_canvas.bind("<Button-1>", open_genre)
                card_canvas.bind("<Destroy>", lambda _e, cancel_fn=cancel_card_hover: cancel_fn())
        except sqlite3.Error as err:
            self.show_db_error("Couldn't load categories", err)

        programmes_heading = self.render_section_title(page, "Programmes")
        results_pane.pack(fill="both", expand=True)
        perform_search_action()

    def expand_genre_in_tab(self, card, genre_name, genre_icon, genre_desc, start_col, apply_filter, heading_widget, page):
        """Expand a clicked genre tile within the Genres content area and scroll to its programmes."""
        if self._is_busy_transitioning():
            return
        canvas_pane, _window = self._page_transition_target
        area_frame = canvas_pane.master
        if getattr(area_frame, "_expanding_genre", False) or not area_frame.winfo_exists() or not card.winfo_exists():
            return
        area_frame._expanding_genre = True
        self._transition_active = True

        start_x = card.winfo_rootx() - area_frame.winfo_rootx()
        start_y = card.winfo_rooty() - area_frame.winfo_rooty()
        start_w = max(1, card.winfo_width())
        start_h = max(1, card.winfo_height())
        target_w = max(1, area_frame.winfo_width())
        target_h = max(1, area_frame.winfo_height())

        if target_w <= 1 or target_h <= 1 or self._is_reduced_motion():
            area_frame._expanding_genre = False
            self._finish_transition()
            apply_filter()
            if canvas_pane.winfo_exists() and heading_widget.winfo_exists() and page.winfo_exists():
                self.update_idletasks()
                region = canvas_pane.cget("scrollregion")
                if region:
                    total_h = int(float(region.split()[3]))
                    if total_h > 0:
                        offset = heading_widget.winfo_rooty() - page.winfo_rooty()
                        canvas_pane.yview_moveto(max(0.0, min(1.0, (offset - 12) / total_h)))
            return

        is_light_mode = getattr(self, "_theme_name", "dark") == "light"
        badge_bg = "#ffffff" if is_light_mode else ORANGE_ACCENT
        badge_fg = blend_colour(start_col, "#000000", 0.20) if is_light_mode else "#ffffff"
        overlay_title_fg = "#ffffff"
        overlay_desc_fg = "#f4f6f9" if is_light_mode else "#f0f0f0"

        expander = tk.Frame(area_frame, bg=start_col, bd=0, highlightthickness=0)
        accent_top = tk.Frame(expander, bg=ORANGE_HL, height=3)
        accent_top.pack(fill="x")
        preview_box = tk.Frame(expander, bg=start_col)
        preview_box.place(relx=0.5, rely=0.5, anchor="center")
        icon_badge = tk.Label(
            preview_box, text=genre_icon, width=3, height=1,
            font=(DEFAULT_FONT, 18, "bold"), bg=badge_bg, fg=badge_fg,
        )
        icon_badge.pack(pady=(0, 8))
        title_lbl = self.create_label(
            preview_box, genre_name.upper(), 24, overlay_title_fg, "bold",
            anchor="center", bg=start_col,
        )
        title_lbl.pack()
        desc_lbl = self.create_label(
            preview_box, genre_desc, 11, overlay_desc_fg,
            anchor="center", justify="center", bg=start_col,
        )
        desc_lbl.pack(pady=(6, 0))

        expander.place(x=start_x, y=start_y, width=start_w, height=start_h)
        tk.Misc.lift(expander)

        expand_duration = 0.240
        expand_st = {"progress": 0.0, "last_t": None}
        last_colors = [(start_col, overlay_title_fg, overlay_desc_fg, badge_bg, badge_fg)]
        last_rect = [None]

        def start_reveal():
            if not expander.winfo_exists() or not area_frame.winfo_exists():
                area_frame._expanding_genre = False
                self._finish_transition()
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

            reveal_duration = 0.210
            reveal_st = {"progress": 0.0, "last_t": None}
            last_y = [0]

            def draw_reveal():
                if not expander.winfo_exists() or not area_frame.winfo_exists():
                    area_frame._expanding_genre = False
                    self._finish_transition()
                    return
                t0 = monotonic()
                dt = 0.016 if reveal_st["last_t"] is None else max(0.004, min(0.042, t0 - reveal_st["last_t"]))
                reveal_st["last_t"] = t0
                reveal_st["progress"] = min(1.0, reveal_st["progress"] + dt / reveal_duration)
                progress = reveal_st["progress"]
                eased = 1.0 - (1.0 - progress) ** 3
                cur_y = round(-target_h * eased)
                if cur_y != last_y[0]:
                    expander.place(x=0, y=cur_y, width=target_w, height=target_h)
                    last_y[0] = cur_y
                if progress < 1.0:
                    spent = (monotonic() - t0) * 1000.0
                    self.after(self._next_frame_delay(spent, 16), draw_reveal)
                else:
                    expander.destroy()
                    area_frame._expanding_genre = False
                    self._finish_transition()

            self.after(1, draw_reveal)

        def draw_expand():
            if not expander.winfo_exists() or not area_frame.winfo_exists():
                area_frame._expanding_genre = False
                self._finish_transition()
                return
            t0 = monotonic()
            dt = 0.016 if expand_st["last_t"] is None else max(0.004, min(0.042, t0 - expand_st["last_t"]))
            expand_st["last_t"] = t0
            expand_st["progress"] = min(1.0, expand_st["progress"] + dt / expand_duration)
            progress = expand_st["progress"]
            eased = 1.0 - (1.0 - progress) ** 3 if sys.platform != "win32" else ease_out_elastic(progress, damping=5.8, frequency=1.05)
            cur_x = max(0, round(start_x * (1.0 - eased)))
            cur_y = max(0, round(start_y * (1.0 - eased)))
            cur_w = max(1, min(target_w, round(start_w + (target_w - start_w) * eased)))
            cur_h = max(1, min(target_h, round(start_h + (target_h - start_h) * eased)))

            if progress > 0.45:
                fade = (progress - 0.45) / 0.55
                cur_bg = blend_colour(start_col, DARK_BG, fade)
                cur_title_fg = blend_colour(overlay_title_fg, cur_bg, fade)
                cur_desc_fg = blend_colour(overlay_desc_fg, cur_bg, fade)
                cur_ico_bg = blend_colour(badge_bg, cur_bg, fade)
                cur_ico_fg = blend_colour(badge_fg, cur_bg, fade)
            else:
                cur_bg = start_col
                cur_title_fg = overlay_title_fg
                cur_desc_fg = overlay_desc_fg
                cur_ico_bg = badge_bg
                cur_ico_fg = badge_fg

            colors = (cur_bg, cur_title_fg, cur_desc_fg, cur_ico_bg, cur_ico_fg)
            if colors != last_colors[0]:
                expander.configure(bg=cur_bg)
                preview_box.configure(bg=cur_bg)
                title_lbl.configure(bg=cur_bg, fg=cur_title_fg)
                desc_lbl.configure(bg=cur_bg, fg=cur_desc_fg)
                icon_badge.configure(bg=cur_ico_bg, fg=cur_ico_fg)
                last_colors[0] = colors

            rect = (cur_x, cur_y, cur_w, cur_h)
            if rect != last_rect[0]:
                expander.place(x=cur_x, y=cur_y, width=cur_w, height=cur_h)
                last_rect[0] = rect

            if progress < 1.0:
                self.after(self._anim_frame_interval(16), draw_expand)
            else:
                # Brief hold at full expansion before sliding the curtain up to reveal programmes.
                self.after(80, start_reveal)

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
                lambda: self.transition_to(self.show_preferences, "Settings"), primary=True,
            ).pack(anchor="w", pady=7)
            self.render_section_title(page, "Explore the catalogue while you decide")
            order_cache = getattr(self, "_tab_podcast_order_cache", None)
            if order_cache is None:
                order_cache = {}
                self._tab_podcast_order_cache = order_cache
            fallback_key = ("for_you_fallback", self.current_user)
            fallback_rows = order_cache.get(fallback_key)
            if fallback_rows is None:
                fallback_rows = self.query_podcasts(item_limit=8, shuffle=True)
                order_cache[fallback_key] = fallback_rows
            self.render_podcast_grid(page, fallback_rows, show_play=True)
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
        # Keep the For You podcast order stable while opening/closing details; reshuffle only on tab change.
        order_cache = getattr(self, "_tab_podcast_order_cache", None)
        if order_cache is None:
            order_cache = {}
            self._tab_podcast_order_cache = order_cache
        recs_key = ("for_you_recs", self.current_user, genres_val, length_val)
        rec_results = order_cache.get(recs_key)
        if rec_results is None:
            rec_results = self.get_custom_recommendations(40, shuffle=True)
            order_cache[recs_key] = rec_results
        if rec_results:
            self.render_podcast_grid(page, rec_results, columns_count=6, show_play=True, max_count=40)
        else:
            self.render_empty_message(page, "No exact matches yet", "Try another genre or episode length to see more programmes.")
            self.create_button(
                page, "Edit preferences",
                lambda: self.transition_to(self.show_preferences, "Settings"), compact=True,
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
        hist_count = [len(history_rows)]
        hist_count_lbl = self.create_label(control_bar, f"{hist_count[0]} programmes", 10, TEXT_GRAY)
        hist_count_lbl.pack(side="left")

        def update_hist_count(delta):
            hist_count[0] = max(0, hist_count[0] + delta)
            if hist_count_lbl.winfo_exists():
                hist_count_lbl.configure(text=translate(f"{hist_count[0]} programmes"))

        self._active_count_updater = update_hist_count
        self.create_button(control_bar, "Clear history", self.clear_history, compact=True).pack(side="right")
        pending = getattr(self, "_pending_card_insert", None)
        insert_spec = pending if (pending and pending.get("mode") == "history") else None
        if insert_spec is not None:
            self._pending_card_insert = None
            target_pid = str(insert_spec["podcast_id"])
            history_rows = list(history_rows)
            for idx_h, row_h in enumerate(history_rows):
                if str(row_h[0]) == target_pid:
                    if idx_h != 0:
                        history_rows.insert(0, history_rows.pop(idx_h))
                    break
        self.render_podcast_grid(
            page, history_rows, columns_count=6,
            show_play=True, show_remove=True, max_count=len(history_rows),
            insert_anim=insert_spec,
        )

    def show_ratings(self):
        """Render the Ratings tab with paginated rated programme cards."""
        page = self.build_shell("Ratings")
        self.render_page_title(page, "Podcasts you rated", "Every programme you have scored is collected here.")
        rating_rows = self.fetch_user_ratings()
        pending = getattr(self, "_pending_card_insert", None)
        insert_spec = pending if (pending and pending.get("mode") == "ratings") else None
        if insert_spec is not None:
            self._pending_card_insert = None
            target_pid = str(insert_spec["podcast_id"])
            rating_rows = list(rating_rows)
            for idx_r, row_r in enumerate(rating_rows):
                if str(row_r[0]) == target_pid:
                    if idx_r != 0:
                        rating_rows.insert(0, rating_rows.pop(idx_r))
                    break
        if not rating_rows:
            self.render_empty_message(page, "No ratings yet", "Listen to a programme, then add a rating from its details page.")
            self.create_button(
                page, "Explore programmes",
                lambda: self.transition_to(self.show_search, "Genres"), primary=True, compact=True,
            ).pack(anchor="w", pady=6)
            return

        summary_bar = self.create_card_frame(page, bg=SUBCARD_BG)
        summary_bar.pack(fill="x", pady=(0, 12))
        rating_count = [len(rating_rows)]
        rating_count_lbl = self.create_label(summary_bar, str(rating_count[0]), 24, ORANGE_ACCENT, "bold")
        rating_count_lbl.pack(side="left", padx=(18, 8), pady=12)

        def update_rating_count(delta):
            rating_count[0] = max(0, rating_count[0] + delta)
            if rating_count_lbl.winfo_exists():
                rating_count_lbl.configure(text=str(rating_count[0]))

        self._active_count_updater = update_rating_count
        self.create_label(summary_bar, "ratings in your library", 10, TEXT_GRAY).pack(side="left", pady=18)
        self.create_label(summary_bar, "Select a programme to update or remove its score.", 10, TEXT_LIGHT).pack(
            side="right", padx=18, pady=18
        )

        self._active_ratings_insert_anim = insert_spec
        self.paginate_podcasts(page, rating_rows, self.render_ratings_page)

    def render_ratings_page(self, parent, rating_rows, last_page):
        """Render one page of responsive rated podcast cards on a single Canvas (zero child HWNDs)."""
        insert_spec = getattr(self, "_active_ratings_insert_anim", None)
        self._active_ratings_insert_anim = None
        self.render_podcast_grid(
            parent, rating_rows, max_count=len(rating_rows),
            rating_index=3, show_end=last_page, ratings_mode=True,
            insert_anim=insert_spec,
        )

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
                lambda: self.transition_to(self.show_preferences, "Settings", direction=1),
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
                lambda: self.transition_to(self.show_preferences, "Settings", direction=1), primary=True,
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
            highlight_card._cover_meta = [highlight_card, highlight_cover, top_programme[0], top_programme[1], top_programme[2], 128]
            highlight_details = tk.Frame(highlight_card, bg=CARD_BG)
            highlight_details.pack(side="left", fill="both", expand=True, pady=16)
            self.create_label(highlight_details, "MOST PLAYED", 8, ORANGE_ACCENT, "bold").pack(anchor="w", pady=(0, 5))
            highlight_title_lbl = self.create_label(highlight_details, top_programme[1], 16, TEXT_WHITE, "bold")
            highlight_title_lbl.pack(anchor="w")
            highlight_cover.bind(
                "<Button-1>",
                lambda _e, tid=top_programme[0], t=top_programme[1], c=top_programme[2], cf=highlight_card, cv=highlight_cover, tl=highlight_title_lbl:
                self.open_podcast_detail(tid, t, c, source_card=cf, source_cover=cv, source_title=tl),
            )
            self.create_label(
                highlight_details, f"{top_programme[4] or 0} plays  ·  {top_programme[2]}", 10, TEXT_GRAY,
            ).pack(anchor="w", pady=(5, 0))
            self.create_label(
                highlight_details, self.podcast_average_text(top_programme[0]), 9, GOLD_STAR,
            ).pack(anchor="w", pady=(4, 0))
            listen_again_btn = self.create_button(
                highlight_card, "▶  Listen again", lambda: None,
                primary=True, compact=True,
            )
            listen_again_btn.configure(
                command=lambda b=listen_again_btn, cv=highlight_cover, tid=top_programme[0], t=top_programme[1], c=top_programme[2]: (
                    self.play_podcast_to_mini_bar(b, tid, t, c, cover_widget=cv)
                )
            )
            listen_again_btn.pack(side="right", padx=18)
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
        profile_details.pack(side="left", fill="both", expand=True, pady=18, padx=(0, 20))
        saved_name = str(
            self.get_row_field(listener_info, "Name", None)
            or self.get_row_field(listener_info, "Username", None)
            or ""
        ).strip()
        self.create_label(profile_details, "YOUR PROFILE", 8, ORANGE_HL, "bold").pack(anchor="w", pady=(2, 4))
        name_heading_lbl = self.create_label(
            profile_details, saved_name or "BBC Sounds listener", 19, TEXT_WHITE, "bold",
        )
        name_heading_lbl.pack(anchor="w")
        self.create_label(profile_details, f"Listener ID  ·  {self.current_user}", 10, TEXT_GRAY).pack(
            anchor="w", pady=(5, 12)
        )

        # Inline display-name editor saved to listeners.Name in database.db.
        name_row = tk.Frame(profile_details, bg=CARD_BG)
        name_row.pack(fill="x")
        name_var = tk.StringVar(value=saved_name)
        name_box = self.create_card_frame(name_row, bg=INPUT_BG, width=260, height=38)
        name_box.pack(side="left", padx=(0, 10))
        name_box.pack_propagate(False)
        name_entry = tk.Entry(
            name_box, textvariable=name_var, font=(DEFAULT_FONT, 10),
            bg=INPUT_BG, fg=TEXT_WHITE, insertbackground=TEXT_WHITE,
            relief="flat", bd=0, highlightthickness=0,
        )
        name_entry.pack(fill="both", expand=True, padx=10, pady=5)
        name_placeholder = tk.Label(
            name_box, text=translate("Choose your name..."), font=(DEFAULT_FONT, 10),
            bg=INPUT_BG, fg=TEXT_GRAY, cursor="xterm",
        )
        name_status_lbl = self.create_label(profile_details, "", 9, ORANGE_HL)
        name_status_lbl.pack(anchor="w", pady=(6, 0))

        def update_name_placeholder(_event=None):
            if name_var.get().strip() or self.focus_get() is name_entry:
                name_placeholder.place_forget()
            else:
                name_placeholder.place(x=10, rely=0.5, anchor="w")

        def refresh_clear_btn():
            has_saved = bool(name_heading_lbl.cget("text") != "BBC Sounds listener")
            clear_name_btn.configure(state="normal" if has_saved else "disabled")

        def on_save_name(_event=None):
            cleaned = " ".join(name_var.get().split()).strip()[:40]
            name_var.set(cleaned)
            if self.save_listener_name(self.current_user, cleaned):
                name_heading_lbl.configure(text=cleaned or translate("BBC Sounds listener"))
                if cleaned:
                    name_status_lbl.configure(text=translate(f"Saved — Home will greet you as \"Good to have you back, {cleaned}!\""))
                else:
                    name_status_lbl.configure(text=translate("Name cleared."))
                refresh_clear_btn()
                update_name_placeholder()

        def on_clear_name():
            name_var.set("")
            if self.save_listener_name(self.current_user, ""):
                name_heading_lbl.configure(text=translate("BBC Sounds listener"))
                name_status_lbl.configure(text=translate("Name cleared."))
                refresh_clear_btn()
                update_name_placeholder()

        name_placeholder.bind("<Button-1>", lambda _e: name_entry.focus_set())
        name_entry.bind("<FocusIn>", lambda _e: name_placeholder.place_forget())
        name_entry.bind("<FocusOut>", update_name_placeholder)
        name_entry.bind("<Return>", on_save_name)
        name_entry.bind("<KeyRelease>", lambda _e: name_status_lbl.configure(text=""))

        self.create_button(name_row, "Save name", on_save_name, primary=True, compact=True).pack(
            side="left", padx=(0, 8)
        )
        clear_name_btn = self.create_button(name_row, "Clear", on_clear_name, compact=True)
        clear_name_btn.pack(side="left")
        refresh_clear_btn()
        update_name_placeholder()

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
            lambda: self.transition_to(self.show_preferences, "Settings", direction=1), primary=True,
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

        # Divider and Language selector row (English / Cymraeg) inside the Accessibility settings card.
        tk.Frame(access_card, bg=BORDER_LINE, height=1).pack(fill="x", padx=18)
        lang_row = tk.Frame(access_card, bg=CARD_BG)
        lang_row.pack(fill="x", padx=18, pady=16)

        lang_labels = {
            "en": "English  ·  Default",
            "cy": "Cymraeg  ·  Welsh",
        }
        active_lang = getattr(self, "_language", "en")

        lang_info = tk.Frame(lang_row, bg=CARD_BG)
        lang_info.pack(side="left", fill="x", expand=True)
        self.create_label(lang_info, "LANGUAGE", 9, TEXT_GRAY, "bold").pack(anchor="w")
        self.create_label(
            lang_info, lang_labels.get(active_lang, "English  ·  Default"), 13, TEXT_WHITE, "bold",
        ).pack(anchor="w", pady=(4, 0))

        lang_controls = tk.Frame(lang_row, bg=CARD_BG)
        lang_controls.pack(side="right")
        for lang_key, lang_caption in (("en", "English"), ("cy", "Cymraeg (Welsh)")):
            is_selected = active_lang == lang_key
            self.create_button(
                lang_controls,
                lang_caption,
                lambda code=lang_key: self.set_language(code),
                primary=is_selected,
                compact=True,
            ).pack(side="left", padx=(0 if lang_key == "en" else 8, 0))

        # Divider and Motion / Animations selector row (Smooth / Reduced) for low-end devices & comfort.
        tk.Frame(access_card, bg=BORDER_LINE, height=1).pack(fill="x", padx=18)
        motion_row = tk.Frame(access_card, bg=CARD_BG)
        motion_row.pack(fill="x", padx=18, pady=16)

        active_reduced = self._is_reduced_motion()
        motion_info = tk.Frame(motion_row, bg=CARD_BG)
        motion_info.pack(side="left", fill="x", expand=True)
        self.create_label(motion_info, "ANIMATIONS", 9, TEXT_GRAY, "bold").pack(anchor="w")
        self.create_label(
            motion_info,
            "Reduced motion  ·  Faster on older devices" if active_reduced else "Smooth  ·  Default",
            13, TEXT_WHITE, "bold",
        ).pack(anchor="w", pady=(4, 0))

        motion_controls = tk.Frame(motion_row, bg=CARD_BG)
        motion_controls.pack(side="right")
        for is_red, caption in ((False, "Smooth"), (True, "Reduced motion")):
            self.create_button(
                motion_controls,
                caption,
                lambda flag=is_red: self.set_reduced_motion(flag),
                primary=(active_reduced == is_red),
                compact=True,
            ).pack(side="left", padx=(0 if not is_red else 8, 0))

        def format_text_scale_label(scale_val):
            pct = round(scale_val * 100)
            if pct == 100:
                return translate("100%  ·  Default")
            return translate(f"{pct}%  ·  {'Larger' if pct > 100 else 'Smaller'}")

        def refresh_accessibility_controls():
            scale_val = getattr(self, "_text_scale", 1.0)
            cur_theme = getattr(self, "_theme_name", "dark")
            cur_lang = getattr(self, "_language", "en")
            cur_reduced = self._is_reduced_motion()
            size_status_label.configure(text=format_text_scale_label(scale_val))
            smaller_btn.configure(state="disabled" if scale_val <= 0.805 else "normal")
            larger_btn.configure(state="disabled" if scale_val >= 1.395 else "normal")
            at_defaults = abs(scale_val - 1.0) < 0.005 and cur_theme == "dark" and cur_lang == "en" and not cur_reduced
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

        # Interactive Q&A accordion section answering common questions about the app.
        self.render_section_title(
            page, "Q&A",
            "Select a question below to see how BBC Sounds features work.",
        )
        qa_items = [
            (
                "How are my recommendations chosen?",
                "Recommendations on the For you tab match your saved favourite genres and preferred "
                "episode length (Short, Medium, or Long), weighted toward higher-rated programmes.",
            ),
            (
                "How do I rate a programme?",
                "Open any podcast by clicking its picture or Details button, press Listen now at least once, "
                "and then click Rate this programme to choose a 1 to 5 star score.",
            ),
            (
                "Why does it say playback is simulated?",
                "This desktop prototype simulates audio playback so you can explore recommendations, "
                "track your listening history, and rate programmes without streaming live audio.",
            ),
            (
                "How do I save or remove favourites?",
                "Click any podcast picture to open its details page, then click Save to favourites. "
                "Saved shows appear in the Favourites tab and can be removed at any time.",
            ),
            (
                "How do I change text size or switch themes?",
                "Use the Accessibility settings above to adjust text size (80%–140%) or switch between "
                "Dark, Light, and High contrast themes. Your choices are saved automatically to your Listener ID.",
            ),
            (
                "Can I update or reset my listening survey?",
                "Yes — click Edit survey answers above to update your favourite genres (up to five) or "
                "preferred episode length, or click Reset survey to clear your saved preferences.",
            ),
        ]
        # Render the entire Q&A card on a single Canvas (one Win32 HWND, zero child-frame pack
        # reflows) so lower questions slide smoothly and never flicker or get hidden mid-animation.
        qa_canvas = tk.Canvas(page, bg=DARK_BG, bd=0, highlightthickness=0, height=200)
        qa_canvas.pack(fill="x", pady=(5, 14))

        scale = getattr(self, "_ui_scale_factor", 1.0) * getattr(self, "_text_scale", 1.0)
        q_font = (DEFAULT_FONT, max(8, round(11 * scale)), "bold")
        a_font = (DEFAULT_FONT, max(8, round(10 * scale)), "normal")

        def rounded_poly_coords(w, h, r=12):
            m = 1
            x1 = max(m + 2, w - 1)
            y1 = max(m + 2, h - 1)
            rad = min(r, (x1 - m) / 2, (y1 - m) / 2)
            return (
                rad + m, m, x1 - rad, m, x1, m, x1, rad + m, x1, y1 - rad, x1, y1,
                x1 - rad, y1, rad + m, y1, m, y1, m, y1 - rad, m, rad + m, m, m,
            )

        card_fill = qa_canvas.create_polygon(0, 0, 0, 0, smooth=True, fill=CARD_BG, outline="")

        qa_anim_items = []
        for q_idx, (question_text, answer_text) in enumerate(qa_items):
            # Each row's solid CARD_BG backdrop sits above the previous row's answer text in Z-order,
            # acting as a clean clipping curtain so lower questions never get overlapped or hidden.
            row_bg = qa_canvas.create_rectangle(0, 0, 0, 0, fill=CARD_BG, outline="")
            divider = (
                qa_canvas.create_line(0, 0, 0, 0, fill=BORDER_LINE, width=1)
                if q_idx > 0 else None
            )
            arrow_id = qa_canvas.create_text(
                0, 0, text="▸", fill=ORANGE_HL, font=q_font, anchor="nw",
            )
            q_id = qa_canvas.create_text(
                0, 0, text=translate(question_text), fill=TEXT_WHITE, font=q_font, anchor="nw", width=800,
            )
            ans_id = qa_canvas.create_text(
                0, 0, text=translate(answer_text), fill=CARD_BG, font=a_font, anchor="nw", width=780,
                state="hidden",
            )
            qa_anim_items.append({
                "open": False,
                "progress": 0.0,
                "target": 0.0,
                "row_bg": row_bg,
                "divider": divider,
                "arrow_id": arrow_id,
                "q_id": q_id,
                "ans_id": ans_id,
                "q_h": 22,
                "ans_h": 36,
                "hit_top": 0,
                "hit_bottom": 0,
                "last_ans_fg": CARD_BG,
                "last_q_fg": TEXT_WHITE,
                "ans_visible": False,
            })

        # Bottom curtain masks the last item's answer cleanly inside the rounded card footer.
        bottom_curtain = qa_canvas.create_rectangle(0, 0, 0, 0, fill=CARD_BG, outline="")
        card_border = qa_canvas.create_polygon(0, 0, 0, 0, smooth=True, fill="", outline=BORDER_LINE)

        qa_layout = {"width": 0, "height": 0}
        qa_loop = {"job": None, "last_t": None}
        qa_duration = 0.220

        def measure_texts(canvas_w):
            pad_x = 20
            q_w = max(220, canvas_w - pad_x * 2 - 24)
            a_w = max(220, canvas_w - pad_x * 2 - 28)
            for st in qa_anim_items:
                qa_canvas.itemconfigure(st["q_id"], width=q_w)
                qa_canvas.itemconfigure(st["ans_id"], width=a_w)
                qb = qa_canvas.bbox(st["q_id"])
                st["q_h"] = max(20, (qb[3] - qb[1]) if qb else 22)
                was_hidden = not st["ans_visible"]
                if was_hidden:
                    qa_canvas.itemconfigure(st["ans_id"], state="normal")
                ab = qa_canvas.bbox(st["ans_id"])
                st["ans_h"] = max(20, (ab[3] - ab[1]) if ab else 36)
                if was_hidden:
                    qa_canvas.itemconfigure(st["ans_id"], state="hidden")

        def layout_qa(canvas_w=None):
            if not qa_canvas.winfo_exists():
                return
            w = canvas_w if canvas_w is not None else qa_layout["width"]
            if w <= 1:
                w = max(400, qa_canvas.winfo_width())
            if w != qa_layout["width"]:
                qa_layout["width"] = w
                measure_texts(w)

            pad_x = 20
            y = 8
            for st in qa_anim_items:
                cur = st["progress"]
                tgt = st["target"]
                eased = 1.0 - (1.0 - cur) ** 3 if tgt > 0.5 else cur * cur * (3.0 - 2.0 * cur)
                open_h = round((st["ans_h"] + 12) * eased) if cur > 0.0 else 0

                row_top = y
                if st["divider"] is not None:
                    qa_canvas.coords(st["divider"], pad_x, row_top, w - pad_x, row_top)

                q_y = row_top + 12
                header_bottom = q_y + st["q_h"] + 12
                row_bottom = header_bottom + open_h
                st["hit_top"] = row_top
                st["hit_bottom"] = header_bottom

                qa_canvas.coords(st["row_bg"], 6, row_top, w - 6, row_bottom + 2)
                qa_canvas.coords(st["arrow_id"], pad_x, q_y)
                qa_canvas.coords(st["q_id"], pad_x + 20, q_y)

                if open_h > 0:
                    if not st["ans_visible"]:
                        qa_canvas.itemconfigure(st["ans_id"], state="normal")
                        st["ans_visible"] = True
                    qa_canvas.coords(st["ans_id"], pad_x + 20, q_y + st["q_h"] + 6)
                elif st["ans_visible"]:
                    qa_canvas.itemconfigure(st["ans_id"], state="hidden")
                    st["ans_visible"] = False

                ans_col = blend_colour(CARD_BG, TEXT_GRAY, eased)
                if ans_col != st["last_ans_fg"]:
                    qa_canvas.itemconfigure(st["ans_id"], fill=ans_col)
                    st["last_ans_fg"] = ans_col

                q_col = blend_colour(TEXT_WHITE, ORANGE_HL, eased * 0.65)
                if q_col != st["last_q_fg"]:
                    qa_canvas.itemconfigure(st["q_id"], fill=q_col)
                    st["last_q_fg"] = q_col

                y = row_bottom

            total_h = y + 10
            qa_canvas.coords(bottom_curtain, 12, y, w - 12, total_h - 1)
            poly = rounded_poly_coords(w, total_h)
            qa_canvas.coords(card_fill, *poly)
            qa_canvas.coords(card_border, *poly)
            if total_h != qa_layout["height"]:
                qa_layout["height"] = total_h
                qa_canvas.configure(height=total_h)

        def cancel_all_qa_anims(_event=None):
            if qa_loop["job"] is not None:
                try:
                    self.after_cancel(qa_loop["job"])
                except tk.TclError:
                    pass
                qa_loop["job"] = None
            qa_loop["last_t"] = None

        def tick_qa_animations():
            qa_loop["job"] = None
            if not qa_canvas.winfo_exists():
                qa_loop["last_t"] = None
                return
            now = monotonic()
            dt = 0.012 if qa_loop["last_t"] is None else min(0.05, now - qa_loop["last_t"])
            qa_loop["last_t"] = now
            step_delta = dt / qa_duration

            any_active = False
            for st in qa_anim_items:
                cur = st["progress"]
                tgt = st["target"]
                if cur == tgt:
                    continue
                if cur < tgt:
                    cur = min(tgt, cur + step_delta)
                else:
                    cur = max(tgt, cur - step_delta)
                st["progress"] = cur
                if cur != tgt:
                    any_active = True

            layout_qa()
            if any_active:
                spent = (monotonic() - now) * 1000.0
                qa_loop["job"] = self.after(self._next_frame_delay(spent, 16), tick_qa_animations)
            else:
                qa_loop["last_t"] = None

        def on_qa_click(event):
            for st in qa_anim_items:
                if st["hit_top"] <= event.y <= st["hit_bottom"]:
                    st["open"] = not st["open"]
                    st["target"] = 1.0 if st["open"] else 0.0
                    qa_canvas.itemconfigure(st["arrow_id"], text="▾" if st["open"] else "▸")
                    if self._is_reduced_motion():
                        st["progress"] = st["target"]
                        layout_qa()
                    elif qa_loop["job"] is None:
                        qa_loop["last_t"] = None
                        tick_qa_animations()
                    break

        def on_qa_motion(event):
            over_header = any(st["hit_top"] <= event.y <= st["hit_bottom"] for st in qa_anim_items)
            desired = "hand2" if over_header else ""
            if qa_canvas.cget("cursor") != desired:
                qa_canvas.configure(cursor=desired)

        def on_qa_configure(event):
            if event.width > 1 and event.width != qa_layout["width"]:
                layout_qa(event.width)

        qa_canvas.bind("<Button-1>", on_qa_click)
        qa_canvas.bind("<Motion>", on_qa_motion)
        qa_canvas.bind("<Leave>", lambda _e: qa_canvas.configure(cursor=""))
        qa_canvas.bind("<Configure>", on_qa_configure)
        qa_canvas.bind("<Destroy>", cancel_all_qa_anims)
        layout_qa(860)

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
            self._attach_genre_tile_hover(tile, g_name, check_lbl, art_cnv)
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

    def _attach_genre_tile_hover(self, tile, genre_name, check_lbl, art_cnv):
        """Attach a bouncy elastic pop-out hover spring to a selectable preference genre tile."""
        base_inset = 5
        tile.set_inset(base_inset)
        hstate = {"step": 0, "target": 0, "job": None, "leave_job": None}

        def cancel_jobs(_event=None):
            for k in ("job", "leave_job"):
                jid = hstate[k]
                if jid is not None:
                    try:
                        self.after_cancel(jid)
                    except tk.TclError:
                        pass
                    hstate[k] = None

        def is_inside():
            if not tile.winfo_exists():
                return False
            try:
                px, py = tile.winfo_pointerxy()
                w = tile.winfo_containing(px, py)
            except tk.TclError:
                return False
            while w is not None:
                if w is tile:
                    return True
                w = getattr(w, "master", None)
            return False

        def apply_frame():
            hstate["job"] = None
            if not tile.winfo_exists():
                return
            cur = hstate["step"]
            tgt = hstate["target"]
            if cur == tgt:
                return
            cur += 1 if tgt > cur else -1
            hstate["step"] = cur
            t = cur / 10.0
            raw = ease_out_elastic(t, damping=3.0, frequency=1.65) if tgt > 0 else 1.0 - (1.0 - t) ** 2.4
            col_t = max(0.0, min(1.0, raw))
            inset = max(0, min(base_inset, round(base_inset - 3.0 * raw)))
            tile.set_inset(inset)
            is_active = genre_name in self.active_genres
            rest_bg = SELECTED_BG if is_active else CARD_BG
            rest_bd = ORANGE_ACCENT if is_active else BORDER_LINE
            hi_bg = blend_colour(rest_bg, ORANGE_ACCENT if is_active else "#ffffff", 0.08)
            cur_bg = blend_colour(rest_bg, hi_bg, col_t)
            cur_bd = blend_colour(rest_bd, ORANGE_HL if is_active else ORANGE_ACCENT, col_t)
            tile.set_surface(cur_bg, cur_bd)
            if check_lbl.winfo_exists():
                check_lbl.configure(bg=cur_bg)
            if art_cnv.winfo_exists():
                art_cnv.configure(bg=cur_bg)
            if cur != tgt:
                hstate["job"] = self.after(self._anim_frame_interval(16), apply_frame)

        def set_target(tgt):
            hstate["target"] = tgt
            if self._is_reduced_motion():
                cancel_jobs()
                if hstate["step"] != tgt:
                    hstate["step"] = max(0, tgt - 1) if tgt > hstate["step"] else min(10, tgt + 1)
                    apply_frame()
                return
            if hstate["job"] is None and hstate["step"] != tgt:
                apply_frame()

        def on_enter(_e=None):
            if getattr(self, "_transition_active", False) or self._is_scrolling():
                return
            if hstate["leave_job"] is not None:
                try:
                    self.after_cancel(hstate["leave_job"])
                except tk.TclError:
                    pass
                hstate["leave_job"] = None
            set_target(10)

        def on_leave(_e=None):
            if hstate["leave_job"] is not None:
                try:
                    self.after_cancel(hstate["leave_job"])
                except tk.TclError:
                    pass
            hstate["leave_job"] = self.after(18, lambda: (hstate.__setitem__("leave_job", None), None if is_inside() else set_target(0)))

        for w in (tile, tile.backdrop, check_lbl, art_cnv):
            w.bind("<Enter>", on_enter, add="+")
            w.bind("<Leave>", on_leave, add="+")
        tile.bind("<Destroy>", cancel_jobs, add="+")

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
