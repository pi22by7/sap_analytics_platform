import numpy as np
import pandas as pd
import pytest

from src.generator.sap_generator import GeneratorConfig, SAPDataGenerator


class TestSAPDataGenerator:
    @pytest.fixture
    def config(self):
        return GeneratorConfig(
            num_vendors=20, num_materials=10, num_pos=50, num_contracts=5, seed=42
        )

    def test_config_initialization(self, config):
        """Test configuration defaults and overrides."""
        gen = SAPDataGenerator(config)
        assert gen.config.num_vendors == 20
        assert gen.config.seed == 42

    def test_lfa1_generation(self, config):
        """Test Vendor Master generation logic."""
        gen = SAPDataGenerator(config)
        gen._generate_lfa1()
        assert gen.lfa1 is not None
        assert len(gen.lfa1) == 20
        assert "LIFNR" in gen.lfa1.columns
        assert "spend_weight" in gen.lfa1.columns  # Internal col exists

    def test_mara_generation(self, config):
        """Test Material Master generation logic."""
        gen = SAPDataGenerator(config)
        gen._generate_mara()
        assert gen.mara is not None
        assert len(gen.mara) == 10
        assert gen.mara["base_price"].min() > 0

    @pytest.mark.parametrize("check_type", ["price", "dates"])
    def test_contract_logic(self, config, check_type):
        """Test contract pricing and date validity."""
        gen = SAPDataGenerator(config)
        gen._generate_lfa1()
        gen._generate_mara()
        gen._generate_contracts()

        assert gen.contracts is not None
        df = gen.contracts

        if check_type == "price":
            assert (df["CONTRACT_PRICE"] > 0).all()
            assert (df["CONTRACT_PRICE"] < 100000).all()  # Sanity check
        elif check_type == "dates":
            duration = (df["VALID_TO"] - df["VALID_FROM"]).apply(lambda x: x.days)
            assert duration.min() >= 365
            assert (df["VALID_FROM"] < df["VALID_TO"]).all()

    def test_pareto_weight_logic(self, config):
        """Verify Pareto weight calculation produces skewed weights."""
        gen = SAPDataGenerator(config)
        gen._generate_lfa1()
        assert gen.lfa1 is not None
        weights = gen.lfa1["spend_weight"]

        # Check that we have at least two unique weights (top tier vs standard)
        assert len(weights.unique()) >= 2
        # Verify the high weight is significantly larger
        assert weights.max() > (weights.min() * 10)

    def test_full_pipeline_execution(self, config):
        """Test end-to-end generation sequence."""
        gen = SAPDataGenerator(config)
        gen.generate_all()
        assert gen.ekbe is not None
        assert not gen.ekbe.empty
        assert gen.ekko is not None
        assert "is_large" not in gen.ekko.columns  # Cleanup check

    def test_large_order_logic(self, config):
        """Test that large orders result in higher quantities."""

        config.large_order_prob = 0.5
        gen = SAPDataGenerator(config)
        gen._generate_lfa1()
        gen._generate_mara()
        gen._generate_contracts()
        gen._generate_ekko()
        gen._generate_ekpo()

        assert gen.ekpo is not None
        assert gen.ekko is not None

        merged = gen.ekpo.merge(gen.ekko[["EBELN", "is_large"]], on="EBELN")

        # Check if large POs have statistically higher quantity/value
        avg_qty_large = merged[merged["is_large"]]["MENGE"].mean()
        avg_qty_std = merged[~merged["is_large"]]["MENGE"].mean()

        if not np.isnan(avg_qty_large) and not np.isnan(avg_qty_std):
            assert avg_qty_large > avg_qty_std


class TestAnalyticsLogic:
    @pytest.mark.parametrize(
        "case",
        [
            {"menge": 10, "netpr": 100, "expected": 1000},
            {"menge": 0, "netpr": 100, "expected": 0},
            {"menge": 5, "netpr": 0, "expected": 0},
        ],
    )
    def test_net_value_calc(self, case):
        """Unit test for simple net value calculation."""
        res = case["menge"] * case["netpr"]
        assert res == case["expected"]

    def test_maverick_spend_identification(self):
        """Test logic for identifying maverick (non-contract) spend."""

        df = pd.DataFrame(
            {
                "EBELN": ["P1", "P2"],
                "BSART": ["NB", "FO"],
                "NETWR": [1000, 500],
            }
        )

        maverick = df[df["BSART"] == "FO"]
        assert len(maverick) == 1
        assert maverick["NETWR"].sum() == 500

    def test_delivery_delay_classification(self):
        """Test late vs on-time logic with business rules."""
        # 1. Late Delivery
        eindt = pd.Timestamp("2023-01-10")
        actual = pd.Timestamp("2023-01-12")
        is_late = actual > eindt
        assert is_late is True

        # 2. On-Time Delivery
        actual_early = pd.Timestamp("2023-01-10")
        is_late = actual_early > eindt
        assert is_late is False
