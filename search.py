import sqlite3
import time

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
    clear()
    print("***SEARCH FOR PODCASTS***\n")
    print("Enter nothing to return to the main menu.")
    search_query = input("Enter a keyword to search for podcasts: \n").strip()

    if search_query == "":
        main(username)
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
            time.sleep(1)
            search_programmes(username)


    conn.close()

    podcast_title = input("\nEnter the title of the podcast you want to view details for, or press Enter to return to the main menu: ").strip()
    podcast_title = podcast_title.capitalize()
    if podcast_title == "":
        main(username)
        return
    else:
        view_podcast_details(podcast_title, username)