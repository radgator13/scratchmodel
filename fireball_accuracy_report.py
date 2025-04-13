import pandas as pd

# === Load model prediction file ===
df = pd.read_csv("mlb_model_predictions.csv")
df = df.dropna(subset=["Home Score", "Away Score", "Spread Home", "Total"])

# === Recalculate actual outcomes ===
df["ATS Result"] = df.apply(
    lambda r: "Home" if (r["Home Score"] + r["Spread Home"]) > r["Away Score"]
    else "Away" if (r["Home Score"] + r["Spread Home"]) < r["Away Score"]
    else "Push", axis=1
)

df["Total Result"] = df.apply(
    lambda r: "Over" if (r["Home Score"] + r["Away Score"]) > r["Total"]
    else "Under" if (r["Home Score"] + r["Away Score"]) < r["Total"]
    else "Push", axis=1
)

# === Filter out Pushes ===
df = df[(df["ATS Result"] != "Push") & (df["Total Result"] != "Push")]

# === Classify outcome per fireball ===
def get_result_col(pred_col, actual_col):
    return df.apply(lambda r: "Win" if r[pred_col] == r[actual_col] else "Loss", axis=1)

df["ATS Outcome"] = get_result_col("Model ATS Pick", "ATS Result")
df["Total Outcome"] = get_result_col("Model Total Pick", "Total Result")

# === Group by Fireballs and calculate accuracy ===
def fireball_stats(label_col, outcome_col):
    grouped = df.groupby(label_col)[outcome_col].value_counts().unstack().fillna(0)
    grouped["Total"] = grouped.sum(axis=1)
    grouped["Accuracy"] = (grouped.get("Win", 0) / grouped["Total"] * 100).round(1)
    return grouped.sort_index(ascending=False)

ats_stats = fireball_stats("ATS Fireballs", "ATS Outcome")
total_stats = fireball_stats("Total Fireballs", "Total Outcome")

# === Save report ===
with pd.ExcelWriter("fireball_accuracy_report.xlsx") as writer:
    ats_stats.to_excel(writer, sheet_name="ATS Accuracy")
    total_stats.to_excel(writer, sheet_name="Total Accuracy")

print("✅ Fireball accuracy report saved to fireball_accuracy_report.xlsx")
