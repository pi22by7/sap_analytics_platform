"""
Main entry point for Data Quality Framework.
Executes validation against generated parquet data.
"""

import sys
import os

# Ensure we can import from src


if __name__ == "__main__":
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    from quality.core import DQCore

    print("🔌 Initializing Data Quality Framework...")
    core = DQCore(data_path="data")
    success = core.run()

    # Exit code for CI/CD pipelines (0=Success, 1=Fail)
    sys.exit(0 if success else 1)
