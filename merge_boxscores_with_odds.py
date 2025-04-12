import pandas as pd

# Load both files
boxscores = pd.read_csv("mlb_boxscores_cleaned.csv")
odds = pd.read_csv("mlb_odds_mybookie.csv")

# Normalize strings (strip spaces & title case for clean merge)
for df in [boxscores, odds]:
    df["Game Date"] = pd.to_datetime(df["Game Date"]).dt.strftime("%Y-%m-%d")
    df["Home Team"] = df["Home Team"].str.strip().str.title()
    df["Away Team"] = df["Away Team"].str.strip().str.title()

# Merge on Game Date + Home Team + Away Team
merged = pd.merge(
    boxscores,
    odds,
    on=["Game Date", "Home Team", "Away Team"],
    how="left"
)

# Optional: reorder columns (boxscore first, then odds)
core_columns = [
    "Game Date", "Away Team", "Away Record", "Away Score",
    "Home Team", "Home Record", "Home Score"
]

odds_columns = [col for col in merged.columns if col not in core_columns]
merged = merged[core_columns + odds_columns]

# Save to file
output_file = "mlb_merged_model_and_odds.csv"
merged.to_csv(output_file, index=False)
print(f"✅ Merged file saved as {output_file} ({len(merged)} rows)")
