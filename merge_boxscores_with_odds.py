import os
import pandas as pd

# === Verify input files exist ===
if not os.path.exists("mlb_boxscores_cleaned.csv") or not os.path.exists("mlb_odds_mybookie.csv"):
    print("❌ Missing input files for merging.")
    exit(1)

# === Load files with error handling ===
try:
    boxscores = pd.read_csv("mlb_boxscores_cleaned.csv")
    odds = pd.read_csv("mlb_odds_mybookie.csv")
except Exception as e:
    print(f"❌ Failed to read input files: {e}")
    exit(1)

# === Normalize team names and dates ===
for df in [boxscores, odds]:
    df["Game Date"] = pd.to_datetime(df["Game Date"], errors='coerce').dt.strftime("%Y-%m-%d")
    df["Home Team"] = df["Home Team"].astype(str).str.strip().str.title()
    df["Away Team"] = df["Away Team"].astype(str).str.strip().str.title()

# === Merge on Game Date + Home Team + Away Team
try:
    merged = pd.merge(
        boxscores,
        odds,
        on=["Game Date", "Home Team", "Away Team"],
        how="left"
    )
except Exception as e:
    print(f"❌ Merge failed: {e}")
    exit(1)

# === Optional: reorder columns (boxscore first, then odds)
core_columns = [
    "Game Date", "Away Team", "Away Record", "Away Score",
    "Home Team", "Home Record", "Home Score"
]
odds_columns = [col for col in merged.columns if col not in core_columns]
merged = merged[core_columns + odds_columns]

# === Save to file
output_file = "mlb_merged_model_and_odds.csv"
merged.to_csv(output_file, index=False)
print(f"✅ Merged file saved as {output_file} ({len(merged)} rows)")
