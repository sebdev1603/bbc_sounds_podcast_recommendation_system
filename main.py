import sqlite3
import os

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

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
        search_programmes()
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

def survey():
    clear()
    print("***BBC SOUNDS SURVEY***\n")
    print("Please answer the following questions:\n")

    # Example survey questions
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

def search_programmes():
    clear()
    print("***SEARCH FOR PROGRAMMES***\n")
    search_query = input("Enter a keyword to search for programmes: ")

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
        conn.close()
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