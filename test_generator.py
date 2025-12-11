import numpy as np
import pandas as pd
from typing import cast, Any
from src.generator.sap_generator import SAPDataGenerator, GeneratorConfig

config = GeneratorConfig(seed=42, num_vendors=1000, num_materials=5000, num_pos=10000)

gen = SAPDataGenerator(config)
gen._generate_lfa1()

assert gen.lfa1 is not None, "Failed to generate LFA1 data"

print("=" * 80)
print("LFA1")
print("=" * 80)
print(f"\nTotal vendors generated: {len(gen.lfa1)}")
print("\nFirst 10 vendors:")
print(gen.lfa1.head(10))

print("\n\nData Types:")
print(gen.lfa1.dtypes)

print("\n\nBasic Statistics:")
print(gen.lfa1.describe(include="all"))

print("\n" + "=" * 80)

# pareto
top_20_pct = int(len(gen.lfa1) * 0.20)
top_vendors = gen.lfa1.head(top_20_pct)
print("\n1. Pareto Distribution Check:")
top_100_count = (top_vendors["spend_weight"] == 100).sum()
bottom_1_count = (gen.lfa1["spend_weight"] == 1).sum()
print(
    f"    Top 20% vendors with weight=100: " f"{top_100_count} (expected: {top_20_pct})"
)
print(
    f"    Bottom 80% vendors with weight=1: "
    f"{bottom_1_count} (expected: {len(gen.lfa1) - top_20_pct})"
)

# KTOKK distribution
print("\n2. Vendor Types (KTOKK):")
ktokk_counts = gen.lfa1["KTOKK"].value_counts()
pref_count = ktokk_counts.get("PREF", 0)
std_count = ktokk_counts.get("STD", 0)
print(f"   PREF: {pref_count} " f"({pref_count/len(gen.lfa1)*100:.1f}%)")
print(f"   STD: {std_count} " f"({std_count/len(gen.lfa1)*100:.1f}%)")

# Check correlation between spend_weight and KTOKK
top_vendors_pref = top_vendors["KTOKK"].value_counts().get("PREF", 0)
bottom_vendors = gen.lfa1[gen.lfa1["spend_weight"] == 1]
bottom_vendors_pref = bottom_vendors["KTOKK"].value_counts().get("PREF", 0)
print(
    f"   Top vendors that are PREF: {top_vendors_pref}/{len(top_vendors)} "
    f"({top_vendors_pref/len(top_vendors)*100:.1f}%)"
)
print(
    f"   Bottom vendors that are PREF: "
    f"{bottom_vendors_pref}/{len(bottom_vendors)} "
    f"({bottom_vendors_pref/len(bottom_vendors)*100:.1f}%)"
)

# Check blocked status
print("\n3. Blocked Vendors (SPERR):")
blocked_count = (gen.lfa1["SPERR"] == "X").sum()
active_count = len(gen.lfa1) - blocked_count
print(f"   Blocked: {blocked_count} " f"({blocked_count/len(gen.lfa1)*100:.1f}%)")
print(f"   Active: {active_count} " f"({active_count/len(gen.lfa1)*100:.1f}%)")

# Check performance bias distribution
print("\n4. Performance Bias (perf_bias):")
print(f"   Mean: {gen.lfa1['perf_bias'].mean():.2f} (should be ~0)")
print(f"   Std: {gen.lfa1['perf_bias'].std():.2f} (should be ~2)")
print(f"   Min: {gen.lfa1['perf_bias'].min():.2f}")
print(f"   Max: {gen.lfa1['perf_bias'].max():.2f}")

# Check for duplicates
print("\n5. Data Quality:")
print(f"   Duplicate LIFNR: {gen.lfa1['LIFNR'].duplicated().sum()}")
print(f"   Null values: {gen.lfa1.isnull().sum().sum()}")

print("\n" + "=" * 80)

# Generate MARA
gen._generate_mara()

assert gen.mara is not None, "Failed to generate MARA data"

print("\n" + "=" * 80)
print("MARA")
print("=" * 80)
print(f"\nTotal materials generated: {len(gen.mara)}")
print("\nFirst 10 materials:")
print(gen.mara.head(10))

