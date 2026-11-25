"""SQLite connection manager and read-only query helpers for the BBC Sounds GUI."""
from contextlib import contextmanager
from difflib import SequenceMatcher
import hashlib
import hmac
import random
import secrets
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
        """Search podcasts: exact/closest match first, then similar title/genre/region in rating-weighted random order."""
        cleaned = " ".join(str(search_term or "").strip().split())
        if not cleaned:
            query_str = "SELECT PodcastID, Title, Category, AverageLengthMins FROM podcasts"
            params = []
            if not shuffle:
                query_str += f" ORDER BY {self.determine_sort_sql()} LIMIT ?"
                params.append(item_limit)
            with self.get_db_connection() as conn:
                rows = conn.execute(query_str, params).fetchall()
            return self.shuffle_podcasts(rows, item_limit) if shuffle else rows

        with self.get_db_connection() as conn:
            all_rows = conn.execute(
                "SELECT PodcastID, Title, Category, AverageLengthMins, BBCRegion, AudienceRating "
                "FROM podcasts"
            ).fetchall()
        if not all_rows:
            return []

        q = cleaned.lower()
        q_tokens = [tok for tok in q.split() if tok]
        averages = self.get_podcast_averages()

        def row_rating(row):
            avg = averages.get(row[0])
            if avg is not None:
                return float(avg)
            aud = row[5]
            return float(aud) if aud is not None else 2.5

        def direct_match_rank(row):
            title_l = str(row[1] or "").lower().strip()
            cat_l = str(row[2] or "").lower().strip()
            reg_l = str(row[4] or "").lower().strip()
            if title_l == q:
                tier = 0
            elif title_l.startswith(q):
                tier = 1
            elif q in title_l:
                tier = 2
            elif cat_l == q or reg_l == q:
                tier = 3
            elif q in cat_l or q in reg_l:
                tier = 4
            elif q_tokens and all(
                (tok in title_l or tok in cat_l or tok in reg_l) for tok in q_tokens
            ):
                tier = 5
            else:
                return None
            return (tier, len(title_l), -row_rating(row))

        direct_candidates = []
        for row in all_rows:
            rank = direct_match_rank(row)
            if rank is not None:
                direct_candidates.append((rank, row))

        if direct_candidates:
            direct_candidates.sort(key=lambda item: item[0])
            primary_row = direct_candidates[0][1]
        else:
            # Fuzzy fallback: pick the closest title/genre/region to the query as the top match.
            best_score = 0.0
            primary_row = None
            for row in all_rows:
                title_l = str(row[1] or "").lower().strip()
                cat_l = str(row[2] or "").lower().strip()
                reg_l = str(row[4] or "").lower().strip()
                fuzzy = max(
                    SequenceMatcher(None, q, title_l).ratio(),
                    SequenceMatcher(None, q, cat_l).ratio() * 0.9,
                    SequenceMatcher(None, q, reg_l).ratio() * 0.85,
                )
                if fuzzy > best_score:
                    best_score = fuzzy
                    primary_row = row
            if primary_row is None or best_score < 0.35:
                return []

        primary_id = primary_row[0]
        primary_title = str(primary_row[1] or "").lower().strip()
        primary_cat = str(primary_row[2] or "").lower().strip()
        primary_reg = str(primary_row[4] or "").lower().strip()
        query_matched_title = (q in primary_title) or (
            bool(q_tokens) and any(tok in primary_title for tok in q_tokens)
        )
        ref_tokens = {tok for tok in q_tokens if len(tok) >= 2}
        if query_matched_title:
            ref_tokens |= {tok for tok in primary_title.split() if len(tok) >= 2}

        related_pool = []
        for row in all_rows:
            if row[0] == primary_id:
                continue
            title_l = str(row[1] or "").lower().strip()
            cat_l = str(row[2] or "").lower().strip()
            reg_l = str(row[4] or "").lower().strip()

            sim = 0.0
            if q in title_l:
                sim += 4.5
            if q in cat_l:
                sim += 4.0
            if q in reg_l:
                sim += 3.5
            if primary_cat and cat_l == primary_cat:
                sim += 2.6
            if primary_reg and reg_l == primary_reg:
                sim += 2.0

            title_tokens = {tok for tok in title_l.split() if len(tok) >= 2}
            if ref_tokens and title_tokens:
                overlap = len(ref_tokens & title_tokens) / float(len(ref_tokens))
                sim += overlap * 1.6
            title_ratio = SequenceMatcher(None, q, title_l).ratio()
            if query_matched_title:
                title_ratio = max(title_ratio, SequenceMatcher(None, primary_title, title_l).ratio() * 0.85)
            if title_ratio >= 0.45:
                sim += title_ratio * 1.8

            if sim >= 2.0:
                rating = max(0.5, row_rating(row))
                # Order semi-randomly while clearly favouring higher ratings (highest to lowest) and stronger similarity.
                jitter = random.uniform(-0.85, 0.85) if shuffle else 0.0
                score = rating * 2.0 + sim * 0.65 + jitter
                related_pool.append((-score, title_l, row))

        related_pool.sort(key=lambda item: (item[0], item[1]))
        ordered = [primary_row] + [row for _, _, row in related_pool]
        return [(r[0], r[1], r[2], r[3]) for r in ordered[:item_limit]]

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

    @staticmethod
    def _ensure_downloads_table(conn):
        """Create the per-user downloads table in database.db if it does not exist."""
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_downloads ("
            "ListenerID NOT NULL, "
            "PodcastID NOT NULL, "
            "DownloadedAt REAL NOT NULL DEFAULT 0, "
            "PRIMARY KEY (ListenerID, PodcastID))"
        )

    def check_if_downloaded(self, pid):
        """Return True if the active listener has downloaded the given PodcastID."""
        if self.current_user is None:
            return False
        try:
            with self.get_db_connection() as conn:
                self._ensure_downloads_table(conn)
                row = conn.execute(
                    "SELECT 1 FROM user_downloads WHERE ListenerID = ? AND PodcastID = ?",
                    (self.current_user, pid),
                ).fetchone()
            return row is not None
        except sqlite3.Error:
            return False

    def fetch_user_downloads(self):
        """Return podcast rows downloaded by the active listener, newest first."""
        if self.current_user is None:
            return []
        try:
            with self.get_db_connection() as conn:
                self._ensure_downloads_table(conn)
                return conn.execute(
                    "SELECT p.PodcastID, p.Title, p.Category, p.AverageLengthMins "
                    "FROM user_downloads d JOIN podcasts p ON p.PodcastID = d.PodcastID "
                    "WHERE d.ListenerID = ? "
                    "ORDER BY d.DownloadedAt DESC, p.Title COLLATE NOCASE",
                    (self.current_user,),
                ).fetchall()
        except sqlite3.Error:
            return []

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

    @staticmethod
    def _ensure_listener_avatar_column(conn):
        """Ensure the listeners table has an Avatar column for storing the chosen premade avatar key."""
        cols = {row[1].lower() for row in conn.execute("PRAGMA table_info(listeners)").fetchall()}
        if "avatar" not in cols:
            conn.execute("ALTER TABLE listeners ADD COLUMN Avatar TEXT")

    @staticmethod
    def validate_password_strength(password):
        """Enforce password policy for new/changed/reset passwords (existing legacy logins remain valid).

        Policy: 8-128 characters, including at least one uppercase letter, one lowercase letter,
        and one digit. Capping length at 128 also prevents CPU DoS against scrypt hashing.
        Returns (True, "") if valid, otherwise (False, reason_message).
        """
        pw = str(password or "")
        if len(pw) < 8:
            return False, "Password must be at least 8 characters long."
        if len(pw) > 128:
            return False, "Password must be 128 characters or fewer."
        missing = []
        if not any(ch.isupper() for ch in pw):
            missing.append("an uppercase letter")
        if not any(ch.islower() for ch in pw):
            missing.append("a lowercase letter")
        if not any(ch.isdigit() for ch in pw):
            missing.append("a number")
        if missing:
            return False, "Password must include " + ", ".join(missing) + "."
        return True, ""

    @staticmethod
    def password_strength_summary(password):
        """Return a (label, hex_colour) live strength indicator for password input fields."""
        pw = str(password or "")
        if not pw:
            return "", "#9a9fa8"
        score = 0
        if len(pw) >= 8:
            score += 1
        if len(pw) >= 12:
            score += 1
        if any(ch.isupper() for ch in pw) and any(ch.islower() for ch in pw):
            score += 1
        if any(ch.isdigit() for ch in pw):
            score += 1
        if any(not ch.isalnum() for ch in pw):
            score += 1
        if score <= 2 or len(pw) < 8:
            return "Strength: Weak  ·  Use 8+ chars, upper, lower & a number", "#ff6b6b"
        if score == 3:
            return "Strength: Fair  ·  Meets policy (add length or a symbol to strengthen)", "#ffb347"
        return "Strength: Strong", "#7ce38b"

    @staticmethod
    def hash_password(password):
        """Hash a plaintext password using scrypt with a unique random 16-byte salt.

        Format returned: 'scrypt$<salt_hex>$<hash_hex>'
        - Random salt ensures identical passwords (e.g. default '1') produce completely
          different hashes for every listener, defeating rainbow-table lookups.
        - scrypt (n=2**14, r=8, p=1) is intentionally slow and memory-hard so an attacker
          with a copy of database.db cannot rapidly brute-force passwords on a GPU.
        """
        # Generate 16 cryptographically secure random bytes (128 bits) for this password's salt.
        salt = secrets.token_bytes(16)
        # Derive a 32-byte (256-bit) key from the UTF-8 password bytes and salt using scrypt.
        digest = hashlib.scrypt(
            str(password).encode("utf-8"),
            salt=salt,
            n=2**14,   # CPU/memory cost factor (16,384 iterations)
            r=8,       # Block size factor (memory usage scales with r * n)
            p=1,       # Parallelization factor
            dklen=32,  # Output hash length in bytes
        )
        # Store the algorithm tag, hex-encoded salt, and hex-encoded hash together in one column.
        return f"scrypt${salt.hex()}${digest.hex()}"

    @staticmethod
    def check_password_hash(password, stored_value):
        """Verify a candidate plaintext password against a stored salted scrypt hash.

        Uses hmac.compare_digest for constant-time comparison so execution time never
        leaks how many leading bytes of the hash matched (prevents timing attacks).
        """
        stored = str(stored_value or "")
        # Safety fallback if a legacy row has not yet been migrated from plaintext.
        if not stored.startswith("scrypt$"):
            legacy_plain = stored if stored != "" else "1"
            return hmac.compare_digest(str(password), legacy_plain)
        try:
            # Split 'scrypt$<salt_hex>$<hash_hex>' back into its original salt and expected digest.
            _scheme, salt_hex, hash_hex = stored.split("$", 2)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            # Re-run scrypt with the exact same salt and cost parameters on the candidate password.
            actual = hashlib.scrypt(
                str(password).encode("utf-8"),
                salt=salt,
                n=2**14,
                r=8,
                p=1,
                dklen=len(expected),
            )
            # Compare both byte strings in constant time; returns True only on an exact match.
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError):
            return False

    @classmethod
    def _ensure_listener_password_column(cls, conn):
        """Ensure listeners.Password exists (legacy rows are lazily migrated to scrypt on sign-in)."""
        cols = {row[1].lower() for row in conn.execute("PRAGMA table_info(listeners)").fetchall()}
        if "password" not in cols:
            conn.execute("ALTER TABLE listeners ADD COLUMN Password TEXT")

    @classmethod
    def _verify_and_upgrade_password(cls, conn, listener_id, password_text, stored_value):
        """Verify password_text against stored_value, lazily upgrading legacy plaintext/NULL rows to scrypt."""
        stored = str(stored_value or "")
        if stored.startswith("scrypt$"):
            return cls.check_password_hash(password_text, stored)
        # Legacy row (NULL, empty, or plaintext): upgrade only this listener on demand so login stays fast.
        legacy_plain = stored if stored != "" else "1"
        hashed = cls.hash_password(legacy_plain)
        conn.execute(
            "UPDATE listeners SET Password = ? WHERE ListenerID = ?",
            (hashed, listener_id),
        )
        return hmac.compare_digest(str(password_text), legacy_plain)

    def verify_listener_password(self, listener_id, password_text):
        """Return True if password_text matches the salted scrypt hash stored for listener_id."""
        if listener_id is None:
            return False
        try:
            with self.get_db_connection() as conn:
                self._ensure_listener_password_column(conn)
                row = conn.execute(
                    "SELECT Password FROM listeners WHERE ListenerID = ?",
                    (listener_id,),
                ).fetchone()
                if row is None:
                    return False
                # Verify against the stored salted hash (or lazily upgrade a legacy row).
                return self._verify_and_upgrade_password(conn, listener_id, password_text, row[0])
        except sqlite3.Error:
            return False

    def update_listener_password(self, listener_id, new_password):
        """Hash new_password with a fresh random salt and persist it for listener_id."""
        if listener_id is None or not str(new_password):
            return False
        try:
            with self.get_db_connection() as conn:
                self._ensure_listener_password_column(conn)
                # Always generate a brand-new salt whenever a password is changed.
                hashed_pw = self.hash_password(new_password)
                cur = conn.execute(
                    "UPDATE listeners SET Password = ? WHERE ListenerID = ?",
                    (hashed_pw, listener_id),
                )
                return cur.rowcount > 0
        except sqlite3.Error as err:
            self.show_db_error("Couldn't update password", err)
            return False

    def create_listener_account(self, password, age_group="19-25"):
        """Create a new listener row with the next sequential ListenerID and a salted password hash."""
        if not str(password):
            return None
        valid_ages = ("16-18", "19-25", "26-35", "36-50", "50+")
        chosen_age = age_group if age_group in valid_ages else "19-25"
        try:
            with self.get_db_connection() as conn:
                self._ensure_listener_name_column(conn)
                self._ensure_listener_avatar_column(conn)
                self._ensure_listener_password_column(conn)
                row = conn.execute("SELECT MAX(ListenerID) FROM listeners").fetchone()
                next_id = int(row[0] if (row and row[0] is not None) else 1000) + 1
                # Hash the chosen password with a unique random salt before storing it in SQLite.
                hashed_pw = self.hash_password(password)
                conn.execute(
                    "INSERT INTO listeners "
                    "(ListenerID, AgeGroup, PreferredCategory, ListeningHoursPerWeek, CompleteSurvey, "
                    "LengthPreference, FavoritePodcasts, FavoriteGenres, Name, Avatar, Password) "
                    "VALUES (?, ?, ?, 0, 0, 'Medium', '', '', NULL, 'default', ?)",
                    (next_id, chosen_age, "", hashed_pw),
                )
            return next_id
        except sqlite3.Error as err:
            self.show_db_error("Couldn't create account", err)
            return None

    def save_listener_avatar(self, listener_id, avatar_key):
        """Persist a listener's chosen premade avatar key in database.db."""
        if listener_id is None:
            return False
        valid_keys = ("default", "vinyl", "headphones", "mic", "waves", "owl", "bot", "sunset")
        stored = avatar_key if avatar_key in valid_keys else "default"
        try:
            with self.get_db_connection() as conn:
                self._ensure_listener_avatar_column(conn)
                conn.execute(
                    "UPDATE listeners SET Avatar = ? WHERE ListenerID = ?",
                    (stored, listener_id),
                )
            return True
        except sqlite3.Error as err:
            self.show_db_error("Couldn't save profile picture", err)
            return False

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
            "Language TEXT NOT NULL DEFAULT 'en', "
            "ReducedMotion INTEGER NOT NULL DEFAULT 0, "
            "ScreenReader INTEGER NOT NULL DEFAULT 0)"
        )
        cols = {row[1].lower() for row in conn.execute("PRAGMA table_info(user_accessibility)").fetchall()}
        for col, ddl in (
            ("language", "Language TEXT NOT NULL DEFAULT 'en'"),
            ("reducedmotion", "ReducedMotion INTEGER NOT NULL DEFAULT 0"),
            ("screenreader", "ScreenReader INTEGER NOT NULL DEFAULT 0"),
        ):
            if col not in cols:
                conn.execute(f"ALTER TABLE user_accessibility ADD COLUMN {ddl}")

    def _query_accessibility_row(self, listener_id, columns):
        if listener_id is None:
            return None
        try:
            with self.get_db_connection() as conn:
                self._ensure_accessibility_table(conn)
                return conn.execute(
                    f"SELECT {columns} FROM user_accessibility WHERE ListenerID = ?", (listener_id,),
                ).fetchone()
        except sqlite3.Error:
            return None

    def _upsert_accessibility(self, listener_id, err_title, **updates):
        if listener_id is None:
            return
        values = {
            "TextScale": getattr(self, "_text_scale", 1.0),
            "Theme": getattr(self, "_theme_name", "dark"),
            "Language": getattr(self, "_language", "en"),
            "ReducedMotion": 1 if getattr(self, "_reduced_motion", False) else 0,
            "ScreenReader": 1 if getattr(self, "_screen_reader", False) else 0,
            **updates,
        }
        set_clause = ", ".join(f"{col} = excluded.{col}" for col in updates)
        try:
            with self.get_db_connection() as conn:
                self._ensure_accessibility_table(conn)
                conn.execute(
                    "INSERT INTO user_accessibility (ListenerID, TextScale, Theme, Language, ReducedMotion, ScreenReader) "
                    f"VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(ListenerID) DO UPDATE SET {set_clause}",
                    (
                        listener_id, values["TextScale"], values["Theme"],
                        values["Language"], values["ReducedMotion"], values["ScreenReader"],
                    ),
                )
        except sqlite3.Error as err:
            self.show_db_error(err_title, err)

    def load_user_screen_reader(self, listener_id):
        """Load the listener's saved screen-reader preference (bool), defaulting to False."""
        row = self._query_accessibility_row(listener_id, "ScreenReader")
        return bool(row and row[0])

    def save_user_screen_reader(self, listener_id, enabled):
        """Persist a listener's screen-reader preference in database.db."""
        self._upsert_accessibility(listener_id, "Couldn't save screen reader setting", ScreenReader=1 if enabled else 0)

    def load_user_reduced_motion(self, listener_id):
        """Load the listener's saved reduced-motion preference (bool), defaulting to False."""
        row = self._query_accessibility_row(listener_id, "ReducedMotion")
        return bool(row and row[0])

    def save_user_reduced_motion(self, listener_id, reduced_motion):
        """Persist a listener's reduced-motion preference in database.db."""
        self._upsert_accessibility(listener_id, "Couldn't save motion setting", ReducedMotion=1 if reduced_motion else 0)

    def load_user_language(self, listener_id):
        """Load the listener's saved UI language ('en' or 'cy'), defaulting to 'en'."""
        row = self._query_accessibility_row(listener_id, "Language")
        return "cy" if row and row[0] and str(row[0]).strip().lower() == "cy" else "en"

    def save_user_language(self, listener_id, lang_code):
        """Persist a listener's UI language ('en' or 'cy') in database.db."""
        lang = "cy" if str(lang_code or "").strip().lower() == "cy" else "en"
        self._upsert_accessibility(listener_id, "Couldn't save language setting", Language=lang)

    def load_user_accessibility(self, listener_id):
        """Load (text_scale, theme_name) for a listener from SQLite, defaulting to (1.0, 'dark')."""
        row = self._query_accessibility_row(listener_id, "TextScale, Theme")
        if not row:
            return 1.0, "dark"
        try:
            scale = round(max(0.80, min(1.40, float(row[0]))), 2)
        except (TypeError, ValueError):
            scale = 1.0
        theme = str(row[1] or "dark").strip().lower()
        return scale, theme if theme in ("dark", "light", "high_contrast") else "dark"

    def save_user_accessibility(self, listener_id, text_scale, theme_name):
        """Persist a listener's text size and theme preference in database.db."""
        scale = round(max(0.80, min(1.40, float(text_scale))), 2)
        theme = theme_name if theme_name in ("dark", "light", "high_contrast") else "dark"
        self._upsert_accessibility(listener_id, "Couldn't save accessibility settings", TextScale=scale, Theme=theme)
