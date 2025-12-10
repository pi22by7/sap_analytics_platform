from src.generator.sap_generator import SAPDataGenerator, GeneratorConfig

config = GeneratorConfig(seed=42, num_vendors=1000, num_materials=5000, num_pos=10000)

gen = SAPDataGenerator(config)
gen._generate_lfa1()  # type: ignore[reportPrivateUsage]

assert gen.lfa1 is not None, "Failed to generate LFA1 data"

print("=" * 80)
print("LFA1")
print("=" * 80)
print(f"\nTotal vendors generated: {len(gen.lfa1)}")
print(f"\nFirst 10 vendors:")
print(gen.lfa1.head(10))

print(f"\n\nData Types:")
print(gen.lfa1.dtypes)

print(f"\n\nBasic Statistics:")
print(gen.lfa1.describe(include="all"))

print("\n" + "=" * 80)

# pareto
top_20_pct = int(len(gen.lfa1) * 0.20)
top_vendors = gen.lfa1.head(top_20_pct)
print(f"\n1. Pareto Distribution Check:")
print(
    f"    Top 20% vendors with weight=100: {(top_vendors['spend_weight'] == 100).sum()} (expected: {top_20_pct})"
)
print(
    f"    Bottom 80% vendors with weight=1: {(gen.lfa1['spend_weight'] == 1).sum()} (expected: {len(gen.lfa1) - top_20_pct})"
)

# KTOKK distribution
print(f"\n2. Vendor Types (KTOKK):")
ktokk_counts = gen.lfa1["KTOKK"].value_counts()
print(
    f"   PREF: {ktokk_counts.get('PREF', 0)} ({ktokk_counts.get('PREF', 0)/len(gen.lfa1)*100:.1f}%)"
)
print(
    f"   STD: {ktokk_counts.get('STD', 0)} ({ktokk_counts.get('STD', 0)/len(gen.lfa1)*100:.1f}%)"
)

# Check correlation between spend_weight and KTOKK
top_vendors_pref = top_vendors["KTOKK"].value_counts().get("PREF", 0)
bottom_vendors = gen.lfa1[gen.lfa1["spend_weight"] == 1]
bottom_vendors_pref = bottom_vendors["KTOKK"].value_counts().get("PREF", 0)
print(
    f"   Top vendors that are PREF: {top_vendors_pref}/{len(top_vendors)} ({top_vendors_pref/len(top_vendors)*100:.1f}%)"
)
print(
    f"   Bottom vendors that are PREF: {bottom_vendors_pref}/{len(bottom_vendors)} ({bottom_vendors_pref/len(bottom_vendors)*100:.1f}%)"
)

# Check blocked status
print(f"\n3. Blocked Vendors (SPERR):")
blocked_count = (gen.lfa1["SPERR"] == "X").sum()
print(f"   Blocked: {blocked_count} ({blocked_count/len(gen.lfa1)*100:.1f}%)")
print(
    f"   Active: {len(gen.lfa1) - blocked_count} ({(len(gen.lfa1) - blocked_count)/len(gen.lfa1)*100:.1f}%)"
)

# Check performance bias distribution
print(f"\n4. Performance Bias (perf_bias):")
print(f"   Mean: {gen.lfa1['perf_bias'].mean():.2f} (should be ~0)")
print(f"   Std: {gen.lfa1['perf_bias'].std():.2f} (should be ~2)")
print(f"   Min: {gen.lfa1['perf_bias'].min():.2f}")
print(f"   Max: {gen.lfa1['perf_bias'].max():.2f}")

# Check for duplicates
print(f"\n5. Data Quality:")
print(f"   Duplicate LIFNR: {gen.lfa1['LIFNR'].duplicated().sum()}")
print(f"   Null values: {gen.lfa1.isnull().sum().sum()}")

print("\n" + "=" * 80)

# Generate MARA
gen._generate_mara()  # type: ignore[reportPrivateUsage]

assert gen.mara is not None, "Failed to generate MARA data"

print("\n" + "=" * 80)
print("MARA")
print("=" * 80)
print(f"\nTotal materials generated: {len(gen.mara)}")
print(f"\nFirst 10 materials:")
print(gen.mara.head(10))

print(f"\n\nData Types:")
print(gen.mara.dtypes)

print(f"\n\nBasic Statistics:")
print(gen.mara.describe(include="all"))

