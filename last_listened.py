# Helpers for tracking each listener's most recently played podcast and play recency order.

def record_last_listened(conn, listener_id, podcast_id):
    """Remember a play in the same transaction as the history update."""
    # Ensure both recency tracking tables exist before writing.
    conn.execute(
        "CREATE TABLE IF NOT EXISTS last_listened ("
        "ListenerID PRIMARY KEY NOT NULL, PodcastID NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS listening_recency ("
        "ListenerID NOT NULL, PodcastID NOT NULL, PlayOrder INTEGER NOT NULL, "
        "PRIMARY KEY (ListenerID, PodcastID))"
    )
    # Backfill any previously stored last_listened entry at order 0 so it isn't lost.
    conn.execute(
        "INSERT OR IGNORE INTO listening_recency (ListenerID, PodcastID, PlayOrder) "
        "SELECT ListenerID, PodcastID, 0 FROM last_listened WHERE ListenerID = ?",
        (listener_id,),
    )
    # Assign the next monotonically increasing PlayOrder for this listener and podcast.
    conn.execute(
        "INSERT INTO listening_recency (ListenerID, PodcastID, PlayOrder) "
        "VALUES (?, ?, (SELECT COALESCE(MAX(PlayOrder), 0) + 1 "
        "FROM listening_recency WHERE ListenerID = ?)) "
        "ON CONFLICT(ListenerID, PodcastID) DO UPDATE SET PlayOrder = excluded.PlayOrder",
        (listener_id, podcast_id, listener_id),
    )
    # Update the single "last listened" pointer for quick lookup in the UI.
    conn.execute(
        "INSERT INTO last_listened (ListenerID, PodcastID) VALUES (?, ?) "
        "ON CONFLICT(ListenerID) DO UPDATE SET PodcastID = excluded.PodcastID",
        (listener_id, podcast_id),
    )


def order_listening_history(conn, listener_id, rows, podcast_id_index, play_count_index):
    """Sort tracked plays newest first and retain the fallback order of older rows."""
    # Build a lookup map of PodcastID -> PlayOrder from recency tables.
    recent = get_last_listened(conn, listener_id)
    play_order = {recent[0]: 0} if recent is not None else {}
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'listening_recency'"
    ).fetchone():
        play_order.update(conn.execute(
            "SELECT PodcastID, PlayOrder FROM listening_recency WHERE ListenerID = ?",
            (listener_id,),
        ).fetchall())

    # Unplayed or untracked rows receive -1 so they stay after recently played shows.
    def recency(row):
        if (row[play_count_index] or 0) > 0:
            return play_order.get(row[podcast_id_index], -1)
        return -1

    return sorted(rows, key=recency, reverse=True)


def get_last_listened(conn, listener_id):
    """Return (PodcastID, Title, Category) for the listener's most recent played podcast, or None."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'last_listened'"
    ).fetchone():
        return None
    # Only return the last listened podcast if it still exists in listening_history with plays > 0.
    return conn.execute(
        "SELECT p.PodcastID, p.Title, p.Category FROM last_listened AS recent "
        "JOIN podcasts AS p ON p.PodcastID = recent.PodcastID "
        "WHERE recent.ListenerID = ? AND EXISTS ("
        "SELECT 1 FROM listening_history AS h "
        "WHERE h.ListenerID = recent.ListenerID AND h.PodcastID = p.PodcastID "
        "AND h.TimesListened > 0)",
        (listener_id,),
    ).fetchone()
