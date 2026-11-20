# CLI module for viewing, adding, and removing favourite genres and favourite podcasts.
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

def get_favorite_genre_count(username):
    """Return how many favourite genres the listener currently has saved."""
    user_id = int(username) if str(username).isdigit() else username
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT FavoriteGenres FROM listeners WHERE ListenerID = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result and result[0]:
        genres_list = [g.strip() for g in result[0].split(',') if g.strip()]
        genre_count = len(genres_list)
    else:
        genre_count = 0

    return genre_count

# Core favourites management functions

def view_favourite_genres(username):
    """List podcasts matching the listener's favourite genres and let them manage genres."""
    clear()
    print("***FAVOURITE GENRES & MATCHING PODCASTS***\n")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Load the listener's comma-separated FavoriteGenres string.
    cursor.execute(
        "SELECT FavoriteGenres FROM listeners WHERE ListenerID = ?",
        (username,)
    )
    res = cursor.fetchone()

    if res and res[0]:
        print(f"Your favourite genres: {res[0].replace(',', ', ')}\n")

        # Match podcasts whose Category appears in the listener's FavoriteGenres CSV.
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
            while True:
                # Re-query on each loop iteration so additions/removals reflect immediately.
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT FavoriteGenres FROM listeners WHERE ListenerID = ?",
                    (username,)
                )
                res = cursor.fetchone()

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
                conn.close()

                clear()
                print("Podcasts matching your favourite genres:", res[0].replace(',', ', '))
                for title, category in results:
                    print(f"\n-{title}")
                    print(f"  Genre: {category}")
                print('''\nWhat would you like to do next?
        
        1. View details of a podcast
        2. Remove a favourite genre
        3. Add a favourite genre
        4. Return to main menu\n''')
                choice = input("Enter your choice: ").strip()
                while choice not in ['1', '2', '3', '4']:
                    print("Invalid choice. Please enter 1, 2, 3, or 4.")
                    choice = input("Enter your choice: ")
                
                if choice == '1':
                    # Open details for one of the matching podcasts.
                    podcast_title = input("\nEnter the title of the podcast you want to view details for, or press Enter to return to the main menu: ").strip()
                    podcast_title = podcast_title.capitalize()
                    if podcast_title == "":
                        print()
                    elif podcast_title not in [result[0] for result in results]:
                        print("\nEnter a valid option from the list.")
                        time.sleep(1)
                    else:
                        conn.close()  
                        view_podcast_details(podcast_title, username)
                        break
                
                elif choice == '2':
                    # Prompt for a favourite genre to remove permanently.
                    result = res  
                    
                    if not result or not result[0]:
                        print("\nYou have no favourite genres set.")
                        time.sleep(1)
                        continue

                    print(f"\nYour favourite genres: {result[0].replace(',', ', ')}\n")
                    print("\nTo go back, press Enter without typing anything.")
                    print("\nWARNING: Deleting a favourite genre is permanent and cannot be undone.")
                    genre_name = input("Enter the name of the genre you want to delete from favourites (Enter it correctly!): ").strip()
                    
                    if genre_name == "":
                        clear()
                        print("\nGoing back to the menu...")
                        time.sleep(1)
                    else:
                        conn.close()
                        delete_favourite_genre(genre_name, username)
                        break
                
                elif choice == '3':
                    # Allow adding genres until the user stops or reaches the 5-genre limit.
                    conn.close() 
                    while get_favorite_genre_count(username) < 5:
                        
                        clear()
                        valid_genres = [
                            "News", "Travel", "History", "Comedy", "True Crime",
                            "Technology", "Science", "Business", "Gaming",
                            "Entertainment", "Sport", "Health"
                        ]

                        add_conn = sqlite3.connect("database.db")
                        add_cursor = add_conn.cursor()
                        
                        add_cursor.execute(
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

                        results = add_cursor.fetchall()
                        current_res = add_cursor.fetchone()
                        add_conn.close()

                        clear()
                        print("Your favourite genres: ", res[0].replace(',', ', '))

                        print('''These are the available genres of podcasts:

    News
    Travel
    History
    Comedy
    True Crime
    Technology
    Science
    Business
    Gaming
    Entertainment
    Sport
    Health
                            ''')

                        genre_name = input("\nEnter the name of the genre you want favourite, or press Enter to return to go back (Type it correctly!): ").strip()
                        genre_name = genre_name.capitalize()
                        if genre_name == "":
                            break
                        elif genre_name not in valid_genres:
                            print("\nEnter a valid option from the list.")
                            time.sleep(1)
                        else:
                            add_favourite_genre(genre_name, username)
                    if get_favorite_genre_count(username) == 5:
                        clear()
                        print("You have reached the maximum number of favourite genres.")
                        time.sleep(1)
                
                elif choice == '4':
                    conn.close()
                    main(username)
                    break
                
                conn.close()
        else:
            print("No podcasts found matching your favourite genres.")
    else:
        print("You have no favourite genres set.")

    conn.close()
    main(username)

def delete_favourite_genre(genre_name, username):
    """Remove a single genre (case-insensitive) from the listener's FavoriteGenres CSV."""
    user_id = int(username) if str(username).isdigit() else username
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT FavoriteGenres FROM listeners WHERE ListenerID = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if result and result[0]:
        current_genres = [g.strip() for g in result[0].split(',') if g.strip()]
        
        matched = next((g for g in current_genres if g.lower() == genre_name.lower()), None)
        
        if matched:
            current_genres.remove(matched)
            updated_genres = ",".join(current_genres)
            
            cursor.execute(
                "UPDATE listeners SET FavoriteGenres = ? WHERE ListenerID = ?",
                (updated_genres, user_id)
            )
            conn.commit()
            print(f"\n'{matched}' removed from your favourite genres.")
            time.sleep(1)
        else:
            print("\nGenre not found in your favourites.")
            time.sleep(1)
    else:
        print("\nYou have no favourite genres set.")
        time.sleep(1)

    conn.close()

def add_favourite_genre(genre_name, username):
    """Append a genre to the listener's FavoriteGenres CSV if it is not already saved."""
    clear()
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
            "SELECT FavoriteGenres FROM listeners WHERE ListenerID = ?",
            (username,)
        )
    
    result = cursor.fetchone()
    current_favourites = result[0] if result else ""
    
    if str(genre_name) not in current_favourites.split(','):
        updated_favourites = current_favourites + ("," if current_favourites else "") + str(genre_name)
        cursor.execute(
            "UPDATE listeners SET FavoriteGenres = ? WHERE ListenerID = ?",
            (updated_favourites, username)
        )
        conn.commit()
        print("\nGenre added to favourites.")
        time.sleep(1)
    else:
        print("\nGenre is already in favourites.")
        time.sleep(1)
    
    conn.close()
    
