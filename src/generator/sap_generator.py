from numpy.random import rand
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional
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

        start_date = datetime.strptime(self.config.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(self.config.end_date, "%Y-%m-%d")
        date_range = (end_date - start_date).days
        erdat = [
            start_date + timedelta(days=int(np.random.random() * date_range))
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
        # TODO: Implementation
        pass

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
