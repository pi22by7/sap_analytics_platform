# Analytics Methodology

This document outlines the calculation logic, formulas, and business rules used in the SAP Procurement Analytics Platform.

## 1. Key Performance Indicators (KPIs)

| KPI | Formula / Logic | Purpose |
| :--- | :--- | :--- |
| **Total Spend** | $\sum \text{Net Value (NETWR)}$ for all Purchase Orders (POs) within the selected date range. | Measures total procurement expenditure. |
| **Contract Compliance Rate** | $\frac{\text{Count of Contract POs (BSART='NB')}}{\text{Total PO Count}}$ | Tracks adherence to negotiated contracts. |
| **On-Time Delivery (OTD) Rate** | $1 - \frac{\text{Count of Late Deliveries}}{\text{Total Deliveries}}$ <br> *Late Delivery*: `ACTUAL_DELIVERY_DATE` > `EINDT` (Expected Delivery Date). | Measures supplier reliability. |
| **Active Vendors** | Count of unique Vendor IDs (`LIFNR`) with at least one PO in the current period. | Monitors the size of the active supply base. |

## 2. Vendor Intelligence

### Vendor Performance Scoring
Vendor performance is evaluated based on a matrix of **Spend vs. Reliability**.

*   **Spend Impact:** Total `NETWR` attributed to the vendor.
*   **Reliability:** On-Time Delivery % calculated from `EKBE` (History) and `EKPO` (Line Item) data.
*   **Risk Assessment:** Vendors are flagged based on:
    *   **High Risk:** Low OTD (< 70%) or High Price Variance.
    *   **Critical:** High Spend + Low Performance.

### Vendor Metrics
*   **Avg. Price Competitiveness:** Comparison of a vendor's unit price (`NETPR`) against the category average for the same material.
*   **Lead Time:** Average days between PO Creation Date (`AEDAT`) and Goods Receipt Date (`BUDAT`).

## 3. Savings & Opportunities

Savings potential is estimated using three primary levers:

### A. Maverick Spend (Off-Contract)
*   **Definition:** Spending on non-contract POs (`BSART` != 'NB') where a contract could likely be established.
*   **Calculation:** $\sum (\text{NETWR of Non-Contract POs}) \times 10\%$
*   **Assumption:** Moving spot purchases to contracts yields an average 10% saving.

### B. Price Variance
*   **Definition:** Cost incurred by purchasing materials above their average unit price.
*   **Calculation:** $\sum [(\text{Unit Price} - \text{Avg Material Price}) \times \text{Quantity}]$
*   **Scope:** Only calculated for positive variances (overspending).

### C. Supplier Consolidation
*   **Definition:** Savings from reducing the number of suppliers for a single material to leverage volume discounts.
*   **Identification:** Materials sourced from > 3 distinct vendors.
*   **Calculation:** $\text{Count of fragmented materials} \times \$5,000$ (Estimated admin & volume efficiency per consolidation).

## 4. Data Quality Framework

The platform enforces data integrity through the **DQ Core** engine (`src/quality/core.py`).

| Category | Checks Implemented |
| :--- | :--- |
| **Schema** | Field presence, data types, null checks, ISO currency codes. |
| **Integrity** | Foreign Key validation (PO $\rightarrow$ Vendor, Item $\rightarrow$ Material, History $\rightarrow$ PO). |
| **Business Logic** | `NETWR` calculation accuracy (tolerance 1%), Date sequencing (`EINDT` $\ge$ `AEDAT`), Invoice vs. GR amounts. |
| **Statistics** | Pareto distribution (Spend), Price outliers (> 3 std dev), seasonality checks. |

## 5. Technical Implementation Details

*   **Data Source:** Generated Parquet files mimicking SAP tables (`EKKO`, `EKPO`, `LFA1`, `MARA`, `EKBE`).
*   **Processing:** `Pandas` is used for in-memory data aggregation and vectorised calculations.
*   **Visualization:** `Plotly` and `Streamlit` render interactive charts based on the aggregated metrics.
