import streamlit as st
import pandas as pd

# === Streamlit page config ===
st.set_page_config(page_title="🔥 Fireball Accuracy Report", layout="wide")
st.title("🔥 Fireball Confidence Accuracy")

st.caption("This report summarizes model performance by fireball confidence levels for ATS and Total Picks.")

# === Load and display the Excel report ===
try:
    xls = pd.ExcelFile("fireball_accuracy_report.xlsx")
    ats_stats = pd.read_excel(xls, sheet_name="ATS Accuracy", index_col=0)
    total_stats = pd.read_excel(xls, sheet_name="Total Accuracy", index_col=0)

    # Side-by-side columns
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 ATS Accuracy by Fireball")
        st.dataframe(ats_stats)

    with col2:
        st.subheader("📉 Total Accuracy by Fireball")
        st.dataframe(total_stats)

except FileNotFoundError:
    st.error("⚠️ fireball_accuracy_report.xlsx not found. Please run make_predictions.py first.")
