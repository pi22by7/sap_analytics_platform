import streamlit as st


def get_data():
    """
    Retrieves data from session state and applies global date filtering.

    Returns:
        dict: A dictionary of DataFrames,
            where 'ekko' is filtered by the selected date range.
    """
    if "data" not in st.session_state:
        st.warning("Data not found. Please run the main application first.")
        st.stop()

    data = st.session_state["data"]

    date_filter = st.session_state.get("date_filter")
    if date_filter:
        mask = (data["ekko"]["AEDAT"] >= date_filter["start"]) & (
            data["ekko"]["AEDAT"] <= date_filter["end"]
        )

        # Create a shallow copy to preserve original data structure
        filtered_data = data.copy()
        filtered_data["ekko"] = data["ekko"][mask]
        return filtered_data

    return data
