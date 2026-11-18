from contextlib import contextmanager
import math
import sqlite3
import tkinter as tk
import xml.etree.ElementTree as ET
from pathlib import Path
from tkinter import messagebox, simpledialog

ROOT_PATH = Path(__file__).resolve().parent
DATABASE_PATH = ROOT_PATH / "database.db"
CANVA_DIR = ROOT_PATH / "canva design"

DARK_BG = "#101113"
SIDEBAR_BG = "#17181b"
CARD_BG = "#1b1d21"
INPUT_BG = "#22252a"
BORDER_LINE = "#303339"
ORANGE_ACCENT = "#ff751f"
ORANGE_HL = "#ff914d"
TEXT_WHITE = "#f7f7f7"
TEXT_GRAY = "#a8abb1"
TEXT_LIGHT = "#d6d8dc"
GOLD_STAR = "#ffd166"
DEFAULT_FONT = "Segoe UI"

GENRE_LIST = [
    "News", "Travel", "History", "Comedy", "True Crime", "Technology",
    "Science", "Business", "Gaming", "Entertainment", "Sport", "Health",
]
DURATION_RANGES = {"Short": (0, 30), "Medium": (25, 45), "Long": (45, 60)}
PALETTE_SWATCHES = ["#5b315e", "#185a70", "#7a3d2d", "#2e6654", "#6c5631", "#373e79"]
GENRE_TILE_DETAILS = {
    "News": ("#7a2838", "N", "Headlines, investigations and current affairs"),
    "Travel": ("#176c78", "✈", "Journeys, places and stories from around the world"),
    "History": ("#76512d", "H", "People and events that shaped our world"),
    "Comedy": ("#7b3f91", "☺", "Stand-up, panel shows and funny conversations"),
    "True Crime": ("#633344", "?", "Real cases, mysteries and investigations"),
    "Technology": ("#285d8b", ">_", "Digital culture, inventions and the future"),
    "Science": ("#23705b", "Σ", "Discoveries, nature and how things work"),
    "Business": ("#6f5d24", "£", "Money, markets, careers and entrepreneurship"),
    "Gaming": ("#394a91", "+", "Games, creators and player culture"),
    "Entertainment": ("#9a3e67", "★", "Film, television, music and celebrity stories"),
    "Sport": ("#39713b", "●", "Matches, athletes and expert sporting analysis"),
    "Health": ("#8a4b35", "♥", "Wellbeing, medicine and healthier living"),
}
GENRE_CIRCLE_COLOURS = [
    ("#b79cff", "#5e17eb", "#2e0b70"), ("#9cecff", "#38b6ff", "#0b4f78"),
    ("#ffb7ad", "#e84a5f", "#7c1f2c"), ("#b9f4c7", "#43aa8b", "#175b49"),
    ("#ffe8a6", "#f9c74f", "#80600b"), ("#d9bcff", "#8d1370", "#49083a"),
    ("#9dfff0", "#1bd5d3", "#087675"), ("#ffc8f0", "#ff5cb8", "#80245d"),
    ("#bed0ff", "#4b56d2", "#252a75"), ("#ffd4ad", "#ff914d", "#8c3b0d"),
    ("#c4f2ff", "#56ccf2", "#1d6880"), ("#f5d0ff", "#b54dce", "#5d176d"),
]


def format_user_id(uid):
    cleaned_id = str(uid).strip()
    return int(cleaned_id) if cleaned_id.isdigit() else cleaned_id


def sanitize_column_name(col):
    return '"' + str(col).replace('"', '""') + '"'


def blend_colour(hex_colour, target_colour, amount):
    """Blend two #RRGGBB colours for generated programme artwork."""
    source = tuple(int(hex_colour[pos:pos + 2], 16) for pos in (1, 3, 5))
    target = tuple(int(target_colour[pos:pos + 2], 16) for pos in (1, 3, 5))
    mixed = tuple(round(start + (end - start) * amount) for start, end in zip(source, target))
    return "#" + "".join(f"{channel:02x}" for channel in mixed)


class BBCSoundsGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BBC Sounds | Discover something new")
        self.geometry("1320x850")
        self.minsize(1024, 700)
        self.configure(bg=DARK_BG)

        self._base_tk_scaling = float(self.tk.call("tk", "scaling"))
        self._ui_scale_factor = 1.0
        self._resize_after_id = None

        self.current_user = None
        self.active_genres = []
        self.active_length = "Medium"
        self.svg_store = {}
        self.image_store = {}
        self.genre_elements = {}
        self.length_buttons = {}
        self.search_text = tk.StringVar()
        self.current_page = None
        self._sort_sql = None
        self._pending_render_id = None
        self._render_queue = []
        self._search_after_id = None
        self._live_search_callback = None
        self._search_entry = None
        self._search_prompt = None

        self.bind("<Configure>", self.schedule_interface_scaling)
        self.show_login()

    def schedule_interface_scaling(self, event):
        if event.widget is not self:
            return
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(120, self.apply_interface_scaling)

    def apply_interface_scaling(self):
        """Scale point-based UI elements to suit the current window dimensions."""
        self._resize_after_id = None
        width_factor = self.winfo_width() / 1320
        height_factor = self.winfo_height() / 850
        new_scale_factor = max(0.84, min(1.25, min(width_factor, height_factor)))
        if abs(new_scale_factor - self._ui_scale_factor) < 0.035:
            return
        self._ui_scale_factor = new_scale_factor
        self.tk.call("tk", "scaling", self._base_tk_scaling * new_scale_factor)
        pending_widgets = list(self.winfo_children())
        while pending_widgets:
            widget = pending_widgets.pop()
            pending_widgets.extend(widget.winfo_children())
            try:
                font_spec = widget.cget("font")
                if font_spec:
                    widget.configure(font=font_spec)
            except tk.TclError:
                pass
        self.update_idletasks()

    @contextmanager
    def get_db_connection(self):
        conn = sqlite3.connect(str(DATABASE_PATH), timeout=8)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_listener_data(self):
        if self.current_user is None:
            return None
        with self.get_db_connection() as conn:
            return conn.execute(
                "SELECT * FROM listeners WHERE ListenerID = ?", (self.current_user,)
            ).fetchone()

    @staticmethod
    def get_row_field(row, key_name, default_val=None):
        if row is None:
            return default_val
        lookup_dict = {k.lower(): row[k] for k in row.keys()}
        return lookup_dict.get(key_name.lower(), default_val)

    def determine_sort_sql(self):
        if self._sort_sql is not None:
            return self._sort_sql
        with self.get_db_connection() as conn:
            columns_map = {row[1].lower(): row[1] for row in conn.execute("PRAGMA table_info(podcasts)")}
        for candidate in ("averagerating", "average_rating", "ratingaverage"):
            if candidate in columns_map:
                self._sort_sql = sanitize_column_name(columns_map[candidate]) + " DESC"
                break
        else:
            self._sort_sql = "Title COLLATE NOCASE ASC"
        return self._sort_sql

    def get_single_podcast(self, pid):
        with self.get_db_connection() as conn:
            return conn.execute(
                "SELECT PodcastID, Title, Category, AverageLengthMins "
                "FROM podcasts WHERE PodcastID = ?",
                (pid,),
            ).fetchone()

    def query_podcasts(self, search_term="", item_limit=100):
        query_str = "SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts"
        params = []
        if search_term.strip():
            pattern = f"%{search_term.strip()}%"
            query_str += " WHERE Title LIKE ? OR Category LIKE ?"
            params.extend([pattern, pattern])
        query_str += f" ORDER BY {self.determine_sort_sql()} LIMIT ?"
        params.append(item_limit)
        with self.get_db_connection() as conn:
            return conn.execute(query_str, params).fetchall()

    def fetch_user_history(self):
        with self.get_db_connection() as conn:
            return conn.execute(
                "SELECT p.PodcastID, p.Title, p.Category, p.AverageLengthMins, "
                "h.TimesListened, h.RatingGiven "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ? ORDER BY COALESCE(h.TimesListened, 0) DESC, "
                "p.Title COLLATE NOCASE",
                (self.current_user,),
            ).fetchall()

    def fetch_user_favourites(self):
        listener_row = self.get_listener_data()
        raw_favs = self.get_row_field(listener_row, "FavoritePodcasts", "") or ""
        id_list = [item.strip() for item in str(raw_favs).split(",") if item.strip()]
        if not id_list:
            return []
        placeholders = ",".join("?" for _ in id_list)
        with self.get_db_connection() as conn:
            return conn.execute(
                f"SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts "
                f"WHERE PodcastID IN ({placeholders}) ORDER BY Title COLLATE NOCASE",
                id_list,
            ).fetchall()

    def fetch_user_ratings(self):
        with self.get_db_connection() as conn:
            return conn.execute(
                "SELECT p.PodcastID, p.Title, p.Category, h.RatingGiven, h.TimesListened "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ? AND h.RatingGiven IS NOT NULL "
                "ORDER BY p.Title COLLATE NOCASE",
                (self.current_user,),
            ).fetchall()

    def get_custom_recommendations(self, count_limit=8):
        listener_row = self.get_listener_data()
        user_genres = [
            g.strip()
            for g in str(self.get_row_field(listener_row, "FavoriteGenres", "") or "").split(",")
            if g.strip()
        ]
        preferred_len = self.get_row_field(listener_row, "LengthPreference", None)
        if not user_genres or preferred_len not in DURATION_RANGES:
            return []
        low_limit, high_limit = DURATION_RANGES[preferred_len]
        marks = ",".join("?" for _ in user_genres)
        with self.get_db_connection() as conn:
            return conn.execute(
                f"SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts "
                f"WHERE Category IN ({marks}) AND AverageLengthMins BETWEEN ? AND ? "
                f"ORDER BY {self.determine_sort_sql()} LIMIT ?",
                (*user_genres, low_limit, high_limit, count_limit),
            ).fetchall()

    def check_if_favourited(self, pid):
        listener_row = self.get_listener_data()
        favourite_string = str(self.get_row_field(listener_row, "FavoritePodcasts", "") or "")
        return str(pid) in [val.strip() for val in favourite_string.split(",")]

    def show_db_error(self, title_text, err_obj):
        messagebox.showerror(title_text, str(err_obj), parent=self)

    def load_svg_images(self, filename):
        if filename in self.svg_store:
            return self.svg_store[filename]
        extracted_list = []
        target_file = CANVA_DIR / filename
        try:
            root_elem = ET.parse(str(target_file)).getroot()
            for node in root_elem.iter():
                if node.tag.split("}")[-1] != "image":
                    continue
                link = node.attrib.get("href") or node.attrib.get("{http://www.w3.org/1999/xlink}href", "")
                if not link.startswith("data:image/png;base64,"):
                    continue
                b64_payload = link.split(",", 1)[1]
                try:
                    w_val = float(node.attrib.get("width", 0))
                    h_val = float(node.attrib.get("height", 0))
                    extracted_list.append((w_val, h_val, b64_payload))
                except (TypeError, ValueError):
                    continue
        except (OSError, ET.ParseError):
            extracted_list = []
        self.svg_store[filename] = extracted_list
        return extracted_list

    def get_svg_photo_object(self, filename, index=0, dimensions=(240, 260)):
        cache_key = (filename, index, dimensions)
        if cache_key in self.image_store:
            return self.image_store[cache_key]
        image_list = self.load_svg_images(filename)
        if not image_list:
            return None
        target_img = image_list[index % len(image_list)]
        try:
            photo = tk.PhotoImage(data=target_img[2], master=self)
            max_w, max_h = dimensions
            ratio = max(
                1,
                int(math.ceil(photo.width() / float(max_w))),
                int(math.ceil(photo.height() / float(max_h))),
            )
            if ratio > 1:
                photo = photo.subsample(ratio, ratio)
            self.image_store[cache_key] = photo
            return photo
        except tk.TclError:
            return None

    @staticmethod
    def create_label(container, text_val, text_size=12, text_color=TEXT_WHITE, font_weight="normal", **kwargs):
        return tk.Label(
            container,
            text=text_val,
            font=(DEFAULT_FONT, text_size, font_weight),
            fg=text_color,
            bg=kwargs.pop("bg", container.cget("bg")),
            justify=kwargs.pop("justify", "left"),
            anchor=kwargs.pop("anchor", "w"),
            **kwargs,
        )

    @staticmethod
    def create_button(container, text_val, command_func, primary=False, compact=False, **kwargs):
        return tk.Button(
            container,
            text=text_val,
            command=command_func,
            font=(DEFAULT_FONT, 10 if compact else 11, "bold" if primary else "normal"),
            bg=ORANGE_ACCENT if primary else INPUT_BG,
            fg=TEXT_WHITE if primary else TEXT_LIGHT,
            activebackground=ORANGE_HL if primary else BORDER_LINE,
            activeforeground=TEXT_WHITE,
            disabledforeground=TEXT_GRAY,
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=13 if compact else 17,
            pady=7 if compact else 10,
            **kwargs,
        )

    @staticmethod
    def create_card_frame(container, **kwargs):
        return tk.Frame(
            container,
            bg=kwargs.pop("bg", CARD_BG),
            highlightthickness=1,
            highlightbackground=BORDER_LINE,
            **kwargs,
        )

    def draw_app_logo(self, container, scaling=1):
        row_frame = tk.Frame(container, bg=container.cget("bg"))
        for char in "BBC":
            tk.Label(
                row_frame,
                text=char,
                font=(DEFAULT_FONT, int(11 * scaling), "bold"),
                fg=DARK_BG,
                bg=TEXT_WHITE,
                padx=int(4 * scaling),
                pady=int(1 * scaling),
            ).pack(side="left", padx=(0, 2))
        self.create_label(row_frame, "SOUNDS", int(13 * scaling), TEXT_WHITE, "bold").pack(
            side="left", padx=(6, 0)
        )
        return row_frame

    def render_section_title(self, container, heading, description=None, button_label=None, action_func=None):
        header_bar = tk.Frame(container, bg=container.cget("bg"))
        header_bar.pack(fill="x", pady=(18, 10))
        text_pane = tk.Frame(header_bar, bg=container.cget("bg"))
        text_pane.pack(side="left", fill="x", expand=True)
        self.create_label(text_pane, heading, 18, TEXT_WHITE, "bold").pack(anchor="w")
        if description:
            self.create_label(text_pane, description, 10, TEXT_GRAY).pack(anchor="w", pady=(3, 0))
        if button_label and action_func:
            self.create_button(header_bar, button_label, action_func, compact=True).pack(side="right")
        return header_bar

    def render_page_title(self, container, main_heading, sub_heading=""):
        self.create_label(
            container, main_heading, 25, TEXT_WHITE, "bold",
            anchor="center", justify="center",
        ).pack(fill="x", pady=(4, 3))
        if sub_heading:
            self.create_label(
                container, sub_heading, 11, TEXT_GRAY,
                anchor="center", justify="center",
            ).pack(fill="x", pady=(0, 16))

    def render_decorative_panel(self, container, filename, idx, bounds, width_px, height_px, label_txt=""):
        frame_box = tk.Frame(container, bg=PALETTE_SWATCHES[idx % len(PALETTE_SWATCHES)], width=width_px, height=height_px)
        frame_box.pack_propagate(False)
        img_photo = self.get_svg_photo_object(filename, idx, bounds)
        if img_photo:
            img_lbl = tk.Label(frame_box, image=img_photo, bg=frame_box.cget("bg"))
            img_lbl.image = img_photo
            img_lbl.pack(expand=True, pady=(5, 0))
        else:
            canvas_obj = tk.Canvas(frame_box, width=width_px, height=height_px, bg=frame_box.cget("bg"), highlightthickness=0)
            canvas_obj.pack(fill="both", expand=True)
            canvas_obj.create_oval(width_px * 0.22, height_px * 0.12, width_px * 0.78, height_px * 0.72, outline="#ffffff55", width=3)
            canvas_obj.create_arc(
                width_px * 0.28, height_px * 0.18, width_px * 0.72, height_px * 0.62,
                start=25, extent=300, style="arc", outline=ORANGE_HL, width=5
            )
            canvas_obj.create_text(width_px / 2, height_px * 0.43, text="♪", fill=TEXT_WHITE, font=(DEFAULT_FONT, 36, "bold"))
        if label_txt:
            self.create_label(frame_box, label_txt, 9, TEXT_WHITE, "bold", anchor="center", bg=frame_box.cget("bg")).pack(
                side="bottom", fill="x", pady=(0, 7)
            )
        return frame_box

    def generate_podcast_cover(self, container, pid, title_text, category_text, width_px, height_px, compact=False):
        fallback_colours = ["#6e4dbb", "#d85d43", "#178d9a", "#b44272", "#658d31", "#c47b1c"]
        try:
            design_idx = int(pid)
        except (TypeError, ValueError):
            design_idx = sum(ord(char) for char in str(title_text))

        category_name = str(category_text or "BBC Sounds")
        genre_details = GENRE_TILE_DETAILS.get(category_name)
        bg_tone = genre_details[0] if genre_details else fallback_colours[design_idx % len(fallback_colours)]
        genre_icon = genre_details[1] if genre_details else category_name[:1].upper()
        highlight_tone = blend_colour(bg_tone, "#ffffff", 0.48)
        soft_tone = blend_colour(bg_tone, "#ffffff", 0.18)
        shade_tone = blend_colour(bg_tone, "#000000", 0.58)

        cnv = tk.Canvas(container, width=width_px, height=height_px, bg=bg_tone, highlightthickness=0, cursor="hand2")
        cnv.pack_propagate(False)

        # Layered shapes give each generated cover the feel of designed podcast artwork.
        if design_idx % 3 == 0:
            cnv.create_polygon(
                0, height_px * 0.18, width_px, 0, width_px, height_px * 0.42, 0, height_px * 0.62,
                fill=soft_tone, outline="",
            )
        elif design_idx % 3 == 1:
            cnv.create_oval(-width_px * 0.22, -height_px * 0.3, width_px * 0.82, height_px * 0.72,
                            fill=soft_tone, outline="")
            cnv.create_oval(width_px * 0.62, height_px * 0.08, width_px * 1.15, height_px * 0.66,
                            fill=highlight_tone, outline="")
        else:
            stripe_width = max(5, width_px // 10)
            for stripe_x in range(-height_px, width_px, stripe_width * 2):
                cnv.create_polygon(
                    stripe_x, 0, stripe_x + stripe_width, 0,
                    stripe_x + height_px + stripe_width, height_px, stripe_x + height_px, height_px,
                    fill=soft_tone, outline="",
                )

        cnv.create_text(
            width_px * 0.08, height_px * 0.09, text="BBC  SOUNDS", anchor="nw",
            fill=TEXT_WHITE, font=(DEFAULT_FONT, max(6, width_px // 25), "bold"),
        )

        disc_size = min(width_px, height_px) * (0.46 if compact else 0.42)
        disc_x = width_px * (0.5 if compact else 0.74)
        disc_y = height_px * (0.49 if compact else 0.43)
        cnv.create_oval(
            disc_x - disc_size / 2 - 3, disc_y - disc_size / 2 - 3,
            disc_x + disc_size / 2 + 3, disc_y + disc_size / 2 + 3,
            fill=shade_tone, outline=TEXT_WHITE, width=max(1, width_px // 70),
        )
        cnv.create_oval(
            disc_x - disc_size / 2 + 5, disc_y - disc_size / 2 + 5,
            disc_x + disc_size / 2 - 5, disc_y + disc_size / 2 - 5,
            fill=bg_tone, outline=highlight_tone, width=max(1, width_px // 80),
        )
        cnv.create_text(
            disc_x, disc_y, text=genre_icon, fill=TEXT_WHITE,
            font=(DEFAULT_FONT, max(12, int(disc_size * 0.34)), "bold"),
        )

        footer_height = height_px * (0.25 if compact else 0.33)
        cnv.create_rectangle(0, height_px - footer_height, width_px, height_px, fill=shade_tone, outline="")
        cnv.create_text(
            width_px * 0.08, height_px - footer_height + height_px * 0.055,
            text=category_name.upper()[:22], anchor="nw", fill=highlight_tone,
            font=(DEFAULT_FONT, max(6, width_px // 24), "bold"),
        )
        if not compact:
            cover_title = " ".join(str(title_text).upper().split()[:5])
            cnv.create_text(
                width_px * 0.08, height_px - footer_height + height_px * 0.145,
                text=cover_title[:38], anchor="nw", width=width_px * 0.84, fill=TEXT_WHITE,
                font=(DEFAULT_FONT, max(8, width_px // 19), "bold"),
            )
        return cnv

    def create_star_rating_bar(self, container, score_val, star_size=18, background_col=None):
        row_pane = tk.Frame(container, bg=background_col or container.cget("bg"))
        numeric_score = int(score_val or 0)
        for val in range(1, 6):
            star_color = GOLD_STAR if val <= numeric_score else "#53575d"
            self.create_label(row_pane, "★", star_size, star_color, bg=row_pane.cget("bg")).pack(
                side="left", padx=1
            )
        return row_pane

    def create_genre_circle(self, container, genre_name, idx, size=54, background_col=CARD_BG):
        light_col, middle_col, outline_col = GENRE_CIRCLE_COLOURS[idx % len(GENRE_CIRCLE_COLOURS)]
        circle_canvas = tk.Canvas(container, width=size, height=size, bg=background_col, highlightthickness=0, cursor="hand2")
        for inset, fill_col in [(2, outline_col), (5, middle_col), (10, light_col), (16, middle_col)]:
            circle_canvas.create_oval(inset, inset, size - inset, size - inset, fill=fill_col, outline="")
        circle_canvas.create_oval(2, 2, size - 2, size - 2, outline=outline_col, width=2)
        circle_canvas.create_text(size / 2, size / 2, text=genre_name[:1].upper(), fill=TEXT_WHITE, font=(DEFAULT_FONT, 14, "bold"))
        return circle_canvas

    def create_default_profile_avatar(self, container, size=112):
        """Draw a clean, neutral white-and-grey default avatar."""
        avatar = tk.Canvas(
            container, width=size, height=size, bg=container.cget("bg"),
            highlightthickness=0,
        )
        centre = size / 2
        outer_margin = size * 0.06
        avatar.create_oval(
            outer_margin, outer_margin,
            size - outer_margin, size - outer_margin,
            fill="#55585e", outline="#e7e8ea", width=3,
        )

        head_radius = size * 0.16
        head_y = size * 0.38
        shoulder_top = size * 0.57
        silhouette = "#f4f4f5"
        avatar.create_oval(
            centre - head_radius, head_y - head_radius,
            centre + head_radius, head_y + head_radius,
            fill=silhouette, outline="",
        )
        avatar.create_oval(
            size * 0.23, shoulder_top,
            size * 0.77, size * 0.88,
            fill=silhouette, outline="",
        )
        avatar.create_rectangle(
            size * 0.18, size * 0.79, size * 0.82, size * 0.92,
            fill="#55585e", outline="",
        )
        return avatar

    def render_podcast_card(
        self, parent_widget, podcast_data, compact=False,
        show_play_btn=False, show_remove_btn=False, rating_value=None,
    ):
        pid, title, category, length_mins = podcast_data[:4]
        card_frame = self.create_card_frame(parent_widget)
        meta_info = str(category or "Programme")
        if length_mins is not None:
            meta_info += f"  ·  {length_mins} min"

        if compact:
            card_frame.pack(fill="x", pady=5)
            cover = self.generate_podcast_cover(card_frame, pid, title, category, 92, 92, compact=True)
            cover.pack(side="left", padx=11, pady=10)
            details_pane = tk.Frame(card_frame, bg=CARD_BG)
            details_pane.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=12)
            self.create_label(details_pane, title, 12, TEXT_WHITE, "bold").pack(anchor="w")
            self.create_label(details_pane, meta_info, 10, TEXT_GRAY).pack(anchor="w", pady=(5, 0))
            self.create_button(details_pane, "View details", lambda target_id=pid: self.show_detail(target_id), compact=True).pack(
                anchor="w", pady=(9, 0)
            )
            if show_play_btn:
                self.create_button(card_frame, "▶  Listen", lambda target_id=pid: self.listen(target_id), primary=True, compact=True).pack(
                    side="right", padx=12
                )
            if show_remove_btn:
                self.create_button(card_frame, "Remove", lambda target_id=pid: self.remove_from_history(target_id), compact=True).pack(
                    side="right", padx=(0, 3)
                )
            return card_frame

        cover = self.generate_podcast_cover(card_frame, pid, title, category, 178, 142)
        cover.pack(fill="x", padx=9, pady=(9, 0))
        details_pane = tk.Frame(card_frame, bg=CARD_BG)
        details_pane.pack(fill="both", expand=True, padx=12, pady=11)
        self.create_label(details_pane, title, 12, TEXT_WHITE, "bold", wraplength=170).pack(anchor="w")
        self.create_label(details_pane, meta_info, 9, TEXT_GRAY).pack(anchor="w", pady=(4, 10))
        if rating_value is not None:
            self.create_star_rating_bar(details_pane, rating_value, star_size=14, background_col=CARD_BG).pack(
                anchor="w", pady=(0, 9)
            )
        button_strip = tk.Frame(details_pane, bg=CARD_BG)
        button_strip.pack(fill="x", side="bottom")
        self.create_button(button_strip, "Details", lambda target_id=pid: self.show_detail(target_id), compact=True).pack(side="left")
        if show_remove_btn:
            self.create_button(
                button_strip, "Remove", lambda target_id=pid: self.remove_from_history(target_id), compact=True
            ).pack(side="left", padx=(6, 0))
        if show_play_btn:
            self.create_button(button_strip, "▶", lambda target_id=pid: self.listen(target_id), primary=True, compact=True).pack(side="right")
        return card_frame

    def render_podcast_grid(
        self, parent_widget, items_list, columns_count=6,
        show_play=False, show_remove=False, max_count=8, single_row=False,
        rating_index=None,
    ):
        if not items_list:
            self.render_empty_message(parent_widget, "No programmes to show yet", "Try another search, or explore all programmes.")
            return
        grid_container = tk.Frame(parent_widget, bg=parent_widget.cget("bg"))
        grid_container.pack(fill="x")

        displayed_items = items_list[:max_count]
        end_message = self.create_label(
            grid_container, "No more results", 10, "#777b83", anchor="center",
        )
        rendered_cards = []
        current_columns = [0]

        def reflow_cards(_event=None):
            available_width = grid_container.winfo_width()
            if available_width <= 1:
                available_width = max(1, self.winfo_width() - 110)
            responsive_columns = max(2, min(columns_count, available_width // 260))
            if responsive_columns == current_columns[0] and _event is not None:
                return
            current_columns[0] = responsive_columns
            for col_idx in range(columns_count):
                grid_container.grid_columnconfigure(
                    col_idx, weight=1 if col_idx < responsive_columns else 0,
                    uniform="programme" if col_idx < responsive_columns else "",
                )
            visible_count = responsive_columns if single_row else len(rendered_cards)
            for card_idx, card_widget in enumerate(rendered_cards):
                if card_idx >= visible_count:
                    card_widget.grid_remove()
                    continue
                card_widget.grid(
                    row=card_idx // responsive_columns,
                    column=card_idx % responsive_columns,
                    sticky="nsew", padx=5, pady=5,
                )

            item_count = len(rendered_cards)
            final_row, used_columns = divmod(item_count, responsive_columns)
            if item_count == len(items_list) and used_columns and (not single_row or final_row == 0):
                end_message.grid(
                    row=final_row, column=used_columns,
                    columnspan=responsive_columns - used_columns,
                    sticky="nsew", padx=5, pady=5,
                )
            else:
                end_message.grid_remove()

        def render_card(podcast):
            rating_value = podcast[rating_index] if rating_index is not None and len(podcast) > rating_index else None
            card = self.render_podcast_card(
                grid_container, podcast, show_play_btn=show_play,
                show_remove_btn=show_remove, rating_value=rating_value,
            )
            rendered_cards.append(card)
            reflow_cards()

        grid_container.bind("<Configure>", reflow_cards)
        self.render_in_batches(displayed_items, render_card)

    def render_empty_message(self, parent_widget, heading, subtitle):
        box_pane = self.create_card_frame(parent_widget)
        box_pane.pack(fill="x", pady=8)
        self.create_label(box_pane, heading, 13, TEXT_WHITE, "bold").pack(anchor="w", padx=16, pady=(15, 5))
        self.create_label(box_pane, subtitle, 10, TEXT_GRAY, wraplength=700).pack(anchor="w", padx=16, pady=(0, 15))

    def render_in_batches(self, items_list, render_item):
        self._render_queue.append([iter(items_list), render_item])
        if self._pending_render_id is None:
            self._pending_render_id = self.after_idle(self._render_next_batch)

    def _render_next_batch(self):
        self._pending_render_id = None
        rendered_count = 0
        while self._render_queue and rendered_count < 12:
            items_iter, render_item = self._render_queue[0]
            try:
                item = next(items_iter)
            except StopIteration:
                self._render_queue.pop(0)
                continue
            render_item(item)
            rendered_count += 1
        if self._render_queue:
            self._pending_render_id = self.after(1, self._render_next_batch)

    def cancel_pending_render(self):
        if self._pending_render_id is not None:
            self.after_cancel(self._pending_render_id)
            self._pending_render_id = None
        self._render_queue.clear()

    def show_login(self, error_message=""):
        self.cancel_pending_render()
        self.unbind_all("<MouseWheel>")
        self.current_user = None
        for child_widget in self.winfo_children():
            child_widget.destroy()
        self.configure(bg=DARK_BG)

        main_box = tk.Frame(self, bg=DARK_BG)
        main_box.pack(fill="both", expand=True, padx=58, pady=38)

        top_header = tk.Frame(main_box, bg=DARK_BG)
        top_header.pack(fill="x")
        self.draw_app_logo(top_header, 1.25).pack(side="left")
        self.create_label(top_header, "PODCASTS · RADIO · MUSIC", 9, TEXT_GRAY, "bold").pack(side="right")

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

        login_panel = self.create_card_frame(left_side)
        login_panel.pack(anchor="w", fill="x", padx=(0, 8), pady=(2, 0))
        self.create_label(login_panel, "Welcome back", 18, TEXT_WHITE, "bold").pack(anchor="w", padx=20, pady=(19, 4))
        self.create_label(login_panel, "Enter your listener ID to continue.", 10, TEXT_GRAY).pack(anchor="w", padx=20)

        id_var = tk.StringVar()
        text_entry = tk.Entry(
            login_panel, textvariable=id_var, font=(DEFAULT_FONT, 13), bg=INPUT_BG, fg=TEXT_WHITE,
            insertbackground=TEXT_WHITE, relief="flat", highlightthickness=1,
            highlightbackground=BORDER_LINE, highlightcolor=ORANGE_ACCENT,
        )
        text_entry.pack(fill="x", padx=20, pady=(15, 10), ipady=10)

        status_label = self.create_label(login_panel, error_message, 10, "#ff9868", wraplength=390)
        status_label.pack(anchor="w", padx=20, pady=(0, 4))

        def handle_login(_event=None):
            username_input = id_var.get().strip()
            if not username_input:
                status_label.config(text="Enter your listener ID to continue.")
                return
            try:
                with self.get_db_connection() as conn:
                    found_record = conn.execute(
                        "SELECT ListenerID FROM listeners WHERE ListenerID = ?",
                        (format_user_id(username_input),),
                    ).fetchone()
                if found_record:
                    self.current_user = found_record[0]
                    listener_obj = self.get_listener_data()
                    if not listener_obj:
                        status_label.config(text="That listener account could not be loaded.")
                        return
                    if not self.get_row_field(listener_obj, "CompleteSurvey", 0):
                        self.active_genres = []
                        self.active_length = "Medium"
                    self.show_home()
                else:
                    status_label.config(text="We couldn't find that listener ID. Check it and try again.")
            except sqlite3.Error as err:
                status_label.config(text="Couldn't open the project database: " + str(err))

        self.create_button(login_panel, "Continue  →", handle_login, primary=True).pack(anchor="w", padx=20, pady=(5, 20))
        text_entry.bind("<Return>", handle_login)
        text_entry.focus_set()

        right_side = tk.Frame(content_split, bg=SIDEBAR_BG, width=380)
        right_side.pack(side="right", fill="y", padx=(10, 0))
        right_side.pack_propagate(False)
        disc_canvas = tk.Canvas(right_side, bg=right_side.cget("bg"), highlightthickness=0)
        disc_canvas.pack(fill="both", expand=True)
        disc_canvas.bind("<Configure>", self.paint_vinyl_record)

    @staticmethod
    def paint_vinyl_record(event):
        canvas_obj = event.widget
        canvas_obj.delete("all")
        disc_size = min(event.width, event.height) * 0.68
        center_x, center_y = event.width * 0.5, event.height * 0.48
        for offset, stroke_color, line_width in [(0, "#f7f7f7", 2), (17, "#4b4b4b", 2), (35, "#2c2c2c", 2),
                                                 (54, "#454545", 2), (73, "#2a2a2a", 2), (96, "#151515", 30)]:
            radius = disc_size / 2 - offset
            if radius > 5:
                canvas_obj.create_oval(center_x - radius, center_y - radius, center_x + radius, center_y + radius, outline=stroke_color, width=line_width)
        canvas_obj.create_oval(center_x - 48, center_y - 48, center_x + 48, center_y + 48, fill=ORANGE_ACCENT, outline=TEXT_WHITE, width=2)
        canvas_obj.create_oval(center_x - 11, center_y - 11, center_x + 11, center_y + 11, fill="#111111", outline=TEXT_WHITE, width=2)
        canvas_obj.create_text(center_x, center_y - 25, text="BBC", fill=TEXT_WHITE, font=(DEFAULT_FONT, 13, "bold"))
        canvas_obj.create_text(center_x, center_y - 4, text="SOUNDS", fill="#111111", font=(DEFAULT_FONT, 10, "bold"))
        canvas_obj.create_text(center_x, center_y + 21, text="DISCOVER", fill=TEXT_WHITE, font=(DEFAULT_FONT, 7, "bold"))

        ring_string = "STREAM · SHARE · BBC SOUND · LISTEN · DISCOVER · "
        outer_radius = disc_size / 2 + 20
        for i, char in enumerate(ring_string):
            deg = math.radians(i * (360 / len(ring_string)) - 90)
            px = center_x + outer_radius * math.cos(deg)
            py = center_y + outer_radius * math.sin(deg)
            canvas_obj.create_text(
                px, py, text=char, fill=TEXT_WHITE, font=(DEFAULT_FONT, 8, "bold"),
                angle=-math.degrees(deg) - 90,
            )
        canvas_obj.create_line(center_x + disc_size * 0.32, center_y - disc_size * 0.36, center_x + disc_size * 0.1, center_y - disc_size * 0.05,
                               fill="#bfc2c8", width=5)
        canvas_obj.create_oval(center_x + disc_size * 0.27, center_y - disc_size * 0.42, center_x + disc_size * 0.38, center_y - disc_size * 0.31,
                               fill="#737780", outline=TEXT_WHITE, width=1)

    def build_shell(self, active_tab_title):
        self.cancel_pending_render()
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
            self._search_after_id = None
        self._live_search_callback = None
        self.unbind_all("<MouseWheel>")
        for widget in self.winfo_children():
            widget.destroy()
        self.configure(bg=DARK_BG)
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
            tk.Button(
                nav_row, text=label_text.upper(), command=handler, font=(DEFAULT_FONT, 9, "bold"),
                bg=ORANGE_ACCENT if selected_flag else "#080808", fg=TEXT_WHITE if selected_flag else TEXT_GRAY,
                activebackground=ORANGE_HL, activeforeground=TEXT_WHITE, relief="flat", bd=0,
                cursor="hand2", padx=11, pady=8,
            ).pack(side="left", padx=2)
        self.create_button(topbar, "Sign out", self.show_login, compact=True).pack(side="right", padx=(6, 9), pady=20)
        search_container = tk.Frame(topbar, bg=INPUT_BG, width=230, height=38)
        search_container.pack(side="right", padx=(0, 14), pady=23)
        search_container.pack_propagate(False)
        self._search_entry = tk.Entry(
            search_container, textvariable=self.search_text, font=(DEFAULT_FONT, 10),
            bg=INPUT_BG, fg=TEXT_WHITE, insertbackground=TEXT_WHITE, relief="flat",
            highlightthickness=1, highlightbackground=BORDER_LINE, highlightcolor=ORANGE_ACCENT,
        )
        self._search_entry.pack(fill="both", expand=True, ipady=7)
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

        area_frame = tk.Frame(shell_box, bg=DARK_BG)
        area_frame.pack(fill="both", expand=True)
        canvas_pane = tk.Canvas(area_frame, bg=DARK_BG, highlightthickness=0, borderwidth=0)
        scroll_bar = tk.Scrollbar(area_frame, orient="vertical", command=canvas_pane.yview,
                                  bg=SIDEBAR_BG, troughcolor=DARK_BG, activebackground=ORANGE_ACCENT)
        scroll_bar.pack(side="right", fill="y")
        canvas_pane.pack(side="left", fill="both", expand=True)
        canvas_pane.configure(yscrollcommand=scroll_bar.set)
        content_pane = tk.Frame(canvas_pane, bg=DARK_BG, padx=46, pady=28)
        canvas_window = canvas_pane.create_window((0, 0), window=content_pane, anchor="nw")
        content_pane.bind("<Configure>", lambda _e: canvas_pane.configure(scrollregion=canvas_pane.bbox("all")))
        canvas_pane.bind("<Configure>", lambda e: canvas_pane.itemconfigure(canvas_window, width=e.width))
        canvas_pane.bind_all("<MouseWheel>", lambda e: canvas_pane.yview_scroll(int(-e.delta / 120), "units"))
        self.current_page = content_pane
        return content_pane

    def schedule_live_search(self, _event=None):
        """Refresh results shortly after the user pauses typing in the header search."""
        self.update_search_prompt()
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(180, self.apply_live_search)

    def update_search_prompt(self):
        if self._search_prompt is None or not self._search_prompt.winfo_exists():
            return
        if self.search_text.get() or self.focus_get() == self._search_entry:
            self._search_prompt.place_forget()
        else:
            self._search_prompt.place(x=9, rely=0.5, anchor="w")

    def apply_live_search(self):
        self._search_after_id = None
        if self._live_search_callback is not None:
            self._live_search_callback()
            return
        self.show_search()
        if self._search_entry is not None:
            self._search_entry.focus_set()
            self._search_entry.icursor(tk.END)

    def show_home(self):
        try:
            page = self.build_shell("Home")
            listener_info = self.get_listener_data()
            name_str = self.get_row_field(listener_info, "Username", None) or self.get_row_field(listener_info, "Name", None)
            first_name = str(name_str or "there").split()[0]
            self.render_page_title(page, f"Good to have you back, {first_name}",
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

            report_strip = self.create_card_frame(page, bg="#1d1e22")
            report_strip.pack(fill="x", pady=(0, 10))
            self.create_label(report_strip, "YOUR LISTENING, SUMMARISED", 9, ORANGE_HL, "bold").pack(
                side="left", padx=(16, 8), pady=14
            )
            self.create_label(report_strip, "See your plays, most-listened programme and average rating.", 10, TEXT_GRAY).pack(
                side="left", pady=14
            )
            self.create_button(report_strip, "Generate listening report", self.show_report, primary=True, compact=True).pack(
                side="right", padx=12, pady=8
            )

            genres_str = str(self.get_row_field(listener_info, "FavoriteGenres", "") or "").replace(",", " · ")
            length_str = self.get_row_field(listener_info, "LengthPreference", "") or ""
            banner_card = self.create_card_frame(page, bg="#26201e")
            banner_card.pack(fill="x", pady=(7, 7))
            banner_text = tk.Frame(banner_card, bg="#26201e")
            banner_text.pack(side="left", fill="both", expand=True, padx=20, pady=19)
            self.create_label(banner_text, "Find your next favourite listen", 17, TEXT_WHITE, "bold").pack(anchor="w")
            hint_msg = "Search thousands of programmes and explore by genre."
            if genres_str:
                hint_msg = "Picked for " + genres_str + (" · " + length_str + " episodes" if length_str else "")
            self.create_label(banner_text, hint_msg, 10, TEXT_GRAY, wraplength=520).pack(anchor="w", pady=(5, 13))
            self.create_button(banner_text, "Explore programmes  →", self.show_search, primary=True, compact=True).pack(anchor="w")
            promo_art = self.render_decorative_panel(banner_card, "1.svg", 0, (150, 138), 155, 138)
            promo_art.pack(side="right", padx=12, pady=10)

            rec_list = self.get_custom_recommendations(8)
            if rec_list:
                self.render_section_title(page, "Made for you", "A match for your favourite genres and episode length.",
                                          "See all", self.show_recommendations)
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
                self.create_button(survey_prompt, "Choose your genres  →", self.show_preferences, primary=True, compact=True).pack(
                    anchor="w", padx=17, pady=(0, 15)
                )

            if history_rows:
                self.render_section_title(page, "Pick up where you left off", "Your most played programmes.",
                                          "Listening history", self.show_history)
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
        page = self.build_shell("Genres")
        self.render_page_title(page, "Browse genres", "Choose a genre below, or use the search bar above.")

        results_pane = tk.Frame(page, bg=DARK_BG)

        def perform_search_action(_event=None):
            self.update_search_prompt()
            self.cancel_pending_render()
            for child in results_pane.winfo_children():
                child.destroy()
            try:
                matching_rows = self.query_podcasts(self.search_text.get(), item_limit=80)
                self.create_label(results_pane, f"{len(matching_rows)} programmes", 10, TEXT_GRAY).pack(anchor="w", pady=(8, 6))
                self.render_podcast_grid(
                    results_pane, matching_rows, columns_count=6,
                    show_play=True, max_count=80,
                )
            except sqlite3.Error as err:
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
                category_card = tk.Frame(
                    category_row, bg=tile_colour, cursor="hand2",
                    highlightthickness=1, highlightbackground=BORDER_LINE,
                )
                category_card.grid(
                    row=idx // columns_count, column=idx % columns_count,
                    sticky="nsew", padx=5, pady=5,
                )
                accent_line = tk.Frame(category_card, bg=ORANGE_HL, height=3, cursor="hand2")
                accent_line.pack(fill="x")
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

                open_genre = lambda _event=None, name=category_name: (
                    self.search_text.set(name), perform_search_action()
                )
                for clickable_widget in (
                    category_card, accent_line, card_header, icon_label,
                    title_label, description_label, action_label,
                ):
                    clickable_widget.bind("<Button-1>", open_genre)
        except sqlite3.Error as err:
            self.show_db_error("Couldn't load categories", err)

        self.render_section_title(page, "Programmes")
        results_pane.pack(fill="both", expand=True)
        perform_search_action()

    def show_recommendations(self):
        page = self.build_shell("For you")
        listener_info = self.get_listener_data()
        genres_val = self.get_row_field(listener_info, "FavoriteGenres", "") or ""
        length_val = self.get_row_field(listener_info, "LengthPreference", "") or ""
        self.render_page_title(page, "Picked for you", "Recommendations use your selected genres and preferred episode length.")
        if not genres_val or not length_val:
            self.render_empty_message(page, "Your listening profile is ready for a few details",
                                      "Choose your favourite genres and episode length to unlock tailored recommendations.")
            self.create_button(page, "Set up your preferences  →", self.show_preferences, primary=True).pack(anchor="w", pady=7)
            self.render_section_title(page, "Explore the catalogue while you decide")
            self.render_podcast_grid(page, self.query_podcasts(item_limit=8), show_play=True)
            return
        self.create_label(page, f"YOUR GENRES   {genres_val.replace(',', '  ·  ')}     /     {length_val} episodes",
                          10, ORANGE_HL, "bold").pack(anchor="w", pady=(0, 12))
        rec_results = self.get_custom_recommendations(40)
        if rec_results:
            self.render_podcast_grid(page, rec_results, columns_count=6, show_play=True, max_count=40)
        else:
            self.render_empty_message(page, "No exact matches yet", "Try another genre or episode length to see more programmes.")
            self.create_button(page, "Edit preferences", self.show_preferences, compact=True).pack(anchor="w", pady=8)

    def show_favourites(self):
        page = self.build_shell("Favourites")
        self.render_page_title(page, "Your favourites", "The programmes you have saved for later.")
        fav_rows = self.fetch_user_favourites()
        if not fav_rows:
            self.render_empty_message(page, "No favourites saved yet", "Open any programme and tap the heart to keep it here.")
            self.create_button(page, "Find a programme", self.show_search, primary=True, compact=True).pack(anchor="w", pady=6)
            return
        self.render_podcast_grid(
            page, fav_rows, columns_count=6,
            show_play=True, max_count=len(fav_rows),
        )

    def show_history(self):
        page = self.build_shell("History")
        self.render_page_title(page, "Listening history", "A record of what you have played in BBC Sounds.")
        history_rows = self.fetch_user_history()
        if not history_rows:
            self.render_empty_message(page, "Your history is empty", "Play a programme and it will appear here.")
            self.create_button(page, "Explore programmes", self.show_search, primary=True, compact=True).pack(anchor="w", pady=6)
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
        page = self.build_shell("Ratings")
        self.render_page_title(page, "Podcasts you rated", "Every programme you have scored is collected here.")
        rating_rows = self.fetch_user_ratings()
        if not rating_rows:
            self.render_empty_message(page, "No ratings yet", "Listen to a programme, then add a rating from its details page.")
            self.create_button(page, "Explore programmes", self.show_search, primary=True, compact=True).pack(anchor="w", pady=6)
            return

        summary_bar = self.create_card_frame(page, bg="#1d1e22")
        summary_bar.pack(fill="x", pady=(0, 12))
        self.create_label(summary_bar, str(len(rating_rows)), 24, ORANGE_ACCENT, "bold").pack(
            side="left", padx=(18, 8), pady=12
        )
        self.create_label(summary_bar, "ratings in your library", 10, TEXT_GRAY).pack(side="left", pady=18)
        self.create_label(summary_bar, "Select a programme to update or remove its score.", 10, TEXT_LIGHT).pack(
            side="right", padx=18, pady=18
        )

        ratings_grid = tk.Frame(page, bg=DARK_BG)
        ratings_grid.pack(fill="x")
        for column_idx in range(4):
            ratings_grid.grid_columnconfigure(column_idx, weight=1, uniform="rating-cards")

        def render_rating_card(row):
            card = self.create_card_frame(ratings_grid)
            idx = len(ratings_grid.winfo_children()) - 1
            card.grid(row=idx // 4, column=idx % 4, sticky="nsew", padx=6, pady=6)
            cover = self.generate_podcast_cover(card, row[0], row[1], row[2], 190, 145)
            cover.pack(fill="x", padx=9, pady=(9, 0))
            details_pane = tk.Frame(card, bg=CARD_BG)
            details_pane.pack(fill="both", expand=True, padx=13, pady=12)
            self.create_label(details_pane, row[1], 12, TEXT_WHITE, "bold", wraplength=180).pack(anchor="w")
            self.create_label(details_pane, str(row[2]), 9, TEXT_GRAY).pack(anchor="w", pady=(4, 0))
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
        self.render_in_batches(rating_rows, render_rating_card)

    def show_genres(self):
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
            self.create_button(page, "Edit preferences", self.show_preferences, primary=True, compact=True).pack(anchor="w", pady=7)
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
            self.create_button(page, "Choose genres", self.show_preferences, primary=True).pack(anchor="w", pady=6)

    def show_report(self):
        page = self.build_shell("Listening report")
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
                highlight_card, top_programme[0], top_programme[1], top_programme[2], 145, 112,
            )
            highlight_cover.pack(side="left", padx=12, pady=12)
            highlight_details = tk.Frame(highlight_card, bg=CARD_BG)
            highlight_details.pack(side="left", fill="both", expand=True, pady=16)
            self.create_label(highlight_details, "MOST PLAYED", 8, ORANGE_ACCENT, "bold").pack(anchor="w", pady=(0, 5))
            self.create_label(highlight_details, top_programme[1], 16, TEXT_WHITE, "bold").pack(anchor="w")
            self.create_label(
                highlight_details, f"{top_programme[4] or 0} plays  ·  {top_programme[2]}", 10, TEXT_GRAY,
            ).pack(anchor="w", pady=(5, 0))
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
        self.create_button(profile_actions, "Edit survey answers", self.show_preferences, primary=True).pack(side="left")
        if survey_done:
            self.create_button(profile_actions, "Reset survey", self.reset_survey, compact=True).pack(side="left", padx=(9, 0))

    def show_detail(self, podcast_id):
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
            back_row = tk.Frame(page, bg=DARK_BG)
            back_row.pack(fill="x", pady=(2, 14))
            self.create_button(back_row, "←  Back to discover", self.show_search, compact=True).pack(side="left")
            self.create_label(back_row, "NOW PLAYING", 9, ORANGE_HL, "bold").pack(side="right", pady=8)

            hero_box = tk.Frame(page, bg=DARK_BG)
            hero_box.pack(fill="x", pady=(0, 8))
            cover_panel = self.create_card_frame(hero_box, bg="#272727")
            cover_panel.pack(side="left", padx=(0, 28))
            cover_art = self.generate_podcast_cover(cover_panel, podcast_id, podcast_rec[1], podcast_rec[2], 275, 275)
            cover_art.pack(padx=10, pady=10)

            actions_box = tk.Frame(hero_box, bg=DARK_BG, width=195)
            actions_box.pack(side="right", fill="y", padx=(24, 0), pady=20)
            actions_box.pack_propagate(False)
            self.create_label(actions_box, "PROGRAMME ACTIONS", 8, TEXT_GRAY, "bold").pack(anchor="w", pady=(0, 10))
            fav_text = "♥  Remove from favourites" if self.check_if_favourited(podcast_id) else "♡  Save to favourites"
            for action_text, action_func in [
                (fav_text, lambda: self.toggle_favourite(podcast_id)),
                ("★  Rate this programme", lambda: self.rate_programme(podcast_id)),
            ]:
                action_label = self.create_label(actions_box, action_text, 10, TEXT_WHITE, "bold", cursor="hand2")
                action_label.pack(anchor="w", pady=6)
                action_label.bind("<Button-1>", lambda _event, callback=action_func: callback())

            details_box = tk.Frame(hero_box, bg=DARK_BG)
            details_box.pack(side="left", fill="both", expand=True, pady=10)
            self.create_label(details_box, str(podcast_rec[2] or "Programme").upper(), 10, ORANGE_HL, "bold").pack(anchor="w")
            self.create_label(details_box, podcast_rec[1], 30, TEXT_WHITE, "bold", wraplength=490).pack(anchor="w", pady=(8, 6))
            length_text = "Episode length not listed" if podcast_rec[3] is None else f"{podcast_rec[3]} minutes"
            self.create_label(details_box, f"BBC SOUNDS  ·  {length_text}", 11, TEXT_GRAY).pack(anchor="w")

            play_row = tk.Frame(details_box, bg=DARK_BG)
            play_row.pack(anchor="w", pady=(25, 12))
            play_canvas = tk.Canvas(play_row, width=74, height=74, bg=DARK_BG, highlightthickness=0, cursor="hand2")
            play_canvas.pack(side="left", padx=(0, 14))
            play_canvas.create_oval(3, 3, 71, 71, fill=ORANGE_ACCENT, outline=TEXT_WHITE, width=2)
            play_canvas.create_polygon(31, 22, 31, 52, 56, 37, fill=TEXT_WHITE, outline="")
            play_canvas.bind("<Button-1>", lambda _event: self.listen(podcast_id))

            play_copy = tk.Frame(play_row, bg=DARK_BG)
            play_copy.pack(side="left", pady=10)
            self.create_label(play_copy, "Listen now", 14, TEXT_WHITE, "bold").pack(anchor="w")

            tk.Frame(page, bg=TEXT_GRAY, height=1).pack(fill="x", pady=(18, 18))

            if history_record:
                sub_card = self.create_card_frame(page, bg="#1d1e22")
                sub_card.pack(fill="x", pady=(20, 8))
                self.create_label(sub_card, "YOUR LISTENING", 8, ORANGE_HL, "bold").pack(anchor="w", padx=16, pady=(12, 5))
                play_count = history_record[0] or 0
                given_rating = history_record[1]
                summary_text = f"{play_count} plays" + (f"  ·  your rating: {'★' * int(given_rating)}" if given_rating else "")
                self.create_label(sub_card, summary_text, 11, TEXT_WHITE).pack(anchor="w", padx=16, pady=(0, 8))
                if given_rating:
                    self.create_star_rating_bar(sub_card, given_rating, star_size=18, background_col="#1d1e22").pack(
                        anchor="w", padx=16, pady=(0, 14)
                    )
        except sqlite3.Error as err:
            self.show_db_error("Couldn't load programme", err)

    def listen(self, podcast_id):
        try:
            with self.get_db_connection() as conn:
                existing_entry = conn.execute(
                    "SELECT TimesListened FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                ).fetchone()
                if existing_entry:
                    conn.execute(
                        "UPDATE listening_history SET TimesListened = COALESCE(TimesListened, 0) + 1 "
                        "WHERE ListenerID = ? AND PodcastID = ?", (self.current_user, podcast_id),
                    )
                else:
                    conn.execute(
                        "INSERT INTO listening_history (PodcastID, ListenerID, TimesListened) VALUES (?, ?, 1)",
                        (podcast_id, self.current_user),
                    )
            messagebox.showinfo("Now playing", "Listening to this programme…\n\nPlayback is simulated in this prototype.", parent=self)
            self.show_detail(podcast_id)
        except sqlite3.Error as err:
            self.show_db_error("Couldn't update listening history", err)

    def rate_programme(self, podcast_id, callback_func=None):
        try:
            with self.get_db_connection() as conn:
                prior_record = conn.execute(
                    "SELECT TimesListened, RatingGiven FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                ).fetchone()
            if not prior_record or (not prior_record[0] and prior_record[1] is None):
                messagebox.showinfo(
                    "Listen first",
                    "Play this programme before adding a rating.",
                    parent=self,
                )
                return
            if prior_record[1] is None:
                dialog_title = "Rate this programme"
                dialog_prompt = "Choose a score from 1 to 5."
                default_score = 5
            else:
                dialog_title = "Update your rating"
                dialog_prompt = f"Your current score is {prior_record[1]}. Enter a new score (1–5)."
                default_score = int(prior_record[1])
            new_score = simpledialog.askinteger(dialog_title, dialog_prompt, parent=self, minvalue=1, maxvalue=5, initialvalue=default_score)
            if new_score is None:
                return
            with self.get_db_connection() as conn:
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
            messagebox.showinfo("Rating saved", "Thanks for rating this programme.", parent=self)
            if callback_func:
                callback_func()
            else:
                self.show_detail(podcast_id)
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save your rating", err)

    def remove_rating(self, podcast_id):
        if not messagebox.askyesno("Remove rating", "Remove your rating for this programme?", parent=self):
            return
        try:
            with self.get_db_connection() as conn:
                conn.execute(
                    "UPDATE listening_history SET RatingGiven = NULL WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                )
            self.show_ratings()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't remove your rating", err)

    def toggle_favourite(self, podcast_id):
        try:
            with self.get_db_connection() as conn:
                record = conn.execute(
                    "SELECT FavoritePodcasts FROM listeners WHERE ListenerID = ?", (self.current_user,)
                ).fetchone()
                current_str = str((record[0] if record else "") or "")
                id_tokens = [item.strip() for item in current_str.split(",") if item.strip()]
                target_str = str(podcast_id)
                if target_str in id_tokens:
                    id_tokens.remove(target_str)
                    message_text = "Removed from your favourites."
                else:
                    id_tokens.append(target_str)
                    message_text = "Added to your favourites."
                conn.execute(
                    "UPDATE listeners SET FavoritePodcasts = ? WHERE ListenerID = ?",
                    (",".join(id_tokens), self.current_user),
                )
            messagebox.showinfo("Favourites updated", message_text, parent=self)
            self.show_detail(podcast_id)
        except sqlite3.Error as err:
            self.show_db_error("Couldn't update favourites", err)

    def remove_from_history(self, podcast_id):
        if not messagebox.askyesno("Remove from history", "Remove this programme from your listening history?", parent=self):
            return
        try:
            with self.get_db_connection() as conn:
                conn.execute(
                    "DELETE FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, podcast_id),
                )
            self.show_history()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't remove programme", err)

    def clear_history(self):
        if not messagebox.askyesno("Clear listening history", "Remove all programmes from your listening history?", parent=self):
            return
        try:
            with self.get_db_connection() as conn:
                conn.execute("DELETE FROM listening_history WHERE ListenerID = ?", (self.current_user,))
            self.show_history()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't clear listening history", err)

    def build_genre_tile(self, parent_widget, genre_name, idx, selected=False):
        bg_col = "#38251d" if selected else CARD_BG
        border_col = ORANGE_ACCENT if selected else BORDER_LINE
        tile_box = tk.Frame(parent_widget, bg=bg_col, highlightthickness=1, highlightbackground=border_col)
        canvas_marker = self.create_genre_circle(tile_box, genre_name, idx, 45, bg_col)
        canvas_marker.pack(pady=(10, 3))
        self.create_label(tile_box, genre_name, 9, ORANGE_HL if selected else TEXT_WHITE, "bold", anchor="center", bg=bg_col).pack(
            fill="x", padx=3, pady=(0, 10)
        )
        return tile_box

    def show_preferences(self):
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
            tile = tk.Frame(grid_frame, bg=CARD_BG, highlightthickness=1, highlightbackground=BORDER_LINE, cursor="hand2")
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
        self.create_button(footer_pane, "Cancel", self.show_home, compact=True).pack(side="left", padx=9)

    def toggle_genre_selection(self, genre_name, counter_lbl):
        if genre_name in self.active_genres:
            self.active_genres.remove(genre_name)
        elif len(self.active_genres) >= 5:
            messagebox.showinfo("Five genre limit", "Choose up to five favourite genres.", parent=self)
            return
        else:
            self.active_genres.append(genre_name)
        self.update_genre_tile_styles(counter_lbl)

    def update_genre_tile_styles(self, counter_lbl=None):
        if counter_lbl and counter_lbl.winfo_exists():
            counter_lbl.config(text=f"{len(self.active_genres)} / 5 selected")
        for name, (tile, lbl, circle) in getattr(self, "genre_elements", {}).items():
            is_active = name in self.active_genres
            background_color = "#38251d" if is_active else CARD_BG
            tile.configure(bg=background_color, highlightbackground=ORANGE_ACCENT if is_active else BORDER_LINE)
            lbl.configure(bg=background_color, fg=ORANGE_HL if is_active else TEXT_WHITE)
            circle.configure(bg=background_color)
            for child in tile.winfo_children():
                if isinstance(child, tk.Label) and child is not lbl:
                    child.configure(bg=background_color)

    def set_length_preference(self, choice_val):
        self.active_length = choice_val
        self.update_length_button_styles()

    def update_length_button_styles(self):
        for val_key, button_obj in getattr(self, "length_buttons", {}).items():
            active_flag = val_key == self.active_length
            button_obj.configure(
                bg=ORANGE_ACCENT if active_flag else INPUT_BG,
                activebackground=ORANGE_HL if active_flag else BORDER_LINE,
                fg=TEXT_WHITE if active_flag else TEXT_LIGHT
            )

    def save_user_preferences(self):
        if not self.active_genres:
            messagebox.showinfo("Choose a genre", "Select at least one favourite genre to continue.", parent=self)
            return
        try:
            with self.get_db_connection() as conn:
                conn.execute(
                    "UPDATE listeners SET CompleteSurvey = 1, FavoriteGenres = ?, LengthPreference = ? "
                    "WHERE ListenerID = ?",
                    (",".join(self.active_genres), self.active_length, self.current_user),
                )
            self.show_recommendations()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save your preferences", err)

    def reset_survey(self):
        if not messagebox.askyesno("Reset survey", "Clear your favourite genres and episode-length preference?", parent=self):
            return
        try:
            with self.get_db_connection() as conn:
                conn.execute(
                    "UPDATE listeners SET CompleteSurvey = 0, FavoriteGenres = '', LengthPreference = NULL "
                    "WHERE ListenerID = ?", (self.current_user,),
                )
            self.active_genres = []
            self.show_profile()
        except sqlite3.Error as err:
            self.show_db_error("Couldn't reset the survey", err)


if __name__ == "__main__":
    BBCSoundsGUI().mainloop()