print("\n\nData Types:")
print(gen.mara.dtypes)

print("\n\nBasic Statistics:")
print(gen.mara.describe(include="all"))

print("\n" + "=" * 80)
print("BUSINESS RULE VALIDATION - MARA")
print("=" * 80)

# Check category distribution
print("\n1. Material Category Distribution (MATKL):")
matkl_counts = gen.mara["MATKL"].value_counts()
for category, count in matkl_counts.items():
    pct = count / len(gen.mara) * 100
    print(f"   {category}: {count} ({pct:.1f}%)")
    if pct > 40:
        print("      WARNING: Exceeds 40% constraint!")

# Check material types match categories
print("\n2. Material Type (MTART) Mapping:")
mtart_by_matkl = cast(Any, gen.mara.groupby("MATKL"))["MTART"].unique()
for category, mtypes in mtart_by_matkl.items():
    print(f"   {category}: {', '.join(mtypes)}")

# Check price ranges by category
print("\n3. Base Price Ranges by Category:")
for category in gen.mara["MATKL"].unique():
    cat_data = gen.mara[gen.mara["MATKL"] == category]
    print(f"   {category}:")
    print(f"      Min: ${cat_data['base_price'].min():.2f}")
    print(f"      Max: ${cat_data['base_price'].max():.2f}")
    print(f"      Mean: ${cat_data['base_price'].mean():.2f}")
    median_price = cat_data["base_price"].median()
    print(f"      Median: ${median_price:.2f}")

# Check weight distribution
print("\n4. Weight Distribution:")
zero_weight = (gen.mara["BRGEW"] == 0).sum()
nonzero_weight = (gen.mara["BRGEW"] > 0).sum()
print(f"   Materials with zero weight (SERV): {zero_weight}")
print(f"   Materials with weight > 0: {nonzero_weight}")
nonzero_mara = gen.mara[gen.mara["BRGEW"] > 0]
print(f"   Avg gross weight (non-zero): " f"{nonzero_mara['BRGEW'].mean():.2f} kg")
weight_ratio = nonzero_mara["NTGEW"] / nonzero_mara["BRGEW"]
print(f"   Net/Gross weight ratio (non-zero): " f"{weight_ratio.mean():.2%}")

# Check UOM distribution
print("\n5. Unit of Measure (MEINS) Distribution:")
meins_counts = gen.mara["MEINS"].value_counts()
for uom, count in meins_counts.items():
    print(f"   {uom}: {count} ({count/len(gen.mara)*100:.1f}%)")

# Check data quality
print("\n6. Data Quality:")
print(f"   Duplicate MATNR: {gen.mara['MATNR'].duplicated().sum()}")
print(f"   Null values: {gen.mara.isnull().sum().sum()}")
print(f"   Total records: {len(gen.mara)} " f"(expected: {config.num_materials})")

# Verify shuffle worked
print("\n7. Shuffle Verification:")
print(f"   First 5 MATNRs: {gen.mara['MATNR'].head().tolist()}")
print(f"   First 5 MATKLs: {gen.mara['MATKL'].head().tolist()}")
print("   (Should show mixed categories, not all ELECT)")

print("\n" + "=" * 80)

# Generate CONTRACTS
gen._generate_contracts()

assert gen.contracts is not None, "Failed to generate CONTRACTS data"

print("\n" + "=" * 80)
print("CONTRACTS - Vendor Contracts")
print("=" * 80)
print(f"\nTotal contracts generated: {len(gen.contracts)}")
print("\nFirst 10 contracts:")
print(gen.contracts.head(10))

print("\n\nData Types:")
print(gen.contracts.dtypes)

print("\n\nBasic Statistics:")
print(gen.contracts.describe(include="all"))

print("\n" + "=" * 80)
print("BUSINESS RULE VALIDATION - CONTRACTS")
print("=" * 80)

