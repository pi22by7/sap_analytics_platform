import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")


@st.cache_data
def load_data():
    """Loads all parquet files into memory once."""
    try:
        return {
            "lfa1": pd.read_parquet(DATA_DIR / "LFA1.parquet"),
            "mara": pd.read_parquet(DATA_DIR / "MARA.parquet"),
            "contracts": pd.read_parquet(DATA_DIR / "VENDOR_CONTRACTS.parquet"),
            "ekko": pd.read_parquet(DATA_DIR / "EKKO.parquet"),
            "ekpo": pd.read_parquet(DATA_DIR / "EKPO.parquet"),
            "ekbe": pd.read_parquet(DATA_DIR / "EKBE.parquet"),
        }
    except FileNotFoundError as e:
        st.error(f"Could not load data: {e}")
        st.stop()
