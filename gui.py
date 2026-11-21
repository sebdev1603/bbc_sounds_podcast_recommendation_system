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
        # Apply the bundled BBC Reith Sans font to Tkinter's built-in named fonts as well.
        for named_font in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
            try:
                tkfont.nametofont(named_font).configure(family=DEFAULT_FONT)
            except tk.TclError:
                pass
        self.title("BBC Sounds | Discover something new")
        self.geometry("1320x850")
        self.minsize(1024, 700)
        self.configure(bg=DARK_BG)

        self._base_tk_scaling = float(self.tk.call("tk", "scaling"))
        self._ui_scale_factor = 1.0
        self._text_scale = 1.0
        self._theme_name = "dark"
        self._language = "en"
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