print("\n" + "=" * 80)
print("BUSINESS RULE VALIDATION - MARA")
print("=" * 80)

# Check category distribution
print(f"\n1. Material Category Distribution (MATKL):")
matkl_counts = gen.mara["MATKL"].value_counts()
for category, count in matkl_counts.items():
    pct = count / len(gen.mara) * 100
    print(f"   {category}: {count} ({pct:.1f}%)")
    if pct > 40:
        print(f"      WARNING: Exceeds 40% constraint!")

# Check material types match categories
print(f"\n2. Material Type (MTART) Mapping:")
mtart_by_matkl = gen.mara.groupby("MATKL")["MTART"].unique()  # type: ignore[call-overload]
for category, mtypes in mtart_by_matkl.items():
    print(f"   {category}: {', '.join(mtypes)}")

# Check price ranges by category
print(f"\n3. Base Price Ranges by Category:")
for category in gen.mara["MATKL"].unique():
    cat_data = gen.mara[gen.mara["MATKL"] == category]  # type: ignore[index]
    print(f"   {category}:")
    print(f"      Min: ${cat_data['base_price'].min():.2f}")  # type: ignore[union-attr]
    print(f"      Max: ${cat_data['base_price'].max():.2f}")  # type: ignore[union-attr]
    print(f"      Mean: ${cat_data['base_price'].mean():.2f}")  # type: ignore[union-attr]
    print(f"      Median: ${cat_data['base_price'].median():.2f}")  # type: ignore[union-attr]

# Check weight distribution
print(f"\n4. Weight Distribution:")
print(f"   Materials with zero weight (SERV): {(gen.mara['BRGEW'] == 0).sum()}")
print(f"   Materials with weight > 0: {(gen.mara['BRGEW'] > 0).sum()}")
print(
    f"   Avg gross weight (non-zero): {gen.mara[gen.mara['BRGEW'] > 0]['BRGEW'].mean():.2f} kg"
)
print(
    f"   Net/Gross weight ratio (non-zero): {(gen.mara[gen.mara['BRGEW'] > 0]['NTGEW'] / gen.mara[gen.mara['BRGEW'] > 0]['BRGEW']).mean():.2%}"
)

# Check UOM distribution
print(f"\n5. Unit of Measure (MEINS) Distribution:")
meins_counts = gen.mara["MEINS"].value_counts()
for uom, count in meins_counts.items():
    print(f"   {uom}: {count} ({count/len(gen.mara)*100:.1f}%)")

# Check data quality
print(f"\n6. Data Quality:")
print(f"   Duplicate MATNR: {gen.mara['MATNR'].duplicated().sum()}")
print(f"   Null values: {gen.mara.isnull().sum().sum()}")
print(f"   Total records: {len(gen.mara)} (expected: {config.num_materials})")

# Verify shuffle worked
print(f"\n7. Shuffle Verification:")
print(f"   First 5 MATNRs: {gen.mara['MATNR'].head().tolist()}")
print(f"   First 5 MATKLs: {gen.mara['MATKL'].head().tolist()}")
print(f"   (Should show mixed categories, not all ELECT)")

print("\n" + "=" * 80)

# Generate CONTRACTS
gen._generate_contracts()  # type: ignore[reportPrivateUsage]

assert gen.contracts is not None, "Failed to generate CONTRACTS data"

print("\n" + "=" * 80)
print("CONTRACTS - Vendor Contracts")
print("=" * 80)
print(f"\nTotal contracts generated: {len(gen.contracts)}")
print(f"\nFirst 10 contracts:")
print(gen.contracts.head(10))

print(f"\n\nData Types:")
print(gen.contracts.dtypes)

print(f"\n\nBasic Statistics:")
print(gen.contracts.describe(include="all"))

print("\n" + "=" * 80)
print("BUSINESS RULE VALIDATION - CONTRACTS")
print("=" * 80)

# Check uniqueness of vendor-material pairs
print(f"\n1. Vendor-Material Pair Uniqueness:")
duplicates = gen.contracts.duplicated(subset=["LIFNR", "MATNR"]).sum()
print(f"   Duplicate (LIFNR, MATNR) pairs: {duplicates} (expected: 0)")
print(f"   Unique pairs: {len(gen.contracts)}")

