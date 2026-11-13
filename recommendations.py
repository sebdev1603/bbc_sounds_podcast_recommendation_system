import sqlite3


def view_recommendations(username, clear, main):
    clear()
    print("***YOUR RECOMMENDATIONS***\n")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT FavoriteGenres, LengthPreference FROM listeners WHERE ListenerID = ?",
        (username,)
    )

    result = cursor.fetchone()

    if result:
        favorite_genres, length_preference = result
        cursor.execute(
            "SELECT Title FROM podcasts WHERE Category IN ({}) AND Length = ?".format(','.join('?' * len(favorite_genres.split(',')))),
            (length_preference)
        )

        recommendations = cursor.fetchall()

        if recommendations:
            print(f"Based on your survey responses, we recommend the following podcasts in the '{favorite_genres}' genres with '{length_preference}' length:")
            for recommendation in recommendations:
                print(f"- {recommendation[0]}")
        else:
            print("No recommendations available based on your survey responses.")
    else:
        print("No survey responses found for your account.")

    conn.close()
    input("\nPress Enter to return to the main menu...")
    main()