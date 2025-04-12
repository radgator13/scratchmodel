import os
import subprocess
import sys

def run_step(name, command):
    print(f"\n🚀 STEP: {name}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"❌ {name} failed.")
        sys.exit(result.returncode)
    else:
        print(f"✅ {name} completed.")

if __name__ == "__main__":
    print("🏁 Starting Full MLB Model + Odds Pipeline")

    # 1. Run model scraper (scores)
    run_step("Scraping Boxscores (model results)", "python MyModelFromScratch.py")

    # 2. Run odds scraper (MyBookie + fallback, with merge)
    run_step("Scraping Odds + Merging", "python odds_scraper_with_fallback.py")

    # 3. Final result is mlb_model_and_odds.csv
    print("\n🎯 Pipeline complete. Merged file saved as: mlb_model_and_odds.csv")
    print("📊 To view your dashboard, run:")
    print("   👉 streamlit run dashboard.py")
