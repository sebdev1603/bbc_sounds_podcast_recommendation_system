import sqlite3
import time


def clear():
    import main as app
    app.clear()


def main(username):
    import main as app
    app.main(username)


def view_listening_history(username, view_podcast_details):
    clear()
    print("***LISTENING HISTORY***\n")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT podcasts.Title, listening_history.TimesListened FROM podcasts JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID WHERE listening_history.ListenerID = ?",
        (username,),
    )

    results = cursor.fetchall()

    if results:
        print("Your listening history:")
        for result in results:
            print(f"- {result[0]}")
            print(f"    Times listened: {result[1]}")

        print(
            '''\nWhat would you like to do next?
        1. View details of a podcast in your listening history
        2. Remove a podcast from your listening history
        3. Delete your entire listening history
        4. Return to main menu'''
        )
        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            podcast_title = input(
                "Enter the title of the podcast you want to view details for (The name must match exactly): "
            ).strip()
            if podcast_title not in [result[0] for result in results]:
                print("\nThe podcast is not in your listening history.")
                time.sleep(1)
                clear()
            else:
                view_podcast_details(podcast_title)
        elif choice == "2":
            podcast_title = input(
                "Enter the title of the podcast you want to remove from your listening history (The name must match exactly): "
            ).strip()
            if podcast_title not in [result[0] for result in results]:
                print("\nThe podcast is not in your listening history.")
                time.sleep(1)
                clear()
            else:
                remove_from_listening_history(podcast_title, username)
        elif choice == "3":
            delete_listening_history(username)
        elif choice == "4":
            main(username)
    else:
        print("You have no listening history.")
        time.sleep(1)
        print("\nReturning to main menu...")
        time.sleep(1)
        main(username)

    conn.close()

def remove_from_listening_history(podcast_title, username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT PodcastID FROM podcasts WHERE Title = ?",
        (podcast_title,),
    )

    result = cursor.fetchone()

    if result:
        podcast_id = result[0]
        cursor.execute(
            "DELETE FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
            (username, podcast_id),
        )
        conn.commit()
        print("\nPodcast removed from listening history.")
    else:
        print("\nPodcast not found.")

    conn.close()

def delete_listening_history(username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM listening_history WHERE ListenerID = ?",
        (username,),
    )

    conn.commit()
    conn.close()

    print("\nYour entire listening history has been deleted.")
    time.sleep(1)