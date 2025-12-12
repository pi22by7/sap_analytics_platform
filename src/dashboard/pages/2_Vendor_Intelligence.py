import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Vendor Intelligence", layout="wide")

if "data" not in st.session_state:
    st.warning("Data not loaded. Run app.py")
    st.stop()

data = st.session_state["data"]
df_lfa1 = data["lfa1"]
df_ekko = data["ekko"]
df_ekpo = data["ekpo"]
df_ekbe = data["ekbe"]

st.title("Vendor Intelligence")

# SIDEBAR FILTERS
st.sidebar.header("Filter Vendors")
selected_country = st.sidebar.multiselect(
    "Country", options=df_lfa1["LAND1"].unique(), default=df_lfa1["LAND1"].unique()[:3]
)
selected_type = st.sidebar.multiselect(
    "Vendor Type", options=df_lfa1["KTOKK"].unique(), default=df_lfa1["KTOKK"].unique()
)

filtered_vendors = df_lfa1[
    (df_lfa1["LAND1"].isin(selected_country)) & (df_lfa1["KTOKK"].isin(selected_type))
]

# Search Panel
vendor_list = filtered_vendors["LIFNR"] + " - " + filtered_vendors["NAME1"]
selected_vendor_str = st.selectbox(
    "🔍 Search & Select Vendor to Analyze:", options=vendor_list
)
selected_lifnr = selected_vendor_str.split(" - ")[0]

# data prep for selected vendor
# filter vendor
vendor_pos = df_ekko[df_ekko["LIFNR"] == selected_lifnr]
vendor_items = df_ekpo[df_ekpo["EBELN"].isin(vendor_pos["EBELN"])]

# vendor metrics
total_spend = vendor_items["NETWR"].sum()
po_count = len(vendor_pos)
avg_order_val = total_spend / po_count if po_count > 0 else 0

# vendor on-time delivery calculation
vendor_gr = df_ekbe[
    (df_ekbe["EBELN"].isin(vendor_pos["EBELN"])) & (df_ekbe["BEWTP"] == "E")
].merge(vendor_items[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"])

if not vendor_gr.empty:
    on_time_pct = (vendor_gr["BUDAT"] <= vendor_gr["EINDT"]).mean() * 100
else:
    on_time_pct = 0.0

# --- UI LAYOUT ---

# 1. Vendor Profile
st.markdown("### 🏢 Vendor Profile")
col1, col2, col3, col4 = st.columns(4)

v_details = df_lfa1[df_lfa1["LIFNR"] == selected_lifnr].iloc[0]

with col1:
    st.caption("Location")
    st.write(f"{v_details['ORT01']}, {v_details['LAND1']}")
with col2:
    st.metric("Total Spend", f"${total_spend:,.0f}")
with col3:
    st.metric("Total POs", f"{po_count}")
with col4:
    color = "normal"
    if on_time_pct < 80:
        color = "inverse"
    st.metric("On-Time Delivery", f"{on_time_pct:.1f}%", delta_color=color)

st.divider()

# 2. spend trend and risk matrix
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Spend Trend")
    if not vendor_pos.empty:
        trend_df = vendor_items.merge(vendor_pos[["EBELN", "AEDAT"]], on="EBELN")
        trend_df["month"] = trend_df["AEDAT"].dt.to_period("M").astype(str)
        monthly = trend_df.groupby("month")["NETWR"].sum().reset_index()

        fig = px.area(monthly, x="month", y="NETWR", title="Monthly Spend Volume")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transaction history.")

with c2:
    st.subheader("Risk Matrix")
    risk_score = 100 - on_time_pct
    st.write(f"Risk Score: **{risk_score:.1f}/100**")
    st.progress(risk_score / 100)
    if v_details["SPERR"] == "X":
        st.error("⚠️ VENDOR BLOCKED")
    else:
        st.success("✅ Active Status")

# 3. top materials
st.subheader("Top Supplied Materials")
if not vendor_items.empty:
    top_mats = vendor_items.groupby("MATNR")["NETWR"].sum().reset_index()
    top_mats = top_mats.merge(data["mara"][["MATNR", "MAKTX"]], on="MATNR")
    top_mats = top_mats.sort_values("NETWR", ascending=False).head(10)

    st.dataframe(
        top_mats,
        column_config={
            "NETWR": st.column_config.NumberColumn("Spend", format="$%.2f"),
            "MAKTX": "Material Name",
        },
        use_container_width=True,
        hide_index=True,
    )
