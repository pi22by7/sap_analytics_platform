# Business Logic & Generation Rules

This document outlines the business rules and logic implemented in the SAP Data Generator engine.

## 1. Vendor Distribution (Pareto Principle)
We model a realistic market structure where a small number of vendors capture the majority of the spend.
*   **Split:** Top 20% of vendors ("Strategic Vendors") receive ~80% of the total spend volume.
*   **Implementation:** Vendors are assigned a `spend_weight` during generation. Top tier vendors get a weight of 4000, while the remaining 80% get a weight of 1. PO generation selects vendors probabilistically based on these weights.

## 2. Pricing Logic
Pricing is dynamic and categorical to simulate real-world variance.
*   **Base Prices:** Assigned per material based on category (e.g., Electronics: \$100-\$10k, Office Supplies: \$1-\$500).
*   **Volatility:** Spot prices fluctuate using a normal distribution with $\sigma=0.15$ (15% volatility).
*   **Preferred Vendors:** Vendors marked as `KTOKK='PREF'` (10% of total) offer a 10-15% discount on spot prices.
*   **Contracts:** Materials with active contracts (`VENDOR_CONTRACTS`) have fixed prices that are 5-15% lower than the market base price.
*   **Maverick Spend:** Items bought off-contract (where a contract exists but wasn't used) or via Spot POs (`BSART='FO'`) pay the volatile market price, creating "Price Variance" opportunities.

## 3. Delivery Performance
Delivery delays are modeled to support supply chain reliability analysis.
*   **Late Rate:** ~25% of all deliveries are late (`ACTUAL_DELIVERY_DATE > EINDT`).
*   **Distribution:**
    *   Minor Delay (1-7 days): 70% of late cases
    *   Medium Delay (8-14 days): 20% of late cases
    *   Major Delay (15-30 days): 10% of late cases
*   **Bias:** Each vendor has a hidden `perf_bias` factor. Some vendors are consistently 20% worse or better than the average.
*   **Lead Time:** Earlier expected delivery dates (short lead times) have a slightly higher risk of delay, modeled by an `early_delivery_bias`.

## 4. Contract Logic
*   **Coverage:** Contracts are generated for ~45% of valid Vendor-Material combinations.
*   **Validity:** Contracts last 1-3 years. POs must fall within `VALID_FROM` and `VALID_TO` to utilize the contract price.
*   **Compliance:** POs for materials with valid contracts *should* use the contract price. If they don't (simulated by random assignment or `BSART='FO'`), it is flagged as non-compliance.

## 5. Transactional Integrity
*   **PO History:** Every PO Item (`EKPO`) generates 1-3 Goods Receipt (`EKBE`, `BEWTP='E'`) records to simulate partial deliveries.
*   **Invoicing:** ~95% of Goods Receipts generate a corresponding Invoice Receipt (`BEWTP='Q'`).
*   **Three-Way Matching:** Invoice amounts match the GR amount within a small random noise (simulation of tax/fee variances < 2%), but large variances are flagged in Data Quality checks.
*   **Sequencing:** `BUDAT` (Posting Date) for Invoices is always 5-30 days after the Goods Receipt.

## 6. Seasonality
*   **Q4 Spike:** Spending probability is weighted 1.3x higher in October, November, and December to simulate year-end budget exhaustion.
