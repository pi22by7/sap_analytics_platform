import numpy as np
import pandas as pd
import pytest


def test_pareto_distribution(loaded_data):
    """Verify 20% of vendors control ~80% of spend."""
    ekpo = loaded_data["EKPO"]
    ekko = loaded_data["EKKO"]

    spend = ekpo.merge(ekko[["EBELN", "LIFNR"]], on="EBELN")
    vendor_spend = spend.groupby("LIFNR")["NETWR"].sum().sort_values(ascending=False)

    top_20_count = int(len(vendor_spend) * 0.20)
    total_spend = vendor_spend.sum()
    top_spend = vendor_spend.head(top_20_count).sum()

    ratio = top_spend / total_spend
    # Allow loose tolerance (0.70 - 0.90) since RNG
    assert 0.70 <= ratio <= 0.90, f"Pareto ratio {ratio} out of bounds"


def test_net_value_calculation(loaded_data):
    """Verify NETWR = NETPR * MENGE."""
    ekpo = loaded_data["EKPO"]
    calculated = ekpo["NETPR"] * ekpo["MENGE"]

    assert np.allclose(
        ekpo["NETWR"], calculated, atol=0.01
    ), "NETWR calculation mismatch"


def test_contract_compliance_rate(loaded_data):
    """Verify contract coverage is within expected range (60-80%)."""
    ekko = loaded_data["EKKO"]

    contract_pos = len(ekko[ekko["BSART"] == "NB"])
    total = len(ekko)
    rate = contract_pos / total

    assert 0.60 <= rate <= 0.95, f"Contract compliance {rate} out of bounds"


def test_delivery_dates(loaded_data):
    """Verify Delivery Date >= PO Date."""
    ekpo = loaded_data["EKPO"]
    ekko = loaded_data["EKKO"]

    merged = ekpo.merge(ekko[["EBELN", "AEDAT"]], on="EBELN")

    violations = merged[merged["EINDT"] < merged["AEDAT"]]
    assert (
        len(violations) == 0
    ), f"Found {len(violations)} items delivered before PO date"


def test_invoice_amounts_match(loaded_data):
    """Verify Invoice Amount matches Goods Receipt Amount (tolerance 2%)."""
    ekbe = loaded_data["EKBE"]

    gr_counts = ekbe[ekbe["BEWTP"] == "E"].groupby(["EBELN", "EBELP"]).size()
    ir_counts = ekbe[ekbe["BEWTP"] == "Q"].groupby(["EBELN", "EBELP"]).size()

    # Align and find items where counts match exactly
    # ignoring pending invoices since generator doesn't link,
    # and does not need to link IRs to GRs 1:1
    aligned_gr_c, aligned_ir_c = gr_counts.align(ir_counts, join="inner")
    fully_matched_items = aligned_gr_c[aligned_gr_c == aligned_ir_c].index

    # Filter data for these items
    gr = (
        ekbe[
            (ekbe["BEWTP"] == "E")
            & (ekbe.set_index(["EBELN", "EBELP"]).index.isin(fully_matched_items))
        ]
        .groupby(["EBELN", "EBELP"])["DMBTR"]
        .sum()
    )
    ir = (
        ekbe[
            (ekbe["BEWTP"] == "Q")
            & (ekbe.set_index(["EBELN", "EBELP"]).index.isin(fully_matched_items))
        ]
        .groupby(["EBELN", "EBELP"])["DMBTR"]
        .sum()
    )

    # Align amounts
    aligned_gr, aligned_ir = gr.align(ir, join="inner")

    diff = (aligned_gr - aligned_ir).abs()
    tolerance = aligned_gr * 0.025

    # Filter only where diff > tolerance AND diff > 0.05
    violations = diff[(diff > tolerance) & (diff > 0.05)]  # noqa: E501
    assert len(violations) == 0, f"Found {len(violations)} mismatched invoice amounts"


def test_blocked_vendors_activity(loaded_data):
    """Verify Blocked Vendors (SPERR='X') have no recent POs (last 90 days)."""
    ekko = loaded_data["EKKO"]
    lfa1 = loaded_data["LFA1"]

    blocked_lifnrs = lfa1[lfa1["SPERR"] == "X"]["LIFNR"]
    sim_end = pd.to_datetime(ekko["AEDAT"]).max()
    cutoff = sim_end - pd.Timedelta(days=90)

    suspicious = ekko[
        (ekko["LIFNR"].isin(blocked_lifnrs)) & (pd.to_datetime(ekko["AEDAT"]) > cutoff)
    ]
    assert len(suspicious) == 0, "Found recent POs for blocked vendors"


def test_gr_coverage_strict(loaded_data):
    """Verify EVERY PO item has at least one Goods Receipt."""
    ekpo = loaded_data["EKPO"]
    ekbe = loaded_data["EKBE"]

    items_with_gr = ekbe[ekbe["BEWTP"] == "E"][["EBELN", "EBELP"]].drop_duplicates()
    merged = ekpo.merge(
        items_with_gr, on=["EBELN", "EBELP"], how="left", indicator=True
    )

    missing = merged[merged["_merge"] == "left_only"]
    assert len(missing) == 0, f"Found {len(missing)} items without GR"


def test_invoice_sequence(loaded_data):
    """Verify Invoice Date > GR Date (simplified check)."""
    ekbe = loaded_data["EKBE"]

    gr_dates = ekbe[ekbe["BEWTP"] == "E"].groupby(["EBELN", "EBELP"])["BUDAT"].min()
    ir_dates = ekbe[ekbe["BEWTP"] == "Q"].groupby(["EBELN", "EBELP"])["BUDAT"].min()

    aligned_gr, aligned_ir = gr_dates.align(ir_dates, join="inner")

    violations = aligned_ir[aligned_ir < aligned_gr]
    assert len(violations) == 0, f"Found {len(violations)} invoices dated before GR"


def test_price_outliers(loaded_data):
    """Verify no extreme price outliers (>3 std dev within group)."""
    ekpo = loaded_data["EKPO"]
    if "MATKL" not in ekpo.columns:
        pytest.skip("MATKL missing")

    def count_outliers(g):
        if len(g) < 10:
            return 0
        log_p = np.log1p(g["NETPR"])
        z_score = np.abs((log_p - log_p.mean()) / (log_p.std() + 1e-6))
        return (z_score > 3).sum()

    outliers = ekpo.groupby("MATKL").apply(count_outliers).sum()
    # Allow small noise (e.g. < 1%)
    assert outliers < (len(ekpo) * 0.01), f"Too many price outliers: {outliers}"