def view_favourite_programmes(username):
    """Display the listener's saved favourite podcasts and allow viewing or removing them."""
    while True:
        clear()
        print("***FAVOURITE PODCASTS***\n")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Join podcasts whose PodcastID appears in the listener's FavoritePodcasts CSV.
        cursor.execute(
            """SELECT podcasts.Title FROM podcasts JOIN listeners ON (
                ',' || listeners.FavoritePodcasts || ',' LIKE '%,' || podcasts.PodcastID || ',%'
                ) WHERE listeners.ListenerID = ?""",
            (username,)
        )

        results = cursor.fetchall()

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
        conn.close()

        if choice == "1":
            podcast_title = input("Enter the title of the podcast you want to view details for (The name must match exactly): ").strip()
            if podcast_title not in [result[0] for result in results]:
                print("\nThe podcast is not in your favourites.")
                time.sleep(1)
                clear()
            else:
                view_podcast_details(podcast_title, username)
        elif choice == "2":
            print("\nTo go back, press Enter without typing anything.")
            print("\nWARNING: Deleting a favourite podcast is permanent and cannot be undone.")
            podcast_title = input("Enter the title of the podcast you want to delete from favourites (The name must match exactly): ").strip()
            if podcast_title == "":
                clear()
                print("\nReturning to favourites menu...")
                time.sleep(1)
                continue
            elif podcast_title not in [result[0] for result in results]:
                print("\nThe podcast is not in your favourites.")
                time.sleep(1)
            else:
                delete_favourite_programme(podcast_title, username)
        elif choice == "3":
            main(username)
            return
        else:
            print("Invalid choice")
            time.sleep(1)

def delete_favourite_programme(podcast_title, username):
    """Remove a podcast ID (resolved from its title) from the listener's FavoritePodcasts CSV."""
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

        # Rebuild the CSV excluding the removed podcast ID.
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

    time.sleep(1)

    conn.close()

def add_to_favourites(podcast_id, username):
    """Append a podcast ID to the listener's FavoritePodcasts CSV if not already saved."""
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT FavoritePodcasts FROM listeners WHERE ListenerID = ?",
        (username,)
    )

    result = cursor.fetchone()
    current_favourites = result[0] if result else ""

    # Only append the podcast ID if it is not already present in the comma-separated list.
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