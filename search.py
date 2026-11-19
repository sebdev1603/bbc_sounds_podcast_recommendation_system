# CLI module for searching podcasts by title or category.
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


def search_programmes(username):
    """Prompt the user for a keyword, search podcast titles then categories, and open details."""
    clear()
    print("***SEARCH FOR PODCASTS***\n")
    print("Enter nothing to return to the main menu.")
    search_query = input("Enter a keyword to search for podcasts: \n").strip()

    # Empty input returns straight to the main menu.
    if search_query == "":
        main(username)
        return
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # First search for partial matches in podcast titles.
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
        # Fall back to searching by category if no title matched.
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
            time.sleep(1)
            search_programmes(username)


    conn.close()

    # Allow the user to open a specific podcast from the results or return to the menu.
    podcast_title = input("\nEnter the title of the podcast you want to view details for, or press Enter to return to the main menu: ").strip()
    podcast_title = podcast_title.capitalize()
    if podcast_title == "":
        main(username)
        return
    else:
        view_podcast_details(podcast_title, username)