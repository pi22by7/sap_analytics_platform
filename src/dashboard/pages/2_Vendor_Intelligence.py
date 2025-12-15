import plotly.express as px
import streamlit as st
from utils import get_data

st.set_page_config(page_title="Vendor Intelligence", layout="wide")
data = get_data()

st.title("Vendor Intelligence")

# --- FILTERS ---
st.sidebar.header("Filter Vendors")

df_lfa1 = data["lfa1"]
all_countries = sorted(df_lfa1["LAND1"].unique())
sel_countries = st.sidebar.multiselect(
    "Country", all_countries, default=all_countries[:3]
)

vendors_filtered = df_lfa1[df_lfa1["LAND1"].isin(sel_countries)]
valid_vendors = vendors_filtered["LIFNR"].unique()

# --- PREPARE METRICS ---
df_ekpo = data["ekpo"]
df_ekko = data["ekko"]

mask_vendor = df_ekko["LIFNR"].isin(valid_vendors)
filtered_ekko = df_ekko[mask_vendor]

vendor_spend = (
    df_ekpo.merge(filtered_ekko[["EBELN", "LIFNR"]], on="EBELN")
    .groupby("LIFNR")["NETWR"]
    .sum()
    .reset_index()
)

# --- Price Competitiveness ---
# Calculate market average price per material
avg_market_price = (
    df_ekpo.groupby("MATNR")["NETPR"].mean().reset_index(name="market_price")
)
ekpo_with_market = df_ekpo.merge(avg_market_price, on="MATNR")
ekpo_with_market = ekpo_with_market.merge(df_ekko[["EBELN", "LIFNR"]], on="EBELN")

# (Market Price / Vendor Price) * 100. >100 is good (cheaper).
ekpo_with_market["competitiveness"] = (
    ekpo_with_market["market_price"] / ekpo_with_market["NETPR"]
) * 100
vendor_competitiveness = (
    ekpo_with_market.groupby("LIFNR")["competitiveness"].mean().reset_index()
)

# --- Delivery Performance & Lead Time ---
df_ekbe = data["ekbe"]

gr_df = df_ekbe[df_ekbe["BEWTP"] == "E"].merge(
    df_ekpo[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"]
)

gr_df = gr_df.merge(df_ekko[["EBELN", "AEDAT", "LIFNR"]], on="EBELN")

gr_df["is_late"] = gr_df["BUDAT"] > gr_df["EINDT"]
gr_df["lead_time"] = (gr_df["BUDAT"] - gr_df["AEDAT"]).dt.days

vendor_perf = (
    gr_df.groupby("LIFNR")
    .agg(
        total_deliveries=("EBELN", "count"),
        late_deliveries=("is_late", "sum"),
        avg_lead_time=("lead_time", "mean"),
    )
    .reset_index()
)

vendor_perf["otd_rate"] = (
    1 - (vendor_perf["late_deliveries"] / vendor_perf["total_deliveries"])
) * 100

summary = vendors_filtered.merge(vendor_spend, on="LIFNR", how="left")
summary = summary.merge(vendor_perf, on="LIFNR", how="left")
summary = summary.merge(vendor_competitiveness, on="LIFNR", how="left")

summary["NETWR"] = summary["NETWR"].fillna(0)
summary["otd_rate"] = summary["otd_rate"].fillna(100)
summary["competitiveness"] = summary["competitiveness"].fillna(100)
summary["avg_lead_time"] = summary["avg_lead_time"].fillna(0)

# --- MAIN SCATTER PLOT ---
st.subheader("Vendor Performance Matrix")
st.caption(
    "Scatter plot analyzing Spend (Y-axis) versus On-Time Delivery Performance "
    "(X-axis). Strategic quadrant analysis aids in identifying high-risk, "
    "high-spend suppliers."
)

fig = px.scatter(
    summary,
    x="otd_rate",
    y="NETWR",
    size="NETWR",
    hover_name="NAME1",
    title="Vendor Matrix: Spend vs. Performance",
    labels={"otd_rate": "On-Time Delivery (%)", "NETWR": "Total Spend ($)"},
    color="NETWR",
    color_continuous_scale="Viridis",
)

fig.add_vline(
    x=90, line_dash="dash", line_color="green", annotation_text="Target (90%)"
)
fig.add_hline(
    y=summary["NETWR"].mean(),
    line_dash="dash",
    line_color="grey",
    annotation_text="Avg Spend",
)
fig.update_layout(yaxis_tickprefix="$")
st.plotly_chart(fig, width="stretch")

# --- DRILL DOWN ---
st.markdown("---")
st.subheader("Detailed Vendor Profile")


def fmt_func(lifnr):
    name = df_lfa1[df_lfa1["LIFNR"] == lifnr]["NAME1"].iloc[0]
    return f"{lifnr} - {name}"


available_vendors = summary[summary["NETWR"] > 0]["LIFNR"].unique()

if len(available_vendors) > 0:
    sel_lifnr = st.selectbox(
        "Select Vendor for Analysis", available_vendors, format_func=fmt_func
    )

    v_stats = summary[summary["LIFNR"] == sel_lifnr].iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Spend", f"${v_stats['NETWR']:,.2f}")
    c2.metric("On-Time Rate", f"{v_stats['otd_rate']:.1f}%")
    c3.metric("Avg Lead Time", f"{v_stats['avg_lead_time']:.1f} Days")
    c4.metric(
        "Price Comp. Score",
        f"{v_stats['competitiveness']:.1f}",
        help="100 = Avg Market Price. >100 = Cheaper.",
    )

    st.markdown("#### Top Supplied Materials")
    v_pos = df_ekpo[
        df_ekpo["EBELN"].isin(
            filtered_ekko[filtered_ekko["LIFNR"] == sel_lifnr]["EBELN"]
        )
    ]
    top_mats = v_pos.groupby("MATNR")["NETWR"].sum().nlargest(5).reset_index()
    top_mats = top_mats.merge(data["mara"], on="MATNR")

    st.dataframe(
        top_mats[["MATNR", "MAKTX", "NETWR"]].style.format({"NETWR": "${:,.2f}"}),
        width="stretch",
        column_config={
            "MATNR": "Material ID",
            "MAKTX": "Material Description",
            "NETWR": "Spend",
        },
    )

else:
    st.info("No active vendors found matching the current filters.")
