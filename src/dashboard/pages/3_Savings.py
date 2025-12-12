import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Savings Opportunities", layout="wide")

if "data" not in st.session_state:
    st.stop()

data = st.session_state["data"]
df_ekpo = data["ekpo"]
df_ekko = data["ekko"]
df_mara = data["mara"]

st.title("💰 Savings & Opportunities")

# --- CALCULATIONS ---

merged = df_ekpo.merge(df_ekko[["EBELN", "BSART", "AEDAT"]], on="EBELN")

# 2. Maverick Spend
maverick_mask = merged["BSART"] == "FO"
maverick_spend = merged[maverick_mask]["NETWR"].sum()
maverick_count = maverick_mask.sum()

# 3. Price Variance Analysis - average because we dropped base_price
avg_prices = (
    df_ekpo.groupby("MATNR")["NETPR"].mean().reset_index(name="avg_market_price")
)
variance_df = merged.merge(avg_prices, on="MATNR")

variance_df["variance_per_unit"] = (
    variance_df["NETPR"] - variance_df["avg_market_price"]
)
variance_df["potential_savings"] = (
    variance_df["variance_per_unit"] * variance_df["MENGE"]
)

savings_opps = variance_df[variance_df["potential_savings"] > 0]
total_variance_savings = savings_opps["potential_savings"].sum()

total_savings = maverick_spend * 0.10 + total_variance_savings

# --- UI LAYOUT ---

# 1. Opportunity Cards
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Savings Potential", f"${total_savings:,.2f}", "Estimated")
    st.caption("Combined impact of variance reduction & maverick control")

with col2:
    st.metric("Maverick Spend Volume", f"${maverick_spend:,.2f}")
    st.caption(f"{maverick_count} transactions off-contract")

with col3:
    st.metric("Price Variance Opportunity", f"${total_variance_savings:,.2f}")
    st.caption("Savings from normalizing prices to average")

st.markdown("---")

# 2. Opportunity Breakdown
c1, c2 = st.columns(2)

with c1:
    st.subheader("Maverick Spend by Category")
    mav_cat = merged[maverick_mask].merge(df_mara[["MATNR", "MATKL"]], on="MATNR")
    mav_agg = mav_cat.groupby("MATKL")["NETWR"].sum().reset_index()

    fig_mav = px.bar(
        mav_agg,
        x="NETWR",
        y="MATKL",
        orientation="h",
        title="Off-Contract Spend by Category",
        labels={"NETWR": "Spend ($)", "MATKL": "Category"},
    )
    st.plotly_chart(fig_mav, use_container_width=True)

with c2:
    st.subheader("Price Variance Distribution")
    fig_hist = px.histogram(
        savings_opps,
        x="potential_savings",
        nbins=30,
        title="Distribution of Overpayment Events",
        labels={"potential_savings": "Potential Savings ($)"},
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# 3. Detailed Action Table
st.subheader("Top Savings Opportunities")
top_savings = (
    savings_opps.groupby("MATNR")
    .agg({"potential_savings": "sum", "NETWR": "sum", "MENGE": "sum"})
    .reset_index()
)

top_savings = top_savings.merge(df_mara[["MATNR", "MAKTX"]], on="MATNR")
top_savings = top_savings.sort_values("potential_savings", ascending=False).head(15)

st.dataframe(
    top_savings[["MATNR", "MAKTX", "potential_savings", "NETWR"]],
    column_config={
        "potential_savings": st.column_config.ProgressColumn(
            "Savings Potential",
            format="$%.2f",
            min_value=0,
            max_value=top_savings["potential_savings"].max(),
        ),
        "NETWR": st.column_config.NumberColumn("Total Spend", format="$%.2f"),
    },
    use_container_width=True,
    hide_index=True,
)
