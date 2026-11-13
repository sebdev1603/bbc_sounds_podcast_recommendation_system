import sqlite3
import time


def view_ratings(username, clear, main):
    clear()
    print("***YOUR RATINGS***\n")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT podcasts.Title
        FROM podcasts
        JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID
        WHERE listening_history.ListenerID = ?
        AND listening_history.RatingGiven IS NOT NULL
        """,
        (username,)
    )

    results = cursor.fetchall()

    while True:
        if results:
            print("You have rated these podcasts  :")
            for result in results:
                print(f"- {result[0]}")
            print('''\nWhat action would you like to take?
    1. Update a rating
    2. Remove a rating
    3. Return to main menu''')
            choice = input("\nEnter your choice: ").strip()
            if choice == "1":
                podcast_title = input("Enter the title of the podcast you want to update the rating for (The name must match exactly): ").strip()
                if podcast_title not in [result[0] for result in results]:
                    print("\nThe podcast is not in your rated podcasts.")
                    time.sleep(1)
                    clear()
                else:
                    conn = sqlite3.connect("database.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT PodcastID FROM podcasts WHERE Title = ?",
                        (podcast_title,)
                    )
                    podcast_id = cursor.fetchone()[0]
                    conn.close()
                    add_rating(podcast_id, True, username, clear)
            elif choice == "2":
                podcast_title = input("Enter the title of the podcast you want to remove the rating for (The name must match exactly): ").strip()
                if podcast_title not in [result[0] for result in results]:
                    print("\nThe podcast is not in your rated podcasts.")
                    time.sleep(1)
                    clear()
                else:
                    conn = sqlite3.connect("database.db")
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT PodcastID FROM podcasts WHERE Title = ?",
                        (podcast_title,)
                    )
                    podcast_id = cursor.fetchone()[0]
                    conn.close()
                    remove_rating(podcast_id, username)
            elif choice == "3":
                main()
        else:
            print("You have no rated podcasts.")

def add_rating(podcast_id, check_for_update, username, clear):
    clear()
    if check_for_update == True:
        print("***UPDATE RATING***\n")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT RatingGiven FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
            (username, podcast_id)
        ).fetchone()
        print("Your previous rating was:", result[0])
    else:
        print("***ADD RATING***\n")
    rating = input("Enter your rating for this podcast (1-5): ").strip()

    while not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
        print("Invalid rating. Please enter a number between 1 and 5.")
        rating = input("Enter your rating for this podcast (1-5): ").strip()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    result = cursor.execute(
        "SELECT EXISTS (SELECT 1 FROM listening_history WHERE ListenerID = ? AND PodcastID = ?)",
        (username, podcast_id)
    ).fetchone()[0]

    if not result:
        cursor.execute(
            "INSERT INTO listening_history (ListenerID, PodcastID, TimesListened, RatingGiven) VALUES (?, ?, ?, ?)",
            (username, podcast_id, 1, int(rating))
        )
    else:
        cursor.execute(
            "UPDATE listening_history SET RatingGiven = ? WHERE ListenerID = ? AND PodcastID = ?",
            (int(rating), username, podcast_id)
        )

    conn.commit()
    conn.close()

    print("\nThank you for your rating!")
    time.sleep(1)

def remove_rating(podcast_id, username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE listening_history SET RatingGiven = NULL WHERE ListenerID = ? AND PodcastID = ?",
        (username, podcast_id)
    )

    conn.commit()
    conn.close()

    print("\nYour rating has been removed.")
    time.sleep(1)