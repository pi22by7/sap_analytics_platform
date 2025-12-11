from typing import Literal

import streamlit as st


def kpi_card(
    title: str,
    value: str,
    delta: str | None = None,
    delta_color: Literal["normal", "inverse", "off"] = "normal",
):
    """
    Reusable KPI Card compatible with Streamlit's native metric.
    """
    st.metric(label=title, value=value, delta=delta, delta_color=delta_color)
