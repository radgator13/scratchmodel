﻿import pandas as pd
import numpy as np
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# === Load dataset ===
df_all = pd.read_csv("mlb_model_and_odds.csv")
df_all["Game Date"] = pd.to_datetime(df_all["Game Date"])

for col in ["Home Team", "Away Team"]:
    df_all[col] = df_all[col].str.strip().str.title()

# === Define training cutoff date ===
cutoff_date = pd.to_datetime("2025-04-01")

# Train on games BEFORE the cutoff, with final scores
df_train = df_all[
    (df_all["Game Date"] < cutoff_date) &
    df_all[["Home Score", "Away Score", "Spread Home", "Total"]].notna().all(axis=1)
].copy()

# --- Targets ---
df_train["ATS Winner"] = np.where(
    (df_train["Home Score"] + df_train["Spread Home"] > df_train["Away Score"]), "Home",
    np.where((df_train["Home Score"] + df_train["Spread Home"] < df_train["Away Score"]), "Away", "Push")
)
df_train = df_train[df_train["ATS Winner"] != "Push"]

df_train["Actual Total Runs"] = df_train["Home Score"] + df_train["Away Score"]

# Encode classification target
lb_ats = LabelEncoder()
df_train["ATS Code"] = lb_ats.fit_transform(df_train["ATS Winner"])

# === Features ===
exclude_cols = [
    "Game Date", "Home Team", "Away Team", "Bookmaker Used",
    "ATS Winner", "ATS Code", "Actual Total Runs",
    "Model ATS Pick", "ATS Confidence", "Model Total Pick", "Total Confidence",
    "ATS Fireballs", "Total Fireballs",
    "Home Score", "Away Score"
]
features = [col for col in df_train.columns if col not in exclude_cols and df_train[col].dtype in [np.float64, np.int64]]

# === Train models ===
X = df_train[features]
y_cls = df_train["ATS Code"]
y_reg = df_train["Actual Total Runs"]

clf = XGBClassifier(eval_metric="logloss")
clf.fit(X, y_cls)

reg = XGBRegressor()
reg.fit(X, y_reg)

# === Predict on ALL GAMES ===
df_all_features = df_all[features].fillna(0)
ats_probs = clf.predict_proba(df_all_features)
total_preds = reg.predict(df_all_features)

# Predictions
df_all["Model ATS Pick"] = lb_ats.inverse_transform(clf.predict(df_all_features))
df_all["ATS Confidence"] = ats_probs.max(axis=1)
df_all["Model Total Pick"] = np.where(total_preds > df_all["Total"], "Over", "Under")
df_all["Total Confidence"] = 1 - np.abs(total_preds - y_reg.mean()) / y_reg.std()

# Fireballs
def fireball_rating(conf):
    if conf >= 0.95: return "🔥🔥🔥🔥🔥"
    elif conf >= 0.85: return "🔥🔥🔥🔥"
    elif conf >= 0.75: return "🔥🔥🔥"
    elif conf >= 0.60: return "🔥🔥"
    else: return "🔥"

df_all["ATS Fireballs"] = df_all["ATS Confidence"].apply(fireball_rating)
df_all["Total Fireballs"] = df_all["Total Confidence"].apply(fireball_rating)

# Save to output
df_all.to_csv("mlb_model_predictions.csv", index=False)
print("✅ Model trained on pre-2025-04-01 games. Predictions written for all games.")
