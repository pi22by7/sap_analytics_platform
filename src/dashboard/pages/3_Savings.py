import streamlit as st
import plotly.express as px
import pandas as pd
from utils import get_data

st.set_page_config(page_title="Savings", layout="wide")
data = get_data()

st.title("Savings Opportunities")

df_ekpo = data["ekpo"]
df_ekko = data["ekko"]
merged = df_ekpo.merge(df_ekko[["EBELN", "BSART", "LIFNR"]], on="EBELN")

# --- 1. MAVERICK SPEND ---
maverick_mask = merged["BSART"] != "NB"  # Assumption: 10% savings
maverick_total = merged[maverick_mask]["NETWR"].sum()
sav_maverick = maverick_total * 0.10

# --- 2. PRICE VARIANCE ---
avg_prices = df_ekpo.groupby("MATNR")["NETPR"].mean().reset_index(name="avg_price")
variance_df = merged.merge(avg_prices, on="MATNR")

variance_df["overspend"] = (
    variance_df["NETPR"] - variance_df["avg_price"]
) * variance_df["MENGE"]


sav_variance = variance_df[variance_df["overspend"] > 0]["overspend"].sum()

# --- 3. CONSOLIDATION ---
# If we buy a material from >3 vendors, we're diluting our buying power.
# Assumption: $5k savings in admin/bulk discounts per consolidated material.
vendor_counts = merged.groupby("MATNR")["LIFNR"].nunique()
candidates = vendor_counts[vendor_counts > 3]
sav_consolidation = len(candidates) * 5000

# --- SUMMARY CHART ---
st.subheader("Total Savings Potential")

savings_df = pd.DataFrame(
    {
        "Category": ["Maverick Spend", "Price Variance", "Consolidation"],
        "Amount": [sav_maverick, sav_variance, sav_consolidation],
    }
)

c1, c2 = st.columns([1, 2])

with c1:
    st.metric("Total Identified Savings", f"${savings_df['Amount'].sum():,.2f}")
    st.dataframe(
        savings_df.style.format({"Amount": "${:,.2f}"}),
        width='stretch',
        column_config={"Category": "Opportunity Type", "Amount": "Estimated Savings"},
    )

with c2:
    fig = px.bar(
        savings_df,
        x="Category",
        y="Amount",
        color="Category",
        title="Savings Breakdown",
        labels={"Amount": "Potential Savings ($)"},
    )
    fig.update_layout(yaxis_tickprefix="$", showlegend=False)
    st.plotly_chart(fig, width='stretch')

st.markdown("---")

# --- DETAILS TABLES ---
st.subheader("Actionable Insights")

tab1, tab2 = st.tabs(["High Variance Materials", "Consolidation Candidates"])

with tab1:
    st.markdown(
        "**Materials with significant price instability (Purchased above Avg Price)**"
    )

    top_var = (
        variance_df[variance_df["overspend"] > 0]
        .groupby("MATNR")["overspend"]
        .sum()
        .nlargest(10)
        .reset_index()
    )
    top_var = top_var.merge(data["mara"][["MATNR", "MAKTX"]], on="MATNR")
    st.dataframe(
        top_var.style.format({"overspend": "${:,.2f}"}),
        width='stretch',
        column_config={
            "MATNR": "Material ID",
            "MAKTX": "Description",
            "overspend": "Total Variance (Overspend)",
        },
    )

with tab2:
    st.markdown("**Materials sourced from fragmented supplier base (>3 Vendors)**")
    cons_df = (
        candidates.reset_index(name="vendor_count")
        .sort_values("vendor_count", ascending=False)
        .head(10)
    )
    cons_df = cons_df.merge(data["mara"][["MATNR", "MAKTX"]], on="MATNR")
    st.dataframe(
        cons_df,
        width='stretch',
        column_config={
            "MATNR": "Material ID",
            "MAKTX": "Description",
            "vendor_count": "Active Vendors",
        },
    )
