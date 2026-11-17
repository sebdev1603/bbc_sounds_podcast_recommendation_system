import tkinter as tk
from tkinter import messagebox, simpledialog
import sqlite3
import math
import pandas as pd

# Import your existing project modules
import main as MainApp
import favourites as Favourites
import rating as Rating
import survey as Survey
import listeningHistory as ListeningHistory

DB_PATH = "database.db"

# Color Palette matching your mockups
BG_BLACK = "#050505"
BG_DARK = "#121212"
BG_GRAD_BOT = "#2E2E2E"
CARD_GREY = "#595959"
CARD_LIGHT = "#6E6E6E"
PILL_GREY = "#4A4A4A"
PILL_LIGHT = "#D9D9D9"
BBC_ORANGE = "#FF5500"
TEXT_WHITE = "#FFFFFF"
TEXT_MUTED = "#B3B3B3"
STAR_GOLD = "#FFD700"
STAR_DIM = "#555555"


class BBCSoundsGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BBC Sounds")
        self.geometry("1280x820")
        self.minsize(1024, 700)
        self.configure(bg=BG_BLACK)

        self.current_user = None
        self.current_username_display = "USERNAME"
        self.selected_survey_genres = []
        self.selected_survey_themes = []
        self.selected_length_pref = "Medium"
        self.previous_screen = "home"

        # Container holding all screens
        self.container = tk.Frame(self, bg=BG_BLACK)
        self.container.pack(fill="both", expand=True)

        self.show_welcome_screen()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def get_db_connection(self):
        return sqlite3.connect(DB_PATH)

    def draw_bbc_logo(self, parent, bg_color=BG_BLACK, font_size=22, boxed=False):
        logo_frame = tk.Frame(parent, bg=bg_color)
        if boxed:
            for ch in ["B", "B", "C"]:
                lbl = tk.Label(
                    logo_frame,
                    text=ch,
                    font=("Arial", font_size - 4, "bold"),
                    fg=TEXT_WHITE,
                    bg=BG_BLACK,
                    bd=1,
                    relief="solid",
                    padx=4,
                    pady=1,
                    highlightbackground=TEXT_WHITE,
                    highlightthickness=1,
                )
                lbl.pack(side="left", padx=1)
            tk.Label(
                logo_frame,
                text=" SOUND",
                font=("Arial", font_size - 2, "bold"),
                fg=BBC_ORANGE,
                bg=bg_color,
            ).pack(side="left")
        else:
            tk.Label(
                logo_frame,
                text="BBC ",
                font=("Arial", font_size, "bold"),
                fg=TEXT_WHITE,
                bg=bg_color,
            ).pack(side="left")
            tk.Label(
                logo_frame,
                text="SOUND",
                font=("Arial", font_size, "bold"),
                fg=BBC_ORANGE,
                bg=bg_color,
            ).pack(side="left")
        return logo_frame

    def create_rounded_rect(self, canvas, x1, y1, x2, y2, r=20, **kwargs):
        points = [
            x1 + r, y1,
            x1 + r, y1,
            x2 - r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1 + r,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    # =========================================================================
    # SCREEN 1: WELCOME / LOGIN (Image 1.jpg)
    # =========================================================================
    def show_welcome_screen(self):
        self.clear_container()
        canvas = tk.Canvas(self.container, bg=BG_BLACK, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Left Brand Text
        canvas.create_text(
            60, 75, text="WELCOME TO", anchor="w",
            fill=TEXT_WHITE, font=("Arial", 22, "bold")
        )
        canvas.create_text(
            60, 145, text="BBC", anchor="w",
            fill=TEXT_WHITE, font=("Arial", 44, "bold")
        )
        canvas.create_text(
            205, 145, text="SOUND", anchor="w",
            fill=BBC_ORANGE, font=("Arial", 44, "bold")
        )

        # Main Hero Headline
        canvas.create_text(
            85, 450, text="Ready to make\nsome noise?", anchor="w",
            fill=TEXT_WHITE, font=("Arial", 54), justify="left"
        )

        # Decorative Vinyl Graphic on top-right matching mockup 1
        cx, cy = 960, 265
        for radius, color, width in [
            (175, "#333333", 2),
            (145, "#C8A96E", 18),
            (115, "#E8D5A7", 24),
            (85, "#D4AF37", 18),
            (42, "#1A1A1A", 35),
            (10, "#FFFFFF", 4),
        ]:
            canvas.create_oval(
                cx - radius, cy - radius, cx + radius, cy + radius,
                outline=color, width=width
            )

        # Circular slogan text around the vinyl
        ring_text = "STREAM . SHARE . BBC SOUND . LISTEN . DISCOVER . "
        for idx, ch in enumerate(ring_text):
            angle = math.radians(idx * (360 / len(ring_text)) - 90)
            tx = cx + 195 * math.cos(angle)
            ty = cy + 195 * math.sin(angle)
            canvas.create_text(
                tx, ty, text=ch, fill=TEXT_WHITE,
                font=("Arial", 13, "bold"),
                angle=-math.degrees(angle) - 90
            )

        # Tonearm accent
        canvas.create_line(cx + 155, cy - 110, cx + 65, cy + 25, fill="#A0A0A0", width=6)
        canvas.create_oval(cx + 140, cy - 125, cx + 170, cy - 95, fill="#555555", outline="#CCCCCC", width=2)

        # Outlined CTA Box: "---> Log into your account"
        btn_frame = tk.Frame(
            canvas, bg=BG_BLACK, highlightbackground=TEXT_WHITE,
            highlightthickness=2, padx=24, pady=14, cursor="hand2"
        )
        canvas.create_window(85, 585, anchor="nw", window=btn_frame)

        arrow_lbl = tk.Label(
            btn_frame, text="───▶", font=("Arial", 20, "bold"),
            fg=TEXT_WHITE, bg=BG_BLACK, cursor="hand2"
        )
        arrow_lbl.pack(side="left", padx=(0, 14))

        login_lbl = tk.Label(
            btn_frame, text="Log into your account", font=("Arial", 22),
            fg=TEXT_WHITE, bg=BG_BLACK, cursor="hand2"
        )
        login_lbl.pack(side="left")

        # Inline Login Entry Frame (appears when CTA is clicked)
        auth_frame = tk.Frame(canvas, bg=BG_BLACK)
        canvas.create_window(85, 675, anchor="nw", window=auth_frame)

        username_var = tk.StringVar()
        status_lbl = tk.Label(
            auth_frame, text="", font=("Arial", 12),
            fg=BBC_ORANGE, bg=BG_BLACK
        )

        def reveal_login(_event=None):
            for w in auth_frame.winfo_children():
                w.destroy()

            tk.Label(
                auth_frame, text="Listener ID / Username:",
                font=("Arial", 14), fg=TEXT_WHITE, bg=BG_BLACK
            ).pack(side="left", padx=(0, 10))

            entry = tk.Entry(
                auth_frame, textvariable=username_var, font=("Arial", 14),
                bg="#1E1E1E", fg=TEXT_WHITE, insertbackground=TEXT_WHITE,
                relief="flat", width=22
            )
            entry.pack(side="left", ipady=6, padx=(0, 10))
            entry.focus_set()

            submit_btn = tk.Button(
                auth_frame, text="Continue", font=("Arial", 13, "bold"),
                bg=BBC_ORANGE, fg=TEXT_WHITE, relief="flat", padx=18, pady=5,
                cursor="hand2", command=attempt_login
            )
            submit_btn.pack(side="left")
            entry.bind("<Return>", lambda e: attempt_login())

            nonlocal status_lbl
            status_lbl = tk.Label(
                auth_frame, text="", font=("Arial", 12),
                fg=BBC_ORANGE, bg=BG_BLACK
            )
            status_lbl.pack(side="left", padx=12)

        def attempt_login():
            uname = username_var.get().strip()
            if not uname:
                status_lbl.config(text="Please enter your Listener ID.")
                return
            try:
                exists = MainApp.username_exists(uname)
            except Exception as exc:
                messagebox.showerror("Database Error", f"Could not connect to database.db:\n{exc}")
                return

            if exists:
                self.current_user = int(uname) if uname.isdigit() else uname
                self.current_username_display = f"Listener #{self.current_user}"
                if not Survey.is_survey_complete(self.current_user):
                    self.selected_survey_genres = []
                    self.show_survey_genres_screen()
                else:
                    self.show_home_screen()
            else:
                status_lbl.config(text="Incorrect username / Listener ID not found.")

        for widget in (btn_frame, arrow_lbl, login_lbl):
            widget.bind("<Button-1>", reveal_login)

    # =========================================================================
    # SCREEN 2: SURVEY STEP 1 - GENRES (Image 2.jpg)
    # =========================================================================
    def show_survey_genres_screen(self):
        self.clear_container()
        canvas = tk.Canvas(self.container, bg=BG_BLACK, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        # Header
        canvas.create_text(595, 55, text="BBC", fill=TEXT_WHITE, font=("Arial", 32, "bold"))
        canvas.create_text(715, 55, text="SOUND", fill=BBC_ORANGE, font=("Arial", 32, "bold"))
        canvas.create_text(640, 110, text="Tell us about yourself!", fill=TEXT_WHITE, font=("Arial", 28))
        canvas.create_text(
            640, 175, text="Pick your\nfavourite genre\nbelow. (Up to 5)",
            fill=TEXT_WHITE, font=("Arial", 18), justify="center"
        )

        # Decorative Studio Mic (top-left) & Headphones (top-right)
        canvas.create_line(70, 0, 70, 220, fill="#3A3A3A", width=10)
        canvas.create_line(70, 220, 230, 140, fill="#4D4D4D", width=12)
        canvas.create_rectangle(210, 95, 310, 165, fill="#262626", outline="#555555", width=2)
        canvas.create_text(245, 130, text="SHURE", fill="#CCCCCC", font=("Arial", 9, "bold"), angle=-30)

        # Headphones illustration on right
        canvas.create_arc(1010, 20, 1230, 260, start=0, extent=190, style="arc", outline="#444444", width=14)
        canvas.create_oval(1015, 165, 1085, 255, fill="#2B2B2B", outline="#666666", width=3)
        canvas.create_oval(1175, 150, 1245, 240, fill="#2B2B2B", outline="#666666", width=3)
        canvas.create_line(1135, 290, 910, 620, fill=TEXT_WHITE, width=2, smooth=True)

        # Album cards & wires on bottom-left
        canvas.create_rectangle(55, 390, 155, 490, fill="#B22222", outline="#FF4444", width=2)
        canvas.create_text(105, 415, text="THE WEEKND", fill="#FFD700", font=("Arial", 8, "bold"))
        canvas.create_line(130, 490, 385, 620, fill=TEXT_WHITE, width=2, smooth=True)

        # Central Rounded Container matching Image 2
        self.create_rounded_rect(
            canvas, 385, 265, 895, 735, r=35,
            fill=BG_BLACK, outline=TEXT_WHITE, width=3
        )

        # Genres matching survey.py valid_genres + mockup 2 visual colors
        genres_grid = [
            ("Comedy", "#4B56D2", "#9D65C9"),
            ("Sport", "#A8E6CF", "#88B0FF"),
            ("Health", "#6C3483", "#F5B041"),
            ("Travel", "#FFF3B0", "#FF9CEE"),
            ("History", "#3D2C00", "#D49A00"),
            ("News", "#E84A5F", "#9B5DE5"),
            ("Technology", "#56CCF2", "#2F80ED"),
            ("Gaming", "#43AA8B", "#F9C74F"),
            ("Business", "#2C2C2C", "#E0E0E0"),
            ("Science", "#FF4E50", "#FC913A"),
            ("Entertainment", "#0F0C29", "#302B63"),
            ("True Crime", "#7F00FF", "#E100FF"),
        ]

        selected_count_id = canvas.create_text(
            640, 762,
            text=f"Selected: {len(self.selected_survey_genres)}/5",
            fill=TEXT_MUTED, font=("Arial", 13)
        )

        circle_items = {}

        def toggle_genre(genre_name):
            if genre_name in self.selected_survey_genres:
                self.selected_survey_genres.remove(genre_name)
            else:
                if len(self.selected_survey_genres) >= 5:
                    messagebox.showinfo("Limit Reached", "You can select up to 5 favourite genres.")
                    return
                self.selected_survey_genres.append(genre_name)

            # Update visual ring
            for g_name, (oval_id, lbl_id) in circle_items.items():
                if g_name in self.selected_survey_genres:
                    canvas.itemconfig(oval_id, outline=BBC_ORANGE, width=4)
                    canvas.itemconfig(lbl_id, fill=BBC_ORANGE, font=("Arial", 11, "bold"))
                else:
                    canvas.itemconfig(oval_id, outline="", width=0)
                    canvas.itemconfig(lbl_id, fill=TEXT_WHITE, font=("Arial", 11))

            canvas.itemconfig(
                selected_count_id,
                text=f"Selected: {len(self.selected_survey_genres)}/5  ({', '.join(self.selected_survey_genres)})"
            )

        start_x, start_y = 450, 345
        col_gap, row_gap = 125, 145
        r = 44

        for idx, (g_name, c1, _c2) in enumerate(genres_grid):
            row = idx // 4
            col = idx % 4
            gx = start_x + col * col_gap
            gy = start_y + row * row_gap

            lbl_id = canvas.create_text(
                gx, gy - 58, text=g_name, fill=TEXT_WHITE, font=("Arial", 11)
            )
            oval_id = canvas.create_oval(
                gx - r, gy - r, gx + r, gy + r,
                fill=c1, outline=BBC_ORANGE if g_name in self.selected_survey_genres else "",
                width=4 if g_name in self.selected_survey_genres else 0
            )
            circle_items[g_name] = (oval_id, lbl_id)

            canvas.tag_bind(oval_id, "<Button-1>", lambda e, name=g_name: toggle_genre(name))
            canvas.tag_bind(lbl_id, "<Button-1>", lambda e, name=g_name: toggle_genre(name))

        # Next -> Step 2 (Themes & Length)
        next_btn = tk.Button(
            canvas, text="Next  ➔", font=("Arial", 14, "bold"),
            bg=BBC_ORANGE, fg=TEXT_WHITE, relief="flat", padx=24, pady=8,
            cursor="hand2", command=self.proceed_to_themes_survey
        )
        canvas.create_window(1080, 745, window=next_btn)

        skip_btn = tk.Button(
            canvas, text="Skip Survey", font=("Arial", 12),
            bg="#222222", fg=TEXT_MUTED, relief="flat", padx=16, pady=6,
            cursor="hand2", command=self.show_home_screen
        )
        canvas.create_window(160, 745, window=skip_btn)

    def proceed_to_themes_survey(self):
        if not self.selected_survey_genres:
            messagebox.showwarning("Selection Required", "Please select at least one favourite genre.")
            return
        self.show_survey_themes_screen()

    # =========================================================================
    # SCREEN 3: SURVEY STEP 2 - THEMES & LENGTH (Image 3.jpg)
    # =========================================================================
    def show_survey_themes_screen(self):
        self.clear_container()
        canvas = tk.Canvas(self.container, bg=BG_BLACK, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        canvas.create_text(595, 55, text="BBC", fill=TEXT_WHITE, font=("Arial", 32, "bold"))
        canvas.create_text(715, 55, text="SOUND", fill=BBC_ORANGE, font=("Arial", 32, "bold"))
        canvas.create_text(640, 110, text="Tell us about yourself!", fill=TEXT_WHITE, font=("Arial", 28))
        canvas.create_text(
            640, 175, text="Now, pick your\nfavourite themes\nbelow.",
            fill=TEXT_WHITE, font=("Arial", 18), justify="center"
        )

        # Speaker graphic top-right matching Image 3
        canvas.create_polygon(1130, 30, 1280, 10, 1280, 190, 1150, 150, fill="#2A2A2A", outline="#8B7355", width=4)
        canvas.create_oval(1165, 45, 1215, 95, fill="#111111", outline="#666666", width=3)
        canvas.create_oval(1210, 95, 1270, 155, fill="#111111", outline="#666666", width=3)
        for wx1, wy1, wx2, wy2 in [(1115, 165, 1145, 150), (1140, 195, 1175, 170), (1175, 225, 1195, 190), (1215, 240, 1220, 200)]:
            canvas.create_line(wx1, wy1, wx2, wy2, fill=TEXT_WHITE, width=6, capstyle="round")

        # 3D Colored Theme Discs matching Image 3
        themes = [
            ("Theatrical", 215, 445, 75, "#D9383A", "#8E1B1D", "#5BC0EB"),
            ("Interview", 125, 635, 95, "#8E24AA", "#4A148C", "#64B5F6"),
            ("Conversational", 365, 615, 125, "#AEEA00", "#558B2F", "#3F51B5"),
            ("REPURPOSED CONTENT", 710, 445, 115, "#F48FB1", "#AD1457", "#64B5F6"),
            ("INVESTIGATING", 625, 635, 95, "#0D47A1", "#002171", "#FF8F00"),
            ("Roundtable", 895, 625, 120, "#0097A7", "#006064", "#FF6D00"),
            ("Mixes of all stated", 1025, 395, 115, "#FFB74D", "#E65100", "#7E57C2"),
            ("Monologue", 1155, 645, 95, "#C6FF00", "#64DD17", "#6A1B9A"),
        ]

        theme_items = {}

        def toggle_theme(t_name):
            if t_name in self.selected_survey_themes:
                self.selected_survey_themes.remove(t_name)
            else:
                self.selected_survey_themes.append(t_name)

            for name, top_id in theme_items.items():
                if name in self.selected_survey_themes:
                    canvas.itemconfig(top_id, outline=TEXT_WHITE, width=4)
                else:
                    canvas.itemconfig(top_id, outline="", width=0)

        for t_name, tx, ty, tr, top_col, side_col, txt_col in themes:
            # 3D shadow/extrusion disc
            canvas.create_oval(
                tx - tr + 10, ty - tr + 8, tx + tr + 10, ty + tr + 8,
                fill=side_col, outline=""
            )
            top_id = canvas.create_oval(
                tx - tr, ty - tr, tx + tr, ty + tr,
                fill=top_col,
                outline=TEXT_WHITE if t_name in self.selected_survey_themes else "",
                width=4 if t_name in self.selected_survey_themes else 0
            )
            txt_id = canvas.create_text(
                tx, ty - tr * 0.55, text=t_name, fill=txt_col,
                font=("Arial", 12 if tr < 100 else 14, "bold")
            )
            theme_items[t_name] = top_id
            canvas.tag_bind(top_id, "<Button-1>", lambda e, n=t_name: toggle_theme(n))
            canvas.tag_bind(txt_id, "<Button-1>", lambda e, n=t_name: toggle_theme(n))

        # Episode Length Preference bar (required by your survey.py -> LengthPreference)
        pref_frame = tk.Frame(canvas, bg="#1A1A1A", padx=16, pady=8)
        canvas.create_window(640, 775, window=pref_frame)

        tk.Label(
            pref_frame, text="Preferred Episode Length:",
            font=("Arial", 12, "bold"), fg=TEXT_WHITE, bg="#1A1A1A"
        ).pack(side="left", padx=(0, 12))

        length_var = tk.StringVar(value=self.selected_length_pref)
        for opt in ("Short", "Medium", "Long"):
            rb = tk.Radiobutton(
                pref_frame, text=opt, variable=length_var, value=opt,
                font=("Arial", 12), fg=TEXT_WHITE, bg="#1A1A1A",
                selectcolor=BBC_ORANGE, activebackground="#1A1A1A",
                activeforeground=TEXT_WHITE, indicatoron=0, padx=14, pady=4,
                command=lambda: setattr(self, "selected_length_pref", length_var.get())
            )
            rb.pack(side="left", padx=4)

        def save_and_finish_survey():
            genres_str = ",".join(self.selected_survey_genres)
            length_pref = length_var.get()
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE listeners SET CompleteSurvey = 1, FavoriteGenres = ?, LengthPreference = ? WHERE ListenerID = ?",
                (genres_str, length_pref, self.current_user)
            )
            conn.commit()
            conn.close()
            self.show_home_screen()

        back_btn = tk.Button(
            canvas, text="← Back", font=("Arial", 13),
            bg="#222222", fg=TEXT_WHITE, relief="flat", padx=18, pady=6,
            cursor="hand2", command=self.show_survey_genres_screen
        )
        canvas.create_window(110, 775, window=back_btn)

        finish_btn = tk.Button(
            canvas, text="Finish Survey  ✓", font=("Arial", 13, "bold"),
            bg=BBC_ORANGE, fg=TEXT_WHITE, relief="flat", padx=20, pady=6,
            cursor="hand2", command=save_and_finish_survey
        )
        canvas.create_window(1155, 775, window=finish_btn)

    # =========================================================================
    # SHARED TOP NAVBAR (Images 4, 5, 6)
    # =========================================================================
    def build_top_navbar(self, parent, search_prefill="", show_menu_and_profile=True):
        nav = tk.Frame(parent, bg=BG_BLACK, height=68)
        nav.pack(fill="x", side="top")
        nav.pack_propagate(False)

        # BBC SOUND Logo (clickable -> Home)
        logo = self.draw_bbc_logo(nav, bg_color=BG_BLACK, font_size=20, boxed=show_menu_and_profile)
        logo.pack(side="left", padx=24, pady=14)
        for child in logo.winfo_children():
            child.configure(cursor="hand2")
            child.bind("<Button-1>", lambda e: self.show_home_screen())

        # Pill Search Bar
        search_wrap = tk.Frame(nav, bg=PILL_LIGHT, padx=14, pady=5)
        search_wrap.pack(side="left", padx=(40, 20), pady=15)

        tk.Label(search_wrap, text="🔍", bg=PILL_LIGHT, fg="#222222", font=("Arial", 12)).pack(side="left")
        search_var = tk.StringVar(value=search_prefill)
        search_entry = tk.Entry(
            search_wrap, textvariable=search_var, bg=PILL_LIGHT, fg="#111111",
            font=("Arial", 12), relief="flat", width=36
        )
        search_entry.pack(side="left", padx=8)
        if not search_prefill:
            search_entry.insert(0, "Search podcasts")
            search_entry.bind("<FocusIn>", lambda e: search_entry.delete(0, "end") if search_entry.get() == "Search podcasts" else None)

        def trigger_search(_event=None):
            q = search_var.get().strip()
            if q == "Search podcasts":
                q = ""
            self.show_search_screen(q)

        search_entry.bind("<Return>", trigger_search)

        if show_menu_and_profile:
            # Profile Circle + Sign in / Listener label on right
            prof_frame = tk.Frame(nav, bg=BG_BLACK, cursor="hand2")
            prof_frame.pack(side="right", padx=24)

            prof_lbl = tk.Label(
                prof_frame,
                text=self.current_username_display if self.current_user else "Sign in",
                font=("Arial", 13), fg=TEXT_WHITE, bg=BG_BLACK, cursor="hand2"
            )
            prof_lbl.pack(side="left", padx=(0, 10))

            avatar_canvas = tk.Canvas(prof_frame, width=36, height=36, bg=BG_BLACK, highlightthickness=0, cursor="hand2")
            avatar_canvas.pack(side="left")
            avatar_canvas.create_oval(2, 2, 34, 34, outline=TEXT_WHITE, width=2)

            for w in (prof_frame, prof_lbl, avatar_canvas):
                w.bind("<Button-1>", lambda e: self.show_profile_screen())

            # Menu ↓ Dropdown Button
            menu_btn = tk.Menubutton(
                nav, text="Menu ↓", font=("Arial", 14), fg=TEXT_WHITE,
                bg=BG_BLACK, activebackground="#222222", activeforeground=BBC_ORANGE,
                relief="flat", cursor="hand2"
            )
            menu_btn.pack(side="right", padx=18)

            dropdown = tk.Menu(menu_btn, tearoff=0, bg="#1E1E1E", fg=TEXT_WHITE, activebackground=BBC_ORANGE)
            dropdown.add_command(label="Home / Podcasts", command=self.show_home_screen)
            dropdown.add_command(label="My Profile & Favourites", command=self.show_profile_screen)
            dropdown.add_command(label="Rated Podcasts", command=self.show_rated_podcasts_screen)
            dropdown.add_command(label="Listening History", command=self.show_listening_history_modal)
            dropdown.add_command(label="Generate Listening Report", command=self.show_listening_report_modal)
            dropdown.add_separator()
            dropdown.add_command(label="Retake / Edit Survey", command=self.show_survey_genres_screen)
            dropdown.add_command(label="Reset Survey", command=self.reset_survey_action)
            dropdown.add_separator()
            dropdown.add_command(label="Sign Out", command=self.show_welcome_screen)
            menu_btn.configure(menu=dropdown)

    # =========================================================================
    # SCREEN 4: HOME / PODCASTS DASHBOARD (Image 4.jpg)
    # =========================================================================
    def show_home_screen(self):
        self.clear_container()
        self.previous_screen = "home"
        self.build_top_navbar(self.container, show_menu_and_profile=True)

        body = tk.Frame(self.container, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        tk.Label(
            body, text="Podcasts", font=("Arial", 28, "bold"),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=28, pady=(14, 8))

        # Fetch data from SQLite
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT FavoriteGenres, LengthPreference FROM listeners WHERE ListenerID = ?",
            (self.current_user,)
        )
        user_row = cursor.fetchone()
        fav_genres_raw = user_row[0] if user_row and user_row[0] else ""
        length_pref = user_row[1] if user_row and user_row[1] else "Medium"
        fav_genres = [g.strip() for g in fav_genres_raw.split(",") if g.strip()]

        # Recommended podcasts based on survey preferences (recommendations.py logic)
        recommended = []
        if fav_genres:
            length_ranges = {"Long": (45, 60), "Medium": (25, 45), "Short": (0, 30)}
            min_l, max_l = length_ranges.get(length_pref, (0, 120))
            placeholders = ",".join("?" for _ in fav_genres)
            cursor.execute(
                f"SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts "
                f"WHERE Category IN ({placeholders}) AND AverageLengthMins BETWEEN ? AND ?",
                (*fav_genres, min_l, max_l)
            )
            recommended = cursor.fetchall()
            if not recommended:
                cursor.execute(
                    f"SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts "
                    f"WHERE Category IN ({placeholders}) LIMIT 5",
                    (*fav_genres,)
                )
                recommended = cursor.fetchall()

        cursor.execute("SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts LIMIT 10")
        all_podcasts = cursor.fetchall()
        conn.close()

        if not recommended:
            recommended = all_podcasts[:5]

        # Section 1: Your Playlists (Favourite Genres)
        playlists_data = []
        for g in fav_genres[:5]:
            count = sum(1 for p in all_podcasts if p[2].lower() == g.lower())
            playlists_data.append((f"{g} Mix", f"({count}) items", g))
        while len(playlists_data) < 5:
            playlists_data.append(("Playlist name", "() items", ""))

        self._render_card_row(
            body,
            section_title="Your Playlists",
            items=playlists_data,
            card_height=155,
            on_click=lambda item: self.show_search_screen(item[2]) if item[2] else self.show_survey_genres_screen()
        )

        # Section 2: Recommended for today
        rec_cards = [
            (p[1], f"{p[2]} / {p[3]} mins", p[1]) for p in recommended[:5]
        ]
        while len(rec_cards) < 5:
            rec_cards.append(("Podcast name", "Items / run time", None))

        self._render_card_row(
            body,
            section_title="Recommended for today",
            items=rec_cards,
            card_height=135,
            on_click=lambda item: self.show_podcast_details_screen(item[2]) if item[2] else None
        )

        # Section 3: New Releases
        rel_cards = [
            (p[1], f"{p[2]} / {p[3]} mins", p[1]) for p in all_podcasts[:5]
        ]
        while len(rel_cards) < 5:
            rel_cards.append(("Podcast name", "Items / run time", None))

        self._render_card_row(
            body,
            section_title="New Releases",
            items=rel_cards,
            card_height=135,
            on_click=lambda item: self.show_podcast_details_screen(item[2]) if item[2] else None
        )

    def _render_card_row(self, parent, section_title, items, card_height=140, on_click=None):
        tk.Label(
            parent, text=section_title, font=("Arial", 15),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=28, pady=(6, 4))

        row_frame = tk.Frame(parent, bg=BG_DARK)
        row_frame.pack(fill="x", padx=24, pady=(0, 6))

        for idx, item in enumerate(items[:5]):
            title_txt, sub_txt, payload = item
            card_w = 230
            c = tk.Canvas(
                row_frame, width=card_w, height=card_height,
                bg=BG_DARK, highlightthickness=0, cursor="hand2" if payload else "arrow"
            )
            c.pack(side="left", padx=6)
            self.create_rounded_rect(c, 2, 2, card_w - 2, card_height - 2, r=28, fill=CARD_GREY, outline="")

            c.create_text(
                14, card_height - 38, text=title_txt[:22], anchor="w",
                fill=TEXT_WHITE, font=("Arial", 12, "bold")
            )
            c.create_text(
                14, card_height - 18, text=sub_txt[:26], anchor="w",
                fill="#E0E0E0", font=("Arial", 9)
            )
            if on_click and payload:
                c.bind("<Button-1>", lambda e, it=item: on_click(it))

    # =========================================================================
    # SCREEN 5: PODCAST / EPISODE DETAILS (Image 5.jpg)
    # =========================================================================
    def show_podcast_details_screen(self, podcast_title):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM podcasts WHERE Title = ?", (podcast_title,))
        podcast = cursor.fetchone()

        if not podcast:
            conn.close()
            messagebox.showerror("Not Found", f"Podcast '{podcast_title}' not found.")
            return

        podcast_id = podcast[0]
        title = podcast[1]
        category = podcast[2]
        length_mins = podcast[3]
        avg_rating = podcast[5] if len(podcast) > 5 else "N/A"

        cursor.execute(
            "SELECT RatingGiven, TimesListened FROM listening_history WHERE PodcastID = ? AND ListenerID = ?",
            (podcast_id, self.current_user)
        )
        hist = cursor.fetchone()
        personal_rating = hist[0] if hist else None
        times_listened = hist[1] if hist and hist[1] else 0

        cursor.execute(
            "SELECT FavoritePodcasts FROM listeners WHERE ListenerID = ?",
            (self.current_user,)
        )
        fav_res = cursor.fetchone()
        current_favs = fav_res[0] if fav_res and fav_res[0] else ""
        is_favourited = str(podcast_id) in current_favs.split(",")
        conn.close()

        self.clear_container()
        self.build_top_navbar(self.container, search_prefill=title, show_menu_and_profile=False)

        body = tk.Frame(self.container, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # Top divider
        tk.Frame(body, bg="#555555", height=2).pack(fill="x", padx=90, pady=(14, 18))

        tk.Label(
            body, text=f"Part of the '{category}' collection",
            font=("Arial", 18, "bold"), fg=TEXT_WHITE, bg=BG_DARK
        ).pack(pady=(0, 24))

        # Center Artwork + Action Controls Row
        center = tk.Frame(body, bg=BG_DARK)
        center.pack(fill="x", padx=180)

        # Left Artwork Card
        art = tk.Canvas(center, width=255, height=255, bg=BG_DARK, highlightthickness=0)
        art.pack(side="left", padx=(0, 45))
        self.create_rounded_rect(art, 2, 2, 253, 253, r=24, fill="#8B1E00", outline="#FF5500", width=2)
        art.create_rectangle(95, 22, 160, 42, fill=TEXT_WHITE, outline="")
        art.create_text(127, 32, text="B B C", fill=BBC_ORANGE, font=("Arial", 10, "bold"))
        art.create_text(127, 130, text=title.upper(), fill=TEXT_WHITE, font=("Arial", 18, "bold"), width=210, justify="center")
        art.create_text(127, 210, text=category.upper(), fill="#FFD166", font=("Arial", 12, "bold"))

        # Right Info & Action Buttons
        info = tk.Frame(center, bg=BG_DARK)
        info.pack(side="left", fill="both", expand=True, pady=8)

        tk.Label(
            info,
            text=f"Podcast . {length_mins} min   |   Avg Rating: {avg_rating}   |   Listened: {times_listened}x",
            font=("Arial", 13), fg="#D0D0D0", bg=BG_DARK
        ).pack(anchor="w")

        tk.Label(
            info,
            text=f"Your rating: {personal_rating if personal_rating is not None else 'Not rated yet'}",
            font=("Arial", 15), fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", pady=(8, 4))

        tk.Label(
            info, text=title, font=("Arial", 22, "bold"),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", pady=(4, 18))

        # Action Buttons Row (Orange Play Circle + Add/Save + Rate/Share + Not Interested)
        actions = tk.Frame(info, bg=BG_DARK)
        actions.pack(anchor="w")

        def play_podcast():
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM listening_history WHERE PodcastID = ? AND ListenerID = ?",
                (podcast_id, self.current_user)
            )
            if cur.fetchone():
                cur.execute(
                    "UPDATE listening_history SET TimesListened = COALESCE(TimesListened, 0) + 1 WHERE PodcastID = ? AND ListenerID = ?",
                    (podcast_id, self.current_user)
                )
            else:
                cur.execute(
                    "INSERT INTO listening_history (PodcastID, ListenerID, TimesListened) VALUES (?, ?, 1)",
                    (podcast_id, self.current_user)
                )
            conn.commit()
            conn.close()
            messagebox.showinfo("Now Playing", f"Playing '{title}' ({length_mins} mins).\nListening history updated!")
            self.show_podcast_details_screen(title)

        def toggle_favourite():
            if is_favourited:
                Favourites.delete_favourite_programme(title, self.current_user)
            else:
                Favourites.add_to_favourites(podcast_id, self.current_user)
            self.show_podcast_details_screen(title)

        def rate_podcast():
            if times_listened == 0 and personal_rating is None:
                messagebox.showwarning("Listen First", "You must listen to this podcast before rating it.")
                return
            new_rating = simpledialog.askinteger(
                "Rate Podcast", f"Enter your rating for '{title}' (1 to 5):",
                minvalue=1, maxvalue=5, parent=self
            )
            if new_rating:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE listening_history SET RatingGiven = ? WHERE ListenerID = ? AND PodcastID = ?",
                    (new_rating, self.current_user, podcast_id)
                )
                conn.commit()
                conn.close()
                self.show_podcast_details_screen(title)

        play_canvas = tk.Canvas(actions, width=78, height=78, bg=BG_DARK, highlightthickness=0, cursor="hand2")
        play_canvas.pack(side="left", padx=(0, 18))
        play_canvas.create_oval(3, 3, 75, 75, fill=BBC_ORANGE, outline="")
        play_canvas.create_polygon(30, 20, 30, 58, 58, 39, fill=BG_BLACK)
        play_canvas.bind("<Button-1>", lambda e: play_podcast())

        plus_canvas = tk.Canvas(actions, width=42, height=42, bg=BG_DARK, highlightthickness=0, cursor="hand2")
        plus_canvas.pack(side="left", padx=(0, 22))
        plus_canvas.create_oval(2, 2, 40, 40, fill=CARD_GREY, outline="")
        plus_canvas.create_text(21, 21, text="✓" if is_favourited else "+", fill=TEXT_WHITE, font=("Arial", 18, "bold"))
        plus_canvas.bind("<Button-1>", lambda e: toggle_favourite())

        right_links = tk.Frame(actions, bg=BG_DARK)
        right_links.pack(side="left")

        save_lbl = tk.Label(
            right_links,
            text="✚  Remove from playlist" if is_favourited else "✚  Save to your playlist",
            font=("Arial", 14), fg=TEXT_WHITE, bg=BG_DARK, cursor="hand2"
        )
        save_lbl.pack(anchor="w", pady=2)
        save_lbl.bind("<Button-1>", lambda e: toggle_favourite())

        rate_lbl = tk.Label(
            right_links, text="⬆  Rate / Share podcast",
            font=("Arial", 14), fg=TEXT_WHITE, bg=BG_DARK, cursor="hand2"
        )
        rate_lbl.pack(anchor="w", pady=2)
        rate_lbl.bind("<Button-1>", lambda e: rate_podcast())

        back_lbl = tk.Label(
            right_links, text="💔  Not interested / Go Back",
            font=("Arial", 14), fg=TEXT_WHITE, bg=BG_DARK, cursor="hand2"
        )
        back_lbl.pack(anchor="w", pady=2)
        back_lbl.bind("<Button-1>", lambda e: self.show_home_screen())

        # Bottom Divider + Episode Description
        tk.Frame(body, bg="#555555", height=2).pack(fill="x", padx=90, pady=(26, 18))

        desc_frame = tk.Frame(body, bg=BG_DARK)
        desc_frame.pack(fill="x", padx=180)
        tk.Label(
            desc_frame, text="Episode Description",
            font=("Arial", 16), fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            desc_frame,
            text=f"{title.upper()} — A BBC Sounds {category} podcast ({length_mins} minutes). "
                 f"Click the orange play button above to listen and log this episode to your history.",
            font=("Arial", 12), fg="#E0E0E0", bg=BG_DARK, wraplength=760, justify="left"
        ).pack(anchor="w")

    # =========================================================================
    # SCREEN 6: SEARCH RESULTS (Image 6.jpg)
    # =========================================================================
    def show_search_screen(self, keyword=""):
        self.clear_container()
        self.build_top_navbar(self.container, search_prefill=keyword, show_menu_and_profile=False)

        body = tk.Frame(self.container, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text=f"Showing search results for {keyword}" if keyword else "Showing all podcasts",
            font=("Arial", 15), fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=20, pady=(10, 8))

        conn = self.get_db_connection()
        cursor = conn.cursor()
        if keyword:
            cursor.execute(
                "SELECT PodcastID, Title, Category, AverageLengthMins, Rating FROM podcasts "
                "WHERE Title LIKE ? OR Category LIKE ?",
                (f"%{keyword}%", f"%{keyword}%")
            )
        else:
            cursor.execute("SELECT PodcastID, Title, Category, AverageLengthMins, Rating FROM podcasts")
        results = cursor.fetchall()
        conn.close()

        # Categories section
        tk.Label(
            body, text="Categories", font=("Arial", 18),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=20, pady=(2, 6))

        cat_row = tk.Frame(body, bg=BG_DARK)
        cat_row.pack(fill="x", padx=20, pady=(0, 10))
        unique_cats = list(dict.fromkeys([r[2] for r in results])) or ["Comedy", "News", "Sport", "Technology"]
        for cat in unique_cats[:6]:
            cat_card = tk.Label(
                cat_row, text=f"\n{cat}", font=("Arial", 11, "bold"),
                fg=TEXT_WHITE, bg="#2C2C2C", width=15, height=3,
                anchor="sw", padx=10, pady=6, cursor="hand2"
            )
            cat_card.pack(side="left", padx=(0, 10))
            cat_card.bind("<Button-1>", lambda e, c=cat: self.show_search_screen(c))

        # Shows Row with < > Arrows
        tk.Label(
            body, text="Shows", font=("Arial", 18),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=20, pady=(4, 6))

        shows_frame = tk.Frame(body, bg=BG_DARK)
        shows_frame.pack(fill="x", padx=16, pady=(0, 12))

        show_offset = [0]

        def render_shows():
            for w in shows_frame.winfo_children():
                w.destroy()

            subset = results[show_offset[0]:show_offset[0] + 6]
            while len(subset) < 6:
                subset.append((None, "Podcast name", "Items / run time", "", ""))

            for idx, item in enumerate(subset):
                pid, ptitle, pcat, plen, _ = item
                c = tk.Canvas(shows_frame, width=192, height=130, bg=BG_DARK, highlightthickness=0, cursor="hand2" if pid else "arrow")
                c.pack(side="left", padx=6)
                self.create_rounded_rect(c, 2, 2, 190, 128, r=26, fill=CARD_GREY, outline="")
                c.create_text(12, 92, text=ptitle[:19], anchor="w", fill=TEXT_WHITE, font=("Arial", 11, "bold"))
                c.create_text(12, 112, text=f"{pcat} / {plen}m" if pid else "Items / run time", anchor="w", fill="#E0E0E0", font=("Arial", 8))

                # Overlay < > navigation arrows on the 5th card like Image 6
                if idx == 4 and len(results) > 6:
                    c.create_text(145, 65, text="<", fill=TEXT_WHITE, font=("Arial", 26, "bold"))
                    c.create_text(182, 65, text=">", fill=TEXT_WHITE, font=("Arial", 26, "bold"))

                if pid:
                    c.bind("<Button-1>", lambda e, t=ptitle: self.show_podcast_details_screen(t))

        render_shows()

        # Episodes Section (Vertical Rows separated by horizontal lines)
        tk.Label(
            body, text="Episodes", font=("Arial", 18),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=20, pady=(4, 6))

        ep_container = tk.Frame(body, bg=BG_DARK)
        ep_container.pack(fill="both", expand=True)

        display_eps = results[:3] if results else [(None, "No matching podcasts found", "Try another keyword", 0, "")]
        for pid, ptitle, pcat, plen, prating in display_eps:
            row = tk.Frame(ep_container, bg=BG_DARK, cursor="hand2" if pid else "arrow")
            row.pack(fill="x", padx=20, pady=6)

            thumb = tk.Canvas(row, width=110, height=100, bg=BG_DARK, highlightthickness=0)
            thumb.pack(side="left", padx=(0, 18))
            self.create_rounded_rect(thumb, 2, 2, 108, 98, r=22, fill=CARD_GREY, outline="")

            meta = tk.Frame(row, bg=BG_DARK)
            meta.pack(side="left", fill="y", pady=8)
            tk.Label(meta, text=ptitle, font=("Arial", 15), fg=TEXT_WHITE, bg=BG_DARK).pack(anchor="w")
            tk.Label(meta, text=f"Category: {pcat}", font=("Arial", 13), fg="#E0E0E0", bg=BG_DARK).pack(anchor="w", pady=2)
            tk.Label(meta, text=f"{plen} mins  •  Rating: {prating}", font=("Arial", 13), fg="#E0E0E0", bg=BG_DARK).pack(anchor="w")

            tk.Frame(ep_container, bg=TEXT_WHITE, height=1).pack(fill="x", pady=2)

            if pid:
                for w in (row, thumb, meta):
                    w.bind("<Button-1>", lambda e, t=ptitle: self.show_podcast_details_screen(t))

    # =========================================================================
    # SCREEN 7: USER PROFILE (Image 7.jpg)
    # =========================================================================
    def show_profile_screen(self):
        self.clear_container()
        body = tk.Frame(self.container, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # Top Bar: < Back Circle | BBC SOUND | Edit: Pill
        top = tk.Frame(body, bg=BG_DARK)
        top.pack(fill="x", padx=26, pady=16)

        back_c = tk.Canvas(top, width=54, height=54, bg=BG_DARK, highlightthickness=0, cursor="hand2")
        back_c.pack(side="left")
        back_c.create_oval(2, 2, 52, 52, fill=PILL_GREY, outline="")
        back_c.create_text(27, 27, text="<", fill=TEXT_WHITE, font=("Arial", 22, "bold"))
        back_c.bind("<Button-1>", lambda e: self.show_home_screen())

        logo = self.draw_bbc_logo(top, bg_color=BG_DARK, font_size=24)
        logo.pack(side="left", padx=290)

        edit_btn = tk.Button(
            top, text="Edit:", font=("Arial", 16), fg=TEXT_WHITE,
            bg=PILL_GREY, activebackground="#666666", activeforeground=TEXT_WHITE,
            relief="flat", padx=26, pady=6, cursor="hand2",
            command=self.show_survey_genres_screen
        )
        edit_btn.pack(side="right", padx=12)

        # Fetch User Data
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT FavoriteGenres, FavoritePodcasts, LengthPreference FROM listeners WHERE ListenerID = ?",
            (self.current_user,)
        )
        user_info = cursor.fetchone()
        fav_genres_str = user_info[0] if user_info and user_info[0] else ""
        fav_pods_str = user_info[1] if user_info and user_info[1] else ""
        len_pref = user_info[2] if user_info and user_info[2] else "Not set"

        fav_genres = [g.strip() for g in fav_genres_str.split(",") if g.strip()]
        fav_pod_ids = [p.strip() for p in fav_pods_str.split(",") if p.strip()]

        liked_podcasts = []
        if fav_pod_ids:
            placeholders = ",".join("?" for _ in fav_pod_ids)
            cursor.execute(f"SELECT PodcastID, Title, Category FROM podcasts WHERE PodcastID IN ({placeholders})", fav_pod_ids)
            liked_podcasts = cursor.fetchall()
        conn.close()

        # PFP + USERNAME + Personal Info Row
        user_row = tk.Frame(body, bg=BG_DARK)
        user_row.pack(fill="x", padx=36, pady=(6, 18))

        pfp = tk.Canvas(user_row, width=128, height=128, bg=BG_DARK, highlightthickness=0)
        pfp.pack(side="left", padx=(0, 28))
        pfp.create_oval(4, 4, 124, 124, fill="#C5CBD3", outline="")
        pfp.create_text(64, 64, text="PFP", fill=TEXT_WHITE, font=("Arial", 20))

        u_meta = tk.Frame(user_row, bg=BG_DARK)
        u_meta.pack(side="left", pady=22)
        tk.Label(
            u_meta, text=self.current_username_display.upper(),
            font=("Arial", 20), fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w")
        tk.Label(
            u_meta,
            text=f"Preferred Length: {len_pref}  |  Favourite Genres: {len(fav_genres)}",
            font=("Arial", 16), fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", pady=(6, 0))

        # Section: Your playlists (Favourite Genres)
        tk.Label(
            body, text="Your playlists", font=("Arial", 19),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=36, pady=(0, 6))

        pl_row = tk.Frame(body, bg=BG_DARK)
        pl_row.pack(fill="x", padx=32, pady=(0, 14))

        disc_colors = ["#FF6B6B", "#4ECDC4", "#C0392B", "#D7BDE2", "#7F8C8D"]
        for i in range(5):
            g_name = fav_genres[i] if i < len(fav_genres) else "Placeholder Name"
            item_f = tk.Frame(pl_row, bg=BG_DARK, cursor="hand2" if i < len(fav_genres) else "arrow")
            item_f.pack(side="left", padx=10)

            cd = tk.Canvas(item_f, width=148, height=130, bg=BG_DARK, highlightthickness=0)
            cd.pack()
            cd.create_rectangle(6, 4, 142, 126, fill="#1E1E1E", outline="#888888", width=2)
            cd.create_oval(22, 12, 126, 116, fill=disc_colors[i % len(disc_colors)], outline="#CCCCCC", width=2)
            cd.create_oval(58, 48, 90, 80, fill="#111111", outline="#FFFFFF", width=2)

            lbl = tk.Label(item_f, text=g_name[:18], font=("Arial", 11), fg=TEXT_WHITE, bg=BG_DARK)
            lbl.pack(pady=(4, 0))

            if i < len(fav_genres):
                for w in (item_f, cd, lbl):
                    w.bind("<Button-1>", lambda e, g=g_name: self.show_search_screen(g))

        see_pl_btn = tk.Button(
            pl_row, text="See all playlists", font=("Arial", 11),
            fg=TEXT_WHITE, bg=PILL_GREY, relief="flat", padx=12, pady=8,
            cursor="hand2", command=self.show_survey_genres_screen
        )
        see_pl_btn.pack(side="left", padx=14)

        # Section: Your Liked Podcasts
        tk.Label(
            body, text="Your Liked Podcasts", font=("Arial", 19),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=36, pady=(4, 8))

        liked_row = tk.Frame(body, bg=BG_DARK)
        liked_row.pack(fill="x", padx=32, pady=(0, 18))

        for i in range(5):
            pod = liked_podcasts[i] if i < len(liked_podcasts) else None
            c = tk.Canvas(liked_row, width=148, height=135, bg=BG_DARK, highlightthickness=0, cursor="hand2" if pod else "arrow")
            c.pack(side="left", padx=10)
            self.create_rounded_rect(c, 4, 4, 144, 131, r=24, fill="#1B1B1B" if pod else "#2A2A2A", outline="#555555", width=2)
            if pod:
                c.create_oval(28, 16, 120, 108, outline=BBC_ORANGE, width=2)
                c.create_text(74, 62, text=pod[1][:16], fill=TEXT_WHITE, font=("Arial", 10, "bold"), width=110, justify="center")
                c.create_text(74, 118, text=pod[2], fill=BBC_ORANGE, font=("Arial", 9))
                c.bind("<Button-1>", lambda e, t=pod[1]: self.show_podcast_details_screen(t))
            else:
                c.create_text(74, 68, text="Empty Slot", fill=TEXT_MUTED, font=("Arial", 11))

        see_pod_btn = tk.Button(
            liked_row, text="See all Podcasts", font=("Arial", 11),
            fg=TEXT_WHITE, bg=PILL_GREY, relief="flat", padx=12, pady=8,
            cursor="hand2", command=lambda: self.show_search_screen("")
        )
        see_pod_btn.pack(side="left", padx=14)

        # Bottom Row: Podcasts you rated -> [ See rated podcasts ]
        rated_footer = tk.Frame(body, bg=BG_DARK)
        rated_footer.pack(anchor="w", padx=36, pady=(6, 12))

        tk.Label(
            rated_footer, text="Podcasts you rated",
            font=("Arial", 20), fg=TEXT_WHITE, bg=BG_DARK
        ).pack(side="left", padx=(0, 32))

        tk.Button(
            rated_footer, text="See rated podcasts", font=("Arial", 17),
            fg=TEXT_WHITE, bg="#262626", activebackground=BBC_ORANGE,
            activeforeground=TEXT_WHITE, relief="flat", padx=36, pady=12,
            cursor="hand2", command=self.show_rated_podcasts_screen
        ).pack(side="left")

    # =========================================================================
    # SCREEN 8: PODCASTS YOU RATED (Image 8.jpg)
    # =========================================================================
    def show_rated_podcasts_screen(self):
        self.clear_container()
        body = tk.Frame(self.container, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # Top Header: BBC SOUND + Back Button
        top = tk.Frame(body, bg=BG_DARK)
        top.pack(fill="x", padx=34, pady=(22, 8))

        logo = self.draw_bbc_logo(top, bg_color=BG_DARK, font_size=24)
        logo.pack(side="left")

        tk.Button(
            top, text="← Back to Profile", font=("Arial", 12),
            fg=TEXT_WHITE, bg=PILL_GREY, relief="flat", padx=16, pady=6,
            cursor="hand2", command=self.show_profile_screen
        ).pack(side="right")

        tk.Label(
            body, text="Podcasts you rated", font=("Arial", 26),
            fg=TEXT_WHITE, bg=BG_DARK
        ).pack(anchor="w", padx=36, pady=(4, 20))

        # Fetch rated podcasts from listening_history
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT podcasts.PodcastID, podcasts.Title, podcasts.Category, listening_history.RatingGiven
            FROM podcasts
            JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID
            WHERE listening_history.ListenerID = ?
            AND listening_history.RatingGiven IS NOT NULL
            """,
            (self.current_user,)
        )
        rated_items = cursor.fetchall()
        conn.close()

        cards_row = tk.Frame(body, bg=BG_DARK)
        cards_row.pack(fill="x", padx=28, pady=(0, 34))

        selected_rated = [rated_items[0] if rated_items else None]

        if not rated_items:
            tk.Label(
                cards_row,
                text="You haven't rated any podcasts yet. Listen to a podcast and give it 1–5 stars!",
                font=("Arial", 15), fg=TEXT_MUTED, bg=BG_DARK
            ).pack(anchor="w", padx=12, pady=40)
        else:
            for pid, ptitle, pcat, r_val in rated_items[:5]:
                col = tk.Frame(cards_row, bg=BG_DARK, cursor="hand2")
                col.pack(side="left", padx=14)

                art = tk.Canvas(col, width=185, height=175, bg=BG_DARK, highlightthickness=0)
                art.pack()
                self.create_rounded_rect(art, 4, 4, 181, 171, r=24, fill="#1A1A1A", outline=BBC_ORANGE, width=2)
                art.create_text(92, 75, text=ptitle, fill=TEXT_WHITE, font=("Arial", 14, "bold"), width=155, justify="center")
                art.create_text(92, 138, text=pcat, fill="#CCCCCC", font=("Arial", 11))

                # 5 Stars Row matching Image 8
                stars_f = tk.Frame(col, bg=BG_DARK)
                stars_f.pack(pady=(10, 0))
                rating_int = int(r_val)
                for s in range(1, 6):
                    tk.Label(
                        stars_f,
                        text="★",
                        font=("Arial", 22),
                        fg=STAR_GOLD if s <= rating_int else STAR_DIM,
                        bg=BG_DARK
                    ).pack(side="left", padx=2)

                for w in (col, art):
                    w.bind("<Button-1>", lambda e, item=(pid, ptitle, pcat, r_val): selected_rated.__setitem__(0, item))

        # Three Rounded Pill Action Buttons matching Image 8
        pills_frame = tk.Frame(body, bg=BG_DARK)
        pills_frame.pack(anchor="w", padx=42, pady=10)

        def pick_rated_podcast(action_label):
            if not rated_items:
                messagebox.showinfo("No Ratings", "You have no rated podcasts.")
                return None
            if len(rated_items) == 1:
                return rated_items[0]
            titles = [r[1] for r in rated_items]
            chosen = simpledialog.askstring(
                action_label,
                f"Enter podcast title to {action_label.lower()}:\nAvailable: {', '.join(titles)}",
                initialvalue=selected_rated[0][1] if selected_rated[0] else titles[0],
                parent=self
            )
            if not chosen:
                return None
            return next((r for r in rated_items if r[1].lower() == chosen.strip().lower()), None)

        def edit_review():
            target = pick_rated_podcast("Edit a review")
            if not target:
                return
            new_val = simpledialog.askinteger(
                "Edit Rating", f"Enter new rating (1-5) for '{target[1]}':",
                minvalue=1, maxvalue=5, initialvalue=int(target[3]), parent=self
            )
            if new_val:
                conn = self.get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE listening_history SET RatingGiven = ? WHERE ListenerID = ? AND PodcastID = ?",
                    (new_val, self.current_user, target[0])
                )
                conn.commit()
                conn.close()
                self.show_rated_podcasts_screen()

        def delete_review():
            target = pick_rated_podcast("Delete a review")
            if not target:
                return
            if messagebox.askyesno("Confirm Delete", f"Remove your rating for '{target[1]}'?"):
                Rating.remove_rating(target[0], self.current_user)
                self.show_rated_podcasts_screen()

        def share_review():
            target = pick_rated_podcast("Share your review")
            if not target:
                return
            share_text = f"I rated '{target[1]}' {int(target[3])}/5 stars on BBC Sounds!"
            self.clipboard_clear()
            self.clipboard_append(share_text)
            messagebox.showinfo("Copied to Clipboard", f"Ready to share:\n\n{share_text}")

        for btn_text, cmd in [
            ("Edit a review:", edit_review),
            ("Delete a review:", delete_review),
            ("Share your review:", share_review),
        ]:
            btn = tk.Button(
                pills_frame, text=btn_text, font=("Arial", 20),
                fg=TEXT_WHITE, bg=PILL_GREY, activebackground=BBC_ORANGE,
                activeforeground=TEXT_WHITE, relief="flat", padx=28, pady=12,
                cursor="hand2", command=cmd
            )
            btn.pack(anchor="w", pady=12)

    # =========================================================================
    # EXTRA PROJECT INTEGRATIONS (Listening History, Report, Reset Survey)
    # =========================================================================
    def show_listening_history_modal(self):
        win = tk.Toplevel(self)
        win.title("Listening History")
        win.geometry("620x460")
        win.configure(bg=BG_DARK)

        tk.Label(win, text="Your Listening History", font=("Arial", 18, "bold"), fg=TEXT_WHITE, bg=BG_DARK).pack(pady=14)

        listbox = tk.Listbox(win, bg="#1E1E1E", fg=TEXT_WHITE, font=("Arial", 12), selectbackground=BBC_ORANGE)
        listbox.pack(fill="both", expand=True, padx=24, pady=8)

        def refresh_list():
            listbox.delete(0, "end")
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT podcasts.Title, listening_history.TimesListened FROM podcasts "
                "JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID "
                "WHERE listening_history.ListenerID = ?",
                (self.current_user,)
            )
            rows = cur.fetchall()
            conn.close()
            for title, count in rows:
                listbox.insert("end", f"{title}  —  Listened {count or 0} time(s)")

        refresh_list()

        btn_bar = tk.Frame(win, bg=BG_DARK)
        btn_bar.pack(pady=14)

        def remove_selected():
            sel = listbox.curselection()
            if not sel:
                return
            title = listbox.get(sel[0]).split("  —  ")[0]
            ListeningHistory.remove_from_listening_history(title, self.current_user)
            refresh_list()

        def clear_all():
            if messagebox.askyesno("Confirm", "Delete your entire listening history?", parent=win):
                ListeningHistory.delete_listening_history(self.current_user)
                refresh_list()

        tk.Button(btn_bar, text="Remove Selected", bg=PILL_GREY, fg=TEXT_WHITE, relief="flat", padx=14, pady=6, command=remove_selected).pack(side="left", padx=8)
        tk.Button(btn_bar, text="Clear All History", bg="#B00020", fg=TEXT_WHITE, relief="flat", padx=14, pady=6, command=clear_all).pack(side="left", padx=8)

    def show_listening_report_modal(self):
        win = tk.Toplevel(self)
        win.title("Listening Report")
        win.geometry("640x480")
        win.configure(bg=BG_DARK)

        tk.Label(win, text="BBC Sounds Listening Report", font=("Arial", 18, "bold"), fg=BBC_ORANGE, bg=BG_DARK).pack(pady=14)

        conn = self.get_db_connection()
        query = """
            SELECT podcasts.Title, listening_history.TimesListened, listening_history.RatingGiven
            FROM podcasts
            JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID
            WHERE listening_history.ListenerID = ?
            ORDER BY listening_history.TimesListened DESC
        """
        df = pd.read_sql_query(query, conn, params=(self.current_user,))
        conn.close()

        report_box = tk.Text(win, bg="#1E1E1E", fg=TEXT_WHITE, font=("Arial", 12), relief="flat", padx=16, pady=12)
        report_box.pack(fill="both", expand=True, padx=24, pady=(0, 18))

        if df.empty:
            report_box.insert("end", "You have no listening history yet.")
        else:
            lines = [
                f"Total unique podcasts listened to: {len(df)}",
                f"Most listened podcast: '{df.iloc[0]['Title']}' ({df.iloc[0]['TimesListened']} listens)",
                f"Least listened podcast: '{df.iloc[-1]['Title']}' ({df.iloc[-1]['TimesListened']} listens)",
            ]
            df_rated = df.dropna(subset=["RatingGiven"])
            if not df_rated.empty:
                lines.append(f"Highest rating given: {df_rated['RatingGiven'].max()}  |  Lowest: {df_rated['RatingGiven'].min()}")
                lines.append(f"Average rating across rated podcasts: {df_rated['RatingGiven'].mean():.2f}")
            else:
                lines.append("You have not rated any podcasts yet.")

            lines.append("\nBreakdown (Most to Least Listened):")
            for _, row in df.iterrows():
                lines.append(f"  • {row['Title']} — {row['TimesListened']} listens (Rating: {row['RatingGiven']})")

            report_box.insert("end", "\n".join(lines))

        report_box.configure(state="disabled")

    def reset_survey_action(self):
        if messagebox.askyesno("Reset Survey", "Delete your current survey responses?"):
            Survey.delete_survey(self.current_user)
            self.selected_survey_genres = []
            self.show_survey_genres_screen()


if __name__ == "__main__":
    app = BBCSoundsGUI()
    app.mainloop()