# Check uniqueness of vendor-material pairs
print("\n1. Vendor-Material Pair Uniqueness:")
duplicates = gen.contracts.duplicated(subset=["LIFNR", "MATNR"]).sum()
print(f"   Duplicate (LIFNR, MATNR) pairs: {duplicates} (expected: 0)")
print(f"   Unique pairs: {len(gen.contracts)}")

# Check vendor distribution (should be Pareto-weighted)
print("\n2. Vendor Distribution in Contracts:")
vendor_contract_counts = gen.contracts["LIFNR"].value_counts()
print(f"   Vendors with contracts: {len(vendor_contract_counts)}")
print("   Top 5 vendors by contract count:")
for vendor, count in vendor_contract_counts.head().items():
    v_data = gen.lfa1[gen.lfa1["LIFNR"] == vendor]
    vendor_type = v_data["KTOKK"].values[0]
    spend_weight = v_data["spend_weight"].values[0]
    print(
        f"      {vendor}: {count} contracts "
        f"(Type: {vendor_type}, Weight: {spend_weight})"
    )

# Check contract price discount (should be 5-15% off base price)
print("\n3. Contract Pricing (Discount Analysis):")
contract_with_base = gen.contracts.merge(
    gen.mara[["MATNR", "base_price"]],
    on="MATNR",
    how="left",
)
discount_pct = (
    1 - contract_with_base["CONTRACT_PRICE"] / contract_with_base["base_price"]
) * 100
print(f"   Discount range: {discount_pct.min():.1f}% - " f"{discount_pct.max():.1f}%")
print(f"   Average discount: {discount_pct.mean():.1f}%")
print("   Expected: 5-15% discount")

# Check contract dates
print("\n4. Contract Date Validation:")
sim_start = config.start_date
sim_end = config.end_date
print(f"   Simulation period: {sim_start} to {sim_end}")
earliest_start = gen.contracts["VALID_FROM"].min()
latest_start = gen.contracts["VALID_FROM"].max()
print(f"   Contract start dates: {earliest_start} to {latest_start}")
# Check 6-month runway constraint
runway_end = pd.Timestamp(sim_end) - pd.Timedelta(days=180)
contracts_after_runway = (gen.contracts["VALID_FROM"] > runway_end).sum()
print(
    f"   Contracts starting after runway cutoff ({runway_end}): "
    f"{contracts_after_runway} (expected: 0)"
)

# Check contract duration
durations = cast(Any, gen.contracts["VALID_TO"] - gen.contracts["VALID_FROM"]).dt.days
print(f"   Duration range: {durations.min()} - " f"{durations.max()} days")
print(f"   Average duration: {durations.mean():.0f} days")
print("   Expected: 180-1095 days (6 months - 3 years)")

# Check contract type distribution
print("\n5. Contract Type (CONTRACT_TYPE) Distribution:")
contract_type_counts = gen.contracts["CONTRACT_TYPE"].value_counts()
for ctype, count in contract_type_counts.items():
    pct = count / len(gen.contracts) * 100
    print(f"   {ctype}: {count} ({pct:.1f}%)")
print("   Expected: ~50% BLANKET, ~40% SPOT, ~10% FRAMEWORK")

# Check volume commitments
print("\n6. Volume Commitment Distribution:")
print(f"   Min: {gen.contracts['VOLUME_COMMITMENT'].min()}")
print(f"   Max: {gen.contracts['VOLUME_COMMITMENT'].max()}")
print(f"   Mean: {gen.contracts['VOLUME_COMMITMENT'].mean():.0f}")
print("   Expected range: 100-10,000")

# Check data quality
print("\n7. Data Quality:")
dup_contract_id = gen.contracts["CONTRACT_ID"].duplicated().sum()
print(f"   Duplicate CONTRACT_ID: {dup_contract_id}")
print(f"   Null values: {gen.contracts.isnull().sum().sum()}")
print(
    f"   Total records: {len(gen.contracts)} "
    f"(target: {config.num_contracts}, after deduplication)"
)

# Check FK integrity
print("\n8. Foreign Key Integrity:")
vendors_in_lfa1 = gen.contracts["LIFNR"].isin(gen.lfa1["LIFNR"]).all()
materials_in_mara = gen.contracts["MATNR"].isin(gen.mara["MATNR"]).all()
print(f"   All vendors exist in LFA1: {vendors_in_lfa1}")
print(f"   All materials exist in MARA: {materials_in_mara}")

