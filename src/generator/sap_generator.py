"""
SAP Data Generator module.

This module contains the SAPDataGenerator class responsible for generating
realistic SAP procurement data (LFA1, MARA, EKKO, EKPO, EKBE, VENDOR_CONTRACTS)
based on a configurable set of business rules and distributions.
"""

import pandas as pd
import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass, field
from typing import Optional, TypedDict, List, Tuple, Any, cast, Dict
from faker import Faker

fake = Faker()


class CategoryConfig(TypedDict):
    price_range: Tuple[int, int]
    uom_options: List[str]
    weight_range: Tuple[float, float]
    mat_type: str


def _default_material_categories() -> Dict[str, CategoryConfig]:
    """Default material categories configuration."""
    return {
        "ELECT_F": {  # Electronics (Finished)
            "price_range": (1000, 10000),
            "uom_options": ["PC", "EA"],
            "weight_range": (1.0, 20.0),
            "mat_type": "FERT",  # Finished
        },
        "ELECT_P": {  # Electronics (Components/Parts)
            "price_range": (100, 1000),
            "uom_options": ["PC", "EA"],
            "weight_range": (0.1, 2.0),
            "mat_type": "HALB",  # Semifinished
        },
        "OFFICE": {  # Office Supplies
            "price_range": (1, 500),
            "uom_options": ["EA", "BOX", "PAK"],
            "weight_range": (0.1, 5.0),
            "mat_type": "HAWA",  # Trading Goods
        },
        "RAW": {  # Raw Materials
            "price_range": (50, 5000),
            "uom_options": ["KG", "L", "M", "TON"],
            "weight_range": (10.0, 1000.0),
            "mat_type": "ROH",  # Raw Materials
        },
        "SERV": {  # Services
            "price_range": (500, 50000),
            "uom_options": ["AU", "HR", "DAY"],
            "weight_range": (0, 0),  # Intangible
            "mat_type": "DIEN",  # Services
        },
    }


@dataclass
class GeneratorConfig:
    """Configuration parameters for the SAP Data Generator."""

    seed: int = 4242
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"  # match requirements doc

    # Volume settings
    num_vendors: int = 1000
    num_materials: int = 5000
    num_pos: int = 10000
    num_contracts: int = 2000000

    # Business Logic parameters - Vendor Distribution
    pareto_split: float = 0.20  # 20% vendors are top tier
    pareto_spend_share: float = 0.80  # 80% spend goes to top vendors

    # Vendor Preferences
    preferred_vendor_ratio: float = 0.10  # 10% of vendors are preferred
    preferred_price_discount: Tuple[float, float] = (0.10, 0.15)  # 10-15% discount

    # Contract Management
    contract_coverage: float = 0.45  # % of vendor-material pairs with contracts
    contract_discount_range: Tuple[float, float] = (0.05, 0.15)  # 5-15% discount

    # Pricing & Volatility
    price_volatility: float = 0.15  # sigma for price noise

    # Order Management
    large_order_prob: float = 0.05
    large_order_threshold: int = 50000  # Value threshold for large orders
    large_order_value_range: Tuple[int, int] = (15000, 50000)  # Target value range

    # PO Line Item Distribution
    po_item_dist_params: Tuple[float, float] = (1.2, 0.5)  # Log-normal (mu, sigma)
    po_max_items: int = 15  # Maximum items per PO

    # Delivery Performance
    delivery_late_rate: float = 0.25  # base probability of late delivery
    delivery_delay_probs: List[float] = field(
        default_factory=lambda: [
            0.70,
            0.20,
            0.10,
        ]  # Short/Medium/Major delay distribution
    )
    early_delivery_bias: float = (
        0.10  # Reduction in late_prob for earlier expected dates
    )

    # Contract Settings
    contract_duration_range: Tuple[int, int] = (
        365,
        1095,
    )  # Contract validity in days (1-3 years)

    # Invoice Processing
    invoice_generation_rate: float = (
        0.95  # Probability that GR has corresponding invoice
    )
    invoice_processing_range: Tuple[int, int] = (5, 30)  # Days after GR for invoice

    # Seasonality
    seasonality_q4_factor: float = 1.3  # Weight multiplier for Q4 months

    # Organizational Structure
    company_codes: List[str] = field(default_factory=lambda: ["1000", "2000", "3000"])
    currencies: List[str] = field(default_factory=lambda: ["USD", "EUR", "GBP"])
    currency_distribution: List[float] = field(default_factory=lambda: [0.6, 0.3, 0.1])
    purchasing_orgs: List[str] = field(default_factory=lambda: ["ORG1", "ORG2", "ORG3"])
    purchasing_groups: List[str] = field(
        default_factory=lambda: ["GRP1", "GRP2", "GRP3", "GRP4"]
    )
    plants: List[str] = field(default_factory=lambda: ["1000", "2000", "3000", "4000"])

    material_categories: Dict[str, CategoryConfig] = field(
        default_factory=_default_material_categories
    )


