"""
Configuration rules for Data Quality Framework.
"""

# Tables to load
REQUIRED_TABLES = ["LFA1", "MARA", "EKKO", "EKPO", "EKBE", "VENDOR_CONTRACTS"]

# Field Constraints (Length, Type)
SCHEMA_RULES = {
    "LFA1": {
        "required": ["LIFNR", "NAME1", "LAND1", "KTOKK", "SPERR"],
        "constraints": {"LIFNR": 10, "LAND1": 2},  # Max length
    },
    "MARA": {
        "required": ["MATNR", "MATKL", "MEINS", "BRGEW"],
        "constraints": {"MATNR": 10, "MATKL": 9},
    },
    "EKKO": {
        "required": ["EBELN", "LIFNR", "BSART", "AEDAT", "WAERS"],
        "constraints": {"EBELN": 10, "WAERS": 3},
        "iso_currency": "WAERS",  # Special flag for ISO check
    },
    "EKPO": {
        "required": ["EBELN", "EBELP", "MATNR", "MENGE", "NETPR", "NETWR"],
        "constraints": {"EBELN": 10},
    },
    "EKBE": {
        "required": ["EBELN", "EBELP", "BEWTP", "DMBTR", "BUDAT"],
        "constraints": {"EBELN": 10},
    },
    "VENDOR_CONTRACTS": {
        "required": ["CONTRACT_ID", "LIFNR", "MATNR", "VALID_FROM", "VALID_TO"],
        "constraints": {"LIFNR": 10},
    },
}

# Thresholds for Business Rules
THRESHOLDS = {
    "netwr_tolerance": 0.01,  # 1% tolerance
    "contract_price_tol": 0.05,  # 5% tolerance
    "invoice_amt_tol": 0.02,  # 2% tolerance
    "pareto_share": (0.70, 0.90),  # Target 80% +/- 10%
    "contract_rate": (0.60, 0.80),  # Target 60-80%
    "late_delivery_rate": (0.20, 0.35),  # Target 20-30%
}
