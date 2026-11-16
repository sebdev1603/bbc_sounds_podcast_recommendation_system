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

username = None

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

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        clear()
        print(Survey.is_survey_complete(username))
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

        choice = input("Enter your choice: ")
        if choice == "1":
            Search.search_programmes(view_podcast_details)
        elif choice == "2":
            Favourites.view_favourite_programmes(username, view_podcast_details)
        elif choice == "3":
            Favourites.view_favourite_genres(username)
        elif choice == "4":
            ListeningHistory.view_listening_history(username, view_podcast_details)
        elif choice == "5":
            GenerateListeningReport.generate_report(username)
        elif choice == "6":
            Recommendations.view_recommendations(username, view_podcast_details)
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
                Favourites.add_to_favourites(podcast[0], username)
                view_podcast_details(podcast_title)
            elif choice == "2":
                Rating.add_rating(podcast[0], False, username)
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
            Search.search_programmes(view_podcast_details)

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

    main()