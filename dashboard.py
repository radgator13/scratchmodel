import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import time

st.set_page_config(page_title="MLB Model vs Vegas", layout="wide")

# === Manual refresh button ===
if st.button("🔄 Refresh predictions from CSV"):
    st.cache_data.clear()

# === Regenerate fireball report if missing ===
def regenerate_fireball_accuracy():
    if not os.path.exists("fireball_accuracy_report.xlsx"):
        try:
            df = pd.read_csv("mlb_model_predictions.csv")
            df = df.dropna(subset=["Home Score", "Away Score", "Spread Home", "Total"])

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

            df = df[(df["ATS Result"] != "Push") & (df["Total Result"] != "Push")]
            df["ATS Outcome"] = df.apply(lambda r: "Win" if r["Model ATS Pick"] == r["ATS Result"] else "Loss", axis=1)
            df["Total Outcome"] = df.apply(lambda r: "Win" if r["Model Total Pick"] == r["Total Result"] else "Loss", axis=1)

            def fireball_stats(label_col, outcome_col):
                grouped = df.groupby(label_col)[outcome_col].value_counts().unstack().fillna(0)
                grouped["Total"] = grouped.sum(axis=1)
                grouped["Accuracy"] = (grouped.get("Win", 0) / grouped["Total"] * 100).round(1)
                return grouped.sort_index(ascending=False)

            ats_stats = fireball_stats("ATS Fireballs", "ATS Outcome")
            total_stats = fireball_stats("Total Fireballs", "Total Outcome")

            with pd.ExcelWriter("fireball_accuracy_report.xlsx") as writer:
                ats_stats.to_excel(writer, sheet_name="ATS Accuracy")
                total_stats.to_excel(writer, sheet_name="Total Accuracy")

            print("✅ Regenerated fireball_accuracy_report.xlsx")
            print("📂 Found:", os.path.exists("fireball_accuracy_report.xlsx"))
        except Exception as e:
            print(f"⚠️ Failed to regenerate fireball report: {e}")

# === Load model predictions ===
@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv("mlb_model_predictions.csv")
    df["Game Date"] = pd.to_datetime(df["Game Date"])
    df["Home Team"] = df["Home Team"].str.strip().str.title()
    df["Away Team"] = df["Away Team"].str.strip().str.title()

    def format_team(row, side):
        name = row[f"{side} Team"]
        rec = row.get(f"{side} Record", "")
        return f"{name} ({rec})" if pd.notna(rec) and rec else name

    df["Home"] = df.apply(lambda r: format_team(r, "Home"), axis=1)
    df["Away"] = df.apply(lambda r: format_team(r, "Away"), axis=1)

    df["Score"] = df.apply(
        lambda r: f"{int(r['Away Score'])} - {int(r['Home Score'])}"
        if pd.notna(r["Away Score"]) and pd.notna(r["Home Score"])
        else "Pending",
        axis=1
    )

    df["Vegas Spread"] = df["Spread Home"]
    df["Vegas Total"] = df["Total"]
    return df

df = load_data()


# === Confirm report exists visually
if os.path.exists("fireball_accuracy_report.xlsx"):
    st.success("✅ Fireball accuracy report is ready.")
else:
    st.error("❌ Fireball accuracy report not found.")

# === Last updated timestamp
if os.path.exists("mlb_model_predictions.csv"):
    modified_time = os.path.getmtime("mlb_model_predictions.csv")
    st.caption(f"📅 **Predictions last updated:** {datetime.fromtimestamp(modified_time).strftime('%b %d, %Y at %I:%M %p')}")

# === Sidebar Filters
st.sidebar.header("📅 Filter Games")
today = pd.Timestamp.today().normalize()
min_date = df["Game Date"].min().date()
max_data_date = df["Game Date"].max().date()
max_display_date = max((today + timedelta(days=2)).date(), max_data_date)

