import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# === Must be first ===
st.set_page_config(page_title="MLB Model vs Vegas", layout="wide")

# === Manual refresh button ===
if st.button("🔄 Refresh predictions from CSV"):
    st.cache_data.clear()

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

# === Load and filter ===
df = load_data()

# Show last updated time for prediction file
file_path = "mlb_model_predictions.csv"
if os.path.exists(file_path):
    modified_time = os.path.getmtime(file_path)
    last_updated = datetime.fromtimestamp(modified_time).strftime("%b %d, %Y at %I:%M %p")
    st.caption(f"📅 **Predictions last updated:** {last_updated}")

# === Sidebar Filters ===
st.sidebar.header("📅 Filter Games")

today = pd.Timestamp.today().normalize()
min_date = df["Game Date"].min().date()
max_data_date = df["Game Date"].max().date()
max_display_date = max((today + timedelta(days=2)).date(), max_data_date)

selected_date = st.sidebar.date_input(
    "Select Game Date",
    value=today.date(),
    min_value=min_date,
    max_value=max_display_date
)

selected_date = pd.to_datetime(selected_date).date()
df["Game Date Normalized"] = df["Game Date"].dt.date
filtered = df[df["Game Date Normalized"] == selected_date]

# === Team filter ===
team_options = sorted(set(df["Home Team"]).union(df["Away Team"]))
selected_team = st.sidebar.selectbox("Filter by team (optional)", options=["All Teams"] + team_options)

if selected_team != "All Teams":
    filtered = filtered[
        (filtered["Home Team"] == selected_team) |
        (filtered["Away Team"] == selected_team)
    ]

# === Display Table ===
st.title("⚾ MLB Model vs Vegas Picks")
display_cols = [
    "Game Date", "Away", "Home", "Score",
    "Vegas Spread", "Model ATS Pick", "ATS Fireballs",
    "Vegas Total", "Model Total Pick", "Total Fireballs"
]

st.dataframe(
    filtered[display_cols].sort_values(["Game Date", "Home"]),
    use_container_width=True
)

# === Daily & Grand Summary ===
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

# === Show summaries ===
filtered_summary = summary_df[summary_df["Game Date Normalized"] == selected_date]
if not filtered_summary.empty:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"📊 Summary for {selected_date.strftime('%B %d, %Y')}")
        summarize(filtered_summary)

    with col2:
        st.subheader("📈 Overall Model Performance")
        summarize(summary_df)

