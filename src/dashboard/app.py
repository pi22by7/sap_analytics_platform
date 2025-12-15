import pandas as pd
import streamlit as st
from data_loader import load_data

st.set_page_config(page_title="Procurement Analytics", page_icon="📊", layout="wide")

# data into session state
if "data" not in st.session_state:
    st.session_state["data"] = load_data()

# Global date filter
st.sidebar.title("Global Filters")
st.sidebar.markdown("---")

data = st.session_state["data"]
df_ekko = data["ekko"]

min_date = df_ekko["AEDAT"].min().date()
max_date = df_ekko["AEDAT"].max().date()

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    help="Filter all data by purchase order date range",
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    st.session_state["date_filter"] = {
        "start": pd.to_datetime(date_range[0]),
        "end": pd.to_datetime(date_range[1]),
    }
else:
    st.session_state["date_filter"] = {
        "start": pd.to_datetime(min_date),
        "end": pd.to_datetime(max_date),
    }

st.title("SAP Procurement Analytics Platform")
st.markdown("Select a module from the sidebar to begin.")

start_date = st.session_state["date_filter"]["start"].strftime("%Y-%m-%d")
end_date = st.session_state["date_filter"]["end"].strftime("%Y-%m-%d")
st.info(f"📅 Viewing data from {start_date} to {end_date}")
