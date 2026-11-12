import sqlite3
import os
import time

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
    8. Exit
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
        exit()
    else:
        print("Invalid choice. Please try again.")

class Search:
    def search_programmes():
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

class Favourites:

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

class ListeningHistory:

    def view_listening_history():
        clear()
        print("***LISTENING HISTORY***\n")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT podcasts.Title, listening_history.TimesListened FROM podcasts JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID WHERE listening_history.ListenerID = ?",
            (username,)
        )

        results = cursor.fetchall()

        if results:
            print("Your listening history:")
            for result in results:
                print(f"- {result[0]}")
                print(f"    Times listened: {result[1]}")
            print('''\nWhat would you like to do next?
            1. View details of a podcast in your listening history
            2. Remove a podcast from your listening history
            3. Delete your entire listening history
            4. Return to main menu''')
            choice = input("\nEnter your choice: ").strip()
            if choice == "1":
                podcast_title = input("Enter the title of the podcast you want to view details for (The name must match exactly): ").strip()
                if podcast_title not in [result[0] for result in results]:
                    print("\nThe podcast is not in your listening history.")
                    time.sleep(1)
                    clear()
                else:
                    view_podcast_details(podcast_title)
            elif choice == "2":
                podcast_title = input("Enter the title of the podcast you want to remove from your listening history (The name must match exactly): ").strip()
                if podcast_title not in [result[0] for result in results]:
                    print("\nThe podcast is not in your listening history.")
                    time.sleep(1)
                    clear()
                else:
                    ListeningHistory.remove_from_listening_history(podcast_title)
            elif choice == "3":
                ListeningHistory.delete_listening_history()
            elif choice == "4":
                main()
        else:
            print("You have no listening history.")
            time.sleep(1)
            print("\nReturning to main menu...")
            time.sleep(1)
            main()

        conn.close()

    def remove_from_listening_history(podcast_title):
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
                "DELETE FROM listening_history WHERE ListenerID = ? AND PodcastID = ?",
                (username, podcast_id)
            )
            conn.commit()
            print("\nPodcast removed from listening history.")
        else:
            print("\nPodcast not found.")

        conn.close()

    def delete_listening_history():
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM listening_history WHERE ListenerID = ?",
            (username,)
        )

        conn.commit()
        conn.close()

        print("\nYour entire listening history has been deleted.")
        time.sleep(1)

class GenerateListeningReport:

    def generate_report():
        clear()
        print("***LISTENING REPORT***\n")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT podcasts.Title, listening_history.TimesListened, listening_history.RatingGiven FROM podcasts JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID WHERE listening_history.ListenerID = ? ORDER BY listening_history.TimesListened DESC",
            (username,)
        )

        results = cursor.fetchall()

        if results:
            print(f"\nYou listened to {len(results)} different podcasts.")
            print(f"\nThe most listened podcast is '{results[0][0]}' with {results[0][1]} listens.")
            print(f"\nThe least listened podcast is '{results[-1][0]}' with {results[-1][1]} listens.")
            print(f"\nYour highest rating given is {max([result[2] for result in results if result[2] is not None])} and your lowest rating given is {min([result[2] for result in results if result[2] is not None])}.")
            print(f"\nYour average rating for all podcasts is {sum([result[2] for result in results if result[2] is not None]) / len([result[2] for result in results if result[2] is not None]):.2f}.")
            print("\nYour podcasts sorted by times listened (from most to least):")

            for result in results:
                print(f"\n- {result[0]}")
                print(f"    Times listened: {result[1]}")
                print(f"    Your rating: {result[2]}")
        else:
            print("You have no listening history.")

        conn.close()
        input("\nPress Enter to return to the main menu...")
        main()

class Recommendations:
    def view_recommendations():
        clear()
        print("***YOUR RECOMMENDATIONS***\n")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT FavoriteGenres, LengthPreference FROM listeners WHERE ListenerID = ?",
            (username,)
        )

        result = cursor.fetchone()

        if result:
            favorite_genres, length_preference = result
            cursor.execute(
                "SELECT Title FROM podcasts WHERE Category IN ({}) AND Length = ?".format(','.join('?' * len(favorite_genres.split(',')))),
                (length_preference)
            )

            recommendations = cursor.fetchall()

            if recommendations:
                print(f"Based on your survey responses, we recommend the following podcasts in the '{favorite_genres}' genres with '{length_preference}' length:")
                for recommendation in recommendations:
                    print(f"- {recommendation[0]}")
            else:
                print("No recommendations available based on your survey responses.")
        else:
            print("No survey responses found for your account.")

        conn.close()
        input("\nPress Enter to return to the main menu...")
        main()

