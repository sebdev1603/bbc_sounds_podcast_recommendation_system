"""Shared paths, colour palette, genre metadata, bundled font loader, and base rounded-panel widget."""
import ctypes
from pathlib import Path
import struct
import sys
import tkinter as tk

# Workspace paths (parent of gui_parts/ is the project root).
ROOT_PATH = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT_PATH / "database.db"
CANVA_DIR = ROOT_PATH / "canva design"


def _read_font_family_name(font_path):
    """Read the Windows GDI Font Family name (Name ID 1 / 16) from a TTF/OTF binary."""
    try:
        data = font_path.read_bytes()
        if len(data) < 12:
            return None
        num_tables = struct.unpack(">H", data[4:6])[0]
        name_offset = None
        for idx in range(num_tables):
            entry = 12 + idx * 16
            if entry + 16 > len(data):
                break
            if data[entry:entry + 4] == b"name":
                name_offset = struct.unpack(">I", data[entry + 8:entry + 12])[0]
                break
        if name_offset is None or name_offset + 6 > len(data):
            return None
        _fmt, count, string_offset = struct.unpack(">HHH", data[name_offset:name_offset + 6])
        storage = name_offset + string_offset
        name_id_1 = None
        name_id_16 = None
        for idx in range(count):
            rec = name_offset + 6 + idx * 12
            if rec + 12 > len(data):
                break
            platform_id, _enc_id, _lang_id, name_id, length, offset = struct.unpack(">HHHHHH", data[rec:rec + 12])
            if name_id not in (1, 16):
                continue
            raw = data[storage + offset:storage + offset + length]
            if platform_id == 3:
                text = raw.decode("utf-16-be", errors="ignore").strip()
            elif platform_id == 1:
                text = raw.decode("latin-1", errors="ignore").strip()
            else:
                continue
            if not text:
                continue
            if name_id == 1 and name_id_1 is None:
                name_id_1 = text
            elif name_id == 16 and name_id_16 is None:
                name_id_16 = text
        # Windows GDI registers fonts by Name ID 1 (Font Family), falling back to Name ID 16.
        return name_id_1 or name_id_16
    except OSError:
        return None


def load_bundled_reith_font():
    """Find and privately register bundled BBC Reith Sans font files before Tk initializes."""
    base_dirs = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base_dirs.append(Path(meipass))
        base_dirs.append(Path(sys.executable).resolve().parent)
    else:
        base_dirs.append(ROOT_PATH)

    font_exts = {".ttf", ".otf", ".ttc"}
    candidates = []
    seen = set()
    for base in base_dirs:
        if not base.is_dir():
            continue
        try:
            for item in base.rglob("*"):
                if item.is_file() and item.suffix.lower() in font_exts:
                    lower_name = item.stem.lower()
                    if "reith" in lower_name:
                        resolved = item.resolve()
                        if resolved not in seen:
                            seen.add(resolved)
                            candidates.append(resolved)
        except OSError:
            continue

    if not candidates:
        return "Segoe UI"

    # Sort so BBC Reith Sans Regular weights come first for family-name detection.
    def font_priority(path):
        name = path.stem.lower()
        is_sans = "sans" in name
        is_regular = any(tok in name for tok in ("regular", "_rg", "-rg", "reg")) and "italic" not in name and "it" not in name
        is_bold = any(tok in name for tok in ("bold", "_bd", "-bd"))
        return (0 if is_sans else 1, 0 if is_regular else (1 if is_bold else 2), len(name), name)

    candidates.sort(key=font_priority)

    # Register every matching BBC Reith font file privately for this Windows process.
    registered_any = False
    if sys.platform == "win32":
        try:
            gdi32 = ctypes.windll.gdi32
            gdi32.AddFontResourceExW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
            gdi32.AddFontResourceExW.restype = ctypes.c_int
            FR_PRIVATE = 0x10
            for font_file in candidates:
                if gdi32.AddFontResourceExW(str(font_file), FR_PRIVATE, 0) > 0:
                    registered_any = True
        except Exception:
            pass

    for font_file in candidates:
        family = _read_font_family_name(font_file)
        if family:
            return family

    return "BBC Reith Sans" if registered_any else "Segoe UI"


