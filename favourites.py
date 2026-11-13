import sqlite3
import time


def clear():
    import main as app
    app.clear()


def main():
    import main as app
    app.main()


def view_favourite_genres(username):
    clear()
    print("***FAVOURITE GENRES & MATCHING PODCASTS***\n")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT FavoriteGenres FROM listeners WHERE ListenerID = ?",
        (username,)
    )
    res = cursor.fetchone()

    if res and res[0]:
        print(f"Your favourite genres: {res[0].replace(',', ', ')}\n")

        cursor.execute(
            """
                SELECT podcasts.Title, podcasts.Category
                FROM podcasts
                JOIN listeners ON (
                    ',' || listeners.FavoriteGenres || ',' LIKE '%,' || podcasts.Category || ',%'
                )
                WHERE listeners.ListenerID = ?
                """,
            (username,)
        )

        results = cursor.fetchall()

        if results:
            print("Podcasts matching your favourite genres:")
            for title, category in results:
                print(f"- {title} ({category})")
        else:
            print("No podcasts found matching your favourite genres.")
    else:
        print("You have no favourite genres set.")

    conn.close()
    input("\nPress Enter to return to the main menu...")
    main()

def view_favourite_programmes(username, view_podcast_details):
    clear()
    print("***FAVOURITE PODCASTS***\n")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """SELECT podcasts.Title FROM podcasts JOIN listeners ON (
            ',' || listeners.FavoritePodcasts || ',' LIKE '%,' || podcasts.PodcastID || ',%'
            ) WHERE listeners.ListenerID = ?""",
        (username,)
    )

    results = cursor.fetchall()

    while True:
        if results:
            print("Your favourite podcasts:")
            for result in results:
                print(f"- {result[0]}")
        else:
            print("You have no favourite podcasts.")

        print('''\nWhat would you like to do next?

            1. View details of a favourite podcast
            2. Delete a favourite podcast
            3. Return to main menu''')

        choice = input("\nEnter your choice: ").strip()
        if choice == "1":
            podcast_title = input("Enter the title of the podcast you want to view details for (The name must match exactly): ").strip()
            if podcast_title not in [result[0] for result in results]:
                print("\nThe podcast is not in your favourites.")
                time.sleep(1)
                clear()
            else:
                view_podcast_details(podcast_title)
        elif choice == "2":
            print("\nTo go back, press Enter without typing anything.")
            print("\nWARNING: Deleting a favourite podcast is permanent and cannot be undone.")
            podcast_title = input("Enter the title of the podcast you want to delete from favourites (The name must match exactly): ").strip()
            if podcast_title == "":
                clear()
                print("\nReturning to favourites menu...")
                time.sleep(1)
                view_favourite_programmes(username, view_podcast_details)
            elif podcast_title not in [result[0] for result in results]:
                print("\nThe podcast is not in your favourites.")
                time.sleep(1)
                clear()
            else:
                delete_favourite_programme(podcast_title, username)
        elif choice == "3":
            main()
        else:
            print("Invalid choice")
            time.sleep(1)
            clear()

    conn.close()

def delete_favourite_programme(podcast_title, username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT PodcastID FROM podcasts WHERE Title = ?",
        (podcast_title,)
    )

    result = cursor.fetchone()

    if result:
        podcast_id = result[0]
        cursor.execute(
            "SELECT FavoritePodcasts FROM listeners WHERE ListenerID = ?",
            (username,)
        )

        result = cursor.fetchone()
        current_favourites = result[0] if result else ""

        updated_favourites = ','.join(
            [pid for pid in current_favourites.split(',') if pid != str(podcast_id)]
        )

        cursor.execute(
            "UPDATE listeners SET FavoritePodcasts = ? WHERE ListenerID = ?",
            (updated_favourites, username)
        )
        conn.commit()
        print("\nPodcast removed from favourites.")
    else:
        print("\nPodcast not found.")

    conn.close()

def add_to_favourites(podcast_id, username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT FavoritePodcasts FROM listeners WHERE ListenerID = ?",
        (username,)
    )

    result = cursor.fetchone()
    current_favourites = result[0] if result else ""

    if str(podcast_id) not in current_favourites.split(','):
        updated_favourites = current_favourites + ("," if current_favourites else "") + str(podcast_id)
        cursor.execute(
            "UPDATE listeners SET FavoritePodcasts = ? WHERE ListenerID = ?",
            (updated_favourites, username)
        )
        conn.commit()
        print("\nPodcast added to favourites.")
        time.sleep(1)
    else:
        print("\nPodcast is already in favourites.")
        time.sleep(1)

    conn.close()