class Rating:
    def view_ratings():
        clear()
        print("***YOUR RATINGS***\n")
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
        """
        SELECT podcasts.Title 
        FROM podcasts 
        JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID 
        WHERE listening_history.ListenerID = ? 
        AND listening_history.RatingGiven IS NOT NULL
        """,
        (username,)
        )

        results = cursor.fetchall()

        while True:
            if results:
                print("You have rated these podcasts  :")
                for result in results:
                    print(f"- {result[0]}")
                print('''\nWhat action would you like to take?
        1. Update a rating
        2. Remove a rating
        3. Return to main menu''')
                choice = input("\nEnter your choice: ").strip()
                if choice == "1":
                    podcast_title = input("Enter the title of the podcast you want to update the rating for (The name must match exactly): ").strip()
                    if podcast_title not in [result[0] for result in results]:
                        print("\nThe podcast is not in your rated podcasts.")
                        time.sleep(1)
                        clear()
                    else:
                        conn = sqlite3.connect("database.db")
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT PodcastID FROM podcasts WHERE Title = ?",
                            (podcast_title,)
                        )
                        podcast_id = cursor.fetchone()[0]
                        conn.close()
                        Rating.add_rating(podcast_id, True)
                elif choice == "2":
                    podcast_title = input("Enter the title of the podcast you want to remove the rating for (The name must match exactly): ").strip()
                    if podcast_title not in [result[0] for result in results]:
                        print("\nThe podcast is not in your rated podcasts.")
                        time.sleep(1)
                        clear()
                    else:
                        conn = sqlite3.connect("database.db")
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT PodcastID FROM podcasts WHERE Title = ?",
                            (podcast_title,)
                        )
                        podcast_id = cursor.fetchone()[0]
                        conn.close()
                        Rating.remove_rating(podcast_id)
                elif choice == "3":
                    main()
            else:
                print("You have no rated podcasts.")

    def add_rating(podcast_id, check_for_update):
        clear()
        if check_for_update == True:
            print("***UPDATE RATING***\n")
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()

            result = cursor.execute(
                "SELECT RatingGiven FROM listening_history WHERE ListenerID = ? AND PodcastID = ?", 
                (username, podcast_id)).fetchone()
            print("Your previous rating was:", result[0])
        else:
            print("***ADD RATING***\n")
        rating = input("Enter your rating for this podcast (1-5): ").strip()

        while not rating.isdigit() or int(rating) < 1 or int(rating) > 5:
            print("Invalid rating. Please enter a number between 1 and 5.")
            rating = input("Enter your rating for this podcast (1-5): ").strip()

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        result = cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM listening_history WHERE ListenerID = ? AND PodcastID = ?)", 
            (username, podcast_id)).fetchone()[0]

        if not result:
            cursor.execute(
                "INSERT INTO listening_history (ListenerID, PodcastID, TimesListened, RatingGiven) VALUES (?, ?, ?, ?)",
                (username, podcast_id, 1, int(rating))
            )
        else:
            cursor.execute(
                "UPDATE listening_history SET RatingGiven = ? WHERE ListenerID = ? AND PodcastID = ?",
                (int(rating), username, podcast_id)
            )

        conn.commit()
        conn.close()

        print("\nThank you for your rating!")
        time.sleep(1)

    def remove_rating(podcast_id):
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE listening_history SET RatingGiven = NULL WHERE ListenerID = ? AND PodcastID = ?",
            (username, podcast_id)
        )

        conn.commit()
        conn.close()

        print("\nYour rating has been removed.")
        time.sleep(1)

class Survey:
    def survey(username):
        clear()
        print("***BBC SOUNDS SURVEY***\n")
        print("Please answer the following questions:\n")

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

        print("\nEnter as many genres as you like, enter nothing when you are finished")
        favorite_genres = []
        while True:
            question1 = input("\nWhat are your favorite genre of podcasts? (or press Enter when finished): ").strip().capitalize()
            if question1 == "":
                if favorite_genres:
                    break
                print("You must enter at least one genre.")
                continue
            if any(character.isdigit() for character in question1):
                print("Please do not include numbers.")
                continue
            favorite_genres.append(question1)

        question1 = ", ".join(favorite_genres)

        question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").strip().capitalize()
        while any(character.isdigit() for character in question2):
            print("Please do not include numbers.")
            question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").strip().capitalize()

        while question2 not in ("Long", "Medium", "Short"):
            print("Please enter a valid option: Short, Medium, or Long.")
            question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").strip().capitalize()
            while any(character.isdigit() for character in question2):
                print("Please do not include numbers.")
                question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").strip().capitalize()

        while question2 != "Long" and question2 != "Medium" and question2 != "Short":
            print("Please enter a valid option: Short, Medium, or Long.")
            question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").capitalize()

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE listeners SET CompleteSurvey = 1, FavoriteGenres = ?, LengthPreference = ? WHERE ListenerID = ?",
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