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
    user_id = int(username) if str(username).isdigit() else username
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM listeners WHERE ListenerID = ?",
        (user_id,)
    )

    result = cursor.fetchone()
    conn.close()
    return result is not None

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def main(username):
    while True:
        clear()
        
        print("***BBC SOUNDS***")

        if Survey.is_survey_complete(username):
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
        else:
            print('''
        1. Search for podcasts
        2. View your favourite podcasts
        3. View your favourite genres and matching podcasts
        4. View your listening history
        5. Generate a listening report
        6. View your recommendations
        7. View your ratings
        8. Complete survey
        9. Exit
        ''')

        choice = input("Enter your choice: ").strip()
        if choice == "1":
            Search.search_programmes(username, lambda title: view_podcast_details(title, username))
        elif choice == "2":
            Favourites.view_favourite_programmes(username, lambda title: view_podcast_details(title, username))
        elif choice == "3":
            Favourites.view_favourite_genres(username)
        elif choice == "4":
            ListeningHistory.view_listening_history(username, lambda title: view_podcast_details(title, username))
        elif choice == "5":
            GenerateListeningReport.generate_report(username)
        elif choice == "6":
            Recommendations.view_recommendations(username, lambda title: view_podcast_details(title, username))
        elif choice == "7":
            Rating.view_ratings(username)
        elif choice == "8":
            if Survey.is_survey_complete(username):
                Survey.delete_survey(username)
            else:
                Survey.survey(username)
        elif choice == "9":
            exit()
        else:
            print("Invalid choice. Please try again.")
            time.sleep(1)

def view_podcast_details(podcast_title, username):
    user_id = int(username) if str(username).isdigit() else username

    while True:
        # Fetch fresh podcast details each loop iteration
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM podcasts WHERE Title = ?",
            (podcast_title,)
        )
        podcast = cursor.fetchone()

        if not podcast:
            conn.close()
            print("\nPodcast not found.")
            time.sleep(1)
            return

        clear()
        print(f"\nTitle: {podcast[1]}")
        print(f"Category: {podcast[2]}")
        print(f"Length: {podcast[3]} minutes")
        print(f"Ratings: {podcast[5]}")

        # Check listening history using podcast[0] (PodcastID)
        cursor.execute(
            "SELECT TimesListened FROM listening_history WHERE PodcastID = ? AND ListenerID = ?",
            (podcast[0], user_id)
        )
        times_listened = cursor.fetchone()
        conn.close()

        if times_listened is None:
            print("You have not listened to this podcast yet.")
        else:
            print(f"Listened times: {times_listened[0]}")

        print('''\nWhat action would you like to take?

        1. Add to favourites
        2. Add a rating
        3. Listen to the podcast
        4. Go back''')
        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            Favourites.add_to_favourites(podcast[0], username)
        elif choice == "2":
            Rating.add_rating(podcast[0], False, username)
        elif choice == "3":
            clear()
            print("Listening to the podcast...")
            print("... (simulated) ...")
            
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            
            # Check if a history row already exists for this user/podcast
            cursor.execute(
                "SELECT 1 FROM listening_history WHERE PodcastID = ? AND ListenerID = ?",
                (podcast[0], user_id)
            )
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute(
                    "UPDATE listening_history SET TimesListened = TimesListened + 1 WHERE PodcastID = ? AND ListenerID = ?",
                    (podcast[0], user_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO listening_history (PodcastID, ListenerID, TimesListened) VALUES (?, ?, 1)",
                    (podcast[0], user_id)
                )

            conn.commit()
            conn.close()
            time.sleep(2)
        elif choice == "4":
            return
        else:
            print("Invalid choice.")
            time.sleep(1)

if __name__ == "__main__":
    username = input("Enter your username: ").strip()
    username_valid = False

    while not username_valid:
        if username_exists(username):
            print("\nWelcome back")
            username_valid = True
        else:
            print("\nIncorrect username")
            username = input("\nEnter your username: ").strip()

    if not Survey.is_survey_complete(username):
        print("\nNOTE: If you do not complete survey, we can't recommend podcasts to you.")
        choice = input("\nYou have not completed the survey. Would you like to complete it now? (yes/no): ").strip()
        if choice.lower() == "yes":
            Survey.survey(username)
        else:
            clear()
            print("Continuing without completing the survey. You may not receive personalized recommendations.")
            time.sleep(1)
    
    main(username)