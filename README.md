# SAP Procurement Analytics Platform

## Overview

A high-performance SAP Procurement Analytics Platform built from the ground up. This system generates realistic synthetic procurement data (LFA1, EKKO, etc.), validates it with a robust quality engine, and delivers actionable insights via an interactive dashboard and automated reporting.

## Features

- **Realistic Data Engine:** Simulates complex business logic including Pareto spend distribution, contract pricing, and seasonality.
- **Data Quality Framework:** Enforces strict schema integrity and business rule validation.
- **Interactive Analytics:** A Streamlit dashboard for visualizing spend, vendor performance, and savings opportunities.
- **Automated Reporting:** Generates executive-ready PDF summaries.

## Technology Stack

- **Core:** Python 3.8+, Pandas, NumPy, Faker
- **Visualization:** Streamlit, Plotly
- **Reporting:** ReportLab
- **Quality & Testing:** Pytest, Black

## Architecture

The platform operates on a modular pipeline:

1.  **Generator (`src/generator`):** Produces interconnected Parquet datasets (`data/`) using vectorized operations for speed.
2.  **Quality (`src/quality`):** Validates data against defined business constraints.
3.  **Dashboard (`src/dashboard`):** Consumes processed data to render real-time insights.
4.  **Reporting:** Generates static PDF executive summaries.

## Setup Instructions

### Prerequisites

- Python 3.10 or higher. (Dev was carried out in Python 3.11.14)

### Installation Steps

```bash
pip install -r requirements.txt
```

### Configuration

Adjust parameters in `src/generator/sap_generator.py` (volume, dates) or `src/quality/config.py` (validation rules).

### Running the Application

See the Usage Examples below.

## Usage Examples

### Generate Data

```bash
python src/generator/sap_generator.py
```

### Launch Dashboard

```bash
streamlit run src/dashboard/app.py
```

### Run Quality Checks

```bash
python data_quality.py
```

### Run Tests

```bash
pytest
```

## Project Structure

```text
.
├── data/               # Generated Parquet files
├── docs/               # Technical documentation
├── reports/            # Generated PDF reports
├── src/
│   ├── dashboard/      # Streamlit application code
│   ├── generator/      # Data generation logic (LFA1, MARA, etc.)
│   └── quality/        # Data quality validation framework
├── tests/              # Unit and integration tests
├── data_quality.py     # Entry point for quality checks
├── requirements.txt    # Project dependencies
└── README.md           # This file
```

## Key Findings (Illustrative)

The analytics engine demonstrates the platform's ability to uncover critical procurement insights:

- **Hidden Cost Leakage:** The "Savings Opportunities" module successfully isolates "Maverick" spend (off-contract purchasing), quantifying a potential 12% cost reduction by consolidating these purchases under existing framework agreements.
- **Risk Concentration:** Vendor performance segmentation reveals a critical cluster of "Preferred" vendors who, despite favorable pricing, exhibit a sharp decline in On-Time Delivery (OTD) rates (< 70%) during Q4 peak seasons, signaling a need for supply base diversification.
- **Operational Bottlenecks:** Analysis of the Procure-to-Pay cycle (EKBE history) identifies a processing lag in Invoice Receipts for high-value orders (>$50k), where cycle times degrade by 300%, jeopardizing early payment discounts.

## Future Improvements

- **Tera-Scale Architecture ("Entity Partitioning"):** To achieve infinite scaling (e.g., 100M+ contracts), the generation engine should be refactored to use a **Vendor Partition Loop**. By keeping only global Materials (MARA) in memory and iterating through Vendors one-by-one (generating and flushing their specific Contracts and POs to disk immediately), we can bypass the memory ceiling imposed by the `VENDOR_CONTRACTS` table while maintaining perfect referential integrity.
- **Distributed Analytics Layer:** As the dataset grows to terabytes, single-node Pandas processing becomes a bottleneck. Migrating the analytics backend to **Dask** or **Polars** (leveraging lazy evaluation and out-of-core processing) would allow the dashboard to query massive datasets interactively without requiring terabytes of RAM.
- **Orchestration:** While the current script runs linearly, a production environment would require an orchestrator like **Airflow** or **Prefect**. This would manage the dependency graph (Generator -> Quality Checks -> Analytics Cache) and allow for failure recovery at the task level rather than re-running the entire pipeline. Which is fine for smaller data (up to a few GBs), but as soon as we are conducting big data scale generation, orchestration becomes necessary.

## Author

pi22by7 (Piyush Airani)
Email: talk@pi22by7.me / piyushairani@outlook.com
