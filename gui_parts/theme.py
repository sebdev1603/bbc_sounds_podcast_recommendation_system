"""Shared paths, colour palette, genre metadata, and base rounded-panel widget."""
from pathlib import Path
import tkinter as tk

# Workspace paths (parent of gui_parts/ is the project root).
ROOT_PATH = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT_PATH / "database.db"
CANVA_DIR = ROOT_PATH / "canva design"

# Shared dark-theme palette and typography constants used across every screen.
DARK_BG = "#101113"          # Primary application background.
SIDEBAR_BG = "#17181b"       # Secondary chrome / scrollbar background.
CARD_BG = "#1b1d21"          # Default rounded card surface colour.
INPUT_BG = "#22252a"         # Text inputs and secondary button background.
BORDER_LINE = "#303339"      # Subtle 1px card/button border outline.
ORANGE_ACCENT = "#ff751f"    # Official BBC Sounds signature orange.
ORANGE_HL = "#ff914d"        # Lighter orange highlight for hover states and labels.
TEXT_WHITE = "#f7f7f7"       # High-contrast primary body and heading text.
TEXT_GRAY = "#a8abb1"        # Muted secondary captions and metadata text.
TEXT_LIGHT = "#d6d8dc"       # Medium-contrast text for secondary buttons.
GOLD_STAR = "#ffd166"        # Warm gold colour for filled rating stars.
DEFAULT_FONT = "Segoe UI"    # Standard Windows UI font family.
PODCASTS_PER_PAGE = 12       # Number of podcast cards rendered per paginated page.

# Supported podcast genres, duration buckets (in minutes), and visual tile metadata.
GENRE_LIST = [
    "News", "Travel", "History", "Comedy", "True Crime", "Technology",
    "Science", "Business", "Gaming", "Entertainment", "Sport", "Health",
]
DURATION_RANGES = {"Short": (0, 30), "Medium": (25, 45), "Long": (45, 60)}
PALETTE_SWATCHES = ["#5b315e", "#185a70", "#7a3d2d", "#2e6654", "#6c5631", "#373e79"]
# Maps each genre name to (card_colour, icon_glyph, short_tagline) for the Genres tab and cover art.
GENRE_TILE_DETAILS = {
    "News": ("#7a2838", "N", "Headlines, investigations and current affairs"),
    "Travel": ("#176c78", "✈", "Journeys, places and stories from around the world"),
    "History": ("#76512d", "H", "People and events that shaped our world"),
    "Comedy": ("#7b3f91", "☺", "Stand-up, panel shows and funny conversations"),
    "True Crime": ("#633344", "?", "Real cases, mysteries and investigations"),
    "Technology": ("#285d8b", ">_", "Digital culture, inventions and the future"),
    "Science": ("#23705b", "Σ", "Discoveries, nature and how things work"),
    "Business": ("#6f5d24", "£", "Money, markets, careers and entrepreneurship"),
    "Gaming": ("#394a91", "♧", "Games, creators and player culture"),
    "Entertainment": ("#9a3e67", "★", "Film, television, music and celebrity stories"),
    "Sport": ("#39713b", "⚽", "Matches, athletes and expert sporting analysis"),
    "Health": ("#8a4b35", "♥", "Wellbeing, medicine and healthier living"),
}
# Concentric (light, mid, dark_outline) ring palettes for circular genre badges.
GENRE_CIRCLE_COLOURS = [
    ("#b79cff", "#5e17eb", "#2e0b70"), ("#9cecff", "#38b6ff", "#0b4f78"),
    ("#ffb7ad", "#e84a5f", "#7c1f2c"), ("#b9f4c7", "#43aa8b", "#175b49"),
    ("#ffe8a6", "#f9c74f", "#80600b"), ("#d9bcff", "#8d1370", "#49083a"),
    ("#9dfff0", "#1bd5d3", "#087675"), ("#ffc8f0", "#ff5cb8", "#80245d"),
    ("#bed0ff", "#4b56d2", "#252a75"), ("#ffd4ad", "#ff914d", "#8c3b0d"),
    ("#c4f2ff", "#56ccf2", "#1d6880"), ("#f5d0ff", "#b54dce", "#5d176d"),
]


def format_user_id(uid):
    """Convert numeric listener ID strings to integers to match SQLite column types."""
    cleaned_id = str(uid).strip()
    return int(cleaned_id) if cleaned_id.isdigit() else cleaned_id


def sanitize_column_name(col):
    """Quote a SQLite identifier safely for dynamic ORDER BY clauses."""
    return '"' + str(col).replace('"', '""') + '"'


def blend_colour(hex_colour, target_colour, amount):
    """Blend two #RRGGBB colours linearly by amount (0.0 -> source, 1.0 -> target)."""
    source = tuple(int(hex_colour[pos:pos + 2], 16) for pos in (1, 3, 5))
    target = tuple(int(target_colour[pos:pos + 2], 16) for pos in (1, 3, 5))
    mixed = tuple(round(start + (end - start) * amount) for start, end in zip(source, target))
    return "#" + "".join(f"{channel:02x}" for channel in mixed)


class RoundedPanel(tk.Frame):
    """Frame backed by a smooth rounded-rectangle Canvas polygon with optional hover inset."""

    def __init__(self, parent, surface, border=BORDER_LINE, **kwargs):
        super().__init__(parent, bg=parent.cget("bg"), **kwargs)
        self.surface = surface
        self.border = border
        self._inset = 0
        self._last_shape_key = None
        self.backdrop = tk.Canvas(self, bg=parent.cget("bg"), bd=0, highlightthickness=0)
        self.backdrop.place(relwidth=1, relheight=1)
        self.shape = self.backdrop.create_polygon(0, 0, 0, 0, smooth=True, fill=surface, outline=border)
        self.backdrop.bind("<Configure>", self.draw_surface)

    def cget(self, key):
        return self.surface if key in ("bg", "background") else super().cget(key)

    def _redraw_shape(self, width, height):
        shape_key = (width, height, self._inset)
        if shape_key == self._last_shape_key:
            return
        self._last_shape_key = shape_key
        m = 1 + self._inset
        w = max(m + 2, width - 1 - self._inset)
        h = max(m + 2, height - 1 - self._inset)
        r = min(12, (w - m) / 2, (h - m) / 2)
        self.backdrop.coords(
            self.shape, r + m, m, w - r, m, w, m, w, r + m, w, h - r, w, h,
            w - r, h, r + m, h, m, h, m, h - r, m, r + m, m, m,
        )

    def draw_surface(self, event):
        self._redraw_shape(event.width, event.height)

    def set_inset(self, inset):
        if inset == self._inset:
            return
        self._inset = inset
        bw, bh = self.backdrop.winfo_width(), self.backdrop.winfo_height()
        if bw > 2 and bh > 2:
            self._redraw_shape(bw, bh)

    def set_surface(self, surface, border):
        self.surface = surface
        self.backdrop.itemconfigure(self.shape, fill=surface, outline=border)
