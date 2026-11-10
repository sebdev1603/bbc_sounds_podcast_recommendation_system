import sqlite3

with sqlite3.connect("database.db") as connection:
    cursor = connection.cursor()

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
