def test_foreign_keys_exist(loaded_data):
    """Ensure all transactional keys exist in master data."""
    lfa1_ids = set(loaded_data["LFA1"]["LIFNR"])
    mara_ids = set(loaded_data["MARA"]["MATNR"])
    ekko_ids = set(loaded_data["EKKO"]["EBELN"])

    # EKKO -> LFA1
    ekko_vendors = set(loaded_data["EKKO"]["LIFNR"])
    assert ekko_vendors.issubset(lfa1_ids), "Found POs with missing Vendors"

    # EKPO -> MARA
    ekpo_mats = set(loaded_data["EKPO"]["MATNR"])
    assert ekpo_mats.issubset(mara_ids), "Found Items with missing Materials"

    # EKPO -> EKKO
    ekpo_headers = set(loaded_data["EKPO"]["EBELN"])
    assert ekpo_headers.issubset(ekko_ids), "Found Items with missing PO Headers"
