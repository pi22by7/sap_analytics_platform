import pytest
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")


@pytest.fixture(scope="session")
def loaded_data():
    """Load all datasets once for the test session."""
    data = {}
    tables = ["LFA1", "MARA", "EKKO", "EKPO", "EKBE", "VENDOR_CONTRACTS"]
    for t in tables:
        file_path = DATA_DIR / f"{t}.parquet"
        if file_path.exists():
            data[t] = pd.read_parquet(file_path)
        else:
            pytest.fail(f"Data file missing: {file_path}")
    return data


@pytest.fixture
def mock_data():
    """Create minimal valid dataframes for unit tests."""
    lfa1 = pd.DataFrame(
        {
            "LIFNR": ["V01", "V02", "V03"],
            "NAME1": ["Vendor A", "Vendor B", "Vendor C"],
            "KTOKK": ["STD", "PREF", "STD"],
            "SPERR": ["", "", "X"],
        }
    )

    mara = pd.DataFrame(
        {
            "MATNR": ["M01", "M02"],
            "MATKL": ["ELECT", "OFFICE"],
            "base_price": [100.0, 50.0],
        }
    )

    ekko = pd.DataFrame(
        {
            "EBELN": ["P01", "P02"],
            "LIFNR": ["V01", "V02"],
            "BSART": ["NB", "NB"],
            "AEDAT": pd.to_datetime(["2023-01-01", "2023-01-02"]),
        }
    )

    ekpo = pd.DataFrame(
        {
            "EBELN": ["P01", "P01", "P02"],
            "EBELP": [10, 20, 10],
            "MATNR": ["M01", "M02", "M01"],
            "MENGE": [10, 5, 20],
            "NETPR": [90.0, 45.0, 85.0],
            "NETWR": [900.0, 225.0, 1700.0],
            "EINDT": pd.to_datetime(["2023-01-10", "2023-01-15", "2023-01-20"]),
        }
    )

    return {"LFA1": lfa1, "MARA": mara, "EKKO": ekko, "EKPO": ekpo}
