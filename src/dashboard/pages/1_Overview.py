import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Executive Overview", layout="wide")

if "data" not in st.session_state:
    st.error("Data not found. Please run the main app first.")
    st.stop()

data = st.session_state["data"]
df_ekko = data["ekko"]
df_ekpo = data["ekpo"]
df_ekbe = data["ekbe"]
df_mara = data["mara"]
df_lfa1 = data["lfa1"]

st.title("Executive Overview")

# prep for efficiency, merge EKPO and EKKO once

spend_df = df_ekpo.merge(df_ekko[["EBELN", "AEDAT", "BSART", "LIFNR"]], on="EBELN")
spend_df["year"] = spend_df["AEDAT"].dt.year
spend_df["month"] = spend_df["AEDAT"].dt.to_period("M")

# kpi 1: ytd vs py
current_year = spend_df["year"].max()
prev_year = current_year - 1

total_spend_cy = spend_df[spend_df["year"] == current_year]["NETWR"].sum()
total_spend_py = spend_df[spend_df["year"] == prev_year]["NETWR"].sum()
spend_delta = ((total_spend_cy - total_spend_py) / total_spend_py) * 100

# kpi 2: contract compliance
total_pos = len(df_ekko)
contract_pos = len(df_ekko[df_ekko["BSART"] == "NB"])
compliance_rate = (contract_pos / total_pos) * 100

# kpi 3: on-time delivery
gr_df = df_ekbe[df_ekbe["BEWTP"] == "E"].copy()
otd_df = gr_df.merge(df_ekpo[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"])


otd_df["is_on_time"] = otd_df["BUDAT"] <= otd_df["EINDT"]
otd_rate = otd_df["is_on_time"].mean() * 100

# kpi 4: active vendors
active_vendors_cy = spend_df[spend_df["year"] == current_year]["LIFNR"].nunique()
active_vendors_py = spend_df[spend_df["year"] == prev_year]["LIFNR"].nunique()
vendor_delta = ((active_vendors_cy - active_vendors_py) / active_vendors_py) * 100


# UI

# cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Spend (YTD)", f"${total_spend_cy/1e6:.1f}M", f"{spend_delta:.1f}%")

with col2:
    st.metric("Contract Compliance", f"{compliance_rate:.1f}%", "Target: 70%")

with col3:
    st.metric("On-Time Delivery", f"{otd_rate:.1f}%", f"Target: 95%")

with col4:
    st.metric("Active Vendors", f"{active_vendors_cy}", f"{vendor_delta:.1f}%")

st.markdown("---")

# charts
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Monthly Spend Trend")
    monthly_spend = spend_df.groupby("month")["NETWR"].sum().reset_index()
    monthly_spend["month"] = monthly_spend["month"].astype(str)

    fig_trend = px.line(
        monthly_spend,
        x="month",
        y="NETWR",
        labels={"NETWR": "Spend ($)", "month": "Date"},
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with col_right:
    st.subheader("Spend by Category")
    cat_spend = spend_df.merge(df_mara[["MATNR", "MATKL"]], on="MATNR")
    cat_agg = cat_spend.groupby("MATKL")["NETWR"].sum().reset_index()

    fig_pie = px.pie(cat_agg, values="NETWR", names="MATKL", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)

# top vendors table
st.subheader("Top 5 Vendors by Spend")
top_vendors = spend_df.groupby("LIFNR")["NETWR"].sum().nlargest(5).reset_index()
top_vendors = top_vendors.merge(df_lfa1[["LIFNR", "NAME1", "LAND1"]], on="LIFNR")

st.dataframe(top_vendors.style.format({"NETWR": "${:,.2f}"}), use_container_width=True)
