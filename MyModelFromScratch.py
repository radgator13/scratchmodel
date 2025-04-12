import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re
import time
import os

def get_game_ids(date_obj):
    date_str = date_obj.strftime("%Y%m%d")
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}"
    r = requests.get(url)
    events = r.json().get("events", [])
    return [{"gameId": e["id"], "date": date_obj.strftime("%Y-%m-%d")} for e in events]

def extract_boxscore(game_id, game_date):
    url = f"https://www.espn.com/mlb/boxscore/_/gameId/{game_id}"
    print(f"🌐 Scraping: {url}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.content, "html.parser")

    team_names = soup.select("h2.ScoreCell__TeamName")
    if len(team_names) < 2:
        print("⚠️ Team names not found.")
        return None
    away_team = team_names[0].text.strip()
    home_team = team_names[1].text.strip()

    records = soup.select("div.Gamestrip__Record")
    away_record = records[0].text.strip().split(',')[0] if len(records) > 0 else ""
    home_record = records[1].text.strip().split(',')[0] if len(records) > 1 else ""

    scores = soup.select("div.Gamestrip__Score")
    away_runs = scores[0].get_text(strip=True) if len(scores) > 0 else ""
    home_runs = scores[1].get_text(strip=True) if len(scores) > 1 else ""

    return {
        "Game Date": game_date,
        "Away Team": re.sub(r"Winner Icon.*", "", away_team).strip(),
        "Away Record": away_record,
        "Away Score": re.sub(r"\D", "", away_runs),
        "Home Team": re.sub(r"Winner Icon.*", "", home_team).strip(),
        "Home Record": home_record,
        "Home Score": re.sub(r"\D", "", home_runs)
    }

def scrape_range(start_date, end_date, output_file="mlb_boxscores_cleaned.csv"):
    # Load existing file if it exists
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
        print(f"📄 Found existing file with {len(existing_df)} rows.")
        existing_dates = pd.to_datetime(existing_df["Game Date"], errors='coerce')
        if not existing_dates.empty:
            start_date = (existing_dates.max() + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            print(f"⏩ Resuming from: {start_date}")
    else:
        existing_df = pd.DataFrame()
        print("🆕 No previous file found. Starting fresh.")

    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    new_rows = []

    while current <= end:
        games = get_game_ids(current)
        for game in games:
            try:
                row = extract_boxscore(game["gameId"], game["date"])
                if row:
                    new_rows.append(row)
            except Exception as e:
                print(f"❌ Error parsing {game['gameId']}: {e}")
            time.sleep(0.75)
        current += timedelta(days=1)

    if new_rows:
        new_df = pd.DataFrame(new_rows)

        if not existing_df.empty:
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined.drop_duplicates(subset=["Game Date", "Away Team", "Home Team"], inplace=True)
        else:
            combined = new_df

        combined.to_csv(output_file, index=False)
        print(f"\n✅ Saved updated data to {output_file} (total rows: {len(combined)})")
    else:
        print("ℹ️ No new games found to append.")

if __name__ == "__main__":
    print("🚀 Fast ESPN scraper with auto-resume...")
    scrape_range("2025-03-27", "2025-04-14")
    input("\nPress Enter to exit...")
