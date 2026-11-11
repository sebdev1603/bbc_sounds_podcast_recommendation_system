import sqlite3
import os
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

with sqlite3.connect("database.db") as connection:
    cursor = connection.cursor()

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

def username_exists(username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM Users WHERE username = ?",
        (username,)
    )

    result = cursor.fetchone()

    conn.close()

    return result is not None

username = input("Enter your username: ")

username_valid = False

while username_valid == False:
    if username_exists(username):
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM Users where username = ?",
            (username,)
        )

        result = cursor.fetchone()

        conn.close()

        print("Welcome back:", result[0])
        break
    else:
        print("\nIncorrect username")
        username = input("\nEnter your username: ")
