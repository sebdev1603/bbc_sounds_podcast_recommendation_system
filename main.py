import sqlite3
import os
import time

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

class Search:
    def search_programmes():
        clear()
        print("***SEARCH FOR PROGRAMMES***\n")
        print("Enter nothing to return to the main menu.")
        search_query = input("Enter a keyword to search for programmes: \n")

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

            conn.close()

            if results:
                print("\nSearch Results:")
                for result in results:
                    print(result[0])
            else:
                print("\nNo podcasts found matching your search query.")
        
        print("\nEnter the title of the podcast you want to view details for, or press Enter to return to the main menu.")
        choice = input("\nWhich podcast would you like to listen to? (Enter the title exactly as shown above): ")
        if choice == "":
            main()
        else:
            view_podcast_details(choice)

class Favourites:
    def delete_favourite_programme(podcast_title):
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

        conn.close()
    
    def view_favourite_programmes():
        clear()
        print("***FAVOURITE PROGRAMMES***\n")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """SELECT podcasts.Title FROM podcasts JOIN listeners ON (
            ',' || listeners.FavoritePodcasts || ',' LIKE '%,' || podcasts.PodcastID || ',%'
            ) WHERE listeners.ListenerID = ?""",
            (username,)
        )

        results = cursor.fetchall()

        while True:
            if results:
                print("Your favourite programmes:")
                for result in results:
                    print(f"- {result[0]}")
            else:
                print("You have no favourite programmes.")

            print('''\nWhat would you like to do next?

            1. View details of a favourite programme
            2. Delete a favourite programme
            3. Return to main menu''')

            choice = input("\nEnter your choice: ").strip()
            if choice == "1":
                podcast_title = input("Enter the title of the programme you want to view details for (The name must match exactly): ")
                if podcast_title not in [result[0] for result in results]:
                    print("\nThe programme is not in your favourites.")
                    time.sleep(1)
                    clear()
                else:
                    view_podcast_details(podcast_title)
            elif choice == "2":
                podcast_title = input("Enter the title of the programme you want to delete from favourites (The name must match exactly): ")
                if podcast_title not in [result[0] for result in results]:
                    print("\nThe programme is not in your favourites.")
                    time.sleep(1)
                    clear()
                else:
                    Favourites.delete_favourite_programme(podcast_title)
            elif choice == "3":
                main()
            else:
                print("Invalid choice")
                time.sleep(1)
                clear()

        conn.close()

    def add_to_favourites(podcast_id):
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT FavoritePodcasts FROM listeners WHERE ListenerID = ?",
            (username,)
        )

        result = cursor.fetchone()
        current_favourites = result[0] if result else ""

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

class Survey:
    def survey():
        clear()
        print("***BBC SOUNDS SURVEY***\n")
        print("Please answer the following questions:\n")

        print('''These are the available genres of programmes:
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

        question1 = input("What is your favorite genre of programmes?: ").capitalize()
        while any(character.isdigit() for character in question1):
            print("Please do not include numbers.")
            question1 = input("What is your favorite genre of programmes? (News/Comedy/Drama/Music): ").capitalize()

        question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").capitalize()
        while any(character.isdigit() for character in question2):
            print("Please do not include numbers.")
            question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").capitalize()
        while question2 != "Long" and question2 != "Medium" and question2 != "Short":
            print("Please enter a valid option: Short, Medium, or Long.")
            question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").capitalize()

        # Store survey responses in the database
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE listeners SET CompleteSurvey = 1, PreferredCategory = ?, LengthPreference = ? WHERE ListenerID = ?",
            (question1, question2, username)
        )

        conn.commit()
        conn.close()

        print("\nThank you for completing the survey!")
        main()


    def is_survey_complete(username):
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM listeners WHERE ListenerID = ? AND CompleteSurvey = 1",
            (username,)
        )

        result = cursor.fetchone()

        conn.close()

        return result is not None

def main():
    clear()
    print("***BBC SOUNDS***\n")
    print('''
    1. Search for programmes
    2. View your favourite programmes
    3. View your listening history
    4. View your recommendations
    5. Exit
    ''')

    choice = input("Enter your choice: ")
    if choice == "1":
        Search.search_programmes()
    elif choice == "2":
        view_favourite_programmes()
    elif choice == "3":
        view_listening_history()
    elif choice == "4":
        view_recommendations()
    elif choice == "5":
        exit()
    else:
        print("Invalid choice. Please try again.")

def view_podcast_details(podcast_title):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM podcasts WHERE Title = ?",
        (podcast_title,)
    )

    podcast = cursor.fetchone()
    conn.close()

    while True:
        if podcast:
            print(f"\nTitle: {podcast[1]}")
            print(f"Category: {podcast[2]}")
            print(f"Length: {podcast[3]} minutes")
            print(f"Ratings: {podcast[5]}")
            print('''What action would you like to take?
            1. Add to favourites
            2. Add a rating
            3. Listen to the podcast
            4. Return to main menu''')
            choice = input("\nEnter your choice: ")

            if choice == "1":
                add_to_favourites(podcast[0])
                view_podcast_details(podcast_title)
            elif choice == "2":
                add_rating(podcast[0])
                view_podcast_details(podcast_title)
            elif choice == "3":
                print("Listening to the podcast...")
                print("... (simulated) ...")
                view_podcast_details(podcast_title)
            elif choice == "4":
                main()
        else:
            print("\nPodcast not found.")

def username_exists(username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM listeners WHERE ListenerID = ?",
        (username,)
    )

    result = cursor.fetchone()

    conn.close()

    return result is not None

username = input("Enter your username: ")

username_valid = False

while username_valid == False:
    if username_exists(username):
        print("Welcome back")
        break
    else:
        print("\nIncorrect username")
        username = input("\nEnter your username: ")

if is_survey_complete(username):
    main()
else:
    print("\nNOTE: If you do not complete survey, we can't recommend programmes to you.")
    choice = input("You have not completed the survey. Would you like to complete it now? (yes/no): ")
    if choice.lower() == "yes":
        survey()
    else:
        print("Continuing without completing the survey. You may not receive personalized recommendations.")
        main()