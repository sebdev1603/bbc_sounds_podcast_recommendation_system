"""SQLite connection manager and read-only query helpers for the BBC Sounds GUI."""
from contextlib import contextmanager
import random
import sqlite3
from tkinter import messagebox

from last_listened import order_listening_history
from gui_parts.theme import DATABASE_PATH, DURATION_RANGES, sanitize_column_name


class DatabaseMixin:
    """Mixin providing database access, podcast queries, and rating-average helpers."""

    def _ensure_db_connection(self):
        """Return a persistent SQLite connection tuned for low-latency desktop queries."""
        conn = getattr(self, "_db_conn", None)
        if conn is None:
            # Open a single reused connection with Row factory so columns can be accessed by name.
            conn = sqlite3.connect(str(DATABASE_PATH), timeout=8)
            conn.row_factory = sqlite3.Row
            try:
                # Apply lightweight SQLite pragmas: balanced durability, in-memory temp tables, ~8MB cache.
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA temp_store = MEMORY")
                conn.execute("PRAGMA cache_size = -8000")
            except sqlite3.Error:
                pass
            self._db_conn = conn
            self._db_depth = 0
        return conn

    def close_db_connection(self):
        """Close the cached SQLite connection cleanly on shutdown."""
        conn = getattr(self, "_db_conn", None)
        if conn is not None:
            # Clear cached state first so subsequent calls never reuse a closed handle.
            self._db_conn = None
            self._db_depth = 0
            try:
                conn.close()
            except sqlite3.Error:
                pass

    @contextmanager
    def get_db_connection(self):
        """Reuse the persistent SQLite connection, auto-committing or rolling back on exit."""
        conn = self._ensure_db_connection()
        # Track nesting depth so nested `with self.get_db_connection()` blocks commit only at the outermost level.
        self._db_depth = getattr(self, "_db_depth", 0) + 1
        try:
            yield conn
            if self._db_depth == 1 and conn.in_transaction:
                conn.commit()
        except Exception:
            # Roll back any uncommitted writes if an error occurs inside the outermost block.
            if self._db_depth == 1 and conn.in_transaction:
                conn.rollback()
            raise
        finally:
            self._db_depth = max(0, self._db_depth - 1)

    def get_listener_data(self):
        """Return the active listener's row from the listeners table, or None."""
        if self.current_user is None:
            return None
        with self.get_db_connection() as conn:
            return conn.execute(
                "SELECT * FROM listeners WHERE ListenerID = ?", (self.current_user,)
            ).fetchone()

    @staticmethod
    def get_row_field(row, key_name, default_val=None):
        """Perform a case-insensitive field lookup on a sqlite3.Row object."""
        if row is None:
            return default_val
        # Normalize column names to lowercase so schema casing differences do not break lookups.
        lookup_dict = {k.lower(): row[k] for k in row.keys()}
        return lookup_dict.get(key_name.lower(), default_val)

    def determine_sort_sql(self):
        """Detect an average-rating column if present in podcasts, otherwise sort alphabetically."""
        if self._sort_sql is not None:
            return self._sort_sql
        # Inspect the podcasts table schema once and cache the resulting ORDER BY clause.
        with self.get_db_connection() as conn:
            columns_map = {row[1].lower(): row[1] for row in conn.execute("PRAGMA table_info(podcasts)")}
        for candidate in ("averagerating", "average_rating", "ratingaverage"):
            if candidate in columns_map:
                self._sort_sql = sanitize_column_name(columns_map[candidate]) + " DESC"
                break
        else:
            # Fall back to case-insensitive alphabetical ordering by title.
            self._sort_sql = "Title COLLATE NOCASE ASC"
        return self._sort_sql

    def get_single_podcast(self, pid):
        """Fetch basic metadata for one podcast by PodcastID."""
        with self.get_db_connection() as conn:
            return conn.execute(
                "SELECT PodcastID, Title, Category, AverageLengthMins "
                "FROM podcasts WHERE PodcastID = ?",
                (pid,),
            ).fetchone()

    def query_podcasts(self, search_term="", item_limit=100, *, shuffle=False):
        """Search podcasts by title or category, optionally returning a weighted shuffle."""
        query_str = "SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts"
        params = []
        # Add a parameterized LIKE filter when a non-empty search keyword is supplied.
        if search_term.strip():
            pattern = f"%{search_term.strip()}%"
            query_str += " WHERE Title LIKE ? OR Category LIKE ?"
            params.extend([pattern, pattern])
        # When not shuffling, let SQLite sort and cap the result set directly.
        if not shuffle:
            query_str += f" ORDER BY {self.determine_sort_sql()} LIMIT ?"
            params.append(item_limit)
        with self.get_db_connection() as conn:
            rows = conn.execute(query_str, params).fetchall()
        return self.shuffle_podcasts(rows, item_limit) if shuffle else rows

    def fetch_user_history(self):
        """Return the active listener's listening history ordered newest-played first."""
        with self.get_db_connection() as conn:
            # Load all listened programmes ordered by play count as a fallback tie-breaker.
            rows = conn.execute(
                "SELECT p.PodcastID, p.Title, p.Category, p.AverageLengthMins, "
                "h.TimesListened, h.RatingGiven "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ? ORDER BY COALESCE(h.TimesListened, 0) DESC, "
                "p.Title COLLATE NOCASE",
                (self.current_user,),
            ).fetchall()
            # Re-order using listening_recency so the most recently played shows appear first.
            return order_listening_history(conn, self.current_user, rows, 0, 4)

    def fetch_user_favourites(self):
        """Return podcast rows corresponding to the listener's FavoritePodcasts CSV."""
        listener_row = self.get_listener_data()
        raw_favs = self.get_row_field(listener_row, "FavoritePodcasts", "") or ""
        # Split the comma-separated FavoritePodcasts string into clean ID tokens.
        id_list = [item.strip() for item in str(raw_favs).split(",") if item.strip()]
        if not id_list:
            return []
        # Build a parameterized IN (...) query to fetch all favourited podcasts in one round trip.
        placeholders = ",".join("?" for _ in id_list)
        with self.get_db_connection() as conn:
            return conn.execute(
                f"SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts "
                f"WHERE PodcastID IN ({placeholders}) ORDER BY Title COLLATE NOCASE",
                id_list,
            ).fetchall()

    def fetch_user_ratings(self):
        """Return all podcasts for which the active listener has saved a rating."""
        with self.get_db_connection() as conn:
            return conn.execute(
                "SELECT p.PodcastID, p.Title, p.Category, h.RatingGiven, h.TimesListened "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ? AND h.RatingGiven IS NOT NULL "
                "ORDER BY p.Title COLLATE NOCASE",
                (self.current_user,),
            ).fetchall()

    def get_custom_recommendations(self, count_limit=8, *, shuffle=False):
        """Return podcasts matching the listener's favourite genres and episode length preference."""
        listener_row = self.get_listener_data()
        # Extract the listener's saved genres and preferred duration bucket (Short/Medium/Long).
        user_genres = [
            g.strip()
            for g in str(self.get_row_field(listener_row, "FavoriteGenres", "") or "").split(",")
            if g.strip()
        ]
        preferred_len = self.get_row_field(listener_row, "LengthPreference", None)
        if not user_genres or preferred_len not in DURATION_RANGES:
            return []
        # Convert the length label into (min_minutes, max_minutes) bounds.
        low_limit, high_limit = DURATION_RANGES[preferred_len]
        marks = ",".join("?" for _ in user_genres)
        query = (
            "SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts "
            f"WHERE Category IN ({marks}) AND AverageLengthMins BETWEEN ? AND ?"
        )
        params = (*user_genres, low_limit, high_limit)
        if not shuffle:
            query += f" ORDER BY {self.determine_sort_sql()} LIMIT ?"
            params += (count_limit,)
        with self.get_db_connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return self.shuffle_podcasts(rows, count_limit) if shuffle else rows

    def check_if_favourited(self, pid):
        """Return True if the given PodcastID is in the listener's favourites."""
        listener_row = self.get_listener_data()
        favourite_string = str(self.get_row_field(listener_row, "FavoritePodcasts", "") or "")
        return str(pid) in [val.strip() for val in favourite_string.split(",")]

    def show_db_error(self, title_text, err_obj):
        """Display a modal error dialog for SQLite failures."""
        messagebox.showerror(title_text, str(err_obj), parent=self)

    def get_podcast_averages(self):
        """Return a cached dict mapping PodcastID -> average user rating."""
        if self._podcast_averages is None:
            # Aggregate all valid 1-5 community ratings once and cache until a rating is changed.
            with self.get_db_connection() as conn:
                self._podcast_averages = dict(conn.execute(
                    "SELECT PodcastID, AVG(RatingGiven) FROM listening_history "
                    "WHERE RatingGiven BETWEEN 1 AND 5 GROUP BY PodcastID"
                ).fetchall())
        return self._podcast_averages

    def shuffle_podcasts(self, rows, limit):
        """Shuffle podcasts using rating-weighted exponential sampling without duplicates."""
        averages = self.get_podcast_averages()

        def draw_priority(row):
            # Exponential draws give higher-rated podcasts smaller keys (earlier positions) without duplicates.
            score = averages.get(row[0], 2.5)
            return random.expovariate(score)

        return sorted(rows, key=draw_priority)[:limit]

    def podcast_average_text(self, podcast_id):
        """Format a podcast's community average rating for display."""
        average = self.get_podcast_averages().get(podcast_id)
        return f"★ {average:.1f} / 5 average" if average is not None else "Not yet rated"

    @staticmethod
    def _ensure_listener_name_column(conn):
        """Ensure the listeners table has a Name column for storing each listener's chosen name."""
        cols = {row[1].lower() for row in conn.execute("PRAGMA table_info(listeners)").fetchall()}
        if "name" not in cols:
            conn.execute("ALTER TABLE listeners ADD COLUMN Name TEXT")

    def save_listener_name(self, listener_id, name_value):
        """Persist (or clear) a listener's display name in database.db."""
        if listener_id is None:
            return False
        cleaned = " ".join(str(name_value or "").split()).strip()[:40]
        stored = cleaned if cleaned else None
        try:
            with self.get_db_connection() as conn:
                self._ensure_listener_name_column(conn)
                conn.execute(
                    "UPDATE listeners SET Name = ? WHERE ListenerID = ?",
                    (stored, listener_id),
                )
            return True
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save your name", err)
            return False

    @staticmethod
    def _ensure_accessibility_table(conn):
        """Create the per-user accessibility settings table in database.db if it does not exist."""
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_accessibility ("
            "ListenerID PRIMARY KEY NOT NULL, "
            "TextScale REAL NOT NULL DEFAULT 1.0, "
            "Theme TEXT NOT NULL DEFAULT 'dark', "
            "Language TEXT NOT NULL DEFAULT 'en')"
        )
        cols = {row[1].lower() for row in conn.execute("PRAGMA table_info(user_accessibility)").fetchall()}
        if "language" not in cols:
            conn.execute("ALTER TABLE user_accessibility ADD COLUMN Language TEXT NOT NULL DEFAULT 'en'")

    def load_user_language(self, listener_id):
        """Load the listener's saved UI language ('en' or 'cy'), defaulting to 'en'."""
        if listener_id is None:
            return "en"
        try:
            with self.get_db_connection() as conn:
                self._ensure_accessibility_table(conn)
                row = conn.execute(
                    "SELECT Language FROM user_accessibility WHERE ListenerID = ?",
                    (listener_id,),
                ).fetchone()
            if not row or not row[0]:
                return "en"
            lang = str(row[0]).strip().lower()
            return "cy" if lang == "cy" else "en"
        except sqlite3.Error:
            return "en"

    def save_user_language(self, listener_id, lang_code):
        """Persist a listener's UI language ('en' or 'cy') in database.db."""
        if listener_id is None:
            return
        lang = "cy" if str(lang_code or "").strip().lower() == "cy" else "en"
        try:
            with self.get_db_connection() as conn:
                self._ensure_accessibility_table(conn)
                conn.execute(
                    "INSERT INTO user_accessibility (ListenerID, TextScale, Theme, Language) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(ListenerID) DO UPDATE SET Language = excluded.Language",
                    (listener_id, getattr(self, "_text_scale", 1.0), getattr(self, "_theme_name", "dark"), lang),
                )
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save language setting", err)

    def load_user_accessibility(self, listener_id):
        """Load (text_scale, theme_name) for a listener from SQLite, defaulting to (1.0, 'dark')."""
        if listener_id is None:
            return 1.0, "dark"
        try:
            with self.get_db_connection() as conn:
                self._ensure_accessibility_table(conn)
                row = conn.execute(
                    "SELECT TextScale, Theme FROM user_accessibility WHERE ListenerID = ?",
                    (listener_id,),
                ).fetchone()
            if not row:
                return 1.0, "dark"
            try:
                scale = round(max(0.80, min(1.40, float(row[0]))), 2)
            except (TypeError, ValueError):
                scale = 1.0
            theme = str(row[1] or "dark").strip().lower()
            if theme not in ("dark", "light", "high_contrast"):
                theme = "dark"
            return scale, theme
        except sqlite3.Error:
            return 1.0, "dark"

    def save_user_accessibility(self, listener_id, text_scale, theme_name):
        """Persist a listener's text size and theme preference in database.db."""
        if listener_id is None:
            return
        scale = round(max(0.80, min(1.40, float(text_scale))), 2)
        theme = theme_name if theme_name in ("dark", "light", "high_contrast") else "dark"
        try:
            with self.get_db_connection() as conn:
                self._ensure_accessibility_table(conn)
                conn.execute(
                    "INSERT INTO user_accessibility (ListenerID, TextScale, Theme) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(ListenerID) DO UPDATE SET "
                    "TextScale = excluded.TextScale, Theme = excluded.Theme",
                    (listener_id, scale, theme),
                )
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save accessibility settings", err)
