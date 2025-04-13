import os
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from datetime import datetime, timedelta
import subprocess

# === Auto-refresh today's data ===
os.system("python MyModelFromScratch.py")
os.system("python odds_scraper_with_fallback.py")
os.system("python merge_boxscores_with_odds.py")

# === Load dataset ===
df_all = pd.read_csv("mlb_model_and_odds.csv")
df_all["Game Date"] = pd.to_datetime(df_all["Game Date"])

for col in ["Home Team", "Away Team"]:
    df_all[col] = df_all[col].str.strip().str.title()

# === Define training cutoff ===
cutoff_date = datetime.today() - timedelta(days=5)

df_train = df_all[
    (df_all["Game Date"] < cutoff_date) &
    df_all[["Home Score", "Away Score", "Spread Home", "Total"]].notna().all(axis=1)
].copy()

if df_train.empty:
    raise ValueError("No training data found before cutoff date.")

# === Classification targets ===
df_train["ATS Winner"] = np.where(
    (df_train["Home Score"] + df_train["Spread Home"] > df_train["Away Score"]), "Home",
    np.where((df_train["Home Score"] + df_train["Spread Home"] < df_train["Away Score"]), "Away", "Push")
)
df_train = df_train[df_train["ATS Winner"] != "Push"]

df_train["Total Result"] = np.where(
    (df_train["Home Score"] + df_train["Away Score"] > df_train["Total"]), "Over",
    np.where((df_train["Home Score"] + df_train["Away Score"] < df_train["Total"]), "Under", "Push")
)
df_train = df_train[df_train["Total Result"] != "Push"]

# === Label encoding ===
lb_ats = LabelEncoder()
lb_ats.fit(["Home", "Away"])
df_train["ATS Code"] = lb_ats.transform(df_train["ATS Winner"])

lb_total = LabelEncoder()
lb_total.fit(["Over", "Under"])
df_train["Total Code"] = lb_total.transform(df_train["Total Result"])

# === Features ===
exclude_cols = [
    "Game Date", "Home Team", "Away Team", "Bookmaker Used",
    "ATS Winner", "ATS Code", "Total Result", "Total Code",
    "Model ATS Pick", "ATS Confidence", "Model Total Pick", "Total Confidence",
    "ATS Fireballs", "Total Fireballs", "Home Score", "Away Score"
]
features = [col for col in df_train.columns if col not in exclude_cols and df_train[col].dtype in [np.float64, np.int64]]

# === Train models ===
X = df_train[features]
y_cls = df_train["ATS Code"]
y_tot = df_train["Total Code"]

clf_ats = XGBClassifier(eval_metric="logloss", objective="binary:logistic", base_score=0.5)
clf_ats.fit(X, y_cls)

clf_total = XGBClassifier(eval_metric="logloss", objective="binary:logistic", base_score=0.5)
clf_total.fit(X, y_tot)

# === Predict on ALL GAMES ===
df_all_features = df_all[features].fillna(0)
ats_probs = clf_ats.predict_proba(df_all_features)
total_probs = clf_total.predict_proba(df_all_features)

df_all["Model ATS Pick"] = lb_ats.inverse_transform(clf_ats.predict(df_all_features))
df_all["ATS Confidence"] = ats_probs.max(axis=1)

df_all["Model Total Pick"] = lb_total.inverse_transform(clf_total.predict(df_all_features))
df_all["Total Confidence"] = total_probs.max(axis=1)

# === Fireball confidence ===
def fireball_rating(conf):
    if conf >= 0.95: return "🔥🔥🔥🔥🔥"
    elif conf >= 0.85: return "🔥🔥🔥🔥"
    elif conf >= 0.75: return "🔥🔥🔥"
    elif conf >= 0.60: return "🔥🔥"
    else: return "🔥"

df_all["ATS Fireballs"] = df_all["ATS Confidence"].apply(fireball_rating)
df_all["Total Fireballs"] = df_all["Total Confidence"].apply(fireball_rating)

# === Save to CSV ===
df_all.to_csv("mlb_model_predictions.csv", index=False)
now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
print(f"✅ Model trained and predictions written at {now}.")

# === Push to GitHub ===
try:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", f"Auto-push with total model classification [{now}]"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("✅ Changes pushed to GitHub.")
except subprocess.CalledProcessError as e:
    print(f"⚠️ Git push failed: {e}")
