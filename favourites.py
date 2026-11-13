def view_favourite_genres():
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