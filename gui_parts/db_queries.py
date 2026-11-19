"""SQLite connection manager and read-only query helpers for the BBC Sounds GUI."""
from contextlib import contextmanager
import random
import sqlite3
from tkinter import messagebox

from last_listened import order_listening_history
from gui_parts.theme import DATABASE_PATH, DURATION_RANGES, sanitize_column_name


class DatabaseMixin:
    """Mixin providing database access, podcast queries, and rating-average helpers."""

    @contextmanager
    def get_db_connection(self):
        """Open a SQLite connection with Row access, auto-committing or rolling back on exit."""
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
        lookup_dict = {k.lower(): row[k] for k in row.keys()}
        return lookup_dict.get(key_name.lower(), default_val)

    def determine_sort_sql(self):
        """Detect an average-rating column if present in podcasts, otherwise sort alphabetically."""
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
        if search_term.strip():
            pattern = f"%{search_term.strip()}%"
            query_str += " WHERE Title LIKE ? OR Category LIKE ?"
            params.extend([pattern, pattern])
        if not shuffle:
            query_str += f" ORDER BY {self.determine_sort_sql()} LIMIT ?"
            params.append(item_limit)
        with self.get_db_connection() as conn:
            rows = conn.execute(query_str, params).fetchall()
        return self.shuffle_podcasts(rows, item_limit) if shuffle else rows

    def fetch_user_history(self):
        """Return the active listener's listening history ordered newest-played first."""
        with self.get_db_connection() as conn:
            rows = conn.execute(
                "SELECT p.PodcastID, p.Title, p.Category, p.AverageLengthMins, "
                "h.TimesListened, h.RatingGiven "
                "FROM listening_history h JOIN podcasts p ON p.PodcastID = h.PodcastID "
                "WHERE h.ListenerID = ? ORDER BY COALESCE(h.TimesListened, 0) DESC, "
                "p.Title COLLATE NOCASE",
                (self.current_user,),
            ).fetchall()
            return order_listening_history(conn, self.current_user, rows, 0, 4)

    def fetch_user_favourites(self):
        """Return podcast rows corresponding to the listener's FavoritePodcasts CSV."""
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
            # Exponential draws give higher weights earlier positions without duplicates.
            score = averages.get(row[0], 2.5)
            return random.expovariate(score)

        return sorted(rows, key=draw_priority)[:limit]

    def podcast_average_text(self, podcast_id):
        """Format a podcast's community average rating for display."""
        average = self.get_podcast_averages().get(podcast_id)
        return f"★ {average:.1f} / 5 average" if average is not None else "Not yet rated"