class SAPDataGenerator:
    def __init__(self, config: GeneratorConfig):
        self.config = config
        np.random.seed(config.seed)
        Faker.seed(config.seed)

        # in-memory master data storage (for FK lookups)
        self.lfa1: Optional[pd.DataFrame] = None
        self.mara: Optional[pd.DataFrame] = None
        self.contracts: Optional[pd.DataFrame] = None

        # transactional data storage
        self.ekko: Optional[pd.DataFrame] = None
        self.ekpo: Optional[pd.DataFrame] = None
        self.ekbe: Optional[pd.DataFrame] = None

    def generate_all(self):
        """master execution pipeline enforcing strict dependency order."""
        print("1. generating master Data...")
        self._generate_lfa1()  # Vendors
        self._generate_mara()  # Materials

        print("2. generating contract relationships...")
        self._generate_contracts()  # Depends on LFA1 + MARA

        print("3. generating txns...")
        self._generate_ekko()  # PO Headers (Depends on LFA1)
        self._generate_ekpo()  # PO Items (Depends on EKKO + MARA + Contracts)
        self._generate_ekbe()  # History (Depends on EKPO)

        print("4. cleanup...")
        self._cleanup_hidden_columns()

    def _generate_lfa1(self):
        """
        Generate Vendor Master (LFA1).
        Vectorized implementation - no loops except for Faker generation.
        """
        n = self.config.num_vendors
        num_top = int(n * self.config.pareto_split)

        # pareto weights: top 20% get weight=4000, rest get 1 (achieves ~80% spend concentration)
        split = self.config.pareto_split
        share = self.config.pareto_spend_share

        if split > 0 and share < 1.0:
            top_weight = (share * (1 - split)) / (split * (1 - share))
        else:
            top_weight = 1.0

        spend_weight = np.where(np.arange(n) < num_top, top_weight, 1)

        # KTOKK - Preferred Vendor Logic
        num_preferred = int(n * self.config.preferred_vendor_ratio)

        num_pref_top = int(num_preferred * 0.80)
        num_pref_bottom = num_preferred - num_pref_top

        probs = np.random.random(n)
        top_threshold = num_pref_top / num_top if num_top > 0 else 0
        bottom_threshold = num_pref_bottom / (n - num_top) if (n - num_top) > 0 else 0

        conditions = [
            (probs < top_threshold) & (spend_weight == 100),  # Top vendors
            (probs < bottom_threshold) & (spend_weight == 1),  # Bottom vendors
        ]
        ktokk = np.select(conditions, ["PREF", "PREF"], default="STD")

        # SPERR: 5% blocked
        sperr = np.where(np.random.random(n) < 0.05, "X", "")

        # Performance bias
        perf_bias = np.random.normal(0, 2.0, n)

        # Faker fields
        name1 = np.array([fake.company() for _ in range(n)])
        land1 = np.array([fake.country_code() for _ in range(n)])
        ort01 = np.array([fake.city() for _ in range(n)])
        stras = np.array([fake.street_address() for _ in range(n)])
        telf1 = np.array([fake.phone_number() for _ in range(n)])
        smtp_addr = np.array([fake.company_email() for _ in range(n)])

        sim_start = pd.Timestamp(self.config.start_date)
        erdat_end = sim_start
        erdat_start = sim_start - pd.Timedelta(
            days=365 * 5
        )  # Max 5 years before sim start
        erdat = pd.to_datetime(
            np.random.choice(pd.date_range(erdat_start, erdat_end), size=n)
        )

        lifnr = np.array([f"V{i:07d}" for i in range(1, n + 1)])

        self.lfa1 = (
            pd.DataFrame(
                {
                    "LIFNR": lifnr,
                    "NAME1": name1,
                    "LAND1": land1,
                    "ORT01": ort01,
                    "STRAS": stras,
                    "TELF1": telf1,
                    "SMTP_ADDR": smtp_addr,
                    "KTOKK": ktokk,
                    "SPERR": sperr,
                    "ERDAT": erdat,
                    "spend_weight": spend_weight,
                    "perf_bias": perf_bias,
                }
            )
            .sample(frac=1, random_state=self.config.seed)
            .reset_index(drop=True)
        )

    def _generate_mara(self):
        """
        Generate Material Master (MARA).
        weight range and uom depend on material category for realism.
        currently hardcoded distribution of categories.
        Can be extended to config later.
        """

        total_materials = self.config.num_materials
        matnr: List[str] = [f"M{i:08d}" for i in range(1, total_materials + 1)]
        maktx: List[str] = []
        mtart: List[str] = []
        matkl: List[str] = []
        meins: List[str] = []
        ersda: List[pd.Timestamp] = []
        brgew: List[float] = []
        ntgew: List[float] = []
        base_price: List[float] = []

        categories = self.config.material_categories

        # can also be made configurable if needed but deferred for now
        c_elect_f = int(total_materials * 0.20)
        c_elect_p = int(total_materials * 0.15)
        c_office = int(total_materials * 0.30)
        c_raw = int(total_materials * 0.25)

        # Calculate SERV as exact remainder to ensure sum == total_materials
        # -- fix because of an off-by-one error
        c_serv = total_materials - (c_elect_f + c_elect_p + c_office + c_raw)

        counts = {
            "ELECT_F": c_elect_f,
            "ELECT_P": c_elect_p,
            "OFFICE": c_office,
            "RAW": c_raw,
            "SERV": c_serv,
        }

        for category, count in counts.items():

            display_cat = "ELECT" if "ELECT" in category else category
            # hidden column for price anchoring
            batch_prices = np.exp(
                np.random.uniform(
                    np.log(categories[category]["price_range"][0]),
                    np.log(categories[category]["price_range"][1]),
                    count,
                )
            )

            # weight
            if category == "SERV":
                batch_brgew = np.zeros(count)
                batch_ntgew = np.zeros(count)
            else:
                batch_brgew = np.random.uniform(
                    categories[category]["weight_range"][0],
                    categories[category]["weight_range"][1],
                    count,
                )
                batch_ntgew = batch_brgew * np.random.uniform(0.8, 0.99, count)

            # units
            uom_opts = categories[category]["uom_options"]
            batch_meins = np.random.choice(uom_opts, count)

            # desc
            batch_maktx = [f"{display_cat} - {fake.bs()}" for _ in range(count)]

            # creation date, <=start of simulation (max 5 years before)
            sim_start = pd.Timestamp(self.config.start_date)
            ersda_end = sim_start
            ersda_start = sim_start - pd.Timedelta(days=365 * 5)
            ersda_range = (ersda_end - ersda_start).days
            batch_ersda = [
                ersda_start + pd.Timedelta(days=int(np.random.random() * ersda_range))
                for _ in range(count)
            ]

            # assemble the df for the category - extend all lists
            matkl.extend([display_cat] * count)
            mtart.extend([categories[category]["mat_type"]] * count)
            base_price.extend(batch_prices.tolist())
            meins.extend(batch_meins.tolist())
            maktx.extend(batch_maktx)
            ersda.extend(batch_ersda)
            brgew.extend(batch_brgew.tolist())
            ntgew.extend(batch_ntgew.tolist())

        # Generate MATNR based on actual total count
        # - this earlier caused an off-by-one error
        actual_total = len(matkl)
        matnr = [f"M{i:08d}" for i in range(1, actual_total + 1)]

        # create df and shuffle
        self.mara = pd.DataFrame(
            {
                "MATNR": matnr,
                "MAKTX": maktx,
                "MTART": mtart,
                "MATKL": matkl,
                "MEINS": meins,
                "ERSDA": ersda,
                "BRGEW": brgew,
                "NTGEW": ntgew,
                "base_price": base_price,
            }
        )

        self.mara = self.mara.sample(frac=1, random_state=self.config.seed).reset_index(
            drop=True
        )

    def _generate_contracts(self):
        """
        Generate Vendor Contracts (Custom Table).
        discrepancy in requirements doc, 2k minimum, but 40% of 5k*1k=2M,
        so function is designed to handle generation of very large data.
        """
        assert self.lfa1 is not None, "LFA1 must be generated before contracts"
        assert self.mara is not None, "MARA must be generated before contracts"

        target = self.config.num_contracts

        # oversample to compensate for deduplication losses
        target_draws = int(target * 1.5)

        # select vendors weighted by spend
        spend_weights = self.lfa1["spend_weight"].to_numpy()
        p_weights = spend_weights / spend_weights.sum()
        sel_vendors = np.random.choice(
            a=self.lfa1["LIFNR"].to_numpy(),
            size=target_draws,
            replace=True,
            p=p_weights,
        )

        # select materials randomly
        sel_materials = np.random.choice(
            self.mara["MATNR"].to_numpy(), size=target_draws, replace=True
        )

        # temp df for deduplication and price lookup
        temp_df = pd.DataFrame({"LIFNR": sel_vendors, "MATNR": sel_materials})
        temp_df = temp_df.drop_duplicates(subset=["LIFNR", "MATNR"]).reset_index(
            drop=True
        )
        # take exactly target rows after deduplication
        temp_df = temp_df.head(target)
        mara_prices = self.mara[["MATNR", "base_price"]].copy()
        temp_df = temp_df.merge(mara_prices, on="MATNR", how="left")
        n = len(temp_df)

        contract_id = np.array([f"C{i:09d}" for i in range(1, n + 1)])
        base_prices = temp_df["base_price"].to_numpy(dtype=np.float64)

        min_discount, max_discount = self.config.contract_discount_range
        contract_price = base_prices * np.random.uniform(
            1 - max_discount, 1 - min_discount, n
        )

        # dates
        sim_start = pd.Timestamp(self.config.start_date)
        sim_end = pd.Timestamp(self.config.end_date)
        # 3 month runway
        valid_from_end = sim_end - pd.Timedelta(days=90)
        valid_from = pd.to_datetime(
            np.random.choice(pd.date_range(sim_start, valid_from_end), size=n)
        )

        min_duration, max_duration = self.config.contract_duration_range
        duration_days: NDArray[np.int_] = np.random.randint(
            min_duration, max_duration, n
        )
        valid_to = valid_from + pd.to_timedelta(duration_days, unit="D")

        contract_type = np.random.choice(
            ["BLANKET", "SPOT", "FRAMEWORK"], size=n, p=[0.5, 0.4, 0.1]
        )
        volume_commitment = np.random.randint(100, 10000, n)

        # assemble final df at once
        self.contracts = pd.DataFrame(
            {
                "CONTRACT_ID": contract_id,
                "LIFNR": temp_df["LIFNR"].values,
                "MATNR": temp_df["MATNR"].values,
                "CONTRACT_PRICE": contract_price,
                "VALID_FROM": valid_from,
                "VALID_TO": valid_to,
                "VOLUME_COMMITMENT": volume_commitment,
                "CONTRACT_TYPE": contract_type,
            }
        )

    def _generate_ekko(self):
        """
        Generate PO Headers (EKKO).
        """
        n = self.config.num_pos
        sim_end = pd.Timestamp(self.config.end_date)
        cutoff_date = sim_end - pd.Timedelta(days=90)

        date_range = pd.date_range(self.config.start_date, self.config.end_date)

        # Q4 weighted higher for year-end spend
        date_weights: NDArray[np.float64] = np.where(
            date_range.month.isin([10, 11, 12]), self.config.seasonality_q4_factor, 1.0
        )
        date_weights = date_weights / date_weights.sum()

        # po dates
        aedat = np.random.choice(date_range, size=n, p=date_weights)

        # vendor selection
        assert self.lfa1 is not None, "LFA1 must be generated before EKKO"
        spend_weights = self.lfa1["spend_weight"].to_numpy()
        p_weights = spend_weights / spend_weights.sum()
        lifnr = np.random.choice(self.lfa1["LIFNR"].to_numpy(), size=n, p=p_weights)

        # blocked vendors cannot have recent POs
        vendor_meta = pd.DataFrame({"LIFNR": lifnr}).merge(
            self.lfa1[["LIFNR", "SPERR", "ERDAT"]], on="LIFNR", how="left"
        )
        bad_mask = (vendor_meta["SPERR"] == "X") & (aedat >= cutoff_date)

        # categorize bad POs
        impossible_mask = bad_mask & (
            vendor_meta["ERDAT"] >= cutoff_date
        )  # impossible (ERDAT >= cutoff)
        shiftable_mask = bad_mask & (
            vendor_meta["ERDAT"] < cutoff_date
        )  # shiftable (ERDAT < cutoff)

        # shift dates back for shiftable POs to between ERDAT and cutoff (but not before sim start)
        if shiftable_mask.any():
            sim_start = pd.Timestamp(self.config.start_date)
            erdat_vals = pd.DatetimeIndex(
                vendor_meta.loc[shiftable_mask, "ERDAT"].values
            )
            lower_bound = np.maximum(
                erdat_vals, pd.DatetimeIndex([sim_start] * len(erdat_vals))
            )
            days_range = (
                pd.DatetimeIndex([cutoff_date] * len(lower_bound)) - lower_bound
            ).days.to_numpy()

            random_fractions = np.random.random(len(days_range))
            random_offsets: NDArray[np.int_] = (
                random_fractions * np.maximum(days_range, 0)
            ).astype(int)
            aedat[shiftable_mask] = lower_bound + pd.to_timedelta(
                random_offsets, unit="D"
            )

        safe_vendors = self.lfa1[self.lfa1["SPERR"] == ""]["LIFNR"].to_numpy()
        lifnr[impossible_mask] = np.random.choice(
            safe_vendors, size=impossible_mask.sum()
        )

        is_large = np.random.random(n) < self.config.large_order_prob

        nb_prob = np.where(
            is_large,
            np.random.uniform(0.8, 0.95, n),
            np.random.uniform(0.6, 0.8, n),
        )
        bsart = np.where(np.random.random(n) < nb_prob, "NB", "FO")

        ebeln = np.array([f"PO{i:08d}" for i in range(1, n + 1)])

        bukrs = np.random.choice(self.config.company_codes, size=n)
        waers = np.random.choice(
            self.config.currencies, size=n, p=self.config.currency_distribution
        )
        ekorg = np.random.choice(self.config.purchasing_orgs, size=n)
        ekgrp = np.random.choice(self.config.purchasing_groups, size=n)
        bedat = aedat  # document date = PO date

        self.ekko = pd.DataFrame(
            {
                "EBELN": ebeln,
                "BUKRS": bukrs,
                "BSART": bsart,
                "AEDAT": aedat,
                "LIFNR": lifnr,
                "WAERS": waers,
                "EKORG": ekorg,
                "EKGRP": ekgrp,
                "BEDAT": bedat,
                "is_large": is_large,
            }
        )

    def _generate_ekpo(self):
        """
        Generate PO Line Items (EKPO).
        """
        assert self.lfa1 is not None
        assert self.ekko is not None
        assert self.mara is not None
        assert self.contracts is not None
        num_headers = self.config.num_pos

        mu, sigma = self.config.po_item_dist_params
        item_counts = np.random.lognormal(mu, sigma, num_headers).astype(int)
        item_counts = np.clip(item_counts, 1, self.config.po_max_items)
        total_items = item_counts.sum()

        items_df = pd.DataFrame(
            {
                "EBELN": np.repeat(self.ekko["EBELN"].to_numpy(), item_counts),
                "LIFNR": np.repeat(self.ekko["LIFNR"].to_numpy(), item_counts),
                "BSART": np.repeat(self.ekko["BSART"].to_numpy(), item_counts),
                "AEDAT": np.repeat(self.ekko["AEDAT"].to_numpy(), item_counts),
                "is_large": np.repeat(self.ekko["is_large"].to_numpy(), item_counts),
            }
        )

        items_df["EBELP"] = (items_df.groupby("EBELN").cumcount() + 1) * 10

        # material assignment
        items_df["MATNR"] = None
        items_df["KONNR"] = None

        spot_mask = items_df["BSART"] == "FO"
        n_spot = spot_mask.sum()

        items_df.loc[spot_mask, "MATNR"] = np.random.choice(
            self.mara["MATNR"].to_numpy(), size=n_spot
        )

        nb_mask = items_df["BSART"] == "NB"
        nb_rows = items_df[nb_mask].copy()

        rel_lifnrs = nb_rows["LIFNR"].unique()
        contracts_df = self.contracts
        valid_contracts = contracts_df[contracts_df["LIFNR"].isin(rel_lifnrs)]

        nb_rows = nb_rows.sort_values("AEDAT")
        valid_contracts = valid_contracts.sort_values("VALID_FROM")

        # prospective = nb_rows.merge(
        #     valid_contracts[["LIFNR", "MATNR", "CONTRACT_PRICE"]],
        #     on="LIFNR",
        #     how="left",
        # ) # This crashed

        selected = pd.merge_asof(
            nb_rows,
            valid_contracts[
                [
                    "LIFNR",
                    "MATNR",
                    "CONTRACT_PRICE",
                    "VALID_FROM",
                    "VALID_TO",
                    "CONTRACT_ID",
                ]
            ],
            left_on="AEDAT",
            right_on="VALID_FROM",
            by="LIFNR",
            direction="backward",
        )

        valid_mask = selected["AEDAT"] <= selected["VALID_TO"]
        selected = selected.loc[valid_mask].copy()

        # update matched rows using index alignment
        if len(selected) > 0 and "MATNR" in selected.columns:
            items_df.loc[selected.index, "MATNR"] = selected["MATNR"]
            items_df.loc[selected.index, "CONTRACT_PRICE"] = selected["CONTRACT_PRICE"]
            items_df.loc[selected.index, "KONNR"] = selected["CONTRACT_ID"]

        left_nans = items_df["MATNR"].isna()
        items_df.loc[left_nans, "MATNR"] = np.random.choice(
            self.mara["MATNR"].to_numpy(), size=left_nans.sum()
        )

        # price
        items_df = items_df.merge(
            self.mara[["MATNR", "base_price"]],
            on="MATNR",
            how="left",
        )

        items_df = items_df.merge(self.lfa1[["LIFNR", "KTOKK"]], on="LIFNR", how="left")

        noise = np.random.normal(1.0, self.config.price_volatility, total_items)
        spot_price = items_df["base_price"] * noise

        pref_mask = items_df["KTOKK"] == "PREF"

        min_discount, max_discount = self.config.preferred_price_discount
        pref_discount = np.random.uniform(
            1 - max_discount, 1 - min_discount, total_items
        )
        spot_price = np.where(pref_mask, spot_price * pref_discount, spot_price)

        if "CONTRACT_PRICE" in items_df.columns:
            has_contract_mask = items_df["CONTRACT_PRICE"].notna()
            contract_variance = np.random.normal(1.0, 0.01, has_contract_mask.sum())

            items_df["NETPR"] = spot_price  # Default to spot price
            items_df.loc[has_contract_mask, "NETPR"] = (
                items_df.loc[has_contract_mask, "CONTRACT_PRICE"] * contract_variance
            )
        else:
            items_df["NETPR"] = spot_price

        # quantity
        menge_vals: NDArray[np.float64] = np.random.lognormal(1.3, 0.6, total_items)
        items_df["MENGE"] = menge_vals.astype(int)

        # large order management - use configurable thresholds
        large_mask = items_df["is_large"]
        num_large = large_mask.sum()

        if num_large > 0:
            min_val, max_val = self.config.large_order_value_range
            target_val: NDArray[np.float64] = np.random.uniform(
                min_val, max_val, size=num_large
            )

            netpr_large = items_df.loc[large_mask, "NETPR"]

            qty_forced: NDArray[np.int_] = (target_val / netpr_large).astype(int)

            # only  large rows to keep the higher value
            items_df.loc[large_mask, "MENGE"] = np.maximum(
                items_df.loc[large_mask, "MENGE"], qty_forced
            )

        items_df["NETWR"] = items_df["MENGE"] * items_df["NETPR"]

        lead_time_days: NDArray[np.int_] = np.random.randint(5, 30, size=len(items_df))
        items_df["EINDT"] = items_df["AEDAT"] + cast(
            Any, pd.to_timedelta(lead_time_days, unit="D")
        )

        items_df = items_df.merge(
            self.mara[["MATNR", "MATKL", "MEINS"]],
            on="MATNR",
            how="left",
            suffixes=("", "_mara"),  # Handle collision if any
        )

        items_df["WERKS"] = np.random.choice(self.config.plants, size=len(items_df))

        self.ekpo = items_df[
            [
                "EBELN",
                "EBELP",
                "MATNR",
                "MENGE",
                "NETPR",
                "NETWR",
                "EINDT",
                "MATKL",
                "MEINS",
                "WERKS",
                "KONNR",
            ]
        ]

    def _generate_ekbe(self):
        """
        Generate PO History (EKBE).
        """
        assert self.ekpo is not None
        assert self.ekko is not None
        assert self.lfa1 is not None

        base_df = self.ekpo.merge(
            self.ekko[["EBELN", "LIFNR", "AEDAT"]],
            on="EBELN",
            how="left",
        )

        base_df = base_df.merge(
            self.lfa1[["LIFNR", "perf_bias"]],
            on="LIFNR",
            how="left",
        )

        # Delivery Dates
        # with Partial Deliveries (1-3 GRs per item)
        # 1. Identify items to split (e.g., 20% of items)
        n_total = len(base_df)
        split_mask = np.random.random(n_total) < 0.20

        # Non-split items (1 delivery)
        df_single = base_df[~split_mask].copy()

        # Split items (2 deliveries)
        df_split = base_df[split_mask].copy()

        # First delivery (40-60% of quantity)
        df_part1 = df_split.copy()
        ratio1 = np.random.uniform(0.4, 0.6, len(df_part1))
        df_part1["MENGE"] = (df_part1["MENGE"] * ratio1).round(0)
        df_part1["MENGE"] = np.maximum(df_part1["MENGE"], 1)  # Ensure at least 1
        df_part1["NETWR"] = df_part1["MENGE"] * df_part1["NETPR"]

        # Second delivery (Remainder)
        df_part2 = df_split.copy()
        df_part2["MENGE"] = df_split["MENGE"] - df_part1["MENGE"]
        df_part2 = df_part2[df_part2["MENGE"] > 0]  # Drop if nothing left
        df_part2["NETWR"] = df_part2["MENGE"] * df_part2["NETPR"]

        # Combine all
        gr_df = pd.concat([df_single, df_part1, df_part2], ignore_index=True)
        gr_df["BEWTP"] = "E"
        n_gr = len(gr_df)

        base_late_prob = self.config.delivery_late_rate

        # normalize within timeframe
        sim_start = pd.Timestamp(self.config.start_date)
        sim_end = pd.Timestamp(self.config.end_date)
        total_days = (sim_end - sim_start).days

        # normalize the "earliness"
        days_from_start = (gr_df["EINDT"] - sim_start).dt.days
        earliness_factor = 1.0 - (days_from_start / total_days)

        # Reduce late probability for early
        early_adjustment = earliness_factor * self.config.early_delivery_bias

        late_prob = np.clip(
            base_late_prob + (gr_df["perf_bias"] * 0.05) - early_adjustment, 0.05, 0.95
        )
        is_late = np.random.random(n_gr) < late_prob

        delay_days = np.zeros(n_gr, dtype=int)

        if is_late.any():
            n_late = is_late.sum()
            # buckets: 1=Short, 2=Medium, 3=Major
            buckets = np.random.choice(
                [1, 2, 3], size=n_late, p=self.config.delivery_delay_probs
            )

            late_delays = np.zeros(n_late, dtype=int)

            # 1-7 days
            mask_1 = buckets == 1
            late_delays[mask_1] = np.random.randint(1, 8, size=mask_1.sum())

            # 8-14 days
            mask_2 = buckets == 2
            late_delays[mask_2] = np.random.randint(8, 15, size=mask_2.sum())

            # 15-30 days
            mask_3 = buckets == 3
            late_delays[mask_3] = np.random.randint(15, 31, size=mask_3.sum())

            delay_days[is_late] = late_delays

        early_days = np.random.randint(-5, 1, size=n_gr)
        final_days = np.where(is_late, delay_days, early_days)

        # actual delivery date
        gr_df["ACTUAL_DELIVERY_DATE"] = gr_df["EINDT"] + cast(
            Any, pd.to_timedelta(final_days, unit="D")
        )

        too_early_mask = gr_df["ACTUAL_DELIVERY_DATE"] < gr_df["AEDAT"]
        gr_df.loc[too_early_mask, "ACTUAL_DELIVERY_DATE"] = gr_df.loc[
            too_early_mask, "AEDAT"
        ]

        gr_df["BUDAT"] = gr_df["ACTUAL_DELIVERY_DATE"]

        gr_df.rename(columns={"NETWR": "DMBTR"}, inplace=True)

        # Invoice Receipt
        has_invoice = np.random.random(len(gr_df)) < self.config.invoice_generation_rate
        ir_df = gr_df[has_invoice].copy()
        ir_df["BEWTP"] = "Q"

        ir_df["ACTUAL_DELIVERY_DATE"] = pd.NaT

        min_inv, max_inv = self.config.invoice_processing_range
        processing_time = np.random.randint(min_inv, max_inv, size=len(ir_df))
        ir_df["BUDAT"] = ir_df["BUDAT"] + cast(
            Any, pd.to_timedelta(processing_time, unit="D")  # type: ignore[reportUnknownMemberType]
        )

        noise_raw = np.random.normal(0, 0.01, len(ir_df))
        noise_clipped = np.clip(noise_raw, -0.019, 0.019)  # Clip to 1.9%
        price_noise = 1.0 + noise_clipped
        ir_df["DMBTR"] = ir_df["DMBTR"] * price_noise
        ir_df["DMBTR"] = ir_df["DMBTR"].round(2)

        self.ekbe = pd.concat([gr_df, ir_df], ignore_index=True)

        self.ekbe = self.ekbe.sort_values(by=["EBELN", "EBELP", "BUDAT"]).reset_index(
            drop=True
        )

        self.ekbe["BELNR"] = np.array(
            [f"5{i:09d}" for i in range(1, len(self.ekbe) + 1)]
        )

        # Order Accuracy: flag items with quantity/quality issues (8% error rate)
        self.ekbe["HAS_ISSUE"] = np.random.choice(
            [True, False], size=len(self.ekbe), p=[0.08, 0.92]
        )

        # Response Time: Days for vendor to respond to inquiries (1-7 days)
        base_response = np.random.randint(1, 8, size=len(self.ekbe))
        perf_adjustment = (self.ekbe["perf_bias"] * 2).astype(int)
        self.ekbe["RESPONSE_DAYS"] = np.clip(base_response + perf_adjustment, 1, 10)

        self.ekbe = self.ekbe[
            [
                "EBELN",
                "EBELP",
                "BEWTP",
                "BUDAT",
                "MENGE",
                "DMBTR",
                "BELNR",
                "ACTUAL_DELIVERY_DATE",
                "HAS_ISSUE",
                "RESPONSE_DAYS",
            ]
        ].reset_index(drop=True)

    def _cleanup_hidden_columns(self):
        """
        Drop internal helper columns (weights, base_price, bias)
        before saving.
        """
        # Clean LFA1
        if self.lfa1 is not None:
            cols_to_drop = ["spend_weight", "perf_bias"]
            existing = [c for c in cols_to_drop if c in self.lfa1.columns]
            if existing:
                self.lfa1.drop(columns=existing, inplace=True)

        # Clean MARA
        if self.mara is not None:
            cols_to_drop = ["base_price"]
            existing = [c for c in cols_to_drop if c in self.mara.columns]
            if existing:
                self.mara.drop(columns=existing, inplace=True)

        # Clean EKKO
        if self.ekko is not None:
            cols_to_drop = ["is_large"]
            existing = [c for c in cols_to_drop if c in self.ekko.columns]
            if existing:
                self.ekko.drop(columns=existing, inplace=True)

    def save_to_parquet(self, output_dir: str):
        """Save all dataframes to Parquet."""
        import os

        os.makedirs(output_dir, exist_ok=True)

        data_map = {
            "LFA1": self.lfa1,
            "MARA": self.mara,
            "VENDOR_CONTRACTS": self.contracts,
            "EKKO": self.ekko,
            "EKPO": self.ekpo,
            "EKBE": self.ekbe,
        }

        print(f"\nSaving data to '{output_dir}/'...")

        for name, df in data_map.items():
            if df is not None and not df.empty:
                file_path = os.path.join(output_dir, f"{name}.parquet")
                df.to_parquet(file_path, index=False)
                print(f"✓ {name}: Saved {len(df):,} rows")
            else:
                print(f"⚠ {name}: Dataframe is empty or None, skipping.")

    def print_summary_stats(self):
        print("\n--- GENERATION SUMMARY ---")

        # Check if required data exists
        if (
            self.ekpo is None
            or self.ekko is None
            or self.ekbe is None
            or self.lfa1 is None
        ):
            print("Error: Required data not generated yet.")
            return

        # 1. Total Spend
        total_spend = self.ekpo["NETWR"].sum()
        print(f"Total Spend: ${total_spend:,.2f}")

        # 2. Contract vs Non-Contract (based on EKKO BSART)
        merged = self.ekpo.merge(self.ekko[["EBELN", "BSART"]], on="EBELN")
        spend_by_type = merged.groupby("BSART")["NETWR"].sum()
        print("\nSpend by PO Type:")
        print(spend_by_type.apply(lambda x: f"${x:,.2f}"))

        # 3. Delivery Performance
        grs = self.ekbe[self.ekbe["BEWTP"] == "E"].merge(
            self.ekpo[["EBELN", "EBELP", "EINDT"]], on=["EBELN", "EBELP"]
        )
        date_col = (
            "ACTUAL_DELIVERY_DATE" if "ACTUAL_DELIVERY_DATE" in grs.columns else "BUDAT"
        )
        late_mask = grs[date_col] > grs["EINDT"]
        late_pct = late_mask.mean() * 100
        print(f"\nDelivery Performance: {late_pct:.1f}% Late Deliveries")

        # 4. Top 5 Vendors
        vendor_spend = (
            self.ekpo.merge(self.ekko[["EBELN", "LIFNR"]], on="EBELN")
            .groupby("LIFNR")["NETWR"]
            .sum()
            .nlargest(5)
        )
        print("\nTop 5 Vendors by Spend:")
        top_vendors = vendor_spend.reset_index().merge(
            self.lfa1[["LIFNR", "NAME1"]], on="LIFNR"
        )
        for _, row in top_vendors.iterrows():
            print(f"- {row['NAME1']} ({row['LIFNR']}): ${row['NETWR']:,.2f}")


if __name__ == "__main__":
    # config
    config = GeneratorConfig(
        seed=42,
        num_vendors=1000,
        num_materials=5000,
        num_pos=10000,  # 10k Headers -> ~40k Items -> ~60k History
        num_contracts=2000,
    )

    generator = SAPDataGenerator(config)
    generator.generate_all()

    generator.save_to_parquet("data")

    print("\nGeneration Complete.")

    generator.print_summary_stats()
