import sqlite3


def search_programmes(clear, main, view_podcast_details):
    clear()
    print("***SEARCH FOR PODCASTS***\n")
    print("Enter nothing to return to the main menu.")
    search_query = input("Enter a keyword to search for podcasts: \n").strip()

    if search_query == "":
        main()
        return
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT Title FROM podcasts WHERE Title LIKE ?",
        ('%' + search_query + '%',)
    )

    results = cursor.fetchall()

    if results:
        print("\nSearch Results:")
        for result in results:
            print(result[0])
    else:
        cursor.execute(
            "SELECT Title FROM podcasts WHERE Category LIKE ?",
            ('%' + search_query + '%',)
        )
        results = cursor.fetchall()

        if results:
            print("\nSearch Results:")
            for result in results:
                print(result[0])
        else:
            print("\nNo podcasts found matching your search query.")

    conn.close()

    print("\nEnter the title of the podcast you want to view details for, or press Enter to return to the main menu.")
    choice = input("\nWhich podcast would you like to listen to? (Enter the title exactly as shown above): ").strip()
    if choice == "":
        main()
        return
    else:
        view_podcast_details(choice)