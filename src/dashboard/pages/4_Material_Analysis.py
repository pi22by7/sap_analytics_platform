import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Material Analysis", layout="wide")

if "data" not in st.session_state:
    st.stop()

data = st.session_state["data"]
df_mara = data["mara"]
df_ekpo = data["ekpo"]
df_ekko = data["ekko"]
df_lfa1 = data["lfa1"]

st.title("📦 Material & Category Analysis")

# --- 1. CATEGORY OVERVIEW ---
st.header("Category Overview")

cat_data = df_ekpo.merge(df_mara[["MATNR", "MATKL"]], on="MATNR")
cat_stats = (
    cat_data.groupby("MATKL").agg({"NETWR": "sum", "EBELN": "nunique"}).reset_index()
)
cat_stats.columns = ["Category", "Total Spend", "PO Count"]

col1, col2 = st.columns([2, 1])

with col1:
    fig_cat = px.bar(
        cat_stats,
        x="Category",
        y="Total Spend",
        color="Total Spend",
        title="Total Spend by Material Group",
        labels={"Total Spend": "Spend ($)"},
    )
    st.plotly_chart(fig_cat, use_container_width=True)

with col2:
    st.dataframe(
        cat_stats.style.format({"Total Spend": "${:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# --- 2. MATERIAL DRILL-DOWN ---
st.header("Material Deep Dive")

selected_cat = st.selectbox(
    "1. Select Category:", options=cat_stats["Category"].unique()
)

valid_materials = df_mara[df_mara["MATKL"] == selected_cat]
material_options = valid_materials["MATNR"] + " - " + valid_materials["MAKTX"]

selected_mat_str = st.selectbox("2. Select Material:", options=material_options)
selected_matnr = selected_mat_str.split(" - ")[0]

# --- 3. MATERIAL DETAILS ---
mat_txns = df_ekpo[df_ekpo["MATNR"] == selected_matnr].merge(
    df_ekko[["EBELN", "AEDAT", "LIFNR"]], on="EBELN"
)

if not mat_txns.empty:
    avg_price = mat_txns["NETPR"].mean()
    min_price = mat_txns["NETPR"].min()
    max_price = mat_txns["NETPR"].max()
    total_qty = mat_txns["MENGE"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg Unit Price", f"${avg_price:,.2f}")
    m2.metric("Price Range", f"${min_price:.2f} - ${max_price:.2f}")
    m3.metric("Total Qty Purchased", f"{total_qty:,.0f}")
    m4.metric("PO Count", f"{mat_txns['EBELN'].nunique()}")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Price History Trend")
        mat_txns = mat_txns.sort_values("AEDAT")
        fig_price = px.line(
            mat_txns,
            x="AEDAT",
            y="NETPR",
            title="Unit Price Fluctuation Over Time",
            markers=True,
        )
        st.plotly_chart(fig_price, use_container_width=True)

    with c2:
        st.subheader("Top Vendors for this Material")
        vendor_share = mat_txns.groupby("LIFNR")["MENGE"].sum().reset_index()
        vendor_share = vendor_share.merge(df_lfa1[["LIFNR", "NAME1"]], on="LIFNR")

        fig_share = px.pie(
            vendor_share,
            values="MENGE",
            names="NAME1",
            title="Volume Share by Vendor",
            hole=0.4,
        )
        st.plotly_chart(fig_share, use_container_width=True)

else:
    st.info("No purchase history found for this material.")
