import pytest
import os
from src.quality.core import DQCore
from src.generator.sap_generator import GeneratorConfig, SAPDataGenerator


def test_pipeline_integration(tmp_path):
    """
    Test the full flow:
    Generate Data -> Save to Temp -> Load in DQ -> Run Checks
    """
    # 1. Generate small dataset
    cfg = GeneratorConfig(num_vendors=5, num_materials=5, num_pos=10, num_contracts=5)
    gen = SAPDataGenerator(cfg)
    gen.generate_all()

    # 2. Save to temporary directory
    data_dir = tmp_path / "data"
    gen.save_to_parquet(str(data_dir))

    assert (data_dir / "EKPO.parquet").exists()

    # 3. Initialize DQ Core with temp path
    report_dir = tmp_path / "reports"
    dq = DQCore(data_path=str(data_dir), report_path=str(report_dir))

    # 4. Run Checks
    success = dq.run()

    # 5. Verify Output
    assert success is True
    assert (report_dir / "dq_dashboard.html").exists()
    assert (report_dir / "dq_report.json").exists()


def test_dq_initialization_failure():
    """Test DQ handling of missing path."""
    dq = DQCore(data_path="non_existent_path")
    assert dq.load_data() is False
