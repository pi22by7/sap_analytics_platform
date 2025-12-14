import streamlit as st
import plotly.express as px
from utils import get_data

st.set_page_config(page_title="Material Analysis", layout="wide")
data = get_data()

st.title("Material Analysis")

df_mara = data["mara"]
df_ekpo = data["ekpo"]
df_ekko = data["ekko"]

merged = df_ekpo.merge(df_ekko[["EBELN", "AEDAT"]], on="EBELN")
merged = merged.merge(df_mara[["MATNR", "MATKL", "MAKTX"]], on="MATNR")

# --- CATEGORY OVERVIEW ---
st.header("Spend by Category")

# Aggregation
cat_summary = merged.groupby("MATKL")["NETWR"].sum().reset_index()

c1, c2 = st.columns(2)
with c1:
    fig = px.bar(
        cat_summary,
        x="MATKL",
        y="NETWR",
        title="Total Spend per Category",
        labels={"MATKL": "Material Group", "NETWR": "Total Spend ($)"},
    )
    fig.update_layout(yaxis_tickprefix="$")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.dataframe(
        cat_summary.style.format({"NETWR": "${:,.2f}"}),
        use_container_width=True,
        column_config={"MATKL": "Category", "NETWR": "Spend Amount"},
    )

# --- DRILL DOWN ---
st.markdown("---")
st.header("Material Deep Dive")

cats = sorted(merged["MATKL"].unique())
sel_cat = st.selectbox("Select Category", cats)

cat_data = merged[merged["MATKL"] == sel_cat]

mats = cat_data["MATNR"].unique()


def mat_fmt(matnr):
    row = df_mara[df_mara["MATNR"] == matnr]
    if not row.empty:
        return f"{matnr} - {row['MAKTX'].iloc[0]}"
    return matnr


sel_mat = st.selectbox("Select Material", mats, format_func=mat_fmt)

# --- MATERIAL STATS ---
mat_txns = cat_data[cat_data["MATNR"] == sel_mat]

if not mat_txns.empty:
    avg_price = mat_txns["NETPR"].mean()
    total_qty = mat_txns["MENGE"].sum()
    spend = mat_txns["NETWR"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Spend", f"${spend:,.2f}")
    c2.metric("Total Qty", f"{total_qty:,.0f}")
    c3.metric("Avg Unit Price", f"${avg_price:,.2f}")

    st.subheader("Price History")
    mat_txns = mat_txns.sort_values("AEDAT")
    fig = px.line(
        mat_txns,
        x="AEDAT",
        y="NETPR",
        markers=True,
        title="Unit Price Fluctuation",
        labels={"AEDAT": "Date", "NETPR": "Unit Price ($)"},
    )
    fig.update_layout(yaxis_tickprefix="$")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("No transactions found for this material.")