# Theme palettes supporting Dark (default), Light, and High Contrast accessibility modes.
THEME_PALETTES = {
    "dark": {
        "DARK_BG": "#101113",
        "SIDEBAR_BG": "#17181b",
        "TOPBAR_BG": "#080808",
        "CARD_BG": "#1b1d21",
        "SUBCARD_BG": "#1d1e22",
        "BANNER_BG": "#26201e",
        "MINI_BAR_BG": "#262228",
        "SELECTED_BG": "#38251d",
        "INPUT_BG": "#22252a",
        "BORDER_LINE": "#303339",
        "DIVIDER_LINE": "#575756",
        "ORANGE_ACCENT": "#ff751f",
        "ORANGE_HL": "#ff914d",
        "TEXT_WHITE": "#f7f7f7",
        "TEXT_GRAY": "#a8abb1",
        "TEXT_LIGHT": "#d6d8dc",
        "GOLD_STAR": "#ffd166",
        "STAR_EMPTY": "#444851",
        "ACTION_BTN_BG": "#23262d",
        "ACTION_BTN_FG": "#f7f7f7",
        "PRIMARY_BTN_FG": "#f7f7f7",
        "SECONDARY_HOVER_BG": "#303339",
        "SECONDARY_HOVER_FG": "#f7f7f7",
        "LOGO_TILE_BG": "#ffffff",
        "LOGO_TILE_FG": "#000000",
        "TITLEBAR_DARK_MODE": 1,
        "TITLEBAR_TEXT": "#f7f7f7",
    },
    "light": {
        "DARK_BG": "#f4f5f7",
        "SIDEBAR_BG": "#e2e5ea",
        "TOPBAR_BG": "#ffffff",
        "CARD_BG": "#ffffff",
        "SUBCARD_BG": "#eceef2",
        "BANNER_BG": "#fff1e6",
        "MINI_BAR_BG": "#ffffff",
        "SELECTED_BG": "#ffe3cf",
        "INPUT_BG": "#e6e8ec",
        "BORDER_LINE": "#cfd4dc",
        "DIVIDER_LINE": "#c5cad3",
        "ORANGE_ACCENT": "#e85d04",
        "ORANGE_HL": "#c94b00",
        "TEXT_WHITE": "#141518",
        "TEXT_GRAY": "#525760",
        "TEXT_LIGHT": "#25282e",
        "GOLD_STAR": "#d48806",
        "STAR_EMPTY": "#c4c9d1",
        "ACTION_BTN_BG": "#e6e8ec",
        "ACTION_BTN_FG": "#141518",
        "PRIMARY_BTN_FG": "#ffffff",
        "SECONDARY_HOVER_BG": "#cfd4dc",
        "SECONDARY_HOVER_FG": "#141518",
        "LOGO_TILE_BG": "#000000",
        "LOGO_TILE_FG": "#ffffff",
        "TITLEBAR_DARK_MODE": 0,
        "TITLEBAR_TEXT": "#141518",
    },
    "high_contrast": {
        "DARK_BG": "#000000",
        "SIDEBAR_BG": "#000000",
        "TOPBAR_BG": "#000000",
        "CARD_BG": "#000000",
        "SUBCARD_BG": "#000000",
        "BANNER_BG": "#000000",
        "MINI_BAR_BG": "#000000",
        "SELECTED_BG": "#2b2200",
        "INPUT_BG": "#121212",
        "BORDER_LINE": "#ffffff",
        "DIVIDER_LINE": "#ffffff",
        "ORANGE_ACCENT": "#ffae00",
        "ORANGE_HL": "#ffd500",
        "TEXT_WHITE": "#ffffff",
        "TEXT_GRAY": "#e8e8e8",
        "TEXT_LIGHT": "#ffffff",
        "GOLD_STAR": "#ffe600",
        "STAR_EMPTY": "#767676",
        "ACTION_BTN_BG": "#1a1a1a",
        "ACTION_BTN_FG": "#ffffff",
        "PRIMARY_BTN_FG": "#000000",
        "SECONDARY_HOVER_BG": "#ffffff",
        "SECONDARY_HOVER_FG": "#000000",
        "LOGO_TILE_BG": "#ffffff",
        "LOGO_TILE_FG": "#000000",
        "TITLEBAR_DARK_MODE": 1,
        "TITLEBAR_TEXT": "#ffffff",
    },
}