print("\n" + "=" * 80)

# Generate EKKO
gen._generate_ekko()

assert gen.ekko is not None, "Failed to generate EKKO data"

print("\n" + "=" * 80)
print("EKKO - PO Headers")
print("=" * 80)
print(f"\nTotal POs generated: {len(gen.ekko)}")
print("\nFirst 10 POs:")
print(gen.ekko.head(10))

print("\n\nData Types:")
print(gen.ekko.dtypes)

print("\n\nBasic Statistics:")
print(gen.ekko.describe(include="all"))

print("\n" + "=" * 80)
print("BUSINESS RULE VALIDATION - EKKO")
print("=" * 80)

# 1. Q4 Seasonality Check
print("\n1. Seasonality Check (Q4 Weighting):")
ekko_dates = pd.to_datetime(gen.ekko["AEDAT"])
q4_count = ekko_dates.dt.month.isin([10, 11, 12]).sum()
q4_pct = q4_count / len(gen.ekko) * 100
print(f"   Q4 POs: {q4_count} ({q4_pct:.1f}%)")
print("   Expected: > 25% (due to 1.3x weighting)")

# 2. Vendor Distribution
print("\n2. Vendor Usage Distribution:")
top_vendors_ekko = gen.ekko["LIFNR"].value_counts().head(5)
print("   Top 5 vendors by PO count:")
for vendor, count in top_vendors_ekko.items():
    v_ekko = gen.lfa1[gen.lfa1["LIFNR"] == vendor]
    spend_weight = v_ekko["spend_weight"].values[0]
    print(f"      {vendor}: {count} POs (Weight: {spend_weight})")

# 3. Blocked Vendor Logic
print("\n3. Blocked Vendor Compliance:")
sim_end_ts = pd.Timestamp(config.end_date)
cutoff_date = sim_end_ts - pd.Timedelta(days=90)
blocked_vendors = gen.lfa1[gen.lfa1["SPERR"] == "X"]["LIFNR"].values
blocked_pos = gen.ekko[gen.ekko["LIFNR"].isin(blocked_vendors)]
recent_blocked_pos = blocked_pos[blocked_pos["AEDAT"] >= cutoff_date]
print(
    f"   Blocked vendors with POs after cutoff "
    f"({cutoff_date.date()}): {len(recent_blocked_pos)} (expected: 0)"
)

# 4. Document Type (BSART) Logic
print("\n4. Document Type (BSART) vs Large Orders:")
large_orders = gen.ekko[gen.ekko["is_large"]]
small_orders = gen.ekko[~gen.ekko["is_large"]]
large_nb_pct = (large_orders["BSART"] == "NB").mean() * 100
small_nb_pct = (small_orders["BSART"] == "NB").mean() * 100
print(f"   'NB' type in Large Orders: {large_nb_pct:.1f}% (Expected: 80-95%)")
print(f"   'NB' type in Small Orders: {small_nb_pct:.1f}% (Expected: 60-80%)")

# 5. Data Quality
print("\n5. Data Quality:")
print(f"   Duplicate EBELN: {gen.ekko['EBELN'].duplicated().sum()}")
print(f"   Null values: {gen.ekko.isnull().sum().sum()}")

# 6. FK Integrity
print("\n6. Foreign Key Integrity:")
vendors_in_lfa1_ekko = gen.ekko["LIFNR"].isin(gen.lfa1["LIFNR"]).all()
print(f"   All vendors exist in LFA1: {vendors_in_lfa1_ekko}")

print("\n" + "=" * 80)

# Generate EKPO
gen._generate_ekpo()

assert gen.ekpo is not None, "Failed to generate EKPO data"

print("\n" + "=" * 80)
print("EKPO - PO Line Items")
print("=" * 80)
print(f"\nTotal line items generated: {len(gen.ekpo)}")
print("\nFirst 10 line items:")
print(gen.ekpo.head(10))

print("\n\nData Types:")
print(gen.ekpo.dtypes)

