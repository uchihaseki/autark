"""Example test for MinimalAdapter using the shared AdapterTestSuite.

Copy this pattern to test your own adapter.
"""

from pathlib import Path

import pytest

from autark.core.protocols import Adapter

# Adjust the import path in your own project:
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.helpers import AdapterTestSuite


class TestMinimalAdapter(AdapterTestSuite):
    def create_adapter(self, tmp_path: Path) -> Adapter:
        from examples.adapter_template.adapter import MinimalAdapter

        # Write a minimal corpus and artifact for testing
        corpus_path = tmp_path / "cases.json"
        corpus_path.write_text(
            '{"artifact_id":"prompt.txt","cases":['
            '{"case_id":"t1","input_text":"2+3","expected_output":"5"}]}'
        )
        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()
        (artifact_dir / "prompt.txt").write_text("You are a math assistant.\n")

        return MinimalAdapter(
            corpus_path=corpus_path,
            artifact_root=artifact_dir,
            output_dir=str(tmp_path / "output"),
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
