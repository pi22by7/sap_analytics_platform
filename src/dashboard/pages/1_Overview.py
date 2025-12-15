import pandas as pd
import plotly.express as px
import streamlit as st
from utils import get_data

st.set_page_config(page_title="Overview", layout="wide")

data = get_data()
df_ekko = data["ekko"]
df_ekpo = data["ekpo"]

st.title("Executive Overview")

# Merge for Spend Analysis
spend_df = df_ekpo.merge(df_ekko[["EBELN", "AEDAT", "BSART", "LIFNR"]], on="EBELN")

# --- KPIs ---

# 1. Total Spend
total_spend = spend_df["NETWR"].sum()

# 2. Compliance (Contract vs Non-Contract)
contract_count = len(df_ekko[df_ekko["BSART"] == "NB"])
compliance_rate = (contract_count / len(df_ekko) * 100) if len(df_ekko) > 0 else 0

# 3. On-Time Delivery
df_ekbe = data["ekbe"]
gr_df = df_ekbe[df_ekbe["BEWTP"] == "E"].merge(
    df_ekpo[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"]
)

# On-Time Calculation
on_time_count = (gr_df["BUDAT"] <= gr_df["EINDT"]).sum()
otd_rate = (on_time_count / len(gr_df) * 100) if len(gr_df) > 0 else 0

# 4. Active Vendors
active_vendors = spend_df["LIFNR"].nunique()

# KPI Display
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Spend", f"${total_spend/1e6:.1f}M")
col2.metric("Compliance Rate", f"{compliance_rate:.1f}%")
col3.metric("On-Time Delivery", f"{otd_rate:.1f}%")
col4.metric("Active Vendors", f"{active_vendors}")

st.markdown("---")

# --- CHARTS ---

c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Monthly Spend Trend")
    spend_df["month"] = spend_df["AEDAT"].dt.to_period("M").astype(str)
    monthly_trend = spend_df.groupby("month")["NETWR"].sum().reset_index()

    fig = px.line(
        monthly_trend,
        x="month",
        y="NETWR",
        markers=True,
        labels={"month": "Month", "NETWR": "Spend Amount ($)"},
    )
    fig.update_layout(yaxis_tickprefix="$")
    st.plotly_chart(fig, width="stretch")

with c2:
    st.subheader("Spend by Category")
    cat_df = spend_df.drop(columns=["MATKL"], errors="ignore").merge(
        data["mara"][["MATNR", "MATKL"]], on="MATNR"
    )
    cat_spend = cat_df.groupby("MATKL")["NETWR"].sum().reset_index()

    fig = px.pie(cat_spend, values="NETWR", names="MATKL", hole=0.4)
    st.plotly_chart(fig, width="stretch")

# --- SAVINGS ESTIMATES ---

st.subheader("Estimated Savings Opportunities")

# 1. Maverick Spend: FO Orders
maverick_spend = spend_df[spend_df["BSART"] != "NB"]["NETWR"].sum()
sav_maverick = maverick_spend * 0.10  # Assumption

# 2. Consolidation: Materials > 3 vendors
mat_vendor_counts = spend_df.groupby("MATNR")["LIFNR"].nunique()
consolidation_candidates = (mat_vendor_counts > 3).sum()
sav_consolidation = consolidation_candidates * 5000  # Estimate: $5k savings

savings_data = pd.DataFrame(
    {
        "Type": ["Maverick Spend", "Vendor Consolidation"],
        "Potential Savings": [sav_maverick, sav_consolidation],
    }
)

fig = px.bar(
    savings_data,
    x="Type",
    y="Potential Savings",
    color="Type",
    labels={"Potential Savings": "Estimated Savings ($)"},
)
fig.update_layout(yaxis_tickprefix="$", showlegend=False)
st.plotly_chart(fig, width="stretch")

# --- TOP VENDORS ---
st.subheader("Top 5 Vendors by Spend")
top_vendors = spend_df.groupby("LIFNR")["NETWR"].sum().nlargest(5).reset_index()
top_vendors = top_vendors.merge(data["lfa1"][["LIFNR", "NAME1"]], on="LIFNR")

st.dataframe(
    top_vendors[["LIFNR", "NAME1", "NETWR"]].style.format({"NETWR": "${:,.2f}"}),
    width="stretch",
    column_config={
        "LIFNR": "Vendor ID",
        "NAME1": "Vendor Name",
        "NETWR": "Total Spend",
    },
)
