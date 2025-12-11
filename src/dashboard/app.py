import streamlit as st
from data_loader import load_data


st.set_page_config(page_title="Procurement Analytics", page_icon="📊", layout="wide")

st.session_state["data"] = load_data()

st.title("SAP Procurement Analytics Platform")
st.markdown("Select a module from the sidebar to begin.")