print("\n\nBasic Statistics:")
print(gen.ekpo.describe(include="all"))

print("\n" + "=" * 80)
print("BUSINESS RULE VALIDATION - EKPO")
print("=" * 80)

# 1. Items per PO distribution
print("\n1. Items per PO Distribution:")
items_per_po = cast(Any, gen.ekpo.groupby("EBELN")).size()
print(f"   Total POs with items: {len(items_per_po)}")
print(f"   Expected POs: {len(gen.ekko)}")
print(f"   Min items: {items_per_po.min()}")
print(f"   Max items: {items_per_po.max()}")
print(f"   Mean items: {items_per_po.mean():.2f}")
print(f"   Median items: {items_per_po.median():.0f}")
print("   Expected: 1-15 items per PO (lognormal distribution)")

# 2. Line item numbering (EBELP)
print("\n2. Line Item Numbering (EBELP):")


def check_ebelp_numbering(x: pd.Series) -> bool:
    expected = pd.Series(range(1, len(x) + 1)) * 10
    return bool((x == expected.values).all())


ebelp_check = cast(Any, gen.ekpo.groupby("EBELN")["EBELP"]).apply(check_ebelp_numbering)
correct_numbering = ebelp_check.sum()
numbering_pct = correct_numbering / len(ebelp_check) * 100
print(
    f"   POs with correct numbering (10, 20, 30...): "
    f"{correct_numbering}/{len(ebelp_check)} "
    f"({numbering_pct:.1f}%)"
)

# 3. Material assignment - check distribution by order type
print("\n3. Material Assignment by Order Type:")
ekpo_with_type = gen.ekpo.merge(gen.ekko[["EBELN", "BSART"]], on="EBELN", how="left")
nb_items = ekpo_with_type[ekpo_with_type["BSART"] == "NB"]
fo_items = ekpo_with_type[ekpo_with_type["BSART"] == "FO"]
nb_pct = len(nb_items) / len(gen.ekpo) * 100
fo_pct = len(fo_items) / len(gen.ekpo) * 100
print(f"   NB (Blanket) items: {len(nb_items)} ({nb_pct:.1f}%)")
print(f"   FO (Spot) items: {len(fo_items)} ({fo_pct:.1f}%)")

# 4. Price Analysis
print("\n4. Price Analysis (NETPR):")
print(f"   Min price: ${gen.ekpo['NETPR'].min():.2f}")
print(f"   Max price: ${gen.ekpo['NETPR'].max():.2f}")
print(f"   Mean price: ${gen.ekpo['NETPR'].mean():.2f}")
print(f"   Median price: ${gen.ekpo['NETPR'].median():.2f}")

# Check contract vs spot pricing
ekpo_enriched = gen.ekpo.merge(
    gen.mara[["MATNR", "base_price"]], on="MATNR", how="left"
)
ekpo_enriched = ekpo_enriched.merge(
    gen.ekko[["EBELN", "BSART", "LIFNR"]], on="EBELN", how="left"
)

# Identify contract-priced items
price_ratio = ekpo_enriched["NETPR"] / ekpo_enriched["base_price"]
contract_priced = (price_ratio < 0.98).sum()
contract_pct = contract_priced / len(gen.ekpo) * 100
print(
    f"   Items likely from contracts (price < 98% of base): "
    f"{contract_priced} ({contract_pct:.1f}%)"
)

# 5. Quantity Analysis
print("\n5. Quantity Analysis (MENGE):")
print(f"   Min quantity: {gen.ekpo['MENGE'].min()}")
print(f"   Max quantity: {gen.ekpo['MENGE'].max()}")
print(f"   Mean quantity: {gen.ekpo['MENGE'].mean():.2f}")
print(f"   Median quantity: {gen.ekpo['MENGE'].median():.0f}")
print("   Expected: Lognormal distribution with adjustments for large orders")

