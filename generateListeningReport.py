import sqlite3


def clear():
    import main as app
    app.clear()


def main(username):
    import main as app
    app.main(username)


def generate_report(username):
    clear()
    print("***LISTENING REPORT***\n")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT podcasts.Title, listening_history.TimesListened, listening_history.RatingGiven FROM podcasts JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID WHERE listening_history.ListenerID = ? ORDER BY listening_history.TimesListened DESC",
        (username,)
    )

    results = cursor.fetchall()

    if results:
        print(f"\nYou listened to {len(results)} different podcasts.")
        print(f"\nThe most listened podcast is '{results[0][0]}' with {results[0][1]} listens.")
        print(f"\nThe least listened podcast is '{results[-1][0]}' with {results[-1][1]} listens.")
        print(f"\nYour highest rating given is {max([result[2] for result in results if result[2] is not None])} and your lowest rating given is {min([result[2] for result in results if result[2] is not None])}.")
        print(f"\nYour average rating for all podcasts is {sum([result[2] for result in results if result[2] is not None]) / len([result[2] for result in results if result[2] is not None]):.2f}.")
        print("\nYour podcasts sorted by times listened (from most to least):")

        for result in results:
            print(f"\n- {result[0]}")
            print(f"    Times listened: {result[1]}")
            print(f"    Your rating: {result[2]}")
    else:
        print("You have no listening history.")

    conn.close()
    input("\nPress Enter to return to the main menu...")
    main(username)