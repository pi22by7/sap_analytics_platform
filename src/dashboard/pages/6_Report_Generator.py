import sys
from pathlib import Path

import streamlit as st

# Add root to path so we can import the report generator eventually
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from pdf_report import generate_executive_report  # noqa: E402

st.set_page_config(page_title="Report Generator")

st.title("Executive Report Generator")
st.caption("Generate a PDF summary of the current dashboard metrics.")

if "data" not in st.session_state:
    st.error("Data not loaded.")
    st.stop()

if st.button("Generate PDF"):
    with st.spinner("Generating..."):
        try:
            # We'll save it to the reports folder
            output_path = "reports/Executive_Report.pdf"
            generate_executive_report(st.session_state["data"], output_path)

            st.success("Report generated!")

            with open(output_path, "rb") as f:
                st.download_button("Download PDF", f, file_name="Executive_Report.pdf")

        except Exception as e:
            st.error(f"Error: {e}")
