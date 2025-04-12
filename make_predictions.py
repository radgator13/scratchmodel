import pandas as pd
import numpy as np
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# === Load full dataset (past + upcoming) ===
df_all = pd.read_csv("mlb_model_and_odds.csv")
df_all["Game Date"] = pd.to_datetime(df_all["Game Date"])

# Clean team strings
for team_col in ["Home Team", "Away Team"]:
    df_all[team_col] = df_all[team_col].str.strip().str.title()

# === Train only on rows with final scores ===
df_train = df_all.dropna(subset=["Home Score", "Away Score", "Spread Home", "Total"])

# --- Create targets ---
df_train["ATS Winner"] = np.where(
    (df_train["Home Score"] + df_train["Spread Home"] > df_train["Away Score"]), "Home",
    np.where((df_train["Home Score"] + df_train["Spread Home"] < df_train["Away Score"]), "Away", "Push")
)
df_train = df_train[df_train["ATS Winner"] != "Push"]

df_train["Actual Total Runs"] = df_train["Home Score"] + df_train["Away Score"]

# Encode ATS target
lb_ats = LabelEncoder()
df_train["ATS Code"] = lb_ats.fit_transform(df_train["ATS Winner"])

# === Features ===
exclude_cols = [
    "Game Date", "Home Team", "Away Team", "Bookmaker Used",
    "ATS Winner", "ATS Code", "Actual Total Runs",
    "Model ATS Pick", "ATS Confidence", "Model Total Pick", "Total Confidence",
    "Home Score", "Away Score", "ATS Fireballs", "Total Fireballs"
]
features = [col for col in df_train.columns if col not in exclude_cols and df_train[col].dtype in [np.float64, np.int64]]

# Train models
X = df_train[features]
y_cls = df_train["ATS Code"]
y_reg = df_train["Actual Total Runs"]

X_train_cls, X_test_cls, y_train_cls, y_test_cls = train_test_split(X, y_cls, test_size=0.2, random_state=42)
X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(X, y_reg, test_size=0.2, random_state=42)

clf = XGBClassifier(eval_metric="logloss")
clf.fit(X_train_cls, y_train_cls)

reg = XGBRegressor()
reg.fit(X_train_reg, y_train_reg)

# === Predict on ALL games ===
df_all_features = df_all[features].fillna(0)

ats_probs = clf.predict_proba(df_all_features)
df_all["Model ATS Pick"] = lb_ats.inverse_transform(clf.predict(df_all_features))
df_all["ATS Confidence"] = ats_probs.max(axis=1)

total_preds = reg.predict(df_all_features)
df_all["Model Total Pick"] = np.where(total_preds > df_all["Total"], "Over", "Under")
df_all["Total Confidence"] = 1 - np.abs(total_preds - y_reg.mean()) / y_reg.std()

# === Fireball Mapping ===
def fireball_rating(conf):
    if conf >= 0.95:
        return "🔥🔥🔥🔥🔥"
    elif conf >= 0.85:
        return "🔥🔥🔥🔥"
    elif conf >= 0.75:
        return "🔥🔥🔥"
    elif conf >= 0.60:
        return "🔥🔥"
    else:
        return "🔥"

df_all["ATS Fireballs"] = df_all["ATS Confidence"].apply(fireball_rating)
df_all["Total Fireballs"] = df_all["Total Confidence"].apply(fireball_rating)

# === Save to final file ===
df_all.to_csv("mlb_model_predictions.csv", index=False)
print("✅ Predictions for ALL games saved to mlb_model_predictions.csv")
