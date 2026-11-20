# Main CLI entry point for the BBC Sounds Podcast Recommendation System.
import sqlite3
import os
import time

# Feature modules for each menu option in the terminal interface.
import favourites as Favourites
import generateListeningReport as GenerateListeningReport
import listeningHistory as ListeningHistory
import rating as Rating
import recommendations as Recommendations
import search as Search
import survey as Survey
from last_listened import record_last_listened

def username_exists(username):
    """Check whether the entered listener ID exists in the SQLite listeners table."""
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
    """Clear the terminal screen on Windows ('cls') or Unix/macOS ('clear')."""
    os.system('cls' if os.name == 'nt' else 'clear')

def main(username):
    """Run the main CLI navigation loop and dispatch each menu choice to its module."""
    while True:
        clear()
        
        print("***BBC SOUNDS***")

        # Adjust option 8 label based on whether the listener has completed the survey.
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
            Search.search_programmes(username)
        elif choice == "2":
            Favourites.view_favourite_programmes(username)
        elif choice == "3":
            Favourites.view_favourite_genres(username)
        elif choice == "4":
            ListeningHistory.view_listening_history(username)
        elif choice == "5":
            GenerateListeningReport.generate_report(username)
        elif choice == "6":
            Recommendations.view_recommendations(username)
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
    """Show metadata, user stats, and actions (favourite, rate, listen) for one podcast."""
    user_id = int(username) if str(username).isdigit() else username

    while True:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        # Look up the selected podcast record by exact title.
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

        # Determine whether the listener has already rated this podcast.
        cursor.execute(
            "SELECT RatingGiven FROM listening_history WHERE PodcastID = ? AND ListenerID = ?",
            (podcast[0], user_id)
        )
        podcast_detail_rating_res = cursor.fetchone()

        if podcast_detail_rating_res and podcast_detail_rating_res[0] is not None:
            podcast_detail_rating_option_changer = 'Change the rating'
            check_for_update = True
        else:
            podcast_detail_rating_option_changer = 'Give a rating'
            check_for_update = False

        # Determine whether this podcast is currently in the listener's favourites list.
        cursor.execute(
            "SELECT FavoritePodcasts FROM listeners WHERE ListenerID = ?",
            (user_id,)
        )
        podcast_detail_favourite_option_changer = cursor.fetchone()
        
        current_favourites = podcast_detail_favourite_option_changer[0] if podcast_detail_favourite_option_changer else ""
        
        if str(podcast[0]) not in current_favourites.split(','):
            podcast_detail_favourite_option_changer = 'Add to your favorites'
            can_be_favourited = True
        else:
            podcast_detail_favourite_option_changer = 'Remove from your favorites'
            can_be_favourited = False

        # Fetch the listener's personal rating and play count for display.
        cursor.execute(
            "SELECT RatingGiven FROM listening_history WHERE PodcastID = ? AND ListenerID = ?",
            (podcast[0], user_id)
        )
        personal_rating = cursor.fetchone()

        cursor.execute(
            "SELECT TimesListened FROM listening_history WHERE PodcastID = ? AND ListenerID = ?",
            (podcast[0], user_id)
        )
        times_listened = cursor.fetchone()

        conn.close()

        # Render the podcast details and action menu.
        clear()
        print(f"\nTitle: {podcast[1]}")
        print(f"Category: {podcast[2]}")
        print(f"Length: {podcast[3]} minutes")
        print(f"Ratings: {podcast[5]}")

        if personal_rating is None or personal_rating[0] is None:
            print("You have not rated this podcast yet.")
        else:
            print(f"Personal rating: {personal_rating[0]}")

        if times_listened is None:
            print("You have not listened to this podcast yet.")
        else:
            print(f"Listened times: {times_listened[0]}")

        print(f'''\nWhat action would you like to take?

        1. {podcast_detail_favourite_option_changer}
        2. {podcast_detail_rating_option_changer}
        3. Listen to the podcast
        4. Go back''')
        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            # Toggle favourite status.
            if can_be_favourited == True:
                Favourites.add_to_favourites(podcast[0], username)
            else:
                Favourites.delete_favourite_programme(podcast[1], username)
        elif choice == "2":
            # Add or update the listener's 1-5 rating.
            Rating.add_rating(podcast[0], check_for_update, username)
        elif choice == "3":
            # Simulate playback, increment TimesListened, and record recency.
            clear()
            print("Listening to the podcast...")
            print("... (simulated) ...")
            
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            
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

            record_last_listened(conn, user_id, podcast[0])
            conn.commit()
            conn.close()
            time.sleep(2)
        elif choice == "4":
            return
        else:
            print("Invalid choice.")
            time.sleep(1)

if __name__ == "__main__":
    # Authenticate the listener ID before entering the app.
    username = input("Enter your username: ").strip()
    username_valid = False

    while not username_valid:
        if username_exists(username):
            print("\nWelcome back")
            username_valid = True
        else:
            print("\nIncorrect username")
            username = input("\nEnter your username: ").strip()

    # Offer the onboarding survey on first sign-in if not yet completed.
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