# Check vendor distribution (should be Pareto-weighted)
print(f"\n2. Vendor Distribution in Contracts:")
vendor_contract_counts = gen.contracts["LIFNR"].value_counts()
print(f"   Vendors with contracts: {len(vendor_contract_counts)}")
print(f"   Top 5 vendors by contract count:")
for vendor, count in vendor_contract_counts.head().items():
    vendor_type = gen.lfa1[gen.lfa1["LIFNR"] == vendor]["KTOKK"].values[0]  # type: ignore[index]
    spend_weight = gen.lfa1[gen.lfa1["LIFNR"] == vendor]["spend_weight"].values[0]  # type: ignore[index]
    print(
        f"      {vendor}: {count} contracts (Type: {vendor_type}, Weight: {spend_weight})"
    )

# Check contract price discount (should be 5-15% off base price)
print(f"\n3. Contract Pricing (Discount Analysis):")
# Merge with mara to compare
contract_with_base = gen.contracts.merge(
    gen.mara[["MATNR", "base_price"]], on="MATNR", how="left"
)  # type: ignore[index]
discount_pct = (
    1 - contract_with_base["CONTRACT_PRICE"] / contract_with_base["base_price"]
) * 100
print(f"   Discount range: {discount_pct.min():.1f}% - {discount_pct.max():.1f}%")
print(f"   Average discount: {discount_pct.mean():.1f}%")
print(f"   Expected: 5-15% discount")

# Check contract dates
print(f"\n4. Contract Date Validation:")
sim_start = config.start_date
sim_end = config.end_date
print(f"   Simulation period: {sim_start} to {sim_end}")
earliest_start = gen.contracts["VALID_FROM"].min()
latest_start = gen.contracts["VALID_FROM"].max()
print(f"   Contract start dates: {earliest_start} to {latest_start}")
# Check 6-month runway constraint
import pandas as pd

runway_end = pd.Timestamp(sim_end) - pd.Timedelta(days=180)
contracts_after_runway = (gen.contracts["VALID_FROM"] > runway_end).sum()
print(
    f"   Contracts starting after runway cutoff ({runway_end}): {contracts_after_runway} (expected: 0)"
)

# Check contract duration
durations = (gen.contracts["VALID_TO"] - gen.contracts["VALID_FROM"]).dt.days  # type: ignore[union-attr]
print(f"   Duration range: {durations.min()} - {durations.max()} days")  # type: ignore[union-attr]
print(f"   Average duration: {durations.mean():.0f} days")  # type: ignore[union-attr]
print(f"   Expected: 180-1095 days (6 months - 3 years)")

# Check contract type distribution
print(f"\n5. Contract Type (CONTRACT_TYPE) Distribution:")
contract_type_counts = gen.contracts["CONTRACT_TYPE"].value_counts()
for ctype, count in contract_type_counts.items():
    pct = count / len(gen.contracts) * 100
    print(f"   {ctype}: {count} ({pct:.1f}%)")
print(f"   Expected: ~50% BLANKET, ~40% SPOT, ~10% FRAMEWORK")

# Check volume commitments
print(f"\n6. Volume Commitment Distribution:")
print(f"   Min: {gen.contracts['VOLUME_COMMITMENT'].min()}")
print(f"   Max: {gen.contracts['VOLUME_COMMITMENT'].max()}")
print(f"   Mean: {gen.contracts['VOLUME_COMMITMENT'].mean():.0f}")
print(f"   Expected range: 100-10,000")

# Check data quality
print(f"\n7. Data Quality:")
print(f"   Duplicate CONTRACT_ID: {gen.contracts['CONTRACT_ID'].duplicated().sum()}")
print(f"   Null values: {gen.contracts.isnull().sum().sum()}")
print(
    f"   Total records: {len(gen.contracts)} (target: {config.num_contracts}, after deduplication)"
)

# Check FK integrity
print(f"\n8. Foreign Key Integrity:")
vendors_in_lfa1 = gen.contracts["LIFNR"].isin(gen.lfa1["LIFNR"]).all()  # type: ignore[arg-type]
materials_in_mara = gen.contracts["MATNR"].isin(gen.mara["MATNR"]).all()  # type: ignore[arg-type]
print(f"   All vendors exist in LFA1: {vendors_in_lfa1}")
print(f"   All materials exist in MARA: {materials_in_mara}")

print("\n" + "=" * 80)
