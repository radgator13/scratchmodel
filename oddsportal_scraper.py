import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os

API_KEY = "591b5b68a9802e9b588155794300ed47"
SPORT_KEY = "baseball_mlb"
MARKETS = "h2h,spreads,totals"
REGION = "us"

START_DATE = datetime.strptime("2025-03-27", "%Y-%m-%d")
END_DATE = datetime.today() + timedelta(days=2)
OUTPUT_CSV = "mlb_odds_mybookie.csv"

# Priority order of bookmakers to try
BOOKMAKER_PRIORITY = ["mybookieag", "fanduel", "draftkings", "betmgm"]

def fetch_odds_for_day(date_obj):
    snapshot_time = date_obj.replace(hour=16).isoformat() + "Z"

    url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": API_KEY,
        "markets": MARKETS,
        "regions": REGION,
        "oddsFormat": "decimal",
        "date": snapshot_time
    }

    print(f"📅 Fetching odds for {date_obj.strftime('%Y-%m-%d')}...")

    try:
        res = requests.get(url, params=params)
        if res.status_code != 200:
            print(f"⚠️ API Error {res.status_code}: {res.text}")
            return []

        snapshot = res.json().get("data", [])
        rows = []

        for game in snapshot:
            home = game["home_team"]
            away = game["away_team"]
            game_date = game["commence_time"][:10]

            bookmaker_row = None

            for bk in BOOKMAKER_PRIORITY:
                book = next((b for b in game.get("bookmakers", []) if b["key"] == bk), None)
                if not book:
                    continue

                row = {
                    "Game Date": game_date,
                    "Home Team": home,
                    "Away Team": away,
                    "Bookmaker Used": book["title"]
                }

                for market in book.get("markets", []):
                    if market["key"] == "h2h":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == home:
                                row["ML Home"] = outcome["price"]
                            elif outcome["name"] == away:
                                row["ML Away"] = outcome["price"]
                    elif market["key"] == "spreads":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == home:
                                row["Spread Home"] = outcome["point"]
                                row["Spread Home Odds"] = outcome["price"]
                            elif outcome["name"] == away:
                                row["Spread Away"] = outcome["point"]
                                row["Spread Away Odds"] = outcome["price"]
                    elif market["key"] == "totals":
                        for outcome in market["outcomes"]:
                            if "Over" in outcome["name"]:
                                row["Total"] = outcome["point"]
                                row["Over Odds"] = outcome["price"]
                            elif "Under" in outcome["name"]:
                                row["Under Odds"] = outcome["price"]

                bookmaker_row = row
                break  # ✅ Use only the first available bookmaker

            if bookmaker_row:
                rows.append(bookmaker_row)

        return rows

    except Exception as e:
        print(f"❌ Error on {date_obj.strftime('%Y-%m-%d')}: {e}")
        return []

def get_existing_dates():
    if not os.path.exists(OUTPUT_CSV):
        return set()
    df = pd.read_csv(OUTPUT_CSV)
    return set(df["Game Date"].unique())

def scrape_range(start_date, end_date):
    existing_dates = get_existing_dates()
    current = start_date
    all_rows = []

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        if date_str in existing_dates:
            print(f"⏭ Skipping {date_str} (already in file)")
        else:
            new_rows = fetch_odds_for_day(current)
            all_rows.extend(new_rows)
            time.sleep(1.25)
        current += timedelta(days=1)

    if all_rows:
        new_df = pd.DataFrame(all_rows)
        if os.path.exists(OUTPUT_CSV):
            existing_df = pd.read_csv(OUTPUT_CSV)
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined.drop_duplicates(subset=["Game Date", "Home Team", "Away Team"], inplace=True)
        else:
            combined = new_df

        combined.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅ Updated odds saved to {OUTPUT_CSV} ({len(combined)} total rows)")
    else:
        print("✅ No new data to append.")

if __name__ == "__main__":
    print("🚀 Running MLB odds scraper with fallback...")
    scrape_range(START_DATE, END_DATE)
    input("\nPress Enter to exit...")
