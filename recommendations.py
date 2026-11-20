# CLI module for displaying personalised podcast recommendations based on survey preferences.
import sqlite3
import time


# Deferred imports avoid circular dependencies with main.py.
def clear():
    import main as app
    app.clear()


def main(username):
    import main as app
    app.main(username)


def view_podcast_details(podcast_title, username):
    import main as app
    app.view_podcast_details(podcast_title, username)


def view_recommendations(username):
    """Fetch and display podcasts matching the user's favourite genres and preferred length."""
    clear()
    print("***YOUR RECOMMENDATIONS***\n")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Load the user's saved genre and episode-length preferences from the listeners table.
    cursor.execute(
        "SELECT FavoriteGenres, LengthPreference FROM listeners WHERE ListenerID = ?",
        (username,)
    )

    result = cursor.fetchone()

    if result and result[0] and result[1]:
        favorite_genres, length_preference = result

        # Parse comma-separated genres and map the length preference to a minute range.
        genres = [genre.strip() for genre in favorite_genres.split(",") if genre.strip()]
        length_ranges = {
            "Long": (45, 60),
            "Medium": (25, 45),
            "Short": (0, 30),
        }
        min_length, max_length = length_ranges.get(length_preference, (0, 120))

        # Query podcasts matching any preferred genre within the target duration range.
        placeholders = ",".join("?" for _ in genres)
        query = (
            f"SELECT Title, Category, AverageLengthMins FROM podcasts "
            f"WHERE Category IN ({placeholders}) "
            "AND AverageLengthMins BETWEEN ? AND ?"
        )
        cursor.execute(query, (*genres, min_length, max_length))

        recommendations = cursor.fetchall()
        conn.close()

        if recommendations:
            while True:
                clear()
                print("***YOUR RECOMMENDATIONS***\n")
                formatted_genres = favorite_genres.replace(',', ', ')
                print(f"Based on your survey responses, we recommend the following podcasts in the '{formatted_genres}' genres with '{length_preference}' length:")
                for recommendation in recommendations:
                    print(f"\n- {recommendation[0]}")
                    print(f"  Genre: {recommendation[1]}")
                    print(f"  Average length: {recommendation[2]} minutes")

                print('''\nWhat would you like to do next?

            1. Choose a podcast
            2. Return to main menu''')

                choice = input("\nEnter your choice: ").strip()

                if choice == "1":
                    # Validate that the selected title exists in the recommended list before opening details.
                    podcast_title = input("\nEnter the title of the podcast you want to choose (The name must match exactly): ").strip()
                    podcast_title = podcast_title.capitalize()
                    if podcast_title == "":
                        continue
                    # Match the typed title case-insensitively against the recommended list.
                    matched_podcast = next(
                        (rec[0] for rec in recommendations if rec[0].lower() == podcast_title.lower()),
                        None
                    )
                    if not matched_podcast:
                        print("\nThe podcast is not in your recommendations.")
                        time.sleep(1)
                    else:    
                        print(f"\nYou selected '{matched_podcast}'.")
                        time.sleep(1)
                        view_podcast_details(podcast_title, username)
                elif choice == "2":
                    main(username)
                    return
                else:
                    print("\nInvalid choice. Please try again.")
                    time.sleep(1)
        else:
            print("No recommendations available based on your survey responses.")
            print("\nGoing back to menu...")
            time.sleep(1)
            main(username)
    else:
        conn.close()
        print("No survey responses found for your account.")
        time.sleep(1)
        print("\nGoing back to menu...")
        time.sleep(1)
        main(username)