# 6. Large order validation
print("\n6. Large Order Handling:")
ekpo_with_large = gen.ekpo.merge(
    gen.ekko[["EBELN", "is_large"]], on="EBELN", how="left"
)
large_order_items = ekpo_with_large[ekpo_with_large["is_large"]]
if len(large_order_items) > 0:
    large_order_values = (
        (large_order_items["NETPR"] * large_order_items["MENGE"])
        .groupby(large_order_items["EBELN"])
        .sum()
    )
    print(f"   Large orders: {len(large_order_values)}")
    print(f"   Min total value: ${large_order_values.min():.2f}")
    print(f"   Max total value: ${large_order_values.max():.2f}")
    print(f"   Mean total value: ${large_order_values.mean():.2f}")
    print("   Expected: Most should be > $15,000")
    below_threshold = (large_order_values < 15000).sum()
    below_pct = below_threshold / len(large_order_values) * 100
    print(f"   Large orders below $15k: {below_threshold} ({below_pct:.1f}%)")
else:
    print("   No large orders found")

# 7. Net worth calculation validation
print("\n7. Net Worth Calculation (NETWR = MENGE × NETPR):")
calculated_netwr = gen.ekpo["MENGE"] * gen.ekpo["NETPR"]
netwr_match = np.isclose(gen.ekpo["NETWR"], calculated_netwr, rtol=1e-5)
match_pct = netwr_match.mean() * 100
print(
    f"   Correct calculations: {netwr_match.sum()}/"
    f"{len(gen.ekpo)} ({match_pct:.1f}%)"
)
if not netwr_match.all():
    print("   WARNING: Some NETWR values don't match " "MENGE × NETPR!")

print(f"   Total order value: ${gen.ekpo['NETWR'].sum():,.2f}")
print(f"   Average line value: ${gen.ekpo['NETWR'].mean():.2f}")

# 8. Delivery date validation (EINDT)
print("\n8. Delivery Date (EINDT) Validation:")
ekpo_with_aedat = gen.ekpo.merge(gen.ekko[["EBELN", "AEDAT"]], on="EBELN", how="left")
lead_times = (
    pd.to_datetime(ekpo_with_aedat["EINDT"]) - pd.to_datetime(ekpo_with_aedat["AEDAT"])
).dt.days
print(f"   Min lead time: {lead_times.min()} days")
print(f"   Max lead time: {lead_times.max()} days")
print(f"   Mean lead time: {lead_times.mean():.1f} days")
print("   Expected: 5-30 days")
invalid_lead_times = ((lead_times < 5) | (lead_times > 30)).sum()
if invalid_lead_times > 0:
    print(
        f"   WARNING: {invalid_lead_times} items with lead time "
        "outside expected range!"
    )

# 9. Foreign key integrity
print("\n9. Foreign Key Integrity:")
pos_in_ekko = gen.ekpo["EBELN"].isin(gen.ekko["EBELN"]).all()
materials_in_mara_ekpo = gen.ekpo["MATNR"].isin(gen.mara["MATNR"]).all()
print(f"   All POs exist in EKKO: {pos_in_ekko}")
print(f"   All materials exist in MARA: {materials_in_mara_ekpo}")

# 10. Data Quality
print("\n10. Data Quality:")
duplicate_items = gen.ekpo.duplicated(subset=["EBELN", "EBELP"]).sum()
print(f"   Duplicate (EBELN, EBELP) pairs: " f"{duplicate_items} (expected: 0)")
print(f"   Null values: {gen.ekpo.isnull().sum().sum()}")
print(f"   Total line items: {len(gen.ekpo)}")

# Summary by PO type
print("\n11. Summary by Purchase Order Type:")
for bsart in ekpo_with_type["BSART"].unique():
    items: pd.DataFrame = ekpo_with_type[ekpo_with_type["BSART"] == bsart]
    print(f"   {bsart}:")
    print(f"      Items: {len(items)}")
    total_val = items["NETWR"].sum()
    print(f"      Total value: ${total_val:,.2f}")
    avg_val = items["NETWR"].mean()
    print(f"      Avg item value: ${avg_val:.2f}")

print("\n" + "=" * 80)

# Generate EKBE
gen._generate_ekbe()

assert gen.ekbe is not None, "Failed to generate EKBE data"