CURRENT_THEME = "dark"

# Active theme colour tokens (updated in-place across loaded GUI modules by apply_theme_palette).
DARK_BG = THEME_PALETTES["dark"]["DARK_BG"]
SIDEBAR_BG = THEME_PALETTES["dark"]["SIDEBAR_BG"]
TOPBAR_BG = THEME_PALETTES["dark"]["TOPBAR_BG"]
CARD_BG = THEME_PALETTES["dark"]["CARD_BG"]
SUBCARD_BG = THEME_PALETTES["dark"]["SUBCARD_BG"]
BANNER_BG = THEME_PALETTES["dark"]["BANNER_BG"]
MINI_BAR_BG = THEME_PALETTES["dark"]["MINI_BAR_BG"]
SELECTED_BG = THEME_PALETTES["dark"]["SELECTED_BG"]
INPUT_BG = THEME_PALETTES["dark"]["INPUT_BG"]
BORDER_LINE = THEME_PALETTES["dark"]["BORDER_LINE"]
DIVIDER_LINE = THEME_PALETTES["dark"]["DIVIDER_LINE"]
ORANGE_ACCENT = THEME_PALETTES["dark"]["ORANGE_ACCENT"]
ORANGE_HL = THEME_PALETTES["dark"]["ORANGE_HL"]
TEXT_WHITE = THEME_PALETTES["dark"]["TEXT_WHITE"]
TEXT_GRAY = THEME_PALETTES["dark"]["TEXT_GRAY"]
TEXT_LIGHT = THEME_PALETTES["dark"]["TEXT_LIGHT"]
GOLD_STAR = THEME_PALETTES["dark"]["GOLD_STAR"]
STAR_EMPTY = THEME_PALETTES["dark"]["STAR_EMPTY"]
ACTION_BTN_BG = THEME_PALETTES["dark"]["ACTION_BTN_BG"]
ACTION_BTN_FG = THEME_PALETTES["dark"]["ACTION_BTN_FG"]
PRIMARY_BTN_FG = THEME_PALETTES["dark"]["PRIMARY_BTN_FG"]
SECONDARY_HOVER_BG = THEME_PALETTES["dark"]["SECONDARY_HOVER_BG"]
SECONDARY_HOVER_FG = THEME_PALETTES["dark"]["SECONDARY_HOVER_FG"]
LOGO_TILE_BG = THEME_PALETTES["dark"]["LOGO_TILE_BG"]
LOGO_TILE_FG = THEME_PALETTES["dark"]["LOGO_TILE_FG"]
TITLEBAR_DARK_MODE = THEME_PALETTES["dark"]["TITLEBAR_DARK_MODE"]
TITLEBAR_TEXT = THEME_PALETTES["dark"]["TITLEBAR_TEXT"]

DEFAULT_FONT = load_bundled_reith_font()  # Bundled BBC Reith Sans (falls back to Segoe UI).
PODCASTS_PER_PAGE = 12       # Number of podcast cards rendered per paginated page.


def apply_theme_palette(theme_name):
    """Switch the active colour palette across theme.py and all loaded GUI modules."""
    global CURRENT_THEME
    key = theme_name if theme_name in THEME_PALETTES else "dark"
    CURRENT_THEME = key
    palette = THEME_PALETTES[key]
    for mod_name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        if mod_name == "__main__" or mod_name == "gui" or mod_name.startswith("gui_parts"):
            mod_dict = mod.__dict__
            for token, value in palette.items():
                if token in mod_dict:
                    mod_dict[token] = value
    return palette

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

    def __init__(self, parent, surface, border=None, **kwargs):
        super().__init__(parent, bg=parent.cget("bg"), **kwargs)
        if border is None:
            border = BORDER_LINE
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