selected_date = st.sidebar.date_input(
    "Select Game Date", value=today.date(),
    min_value=min_date, max_value=max_display_date
)
selected_date = pd.to_datetime(selected_date).date()
df["Game Date Normalized"] = df["Game Date"].dt.date
filtered = df[df["Game Date Normalized"] == selected_date]

team_options = sorted(set(df["Home Team"]).union(df["Away Team"]))
selected_team = st.sidebar.selectbox("Filter by team (optional)", options=["All Teams"] + team_options)
if selected_team != "All Teams":
    filtered = filtered[
        (filtered["Home Team"] == selected_team) |
        (filtered["Away Team"] == selected_team)
    ]

# === Display Main Table
st.title("⚾ MLB Model vs Vegas Picks")
display_cols = [
    "Game Date", "Away", "Home", "Score",
    "Vegas Spread", "Model ATS Pick", "ATS Fireballs",
    "Vegas Total", "Model Total Pick", "Total Fireballs"
]
st.dataframe(filtered[display_cols].sort_values(["Game Date", "Home"]), use_container_width=True)

# === Results evaluation
def evaluate_results(df):
    df = df.copy()
    df = df.dropna(subset=["Home Score", "Away Score", "Spread Home", "Total"])
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
    df["ATS Outcome"] = df.apply(
        lambda r: "Win" if r["ATS Result"] == r["Model ATS Pick"]
        else "Loss" if r["ATS Result"] != "Push" else "Push", axis=1
    )
    df["Total Outcome"] = df.apply(
        lambda r: "Win" if r["Total Result"] == r["Model Total Pick"]
        else "Loss" if r["Total Result"] != "Push" else "Push", axis=1
    )
    return df

summary_df = evaluate_results(df)
summary_df = summary_df[summary_df["Game Date"] >= pd.to_datetime("2025-04-10")]

def summarize(df_subset, label=""):
    ats = df_subset["ATS Outcome"].value_counts()
    total = df_subset["Total Outcome"].value_counts()

    def render_block(title, counts):
        w = counts.get("Win", 0)
        l = counts.get("Loss", 0)
        p = counts.get("Push", 0)
        total = w + l
        pct = (w / total * 100) if total > 0 else 0
        return f"""
**{title}**
- ✅ Wins: {w}
- ❌ Losses: {l}
- ⚪ Pushes: {p}
- 🧮 Win Rate: **{pct:.1f}%**
"""
    st.markdown(render_block(f"{label}ATS Picks", ats))
    st.markdown(render_block(f"{label}Total Picks", total))

if not filtered.empty:
    filtered_summary = evaluate_results(filtered)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"📊 Summary for {selected_date.strftime('%B %d, %Y')}")
        summarize(filtered_summary)
    with col2:
        st.subheader("📈 Overall Model Performance (Since April 10)")
        summarize(summary_df)
regenerate_fireball_accuracy()
time.sleep(1)  # give file system time to register .xlsx
# === Fireball accuracy viewer
def render_fireball_accuracy_section():
    try:
        xls = pd.ExcelFile("fireball_accuracy_report.xlsx")
        ats_stats = pd.read_excel(xls, sheet_name="ATS Accuracy", index_col=0)
        total_stats = pd.read_excel(xls, sheet_name="Total Accuracy", index_col=0)

        with st.expander("🔥 Fireball Accuracy Summary"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**ATS Accuracy by Fireball 🔥**")
                for label, row in ats_stats.iterrows():
                    acc = row.get("Accuracy", 0)
                    st.markdown(f"- `{label}` → **{acc:.1f}%**")
            with col2:
                st.markdown("**Total Accuracy by Fireball 🔥**")
                for label, row in total_stats.iterrows():
                    acc = row.get("Accuracy", 0)
                    st.markdown(f"- `{label}` → **{acc:.1f}%**")
    except Exception as e:
        st.warning("⚠️ Fireball accuracy report not found or unreadable.")

render_fireball_accuracy_section()