print("\n" + "=" * 80)
print("EKBE - PO History")
print("=" * 80)
print(f"\nTotal history records generated: {len(gen.ekbe)}")
print("\nFirst 10 history records:")
print(gen.ekbe.head(10))

print("\n\nData Types:")
print(gen.ekbe.dtypes)

print("\n\nBasic Statistics:")
print(gen.ekbe.describe(include="all"))

print("\n" + "=" * 80)
print("BUSINESS RULE VALIDATION - EKBE")
print("=" * 80)

# 1. Movement Type Distribution
print("\n1. Movement Type (BEWTP) Distribution:")
bewtp_counts = cast(Any, gen.ekbe["BEWTP"].value_counts())
for bewtp, count in bewtp_counts.items():
    pct = count / len(gen.ekbe) * 100
    movement_type = "Goods Receipt (E)" if bewtp == "E" else "Invoice Receipt (Q)"
    print(f"   {bewtp} ({movement_type}): {count} ({pct:.1f}%)")

# Check if GR count matches EKPO
gr_count = (gen.ekbe["BEWTP"] == "E").sum()
print(f"   Total GR records: {gr_count} (Expected: ~{len(gen.ekpo)})")
print(f"   Total IR records: {bewtp_counts.get('Q', 0)} " "(Expected: ~95% of GR)")

