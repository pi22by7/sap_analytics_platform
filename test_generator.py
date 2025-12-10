from src.generator.sap_generator import SAPDataGenerator, GeneratorConfig

config = GeneratorConfig(
    seed=42,
    num_vendors=1000, 
    num_materials=5000,
    num_pos=10000
)

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
print(gen.lfa1.describe(include='all'))

print("\n" + "=" * 80)

# pareto
top_20_pct = int(len(gen.lfa1) * 0.20)
top_vendors = gen.lfa1.head(top_20_pct) 
print(f"\n1. Pareto Distribution Check:")
print(f"    Top 20% vendors with weight=100: {(top_vendors['spend_weight'] == 100).sum()} (expected: {top_20_pct})")
print(f"    Bottom 80% vendors with weight=1: {(gen.lfa1['spend_weight'] == 1).sum()} (expected: {len(gen.lfa1) - top_20_pct})")

# KTOKK distribution
print(f"\n2. Vendor Types (KTOKK):")
ktokk_counts = gen.lfa1['KTOKK'].value_counts()
print(f"   PREF: {ktokk_counts.get('PREF', 0)} ({ktokk_counts.get('PREF', 0)/len(gen.lfa1)*100:.1f}%)")
print(f"   STD: {ktokk_counts.get('STD', 0)} ({ktokk_counts.get('STD', 0)/len(gen.lfa1)*100:.1f}%)")

# Check correlation between spend_weight and KTOKK
top_vendors_pref = top_vendors['KTOKK'].value_counts().get('PREF', 0)
bottom_vendors = gen.lfa1[gen.lfa1['spend_weight'] == 1]
bottom_vendors_pref = bottom_vendors['KTOKK'].value_counts().get('PREF', 0)
print(f"   Top vendors that are PREF: {top_vendors_pref}/{len(top_vendors)} ({top_vendors_pref/len(top_vendors)*100:.1f}%)")
print(f"   Bottom vendors that are PREF: {bottom_vendors_pref}/{len(bottom_vendors)} ({bottom_vendors_pref/len(bottom_vendors)*100:.1f}%)")

# Check blocked status
print(f"\n3. Blocked Vendors (SPERR):")
blocked_count = (gen.lfa1['SPERR'] == 'X').sum()
print(f"   Blocked: {blocked_count} ({blocked_count/len(gen.lfa1)*100:.1f}%)")
print(f"   Active: {len(gen.lfa1) - blocked_count} ({(len(gen.lfa1) - blocked_count)/len(gen.lfa1)*100:.1f}%)")

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
