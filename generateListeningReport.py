import sqlite3
import pandas as pd

def clear():
    import main as app
    app.clear()

def main(username):
    import main as app
    app.main(username)

def generate_report(username):
    user_id = int(username) if str(username).isdigit() else username
    
    clear()
    print("***LISTENING REPORT***\n")
    
    conn = sqlite3.connect("database.db")

    query = """
        SELECT podcasts.Title, listening_history.TimesListened, listening_history.RatingGiven 
        FROM podcasts 
        JOIN listening_history ON podcasts.PodcastID = listening_history.PodcastID 
        WHERE listening_history.ListenerID = ? 
        ORDER BY listening_history.TimesListened DESC
    """

    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()

    if not df.empty:
        print(f"You listened to {len(df)} different podcasts.")
        print(f"\nThe most listened podcast is '{df.iloc[0]['Title']}' with {df.iloc[0]['TimesListened']} listens.")
        print(f"\nThe least listened podcast is '{df.iloc[-1]['Title']}' with {df.iloc[-1]['TimesListened']} listens.")

        # Filter out rows where ratings are missing (None/NaN) using pandas dropna
        df_rated = df.dropna(subset=['RatingGiven'])
        
        if not df_rated.empty:
            print(f"\nYour highest rating given is {df_rated['RatingGiven'].max()} and your lowest rating given is {df_rated['RatingGiven'].min()}.")
            print(f"\nYour average rating for all podcasts is {df_rated['RatingGiven'].mean():.2f}.")
        else:
            print("\nYou have not rated any podcasts yet.")

        print("\nYour podcasts sorted by times listened (from most to least):")

        # Iterate through the DataFrame rows cleanly
        for _, row in df.iterrows():
            print(f"\n- {row['Title']}")
            print(f"    Times listened: {row['TimesListened']}")
            print(f"    Your rating: {row['RatingGiven']}")
    else:
        print("You have no listening history.")

    input("\nPress Enter to return to the main menu...")
    main(username)