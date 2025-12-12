import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Performance Dashboard", layout="wide")

if "data" not in st.session_state:
    st.stop()

data = st.session_state["data"]
df_ekbe = data["ekbe"]
df_ekpo = data["ekpo"]
df_lfa1 = data["lfa1"]
df_ekko = data["ekko"]

st.title("🚀 Performance Dashboard")

# data prep
gr_df = df_ekbe[df_ekbe["BEWTP"] == "E"].merge(
    df_ekpo[["EBELN", "EBELP", "EINDT", "LIFNR", "MATNR"]], on=["EBELN", "EBELP"]
)

# Calculate Delay (Days)
# Posting Date - Delivery Deadline
gr_df["delay_days"] = (gr_df["BUDAT"] - gr_df["EINDT"]).dt.days
gr_df["is_late"] = gr_df["delay_days"] > 0

total_deliveries = len(gr_df)
late_deliveries = gr_df["is_late"].sum()
global_otd = 100 - (late_deliveries / total_deliveries * 100)
avg_delay = gr_df[gr_df["is_late"]]["delay_days"].mean()  # avg of late items

# --- KPI ROW ---
col1, col2, col3 = st.columns(3)

with col1:
    # Gauge Chart for OTD
    fig_gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=global_otd,
            title={"text": "Global On-Time Delivery %"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#2ecc71" if global_otd > 90 else "#f1c40f"},
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
        )
    )
    fig_gauge.update_layout(height=250, margin={"t": 0, "b": 0, "l": 0, "r": 0})
    st.plotly_chart(fig_gauge, use_container_width=True)

with col2:
    st.metric("Total Deliveries Tracked", f"{total_deliveries:,}")
    st.metric(
        "Late Deliveries",
        f"{late_deliveries:,}",
        delta="-High Risk" if late_deliveries > 0 else "Good",
        delta_color="inverse",
    )

with col3:
    st.metric("Avg Delay (When Late)", f"{avg_delay:.1f} Days")
    st.caption("Average slippage on missed deadlines")

st.divider()

# --- VENDOR PERFORMANCE RANKING ---
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("Worst Performing Vendors (Bottom 10)")

    vendor_perf = (
        gr_df.groupby("LIFNR").agg({"is_late": ["count", "sum"]}).reset_index()
    )
    vendor_perf.columns = ["LIFNR", "total_txns", "late_txns"]

    # filter to rule out noise
    vendor_perf = vendor_perf[vendor_perf["total_txns"] > 5]

    vendor_perf["otd_pct"] = 100 - (
        vendor_perf["late_txns"] / vendor_perf["total_txns"] * 100
    )

    # get Name
    vendor_perf = vendor_perf.merge(df_lfa1[["LIFNR", "NAME1"]], on="LIFNR")

    bottom_10 = vendor_perf.sort_values("otd_pct", ascending=True).head(10)

    fig_bar = px.bar(
        bottom_10,
        x="otd_pct",
        y="NAME1",
        orientation="h",
        title="Lowest OTD % (Vendors > 5 Orders)",
        labels={"otd_pct": "On-Time %", "NAME1": "Vendor"},
        color="otd_pct",
        color_continuous_scale="RdYlGn",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with c2:
    st.subheader("Late Deliveries Distribution")
    late_only = gr_df[gr_df["is_late"]]
    fig_hist = px.histogram(
        late_only,
        x="delay_days",
        nbins=20,
        title="How late are the late orders?",
        labels={"delay_days": "Days Overdue"},
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# --- PERFORMANCE HEATMAP ---
st.subheader("Vendor Performance Heatmap (Last 12 Months)")
st.caption(
    "Visualizing OTD% trends. Red cells indicate months with poor delivery performance."
)

# prep: only top 20 vendors for readablity
top_vendors = df_ekpo.groupby("LIFNR")["NETWR"].sum().nlargest(20).index
heatmap_data = gr_df[gr_df["LIFNR"].isin(top_vendors)].copy()

heatmap_data["month"] = heatmap_data["BUDAT"].dt.to_period("M").astype(str)

heatmap_agg = (
    heatmap_data.groupby(["LIFNR", "month"])
    .agg({"is_late": lambda x: 100 - (x.sum() / len(x) * 100)})
    .reset_index()
)
heatmap_agg.columns = ["LIFNR", "month", "otd_pct"]

heatmap_agg = heatmap_agg.merge(df_lfa1[["LIFNR", "NAME1"]], on="LIFNR")

fig_heat = px.density_heatmap(
    heatmap_agg,
    x="month",
    y="NAME1",
    z="otd_pct",
    histfunc="avg",
    color_continuous_scale="RdYlGn",
    range_color=[50, 100],  # <50 is very red
    title="OTD % by Vendor and Month",
)
st.plotly_chart(fig_heat, use_container_width=True)
