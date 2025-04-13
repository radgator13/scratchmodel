import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import argparse

API_KEY = "591b5b68a9802e9b588155794300ed47"
SPORT_KEY = "baseball_mlb"
MARKETS = "h2h,spreads,totals"
REGION = "us"

START_DATE = datetime.strptime("2025-03-27", "%Y-%m-%d")
END_DATE = datetime.today() + timedelta(days=2)
OUTPUT_CSV = "mlb_odds_mybookie.csv"
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
                break

            if bookmaker_row:
                rows.append(bookmaker_row)

        return rows

    except Exception as e:
        print(f"❌ Error on {date_obj.strftime('%Y-%m-%d')}: {e}")
        return []

def scrape_range(start_date, end_date, update_existing=False):
    columns = [
        "Game Date", "Home Team", "Away Team", "Bookmaker Used",
        "ML Home", "ML Away",
        "Spread Home", "Spread Home Odds", "Spread Away", "Spread Away Odds",
        "Total", "Over Odds", "Under Odds"
    ]

    if os.path.exists(OUTPUT_CSV):
        existing_df = pd.read_csv(OUTPUT_CSV)
    else:
        print("🆕 No odds file found. Creating new base file.")
        existing_df = pd.DataFrame(columns=columns)
        existing_df.to_csv(OUTPUT_CSV, index=False)

    all_rows = []
    current = start_date

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        if not update_existing and date_str in existing_df["Game Date"].astype(str).unique():
            print(f"⏭ Skipping {date_str} (already exists)")
        else:
            new_rows = fetch_odds_for_day(current)
            all_rows.extend(new_rows)
            time.sleep(1.25)

        current += timedelta(days=1)

    if all_rows:
        new_df = pd.DataFrame(all_rows)

        if not existing_df.empty:
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined.drop_duplicates(subset=["Game Date", "Home Team", "Away Team"], keep="last", inplace=True)
        else:
            combined = new_df

        combined.to_csv(OUTPUT_CSV, index=False)
        print(f"\n✅ Updated odds saved to {OUTPUT_CSV} ({len(combined)} total rows)")
    else:
        print("✅ No new odds scraped, but file is ready.")

def merge_with_model_results():
    model_file = "mlb_boxscores_cleaned.csv"
    odds_file = OUTPUT_CSV
    output_file = "mlb_model_and_odds.csv"

    print("🔗 Merging model results with odds...")

    if not os.path.exists(model_file) or not os.path.exists(odds_file):
        print("⚠️ One or both input files are missing.")
        return

    model = pd.read_csv(model_file)
    odds = pd.read_csv(odds_file)

    for df in [model, odds]:
        df["Game Date"] = pd.to_datetime(df["Game Date"], errors='coerce').dt.strftime("%Y-%m-%d")
        df["Home Team"] = df["Home Team"].str.strip().str.title()
        df["Away Team"] = df["Away Team"].str.strip().str.title()

    merged = pd.merge(model, odds, on=["Game Date", "Home Team", "Away Team"], how="left")
    merged.to_csv(output_file, index=False)
    print(f"✅ Merged file saved as {output_file} ({len(merged)} rows)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-existing", action="store_true", help="Update odds for existing rows too")
    args = parser.parse_args()

    print("🚀 Starting odds scrape with fallback + model merge")
    scrape_range(START_DATE, END_DATE, update_existing=args.update_existing)
    merge_with_model_results()
