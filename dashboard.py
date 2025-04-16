import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import pytz

st.set_page_config(page_title="MLB Model vs Vegas", layout="wide")

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
        lambda r: "Win" if r["ATS Result"] == r["Model ATS Pick"] else "Loss", axis=1
    )
    df["Total Outcome"] = df.apply(
        lambda r: "Win" if r["Total Result"] == r["Model Total Pick"] else "Loss", axis=1
    )
    return df

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

def fireball_stats(df_eval, label_col, outcome_col):
    grouped = df_eval.groupby(label_col)[outcome_col].value_counts().unstack().fillna(0)
    grouped["Total"] = grouped.sum(axis=1)
    grouped["Accuracy"] = (grouped.get("Win", 0) / grouped["Total"] * 100).round(1)
    return grouped.sort_index(ascending=False)

def render_fireball_accuracy_summary(df_eval, label=""):
    df_eval = df_eval[(df_eval["ATS Outcome"] != "Push") & (df_eval["Total Outcome"] != "Push")]

    ats_stats = fireball_stats(df_eval, "ATS Fireballs", "ATS Outcome")
    total_stats = fireball_stats(df_eval, "Total Fireballs", "Total Outcome")

    with st.expander(f"🔥 Fireball Accuracy Summary ({label})"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**ATS Accuracy by Fireball 🔥**")
            for label, row in ats_stats.iterrows():
                st.markdown(f"- `{label}` → **{row['Accuracy']:.1f}%**")
            if "Accuracy" in ats_stats.columns:
                st.bar_chart(ats_stats["Accuracy"])
            if all(col in ats_stats.columns for col in ["Win", "Loss", "Total"]):
                st.caption("🔢 Pick counts:")
                st.dataframe(ats_stats[["Win", "Loss", "Total"]])
            else:
                st.info("No ATS picks available to show counts for this date.")

        with col2:
            st.markdown("**Total Accuracy by Fireball 🔥**")
            for label, row in total_stats.iterrows():
                st.markdown(f"- `{label}` → **{row['Accuracy']:.1f}%**")
            if "Accuracy" in total_stats.columns:
                st.bar_chart(total_stats["Accuracy"])
            if all(col in total_stats.columns for col in ["Win", "Loss", "Total"]):
                st.caption("🔢 Pick counts:")
                st.dataframe(total_stats[["Win", "Loss", "Total"]])
            else:
                st.info("No Total picks available to show counts for this date.")

# === Load and preprocess
df = load_data()
df["Game Date Normalized"] = df["Game Date"].dt.date

st.sidebar.header("📅 Filter Games")
today = pd.Timestamp.today().normalize()
min_date = df["Game Date"].min().date()
max_data_date = df["Game Date"].max().date()
max_display_date = max((today + timedelta(days=2)).date(), max_data_date)

selected_date = st.sidebar.date_input("Select Game Date", value=today.date(), min_value=min_date, max_value=max_display_date)
selected_date = pd.to_datetime(selected_date).date()
filtered = df[df["Game Date Normalized"] == selected_date]

team_options = sorted(set(df["Home Team"]).union(df["Away Team"]))
selected_team = st.sidebar.selectbox("Filter by team (optional)", options=["All Teams"] + team_options)
if selected_team != "All Teams":
    filtered = filtered[
        (filtered["Home Team"] == selected_team) |
        (filtered["Away Team"] == selected_team)
    ]

# === Timestamp
if os.path.exists("mlb_model_predictions.csv"):
    modified_time = os.path.getmtime("mlb_model_predictions.csv")
    st.caption(f"📅 **Predictions last updated:** {datetime.fromtimestamp(modified_time).strftime('%b %d, %Y at %I:%M %p')}")

# === Display table
st.title("⚾ MLB Model vs Vegas Picks")
display_cols = [
    "Game Date", "Away", "Home", "Score",
    "Vegas Spread", "Model ATS Pick", "ATS Fireballs",
    "Vegas Total", "Model Total Pick", "Total Fireballs"
]
st.dataframe(filtered[display_cols].sort_values(["Game Date", "Home"]), use_container_width=True)

# === Top Picks
st.subheader(f"🔝 Top 10 Model Picks for {selected_date.strftime('%B %d, %Y')}")

top_filtered = filtered.copy()
ats_picks = top_filtered[["Game Date", "Away", "Home", "Model ATS Pick", "ATS Confidence", "ATS Fireballs"]].copy()
ats_picks.columns = ["Game Date", "Away", "Home", "Pick", "Confidence", "Fireballs"]
ats_picks["Type"] = "ATS"

total_picks = top_filtered[["Game Date", "Away", "Home", "Model Total Pick", "Total Confidence", "Total Fireballs"]].copy()
total_picks.columns = ["Game Date", "Away", "Home", "Pick", "Confidence", "Fireballs"]
total_picks["Type"] = "Total"

top_picks = pd.concat([ats_picks, total_picks], ignore_index=True)

pick_filter = st.radio("Show picks by type:", ["All", "ATS Only", "Total Only"], horizontal=True)
if pick_filter == "ATS Only":
    top_picks = top_picks[top_picks["Type"] == "ATS"]
elif pick_filter == "Total Only":
    top_picks = top_picks[top_picks["Type"] == "Total"]

top_picks = top_picks[top_picks["Confidence"] >= 0.75]
top_picks = top_picks.sort_values("Confidence", ascending=False).head(10)

st.dataframe(
    top_picks[["Type", "Away", "Home", "Pick", "Confidence", "Fireballs"]].reset_index(drop=True),
    use_container_width=True
)

# === Timestamp for Top Picks Table
local_tz = pytz.timezone("US/Eastern")  # your actual timezone
top_timestamp = datetime.now(pytz.utc).astimezone(local_tz).strftime("%B %d, %Y at %I:%M %p")
st.caption(f"🕒 Top picks generated on {top_timestamp}")

# === Summary + Fireball Reporting
if not filtered.empty:
    df_results = evaluate_results(df)
    filtered_summary = df_results[df_results["Game Date Normalized"] == selected_date]
    overall_summary = df_results[df_results["Game Date"] >= pd.to_datetime("2025-04-11")]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"📊 Summary for {selected_date.strftime('%B %d, %Y')}")
        summarize(filtered_summary)
    with col2:
        st.subheader("📈 Overall Model Performance (Since April 11)")
        summarize(overall_summary)

    st.subheader("🔥 Fireball Accuracy Reporting")
    scope = st.radio("Choose fireball report scope:", ["Selected Date", "Overall"], horizontal=True)

    if scope == "Selected Date":
        render_fireball_accuracy_summary(filtered_summary, label=selected_date.strftime("%b %d"))
    else:
        render_fireball_accuracy_summary(overall_summary, label="Since Apr 11")

# === Model Explanation Footer
local_tz = pytz.timezone("US/Eastern")  # your actual timezone
footer_time = datetime.now(pytz.utc).astimezone(local_tz).strftime("%B %d, %Y at %I:%M %p")
st.markdown("---")
st.subheader("🧠 Why These Picks?")
st.markdown("""
These picks are generated by a machine learning model trained on:
- Team records, matchup stats, and Vegas lines
- Batter/pitcher splits, lineup strength, and recent performance
- Confidence is based on model probability vs implied market edge

Only picks with a high confidence score (≥ 0.75) are shown above.

Use these picks to track model strength, spot value bets, or supplement DFS decisions.
""")
st.caption(f"🧠 Summary generated on {footer_time}")
