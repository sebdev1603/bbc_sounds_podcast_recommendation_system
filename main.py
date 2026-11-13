import sqlite3
import os
import time
import favourites as Favourites
import generateListeningReport as GenerateListeningReport
import listeningHistory as ListeningHistory
import rating as Rating
import recommendations as Recommendations
import search as Search
import survey as Survey

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

username = input("Enter your username: ").strip()

username_valid = False

while username_valid == False:
    if username_exists(username):
        print("Welcome back")
        username_valid = True
    else:
        print("\nIncorrect username")
        username = input("\nEnter your username: ").strip()

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear()
    print("***BBC SOUNDS***\n")
    print('''
    1. Search for podcasts
    2. View your favourite podcasts
    3. View your favourite genres and matching podcasts
    4. View your listening history
    5. Generate a listening report
    6. View your recommendations
    7. View your ratings
    8. Reset survey
    9. Exit
    ''')

    choice = input("Enter your choice: ")
    if choice == "1":
        Search.search_programmes()
    elif choice == "2":
        Favourites.view_favourite_programmes()
    elif choice == "3":
        Favourites.view_favourite_genres()
    elif choice == "4":
        ListeningHistory.view_listening_history()
    elif choice == "5":
        GenerateListeningReport.generate_report()
    elif choice == "6":
        Recommendations.view_recommendations()
    elif choice == "7":
        Rating.view_ratings()
    elif choice == "8":
        Survey.delete_survey(username)
    elif choice == "9":
        exit()
    else:
        print("Invalid choice. Please try again.")

    def view_favourite_programmes():
        clear()
        print("***FAVOURITE PODCASTS***\n")
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
            if choice == "1":
                podcast_title = input("Enter the title of the podcast you want to view details for (The name must match exactly): ").strip()
                if podcast_title not in [result[0] for result in results]:
                    print("\nThe podcast is not in your favourites.")
                    time.sleep(1)
                    clear()
                else:
                    view_podcast_details(podcast_title)
            elif choice == "2":
                print("\nTo go back, press Enter without typing anything.")
                print("\nWARNING: Deleting a favourite podcast is permanent and cannot be undone.")
                podcast_title = input("Enter the title of the podcast you want to delete from favourites (The name must match exactly): ").strip()
                if podcast_title == "":
                    clear()
                    print("\nReturning to favourites menu...")
                    time.sleep(1)
                    Favourites.view_favourite_programmes()
                elif podcast_title not in [result[0] for result in results]:
                    print("\nThe podcast is not in your favourites.")
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
            print('''\nWhat action would you like to take?
            
            1. Add to favourites
            2. Add a rating
            3. Listen to the podcast
            4. Return to main menu''')
            choice = input("\nEnter your choice: ").strip()

            if choice == "1":
                Favourites.add_to_favourites(podcast[0])
                view_podcast_details(podcast_title)
            elif choice == "2":
                Rating.add_rating(podcast[0], False)
                view_podcast_details(podcast_title)
            elif choice == "3":
                print("Listening to the podcast...")
                print("... (simulated) ...")
                conn = sqlite3.connect("database.db")
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT TimesListened FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",   
                    (username, podcast[0])
                )
                times_listened = cursor.fetchone()
                if times_listened:
                    print(f"You have listened to this podcast {times_listened[0]} times.")
                else:
                    print("You have not listened to this podcast yet.")
                conn.close()
                view_podcast_details(podcast_title)
            elif choice == "4":
                main()
        else:
            print("\nPodcast not found.")
            time.sleep(1)
            Search.search_programmes()

if Survey.is_survey_complete(username):
    main()
else:
    print("\nNOTE: If you do not complete survey, we can't recommend podcasts to you.")
    choice = input("You have not completed the survey. Would you like to complete it now? (yes/no): ").strip()
    if choice.lower() == "yes":
        Survey.survey(username)
    else:
        clear()
        print("Continuing without completing the survey. You may not receive personalized recommendations.")
        time.sleep(1)
        main()