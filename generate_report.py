import pandas as pd
import sys
from pathlib import Path

sys.path.append("src/dashboard")
from pdf_report import generate_executive_report


def load_data():
    data_dir = Path("data")
    if not data_dir.exists():
        print("Error: data/ directory not found. Run generator first.")
        sys.exit(1)

    print("Loading data...")
    return {
        "lfa1": pd.read_parquet(data_dir / "LFA1.parquet"),
        "mara": pd.read_parquet(data_dir / "MARA.parquet"),
        "ekko": pd.read_parquet(data_dir / "EKKO.parquet"),
        "ekpo": pd.read_parquet(data_dir / "EKPO.parquet"),
        "ekbe": pd.read_parquet(data_dir / "EKBE.parquet"),
        "contracts": (
            pd.read_parquet(data_dir / "VENDOR_CONTRACTS.parquet")
            if (data_dir / "VENDOR_CONTRACTS.parquet").exists()
            else pd.DataFrame()
        ),
    }


if __name__ == "__main__":
    data = load_data()
    output = "procurement_report.pdf"
    print(f"Generating report to {output}...")
    generate_executive_report(data, output)
    print("Done.")
