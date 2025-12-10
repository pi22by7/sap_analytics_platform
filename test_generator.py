from src.generator.sap_generator import SAPDataGenerator, GeneratorConfig

config = GeneratorConfig(seed=42, num_vendors=1000, num_materials=5000, num_pos=10000)

gen = SAPDataGenerator(config)
gen._generate_lfa1()

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
gen._generate_mara()

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
mtart_by_matkl = gen.mara.groupby("MATKL")["MTART"].unique()
for category, mtypes in mtart_by_matkl.items():
    print(f"   {category}: {', '.join(mtypes)}")

# Check price ranges by category
print(f"\n3. Base Price Ranges by Category:")
for category in gen.mara["MATKL"].unique():
    cat_data = gen.mara[gen.mara["MATKL"] == category]
    print(f"   {category}:")
    print(f"      Min: ${cat_data['base_price'].min():.2f}")
    print(f"      Max: ${cat_data['base_price'].max():.2f}")
    print(f"      Mean: ${cat_data['base_price'].mean():.2f}")
    print(f"      Median: ${cat_data['base_price'].median():.2f}")

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
