# CLI module for collecting, resetting, and checking a listener's onboarding preference survey.
import sqlite3
import time

# Deferred import avoids a circular dependency with main.py.
def clear():
    import main as app
    app.clear()

def survey(username):
    """Run the interactive survey to choose up to 5 favourite genres and preferred episode length."""
    user_id = int(username) if str(username).isdigit() else username

    clear()

    valid_genres = [
        "News", "Travel", "History", "Comedy", "True Crime",
        "Technology", "Science", "Business", "Gaming",
        "Entertainment", "Sport", "Health"
    ]

    favorite_genres = []
    i = 0

    # Loop until the user selects up to 5 genres or submits an empty line with >= 1 selected.
    while True:
        clear()
        print("***BBC SOUNDS SURVEY***")

        if i > 0:
            print(f"\nSelected genres: {', '.join(favorite_genres)}\n")
        else:
            i = 0

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

        print("\nEnter as many genres as you like (up to 5), enter nothing when you are finished")
        question1 = input("\nWhat are your favorite genre of podcasts? (or press Enter when finished): ").strip()
        if question1 == "":
            if favorite_genres:
                break
            print("You must enter at least one genre.")
            continue

        # Reject numeric input and verify the typed genre exists in valid_genres.
        if any(character.isdigit() for character in question1):
            print("Please do not include numbers.")
            continue

        matched_genre = next((g for g in valid_genres if g.lower() == question1.lower()), None)
        if not matched_genre:
            clear()
            print("Invalid genre. Please choose from the list provided.")
            time.sleep(1)
            clear()
            continue

        # Entering an already-selected genre toggles it off.
        if matched_genre in favorite_genres:
            clear()
            print("Remove", matched_genre, "from your list of favorite genres.")
            favorite_genres.remove(matched_genre)
            time.sleep(1)
            clear()
            continue

        favorite_genres.append(matched_genre)

        i = i + 1
        if i == 5:
            print("\nYou have entered the maximum amount of favourite genres (5).")
            break
        
    # Store selected genres as a comma-separated string.
    question1 = ",".join(favorite_genres)

    # Prompt and validate preferred episode length (Short, Medium, or Long).
    question2 = input("\nWhat length of episodes do you prefer? (Short/Medium/Long): ").strip().capitalize()
    while any(character.isdigit() for character in question2):
        print("Please do not include numbers.")
        question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").strip().capitalize()

    while question2 not in ("Long", "Medium", "Short"):
        print("Please enter a valid option: Short, Medium, or Long.")
        question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").strip().capitalize()
        while any(character.isdigit() for character in question2):
            print("Please do not include numbers.")
            question2 = input("What length of episodes do you prefer? (Short/Medium/Long): ").strip().capitalize()

    # Save the completed survey responses to the listeners table.
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE listeners SET CompleteSurvey = 1, FavoriteGenres = ?, LengthPreference = ? WHERE ListenerID = ?",
        (question1, question2, user_id)
    )

    conn.commit()
    conn.close()

    clear()
    print("\nThank you for completing the survey!")
    time.sleep(1)

def delete_survey(username):
    """Reset the listener's survey completion flag and clear their saved preferences."""
    user_id = int(username) if str(username).isdigit() else username

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE listeners SET CompleteSurvey = 0, FavoriteGenres = ?, LengthPreference = ? WHERE ListenerID = ?",
        ("", None, user_id)
    )

    conn.commit()
    conn.close()

    clear()
    print("\nYour survey responses have been deleted.")
    time.sleep(1)

def is_survey_complete(username):
    """Return True if the listener has already completed the preference survey."""
    user_id = int(username) if str(username).isdigit() else username

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM listeners WHERE ListenerID = ? AND CompleteSurvey = 1",
        (user_id,)
    )

    result = cursor.fetchone()
    conn.close()

    return result is not None