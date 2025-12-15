"""
Core Data Quality Engine.
Executes all validation rules defined in requirements.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from src.quality.config import REQUIRED_TABLES, SCHEMA_RULES, THRESHOLDS
from src.quality.utils import generate_html_report


class DQCore:
    def __init__(self, data_path="data", report_path="reports"):
        self.data_path = data_path
        self.report_path = report_path
        self.data = {}
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "score": 100,
            "checks": [],
            "profile": {},
        }

    def load_data(self):
        print("⏳ Loading data...")
        try:
            for table in REQUIRED_TABLES:
                self.data[table] = pd.read_parquet(f"{self.data_path}/{table}.parquet")

            self.results["profile"]["record_counts"] = {
                table: len(self.data[table]) for table in REQUIRED_TABLES
            }

            ekko = self.data["EKKO"]
            ekpo = self.data["EKPO"]
            ekbe = self.data["EKBE"]

            self.results["profile"]["cardinality"] = {
                "avg_items_per_po": len(ekpo) / len(ekko) if len(ekko) > 0 else 0,
                "avg_receipts_per_item": (
                    len(ekbe[ekbe["BEWTP"] == "E"]) / len(ekpo) if len(ekpo) > 0 else 0
                ),
                "avg_invoices_per_item": (
                    len(ekbe[ekbe["BEWTP"] == "Q"]) / len(ekpo) if len(ekpo) > 0 else 0
                ),
            }

            return True
        except Exception as e:
            print(f"❌ Load Error: {e}")
            return False

    def log(self, category, name, status, msg, examples=None, severity="Info"):
        """Central logging with score penalty logic"""
        penalty = 15 if severity == "Critical" else 5 if severity == "Warning" else 0
        if status == "FAIL":
            self.results["score"] = max(0, self.results["score"] - penalty)
        elif status == "WARN":
            self.results["score"] = max(0, self.results["score"] - 2)

        self.results["checks"].append(
            {
                "category": category,
                "name": name,
                "status": status,
                "message": msg,
                "examples": examples,
                "severity": severity,
            }
        )

        # Console output
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{icon} [{category}] {name}: {msg}")

    def run_schema_checks(self):
        """Validates Schema, Types, and Constraints."""
        for table, rules in SCHEMA_RULES.items():
            df = self.data[table]

            # 1. Required Fields & Nulls
            for col in rules["required"]:
                if col not in df.columns:
                    self.log(
                        "Schema",
                        f"{table} Missing {col}",
                        "FAIL",
                        "Field missing",
                        severity="Critical",
                    )
                    continue

                nulls = df[col].isnull().sum()
                if nulls > 0:
                    ex = df[df[col].isnull()].index.tolist()[:3]
                    self.log(
                        "Schema",
                        f"{table}.{col} Nulls",
                        "FAIL",
                        f"{nulls} nulls found",
                        examples=ex,
                        severity="Critical",
                    )

            # 2. Constraints (Field Length)
            for col, max_len in rules.get("constraints", {}).items():
                if col in df.columns and df[col].dtype == "object":
                    invalids = df[df[col].str.len() > max_len]
                    if not invalids.empty:
                        self.log(
                            "Schema",
                            f"{table}.{col} Length",
                            "FAIL",
                            f"Exceeds {max_len} chars",
                            examples=invalids[col].head(3).tolist(),
                            severity="Warning",
                        )

            # 3. ISO Currency
            if "iso_currency" in rules:
                col = rules["iso_currency"]
                bad_iso = df[~df[col].str.match(r"^[A-Z]{3}$")]
                if not bad_iso.empty:
                    self.log(
                        "Schema",
                        "ISO Currency",
                        "FAIL",
                        f"{len(bad_iso)} invalid codes",
                        examples=bad_iso[col].head(3).tolist(),
                    )

            # 4. Date Type Validation
            date_cols = [
                c
                for c in rules["required"]
                if any(x in c for x in ["DAT", "TIME", "VALID_"])
            ]
            for col in date_cols:
                if col in df.columns:
                    if not pd.api.types.is_datetime64_any_dtype(df[col]):
                        self.log(
                            "Schema",
                            f"{table}.{col} Type",
                            "FAIL",
                            f"Not a valid datetime (Found: {df[col].dtype})",
                            severity="Warning",
                        )

            if table == "EKBE" and "ACTUAL_DELIVERY_DATE" in df.columns:
                invalid_gr = df[
                    (df["BEWTP"] == "E") & (df["ACTUAL_DELIVERY_DATE"].isnull())
                ]
                if not invalid_gr.empty:
                    self.log(
                        "Schema",
                        "EKBE.ACTUAL_DELIVERY_DATE Completeness",
                        "FAIL",
                        f"{len(invalid_gr)} GRs missing Actual Delivery Date",
                        examples=invalid_gr.index.tolist()[:3],
                        severity="Critical",
                    )

    def run_integrity_checks(self):
        """Validates Foreign Keys."""

        def check_fk(src_t, src_c, tgt_t, tgt_c, label):
            left, right = self.data[src_t], self.data[tgt_t]
            missing = left[~left[src_c].isin(right[tgt_c])]
            if not missing.empty:
                self.log(
                    "Integrity",
                    label,
                    "FAIL",
                    f"{len(missing)} orphan records",
                    examples=missing[src_c].head(3).tolist(),
                    severity="Critical",
                )
            else:
                self.log("Integrity", label, "PASS", "Valid")

        check_fk("EKPO", "EBELN", "EKKO", "EBELN", "EKPO->EKKO")
        check_fk("EKKO", "LIFNR", "LFA1", "LIFNR", "EKKO->LFA1")
        check_fk("EKPO", "MATNR", "MARA", "MATNR", "EKPO->MARA")
        check_fk("VENDOR_CONTRACTS", "LIFNR", "LFA1", "LIFNR", "CONTRACTS->LFA1")
        check_fk("VENDOR_CONTRACTS", "MATNR", "MARA", "MATNR", "CONTRACTS->MARA")

        # EKBE Integrity (Composite Key Check)
        ekbe, ekpo = self.data["EKBE"], self.data["EKPO"]
        valid_keys = set(zip(ekpo["EBELN"], ekpo["EBELP"]))
        test_keys = set(zip(ekbe["EBELN"], ekbe["EBELP"]))
        if not test_keys.issubset(valid_keys):
            self.log(
                "Integrity",
                "EKBE->EKPO",
                "FAIL",
                "History records exist for missing items",
                severity="Critical",
            )
        else:
            self.log("Integrity", "EKBE->EKPO", "PASS", "Valid")

    def run_business_logic(self):
        """Validates Business Rules."""
        ekpo = self.data["EKPO"]
        ekko = self.data["EKKO"]
        contracts = self.data["VENDOR_CONTRACTS"]
        ekbe = self.data["EKBE"]
        lfa1 = self.data["LFA1"]

        # 1. NETWR Calculation (Within 1% tolerance)
        calc = ekpo["MENGE"] * ekpo["NETPR"]
        diff = np.abs(ekpo["NETWR"] - calc)
        failures = ekpo[diff > (ekpo["NETWR"] * THRESHOLDS["netwr_tolerance"])]
        if not failures.empty:
            self.log(
                "Logic",
                "Net Value",
                "FAIL",
                f"{len(failures)} mismatch calculations",
                severity="Warning",
            )
        else:
            self.log("Logic", "Net Value", "PASS", "Correct")

        # 2. Delivery Dates (EINDT >= AEDAT)
        merged = ekpo.merge(ekko[["EBELN", "AEDAT"]], on="EBELN")
        early = merged[merged["EINDT"] < merged["AEDAT"]]
        if not early.empty:
            self.log(
                "Logic",
                "Delivery Dates",
                "FAIL",
                f"{len(early)} items delivered before PO date",
            )
        else:
            self.log("Logic", "Delivery Dates", "PASS", "Valid")

        # 3. Contract Logic (Dates)
        invalid_dates = contracts[contracts["VALID_TO"] <= contracts["VALID_FROM"]]
        if not invalid_dates.empty:
            self.log(
                "Logic",
                "Contract Dates",
                "FAIL",
                f"{len(invalid_dates)} contracts end before start",
                severity="Critical",
            )

        # 4. Invoice Logic (Amounts & Dates)
        # Handle multiple GRs/IRs per item by matching
        grs = ekbe[ekbe["BEWTP"] == "E"].copy()
        invs = ekbe[ekbe["BEWTP"] == "Q"].copy()

        if "PAIR_ID" in ekbe.columns:
            # Robust matching using generated linkage ID
            matched = pd.merge(
                grs,
                invs,
                on=["EBELN", "EBELP", "PAIR_ID"],
                suffixes=("_GR", "_INV"),
            )
        else:
            # Fallback: Sort by Date and Sequence (Best Guess)
            grs = grs.sort_values(["EBELN", "EBELP", "BUDAT", "BELNR"])
            invs = invs.sort_values(["EBELN", "EBELP", "BUDAT", "BELNR"])

            grs["seq"] = grs.groupby(["EBELN", "EBELP"]).cumcount()
            invs["seq"] = invs.groupby(["EBELN", "EBELP"]).cumcount()

            matched = pd.merge(
                grs, invs, on=["EBELN", "EBELP", "seq"], suffixes=("_GR", "_INV")
            )

        # Amount (2% tolerance)
        diff_amt = np.abs(matched["DMBTR_GR"] - matched["DMBTR_INV"])
        tol = matched["DMBTR_GR"] * THRESHOLDS["invoice_amt_tol"]
        #  a llow small rounding errors (e.g. 0.01)
        bad_amts = matched[(diff_amt > tol) & (diff_amt > 0.01)]

        if not bad_amts.empty:
            self.log(
                "Logic",
                "Invoice Amounts",
                "FAIL",
                f"{len(bad_amts)} mismatches > 2%",
                severity="Warning",
            )
        else:
            self.log("Logic", "Invoice Amounts", "PASS", "Correct")

        # Date Sequence (Invoice > GR)
        bad_dates = matched[matched["BUDAT_INV"] < matched["BUDAT_GR"]]
        if not bad_dates.empty:
            self.log(
                "Logic",
                "Invoice Sequence",
                "FAIL",
                f"{len(bad_dates)} invoices posted before GR",
                severity="Warning",
            )
        else:
            self.log("Logic", "Invoice Sequence", "PASS", "Valid")

        # 5. Blocked Vendors (No POs in last 90 days)
        blocked_lifnr = lfa1[lfa1["SPERR"] == "X"]["LIFNR"]
        sim_end = pd.to_datetime(ekko["AEDAT"]).max()
        cutoff = sim_end - pd.Timedelta(days=90)

        suspicious = ekko[
            (ekko["LIFNR"].isin(blocked_lifnr))
            & (pd.to_datetime(ekko["AEDAT"]) > cutoff)
        ]
        if not suspicious.empty:
            self.log(
                "Logic",
                "Blocked Vendors",
                "FAIL",
                f"{len(suspicious)} POs for blocked vendors recently",
                severity="Critical",
            )
        else:
            self.log("Logic", "Blocked Vendors", "PASS", "No recent activity")

        # 6. Contract Price Consistency
        self.check_contract_price_compliance()

    def check_contract_price_compliance(self):
        """
        Validates Contract Price Consistency.
        Contract prices within 5% of PO prices for contract POs (BSART='NB').
        Only checks items that explicitly reference a contract (KONNR is present).
        """
        ekpo = self.data["EKPO"]
        contracts = self.data["VENDOR_CONTRACTS"]

        if "KONNR" not in ekpo.columns:
            self.log(
                "Logic",
                "Contract Price Consistency",
                "WARN",
                "KONNR missing in EKPO, skipping check",
            )
            return

        contract_items = ekpo[ekpo["KONNR"].notna()].copy()

        if contract_items.empty:
            self.log(
                "Logic",
                "Contract Price Consistency",
                "PASS",
                "No items with KONNR found",
            )
            return

        with_contract = contract_items.merge(
            contracts[["CONTRACT_ID", "CONTRACT_PRICE"]],
            left_on="KONNR",
            right_on="CONTRACT_ID",
            how="left",
        )

        found_contracts = with_contract[with_contract["CONTRACT_PRICE"].notna()]

        if not found_contracts.empty:
            price_variance = (
                np.abs(found_contracts["NETPR"] - found_contracts["CONTRACT_PRICE"])
                / found_contracts["CONTRACT_PRICE"]
            )
            violations = found_contracts[
                price_variance > THRESHOLDS["contract_price_tol"]
            ]

            if not violations.empty:
                self.results["profile"]["price_variance"] = price_variance.tolist()
                examples = (
                    violations[["EBELN", "EBELP"]]
                    .head(3)
                    .apply(lambda x: f"{x['EBELN']}-{x['EBELP']}", axis=1)
                    .tolist()
                )
                self.log(
                    "Logic",
                    "Contract Price Consistency",
                    "FAIL",
                    f"{len(violations)} items deviate >5% from contract price",
                    examples=examples,
                    severity="Critical",
                )
            else:
                self.log(
                    "Logic",
                    "Contract Price Consistency",
                    "PASS",
                    "All contract items match contract prices",
                )
        else:
            self.log(
                "Logic",
                "Contract Price Consistency",
                "WARN",
                "Items have KONNR but contract not found in Master Data",
            )

    def run_stats_and_completeness(self):
        """Validates Statistics & Completeness."""
        ekpo = self.data["EKPO"]
        ekbe = self.data["EKBE"]
        ekko = self.data["EKKO"]
        mara = self.data["MARA"]

        # 1. Pareto Check
        spend = (
            ekpo.groupby(ekpo.merge(ekko, on="EBELN")["LIFNR"])["NETWR"]
            .sum()
            .sort_values(ascending=False)
        )
        top_20_count = int(len(spend) * 0.2)
        top_20_sum = spend.iloc[:top_20_count].sum()
        ratio = top_20_sum / spend.sum()

        self.results["profile"]["pareto_pct"] = ratio * 100
        target = THRESHOLDS["pareto_share"]
        if target[0] <= ratio <= target[1]:
            self.log("Stats", "Pareto Dist", "PASS", f"Top 20% = {ratio:.1%} spend")
        else:
            self.log(
                "Stats", "Pareto Dist", "WARN", f"Ratio {ratio:.1%} outside {target}"
            )

        # 2. Contract Compliance
        nb_count = len(ekko[ekko["BSART"] == "NB"])
        compliance_rate = nb_count / len(ekko)
        tgt_comp = THRESHOLDS["contract_rate"]
        if tgt_comp[0] <= compliance_rate <= tgt_comp[1]:
            self.log(
                "Stats", "Contract Compliance", "PASS", f"Rate {compliance_rate:.1%}"
            )
        else:
            self.log(
                "Stats",
                "Contract Compliance",
                "WARN",
                f"Rate {compliance_rate:.1%} outside {tgt_comp}",
            )

        # 3. Late Delivery Rate 20-30%
        grs = ekbe[ekbe["BEWTP"] == "E"].merge(
            ekpo[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"]
        )
        late = grs[pd.to_datetime(grs["BUDAT"]) > pd.to_datetime(grs["EINDT"])]
        late_rate = len(late) / len(grs)

        self.results["profile"]["late_pct"] = late_rate * 100
        tgt_late = THRESHOLDS["late_delivery_rate"]
        if tgt_late[0] <= late_rate <= tgt_late[1]:
            self.log("Stats", "Late Delivery Rate", "PASS", f"Rate {late_rate:.1%}")
        else:
            self.log(
                "Stats",
                "Late Delivery Rate",
                "WARN",
                f"Rate {late_rate:.1%} outside {tgt_late}",
            )

        # 4. GR/IR Ratio (~1:1
        counts = ekbe["BEWTP"].value_counts()
        gr, ir = counts.get("E", 0), counts.get("Q", 0)
        ratio = ir / gr if gr > 0 else 0
        if 0.9 <= ratio <= 1.1:
            self.log("Stats", "GR/IR Ratio", "PASS", f"Ratio {ratio:.2f}")
        else:
            self.log("Stats", "GR/IR Ratio", "WARN", f"Imbalanced: {ratio:.2f}")

        # 5. Price Outliers (3 Std Dev)

        if "MATKL" in ekpo.columns:
            # Filter out rows with missing MATKL
            ekpo_with_matkl = ekpo.dropna(subset=["MATKL"])

            def check_outliers(group):
                # Use log-transformed prices for outlier detection
                log_prices = np.log1p(group["NETPR"])
                mean = log_prices.mean()
                std = log_prices.std()
                if std == 0:
                    return 0
                # Identify outliers (> 3 sigma on log scale)
                outliers = group[np.abs(log_prices - mean) > (3 * std)]
                return len(outliers)

            if len(ekpo_with_matkl) > 0:
                total_outliers = (
                    ekpo_with_matkl.groupby("MATKL", dropna=True)
                    .apply(check_outliers, include_groups=False)
                    .sum()
                )
            else:
                total_outliers = 0

            if total_outliers > (len(ekpo) * 0.01):  # Allow 1% outliers max
                self.log(
                    "Stats",
                    "Price Outliers",
                    "WARN",
                    f"{total_outliers} extreme price outliers found",
                )
            else:
                self.log("Stats", "Price Outliers", "PASS", "No significant outliers")
        else:
            self.log(
                "Stats", "Price Outliers", "PASS", "MATKL not available for analysis"
            )

        # 6. Material Balance (No category > 40%)
        counts = mara["MATKL"].value_counts(normalize=True)
        if (counts > 0.40).any():
            self.log(
                "Completeness",
                "Material Balance",
                "FAIL",
                "Category imbalance > 40%",
                severity="Warning",
            )
        else:
            self.log("Completeness", "Material Balance", "PASS", "Balanced")

        # 7. Completeness Checks
        empty_pos = ekko[~ekko["EBELN"].isin(ekpo["EBELN"])]
        if not empty_pos.empty:
            self.log(
                "Completeness",
                "Empty POs",
                "FAIL",
                f"{len(empty_pos)} POs have no items",
                severity="Warning",
            )
        else:
            self.log("Completeness", "Empty POs", "PASS", "Valid")

        items_with_gr = ekpo.merge(
            ekbe[ekbe["BEWTP"] == "E"], on=["EBELN", "EBELP"], how="inner"
        )
        items_with_gr = items_with_gr[["EBELN", "EBELP"]].drop_duplicates()

        coverage = len(items_with_gr) / len(ekpo)

        if coverage < 1.0:
            missing_gr = len(ekpo) - len(items_with_gr)
            self.log(
                "Completeness",
                "GR Coverage",
                "FAIL",
                f"Missing GR for {missing_gr} items ({coverage:.1%})",
                severity="Critical",
            )
        else:
            self.log(
                "Completeness", "GR Coverage", "PASS", f"Full coverage: {coverage:.1%}"
            )

        # Date ranges correct (2020-2024)
        min_date = pd.to_datetime(ekko["AEDAT"]).min()
        max_date = pd.to_datetime(ekko["AEDAT"]).max()
        if min_date.year >= 2020 and max_date.year <= 2024:
            self.log(
                "Completeness",
                "Date Range",
                "PASS",
                f"{min_date.date()} to {max_date.date()}",
            )
        else:
            self.log(
                "Completeness",
                "Date Range",
                "FAIL",
                f"Dates {min_date.date()}-{max_date.date()} out of scope",
            )

    def run(self):
        print("🚀 Starting Validation...")
        if not self.load_data():
            return False

        self.run_schema_checks()
        self.run_integrity_checks()
        self.run_business_logic()
        self.run_stats_and_completeness()

        generate_html_report(self.results, self.report_path)
        print(f"🏁 Validation Complete. Score: {self.results['score']}/100")
        return True
