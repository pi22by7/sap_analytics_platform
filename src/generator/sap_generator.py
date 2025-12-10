import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()


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

    # Business Logic parameters
    pareto_split: float = 0.20  # 20% vendors
    pareto_spend_share: float = 0.80  # 80% spend
    contract_coverage: float = 0.45  # % of vendor-material pairs with contracts
    whale_order_prob: float = 0.05  # Probability of a 'Whale' order (>50k)


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
        Refer to plan.md for logic details during dev (update this docstring later).
        """

        total_vendors = self.config.num_vendors
        lifnr, name1, land1, ort01, ktokk, erdat, stras, telf1, smtp_addr, sperr = (
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
        )
        perf_bias, spend_weight = [], []

        lifnr = [f"V{i:07d}" for i in range(1, total_vendors + 1)]

        num_top_vendors = total_vendors * self.config.pareto_split

        for i in range(self.config.num_vendors):
            if i < num_top_vendors:
                spend_weight.append(100)
            else:
                spend_weight.append(1)

        random_probs = np.random.random(total_vendors)
        for i, prob in enumerate(random_probs):
            threshold = (
                0.40 if spend_weight[i] == 100 else 0.05
            )  # this will ensure ~12% of PREF vendors
            if prob < threshold:
                ktokk.append("PREF")
            else:
                ktokk.append("STD")

        random_probs_2 = np.random.random(total_vendors)
        for prob2 in random_probs_2:
            if prob2 < 0.05:
                sperr.append("X")
            else:
                sperr.append("")

        perf_bias = np.random.normal(0, 2.0, total_vendors)

        name1 = [fake.company() for _ in range(total_vendors)]
        land1 = [fake.country_code() for _ in range(total_vendors)]
        ort01 = [fake.city() for _ in range(total_vendors)]
        stras = [fake.street_address() for _ in range(total_vendors)]
        telf1 = [fake.phone_number() for _ in range(total_vendors)]
        smtp_addr = [fake.company_email() for _ in range(total_vendors)]

        sim_start = datetime.strptime(self.config.start_date, "%Y-%m-%d")
        erdat_end = sim_start - timedelta(days=1)
        erdat_start = sim_start - timedelta(days=365 * 10)

        erdat_range = (erdat_end - erdat_start).days
        erdat = [
            erdat_start + timedelta(days=int(np.random.random() * erdat_range))
            for _ in range(total_vendors)
        ]

        self.lfa1 = pd.DataFrame(
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

    def _generate_mara(self):
        """
        Generate Material Master (MARA).
        """

        total_materials = self.config.num_materials
        matnr, maktx, mtart, matkl, meins, ersda, brgew, ntgew = (
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
        )
        base_price = []  # hidden column for pricing logic

        matnr = [f"M{i:08d}" for i in range(1, total_materials + 1)]

        categories = {
            "ELECT": {  # Electronics
                "price_range": (100, 10000),
                "uom_options": ["PC", "EA"],
                "weight_range": (0.5, 20.0),  # kg
                "mat_type": "FERT",  # Finished Goods
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
                "uom_options": ["AU", "HR", "DAY"],  # Activity Unit, Hour, Day
                "weight_range": (0, 0),  # Intangible
                "mat_type": "DIEN",  # Services
            },
        }

        counts = {
            "ELECT": int(total_materials * 0.35),
            "OFFICE": int(total_materials * 0.30),
            "RAW": int(total_materials * 0.25),
            "SERV": total_materials
            - int(
                total_materials * 0.9
            ),  # subtracted to ensure rounding errors don't leave unaccounted materials
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
            batch_meins = np.random.choice(categories[category]["uom_options"], count)

            # desc
            batch_maktx = [f"{category} - {fake.bs()}" for _ in range(count)]

            # creation date, <=start of simulation
            sim_start = datetime.strptime(self.config.start_date, "%Y-%m-%d")
            ersda_end = sim_start - timedelta(days=1)
            ersda_start = sim_start - timedelta(days=365 * 10)
            ersda_range = (ersda_end - ersda_start).days
            batch_ersda = [
                ersda_start + timedelta(days=int(np.random.random() * ersda_range))
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


        """
        # TODO: Implementation
        pass

    def _generate_ekko(self):
        """
        Generate PO Headers (EKKO).

        """
        # TODO: Implementation
        pass

    def _generate_ekpo(self):
        """
        Generate PO Line Items (EKPO).

        """
        # TODO: Implementation
        pass

    def _generate_ekbe(self):
        """
        Generate PO History (EKBE).

        """
        # TODO: Implementation
        pass

    def _cleanup_hidden_columns(self):
        """Drop internal helper columns (weights, base_price, bias) before saving."""
        # TODO: Drop 'spend_weight', 'perf_bias', 'base_price', 'is_whale'
        pass

    def save_to_parquet(self, output_dir: str):
        """Save all dataframes to Parquet."""
        pass
