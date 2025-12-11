import pandas as pd
import numpy as np
from numpy.typing import NDArray
from dataclasses import dataclass
from typing import Optional, TypedDict, List, Tuple, Any, cast
from faker import Faker

fake = Faker()


class CategoryConfig(TypedDict):
    price_range: Tuple[int, int]
    uom_options: List[str]
    weight_range: Tuple[float, float]
    mat_type: str


@dataclass
class GeneratorConfig:
    """Configuration parameters for the SAP Data Generator."""

    seed: int = 4242
    start_date: str = "2020-01-01"
    end_date: str = "2025-12-31"

    # Volume settings
    num_vendors: int = 1000
    num_materials: int = 5000
    num_pos: int = 10000
    num_contracts: int = 2000000

    # Business Logic parameters
    pareto_split: float = 0.20  # 20% vendors
    pareto_spend_share: float = 0.80  # 80% spend
    # % of vendor-material pairs with contracts
    contract_coverage: float = 0.45
    # Probability of a 'large' order (>50k)
    large_order_prob: float = 0.05


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

        # pareto weights: top 20% get weight=100, rest get 1
        spend_weight = np.where(np.arange(n) < num_top, 100, 1)

        # KTOKK
        # top vendors: 40% chance PREF, Others: 5% chance PREF
        probs = np.random.random(n)
        conditions = [
            (probs < 0.40) & (spend_weight == 100),  # Top vendors, lucky
            (probs < 0.05) & (spend_weight == 1),  # Bottom vendors, lucky
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

        # Dates
        sim_start = pd.Timestamp(self.config.start_date)
        erdat_end = sim_start - pd.Timedelta(days=1)
        erdat_start = sim_start - pd.Timedelta(days=365 * 10)
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

        categories: dict[str, CategoryConfig] = {
            "ELECT": {  # Electronics
                "price_range": (100, 10000),
                "uom_options": ["PC", "EA"],
                "weight_range": (0.5, 20.0),  # kg
                # Finished Goods
                "mat_type": "FERT",
            },
            "OFFICE": {  # Office Supplies
                "price_range": (1, 500),
                "uom_options": ["EA", "BOX", "PAK"],
                "weight_range": (0.1, 5.0),
                # Trading Goods
                "mat_type": "HAWA",
            },
            "RAW": {  # Raw Materials
                "price_range": (50, 5000),
                "uom_options": ["KG", "L", "M", "TON"],
                "weight_range": (10.0, 1000.0),
                # Raw Materials
                "mat_type": "ROH",
            },
            "SERV": {  # Services
                "price_range": (500, 50000),
                "uom_options": ["AU", "HR", "DAY"],  # Activity Unit, Hour, Day
                "weight_range": (0, 0),  # Intangible
                "mat_type": "DIEN",  # Services
            },
        }

        counts = {
            "ELECT": int(total_materials * 0.35),
            "OFFICE": int(total_materials * 0.30),
            "RAW": int(total_materials * 0.25),
            # subtracted to ensure rounding errors don't leave
            # unaccounted materials
            "SERV": total_materials - int(total_materials * 0.9),
        }

        for category, count in counts.items():
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
            batch_maktx = [f"{category} - {fake.bs()}" for _ in range(count)]

            # creation date, <=start of simulation
            sim_start = pd.Timestamp(self.config.start_date)
            ersda_end = sim_start - pd.Timedelta(days=1)
            ersda_start = sim_start - pd.Timedelta(days=365 * 10)
            ersda_range = (ersda_end - ersda_start).days
            batch_ersda = [
                ersda_start + pd.Timedelta(days=int(np.random.random() * ersda_range))
                for _ in range(count)
            ]

            # assemble the df for the category - extend all lists
            matkl.extend([category] * count)
            mtart.extend([categories[category]["mat_type"]] * count)
            base_price.extend(batch_prices.tolist())
            meins.extend(batch_meins.tolist())
            maktx.extend(batch_maktx)
            ersda.extend(batch_ersda)
            brgew.extend(batch_brgew.tolist())
            ntgew.extend(batch_ntgew.tolist())

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
        contract_price = base_prices * np.random.uniform(0.85, 0.95, n)

        # dates
        sim_start = pd.Timestamp(self.config.start_date)
        sim_end = pd.Timestamp(self.config.end_date)
        # 3 month runway
        valid_from_end = sim_end - pd.Timedelta(days=90)
        valid_from = pd.to_datetime(
            np.random.choice(pd.date_range(sim_start, valid_from_end), size=n)
        )
        duration_days: NDArray[np.int_] = np.random.randint(365, 1095, n)
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
            date_range.month.isin([10, 11, 12]), 1.3, 1.0
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

        # shift dates back for shiftable POs to between ERDAT and cutoff
        if shiftable_mask.any():
            erdat_vals = pd.DatetimeIndex(
                vendor_meta.loc[shiftable_mask, "ERDAT"].values
            )
            days_range = (
                pd.DatetimeIndex([cutoff_date] * len(erdat_vals)) - erdat_vals
            ).days.to_numpy()

            random_fractions = np.random.random(len(days_range))
            random_offsets: NDArray[np.int_] = (
                random_fractions * np.maximum(days_range, 0)
            ).astype(int)
            aedat[shiftable_mask] = (
                erdat_vals + pd.to_timedelta(random_offsets, unit="D")
            ).to_numpy()

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

        ebeln = np.array([f"PO{i:010d}" for i in range(1, n + 1)])

        # company codes
        bukrs = np.random.choice(["1000", "2000", "3000"], size=n)
        # Currencies
        waers = np.random.choice(["USD", "EUR", "GBP"], size=n, p=[0.6, 0.3, 0.1])
        # purchasing orgs
        ekorg = np.random.choice(["ORG1", "ORG2", "ORG3"], size=n)
        # purchasing groups
        ekgrp = np.random.choice(["GRP1", "GRP2", "GRP3", "GRP4"], size=n)
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
        assert self.ekko is not None
        assert self.mara is not None
        assert self.contracts is not None
        num_headers = self.config.num_pos

        mu, sigma = 1.2, 0.5
        item_counts = np.random.lognormal(mu, sigma, num_headers).astype(int)
        item_counts = np.clip(item_counts, 1, 15)  # limit to 15 items max
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
                ]
            ],
            left_on="AEDAT",
            right_on="VALID_FROM",
            by="LIFNR",
            direction="backward",
        )

        valid_mask = selected["AEDAT"] <= selected["VALID_TO"]
        selected = selected.loc[valid_mask].copy()

        # ipdate matched rows using index alignment
        if len(selected) > 0 and "MATNR" in selected.columns:
            items_df.loc[selected.index, "MATNR"] = selected["MATNR"]
            items_df.loc[selected.index, "CONTRACT_PRICE"] = selected["CONTRACT_PRICE"]

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

        # Add price noise for spot items
        noise: NDArray[np.float64] = np.random.normal(1.0, 0.15, total_items)
        spot_price: pd.Series[Any] = items_df["base_price"] * noise

        if "CONTRACT_PRICE" in items_df.columns:
            items_df["NETPR"] = np.where(
                items_df["CONTRACT_PRICE"].notna(),
                items_df["CONTRACT_PRICE"],
                spot_price,
            )
        else:
            items_df["NETPR"] = spot_price

        # quantity
        menge_vals: NDArray[np.float64] = np.random.lognormal(1.3, 0.6, total_items)
        items_df["MENGE"] = menge_vals.astype(int)

        # large order management
        large_mask = items_df["is_large"]
        num_large = large_mask.sum()

        if num_large > 0:
            target_val: NDArray[np.float64] = np.random.uniform(
                15000, 50000, size=num_large
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

        self.ekpo = items_df[
            [
                "EBELN",
                "EBELP",
                "MATNR",
                "MENGE",
                "NETPR",
                "NETWR",
                "EINDT",
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

        gr_df = base_df.copy()
        gr_df["BEWTP"] = "E"

        noise = np.random.normal(1.5, 2.0, len(gr_df))

        total_delay = (gr_df["perf_bias"] + noise).astype(int)

        gr_df["BUDAT"] = gr_df["EINDT"] + cast(
            Any, pd.to_timedelta(total_delay, unit="D")  # type: ignore[reportUnknownMemberType]
        )

        early_mask = gr_df["BUDAT"] < gr_df["AEDAT"]
        gr_df.loc[early_mask, "BUDAT"] = gr_df.loc[early_mask, "AEDAT"] + cast(
            Any,
            pd.to_timedelta(np.random.randint(0, 2, size=early_mask.sum()), unit="D"),
        )

        gr_df.rename(columns={"NETWR": "DMBTR"}, inplace=True)

        has_invoice = np.random.random(len(gr_df)) < 0.95
        ir_df = gr_df[has_invoice].copy()
        ir_df["BEWTP"] = "Q"

        processing_time = np.random.randint(5, 30, size=len(ir_df))
        ir_df["BUDAT"] = ir_df["BUDAT"] + cast(
            Any, pd.to_timedelta(processing_time, unit="D")  # type: ignore[reportUnknownMemberType]
        )

        price_noise = np.random.normal(1.0, 0.02, len(ir_df))
        ir_df["DMBTR"] = ir_df["DMBTR"] * price_noise
        ir_df["DMBTR"] = ir_df["DMBTR"].round(2)

        self.ekbe = pd.concat([gr_df, ir_df], ignore_index=True)[
            ["EBELN", "EBELP", "BEWTP", "BUDAT", "MENGE", "DMBTR"]
        ]

        self.ekbe = self.ekbe.sort_values(by=["EBELN", "EBELP", "BUDAT"]).reset_index(
            drop=True
        )

        self.ekbe["BELNR"] = np.array(
            [f"5{i:09d}" for i in range(1, len(self.ekbe) + 1)]
        )

        self.ekbe = self.ekbe[
            ["EBELN", "EBELP", "BEWTP", "BUDAT", "MENGE", "DMBTR", "BELNR"]
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


if __name__ == "__main__":
    # config
    config = GeneratorConfig(
        seed=42,
        num_vendors=1000,
        num_materials=5000,
        num_pos=10000,  # 10k Headers -> ~40k Items -> ~60k History
        num_contracts=2000000,  # 2k Contracts
    )

    generator = SAPDataGenerator(config)
    generator.generate_all()

    generator.save_to_parquet("data")

    print("\nGeneration Complete.")
