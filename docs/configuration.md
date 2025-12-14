# Configuration Documentation

The system is highly configurable via the `GeneratorConfig` dataclass found in `src/generator/sap_generator.py`. This allows users to simulate different business scenarios (e.g., high inflation, supply chain disruptions).

## General Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `seed` | int | 4242 | Random seed for reproducibility. |
| `start_date` | str | "2020-01-01" | Simulation start date. |
| `end_date` | str | "2024-12-31" | Simulation end date. |

## Volume Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_vendors` | int | 1000 | Number of records in LFA1. |
| `num_materials` | int | 5000 | Number of records in MARA. |
| `num_pos` | int | 10000 | Number of PO Headers (EKKO). |
| `num_contracts` | int | 2000 | Number of contracts to generate. |

## Business Logic Parameters

### Vendor Distribution
*   `pareto_split` (0.20): Fraction of vendors considered "Top Tier".
*   `pareto_spend_share` (0.80): Fraction of total spend assigned to Top Tier vendors.
*   `preferred_vendor_ratio` (0.10): Percentage of vendors marked as Preferred.

### Pricing & Contracts
*   `price_volatility` (0.15): Standard deviation for spot price noise (15%).
*   `contract_coverage` (0.45): Probability that a Vendor-Material pair has a contract.
*   `contract_discount_range` (0.05, 0.15): Discount range for contracts vs base price.

### Delivery & Operations
*   `delivery_late_rate` (0.25): Baseline probability of a late delivery.
*   `po_max_items` (15): Maximum number of line items per PO.
*   `seasonality_q4_factor` (1.3): Multiplier for PO generation probability in Q4.

## Modifying Configuration
To change these parameters, modify the instantiation of `GeneratorConfig` in the `if __name__ == "__main__":` block of `src/generator/sap_generator.py` or create a wrapper script to inject a custom config object.

```python
config = GeneratorConfig(
    num_vendors=5000,
    delivery_late_rate=0.40  # Simulate supply chain crisis
)
generator = SAPDataGenerator(config)
```