# 2. Date Validation
print("\n2. Date Validation (BUDAT):")
ekbe_with_dates = gen.ekbe.merge(
    gen.ekpo[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"], how="left"
)
ekbe_with_dates = ekbe_with_dates.merge(
    gen.ekko[["EBELN", "AEDAT"]], on="EBELN", how="left"
)

gr_records = ekbe_with_dates[ekbe_with_dates["BEWTP"] == "E"]
early_gr = gr_records["BUDAT"] < gr_records["AEDAT"]
print(f"   GR before PO date: {early_gr} (Expected: 0)")

delays = (
    pd.to_datetime(gr_records["BUDAT"]) - pd.to_datetime(gr_records["EINDT"])
).dt.days
print("   Delivery delay statistics:")
print(f"      Min delay: {delays.min():.1f} days")
print(f"      Max delay: {delays.max():.1f} days")
print(f"      Mean delay: {delays.mean():.1f} days")
print(f"      Median delay: {delays.median():.1f} days")

on_time = (delays <= 0).sum()
on_time_pct = on_time / len(gr_records) * 100
print(f"   On-time deliveries: {on_time} ({on_time_pct:.1f}%)")

# Define suffix constants for merge operations
_IR = "_IR"
_GR = "_GR"

# 3. Invoice Receipt Validation
print("\n3. Invoice Receipt Validation:")
ir_records = ekbe_with_dates[ekbe_with_dates["BEWTP"] == "Q"]
if len(ir_records) > 0:
    gr_for_ir = ekbe_with_dates[ekbe_with_dates["BEWTP"] == "E"][
        ["EBELN", "EBELP", "BUDAT"]
    ]
    ir_with_gr = ir_records.merge(
        gr_for_ir,
        on=["EBELN", "EBELP"],
        suffixes=(_IR, _GR),
        how="left",
    )

    processing_times = (
        pd.to_datetime(ir_with_gr["BUDAT_IR"]) - pd.to_datetime(ir_with_gr["BUDAT_GR"])
    ).dt.days

    print("   Invoice processing time:")
    print(f"      Min: {processing_times.min():.0f} days")
    print(f"      Max: {processing_times.max():.0f} days")
    print(f"      Mean: {processing_times.mean():.1f} days")
    print("      Expected: 5-30 days")

    invalid_ir = (processing_times < 0).sum()
    if invalid_ir > 0:
        print(f"   WARNING: {invalid_ir} invoices dated before goods receipt!")

# 4. Amount Validation
print("\n4. Amount Validation (DMBTR):")
print(f"   Min amount: ${gen.ekbe['DMBTR'].min():.2f}")
print(f"   Max amount: ${gen.ekbe['DMBTR'].max():.2f}")
print(f"   Mean amount: ${gen.ekbe['DMBTR'].mean():.2f}")
print(f"   Total amount: ${gen.ekbe['DMBTR'].sum():,.2f}")

# Compare GR and IR amounts for the same line items
gr_amounts = gen.ekbe[gen.ekbe["BEWTP"] == "E"][["EBELN", "EBELP", "DMBTR"]]
ir_amounts = gen.ekbe[gen.ekbe["BEWTP"] == "Q"][["EBELN", "EBELP", "DMBTR"]]
if len(ir_amounts) > 0:
    amount_comparison = gr_amounts.merge(
        ir_amounts,
        on=["EBELN", "EBELP"],
        suffixes=(_GR, _IR),
        how="inner",
    )
    price_variance = (
        (amount_comparison["DMBTR_IR"] - amount_comparison["DMBTR_GR"])
        / amount_comparison["DMBTR_GR"]
        * 100
    )
    print("\n   Price variance between GR and IR:")
    print(f"      Min: {price_variance.min():.2f}%")
    print(f"      Max: {price_variance.max():.2f}%")
    print(f"      Mean: {price_variance.mean():.2f}%")
    print("      Expected: Around ±2% due to pricing noise")

# 5. Document Number (BELNR) Validation
print("\n5. Document Number (BELNR) Validation:")
unique_belnr = gen.ekbe["BELNR"].nunique()
print(f"   Unique document numbers: {unique_belnr}")
print(f"   Total records: {len(gen.ekbe)}")
dup_belnr = gen.ekbe["BELNR"].duplicated().sum()
print(f"   Duplicate BELNRs: {dup_belnr} (expected: 0)")

# 6. Foreign Key Integrity
print("\n6. Foreign Key Integrity:")
ekpo_keys = set(zip(gen.ekpo["EBELN"], gen.ekpo["EBELP"]))
ekbe_keys = set(zip(gen.ekbe["EBELN"], gen.ekbe["EBELP"]))
invalid_keys = ekbe_keys - ekpo_keys
print(f"   All EKBE records exist in EKPO: {len(invalid_keys) == 0}")
if len(invalid_keys) > 0:
    print(f"   WARNING: {len(invalid_keys)} EKBE records " "have no matching EKPO!")

# 7. Data Quality
print("\n7. Data Quality:")
print(f"   Null values: {gen.ekbe.isnull().sum().sum()}")
dup_ekbe = gen.ekbe.duplicated(subset=["EBELN", "EBELP", "BEWTP"]).sum()
print(f"   Duplicate (EBELN, EBELP, BEWTP) combinations: {dup_ekbe}")

# 8. Coverage Analysis
print("\n8. Coverage Analysis:")
ekpo_with_gr = gen.ekpo.merge(
    gen.ekbe[gen.ekbe["BEWTP"] == "E"][["EBELN", "EBELP"]],
    on=["EBELN", "EBELP"],
    how="left",
    indicator=True,
)
coverage = (ekpo_with_gr["_merge"] == "both").sum()
coverage_pct = coverage / len(gen.ekpo) * 100
print(
    f"   PO items with goods receipt: {coverage}/{len(gen.ekpo)} "
    f"({coverage_pct:.1f}%)"
)
print("   Expected: 100%")

print("\n" + "=" * 80)
print("OVERALL SUMMARY")
print("=" * 80)
print("\nData Generation Complete:")
print(f"  ✓ LFA1 (Vendors): {len(gen.lfa1):,} records")
print(f"  ✓ MARA (Materials): {len(gen.mara):,} records")
print(f"  ✓ CONTRACTS: {len(gen.contracts):,} records")
print(f"  ✓ EKKO (PO Headers): {len(gen.ekko):,} records")
print(f"  ✓ EKPO (PO Items): {len(gen.ekpo):,} records")
print(f"  ✓ EKBE (PO History): {len(gen.ekbe):,} records")
print(f"\nTotal Purchase Order Value: ${gen.ekpo['NETWR'].sum():,.2f}")
avg_po_value = gen.ekpo.groupby("EBELN")["NETWR"].sum().mean()
print(f"Average PO Value: ${avg_po_value:,.2f}")

print("\n" + "=" * 80)
