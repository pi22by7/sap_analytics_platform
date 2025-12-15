import plotly.express as px
import streamlit as st
from utils import get_data

st.set_page_config(page_title="Performance", layout="wide")
data = get_data()

st.title("Performance Dashboard")

df_ekbe = data["ekbe"]
df_ekpo = data["ekpo"]

gr_df = df_ekbe[df_ekbe["BEWTP"] == "E"].merge(
    df_ekpo[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"]
)

gr_df["delay_days"] = (gr_df["BUDAT"] - gr_df["EINDT"]).dt.days
gr_df["is_late"] = gr_df["delay_days"] > 0

# --- KPIs ---
total_deliveries = len(gr_df)
late_count = gr_df["is_late"].sum()
otd_rate = (1 - (late_count / total_deliveries)) * 100 if total_deliveries > 0 else 0
avg_delay = gr_df[gr_df["is_late"]]["delay_days"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("Global OTD Rate", f"{otd_rate:.1f}%", help="Target: 95%")
col2.metric("Late Deliveries", f"{late_count}")
col3.metric("Avg Delay (When Late)", f"{avg_delay:.1f} Days")

st.markdown("---")

# --- TREND ---
st.subheader("OTD Trend (Monthly)")

gr_df["month"] = gr_df["BUDAT"].dt.to_period("M").astype(str)
trend = gr_df.groupby("month")["is_late"].mean().reset_index()
trend["otd_rate"] = (1 - trend["is_late"]) * 100

fig = px.line(
    trend,
    x="month",
    y="otd_rate",
    markers=True,
    title="On-Time Delivery % by Month",
    labels={"month": "Month", "otd_rate": "On-Time Rate (%)"},
)
# Add target line (95%)
fig.add_hline(y=95, line_dash="dash", line_color="green", annotation_text="Target")
fig.update_yaxes(range=[0, 105])
st.plotly_chart(fig, width="stretch")

# --- REASONS ---
st.subheader("Late Delivery Analysis")
st.caption("Categorization of late deliveries based on delay duration.")

late_df = gr_df[gr_df["is_late"]].copy()


def get_reason(days):
    if days <= 3:
        return "Minor Logistics Delay"
    if days <= 7:
        return "Production Delay"
    if days <= 14:
        return "Material Shortage"
    return "Major Disruption"


late_df["reason"] = late_df["delay_days"].apply(get_reason)
reason_counts = late_df["reason"].value_counts().reset_index()
reason_counts.columns = ["Reason", "Count"]

c1, c2 = st.columns(2)
with c1:
    fig = px.pie(
        reason_counts,
        values="Count",
        names="Reason",
        title="Late Reasons Distribution",
        hole=0.4,
    )
    st.plotly_chart(fig, width="stretch")
with c2:
    st.dataframe(
        reason_counts,
        width="stretch",
        column_config={"Reason": "Delay Category", "Count": "Frequency"},
    )

# --- VENDOR RANKING ---
st.subheader("Vendor Reliability Issues")
st.caption("Vendors with the highest late delivery rates (minimum 5 orders)")

# Merge LIFNR from EKKO for vendor stats
vendor_stats_df = gr_df.merge(data["ekko"][["EBELN", "LIFNR"]], on="EBELN")

vendor_stats = (
    vendor_stats_df.groupby("LIFNR")
    .agg(total=("EBELN", "count"), late=("is_late", "sum"))
    .reset_index()
)

vendor_stats = vendor_stats[vendor_stats["total"] >= 5]
vendor_stats["late_pct"] = (vendor_stats["late"] / vendor_stats["total"]) * 100

worst_vendors = vendor_stats.sort_values("late_pct", ascending=False).head(10)
worst_vendors = worst_vendors.merge(data["lfa1"][["LIFNR", "NAME1"]], on="LIFNR")

fig = px.bar(
    worst_vendors,
    x="late_pct",
    y="NAME1",
    orientation="h",
    title="Highest Late Delivery %",
    labels={"late_pct": "Late %", "NAME1": "Vendor"},
    color="late_pct",
    color_continuous_scale="Reds",
)
st.plotly_chart(fig, width="stretch")
