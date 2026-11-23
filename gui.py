"""Entry point for the BBC Sounds Podcast Recommendation System desktop GUI."""
# Standard library imports for LRU caches, Windows taskbar ID, and Tkinter GUI.
from collections import OrderedDict
import ctypes
import sys
import tkinter as tk
from tkinter import font as tkfont

# Feature mixins split across gui_parts/ to keep the application modular.
from gui_parts.db_queries import DatabaseMixin
from gui_parts.detail_view import DetailViewMixin
from gui_parts.effects import EffectsMixin
from gui_parts.login_view import LoginViewMixin
from gui_parts.pages import PagesMixin
from gui_parts.theme import DARK_BG, DEFAULT_FONT
from gui_parts.widgets import WidgetsMixin


class BBCSoundsGUI(
    DatabaseMixin,
    WidgetsMixin,
    EffectsMixin,
    LoginViewMixin,
    PagesMixin,
    DetailViewMixin,
    tk.Tk,
):
    """Main Tkinter application window composing all modular GUI mixins."""

    def __init__(self):
        # Assign a custom Windows AppUserModelID so the taskbar uses the BBC Sounds icon.
        if sys.platform == "win32":
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("bbc.sounds.podcast.recommender")
            except Exception:
                pass
        super().__init__()
        # Verify the active font family exists in Tk (falls back cleanly on Linux/macOS if needed).
        try:
            available_fonts = set(tkfont.families(self))
            if available_fonts and DEFAULT_FONT not in available_fonts:
                for fallback in (
                    "BBC Reith Sans", "Adwaita Sans", "Cantarell", "Noto Sans",
                    "Liberation Sans", "DejaVu Sans", "Segoe UI", "Helvetica Neue", "Helvetica",
                ):
                    if fallback in available_fonts:
                        import gui_parts.theme as _theme_mod
                        for _m in list(sys.modules.values()):
                            if _m is not None and getattr(_m, "__name__", "").startswith(("gui", "__main__")):
                                if "DEFAULT_FONT" in _m.__dict__:
                                    _m.__dict__["DEFAULT_FONT"] = fallback
                        _theme_mod.DEFAULT_FONT = fallback
                        break
        except tk.TclError:
            pass
        # Apply the active font family to Tkinter's built-in named fonts as well.
        active_font = sys.modules["gui_parts.theme"].DEFAULT_FONT
        for named_font in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
            try:
                tkfont.nametofont(named_font).configure(family=active_font)
            except tk.TclError:
                pass
        self.title("BBC Sounds | Discover something new")
        # Clamp initial and minimum window sizes to the current display so Fedora/HiDPI laptops never clip the UI.
        screen_w = max(800, self.winfo_screenwidth())
        screen_h = max(600, self.winfo_screenheight())
        init_w = min(1320, max(900, screen_w - 40))
        init_h = min(850, max(600, screen_h - 80))
        min_w = min(940, max(760, screen_w - 40))
        min_h = min(620, max(520, screen_h - 80))
        self.geometry(f"{init_w}x{init_h}")
        self.minsize(min_w, min_h)
        self.configure(bg=DARK_BG)

        self._base_tk_scaling = float(self.tk.call("tk", "scaling"))
        self._ui_scale_factor = 1.0
        self._text_scale = 1.0
        self._theme_name = "dark"
        self._language = "en"
        self._reduced_motion = False
        self._anim_ema_ms = 6.0
        self._resize_after_id = None

        self.current_user = None
        self.active_genres = []
        self.active_length = "Medium"
        self.svg_store = {}
        self.image_store = {}
        self.cover_images = OrderedDict()
        self.button_images = OrderedDict()
        self.genre_elements = {}
        self.length_buttons = {}
        self.search_text = tk.StringVar()
        self.current_page = None
        self._sort_sql = None
        self._podcast_averages = None
        self._dismissed_last_listened = None
        self._pending_render_id = None
        self._render_queue = []
        self._search_after_id = None
        self._live_search_callback = None
        self._search_entry = None
        self._search_prompt = None
        self._tab_transition_direction = None
        self._transition_active = False
        self._font_cache = {}
        self._scroll_priority_until = 0.0
        self._active_detail_podcast = None
        self._bottom_bar_info = None
        self._armed_easter_egg = None

        self.bind("<Configure>", self.schedule_interface_scaling)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.set_window_icon()
        self.set_windows_titlebar_colour(DARK_BG)
        self.show_login()

    def _on_close(self):
        """Close the persistent database connection before destroying the app window."""
        self.close_db_connection()
        self.destroy()


if __name__ == "__main__":
    BBCSoundsGUI().mainloop()
