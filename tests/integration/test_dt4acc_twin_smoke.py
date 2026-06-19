import os
from pathlib import Path

import numpy as np
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PYAML_DT4ACC_INTEGRATION") != "1",
        reason="dt4acc Apptainer integration test is opt-in",
    ),
]


@pytest.mark.parametrize(
    "config_file",
    [
        Path(__file__).parent / "data" / "fodo_1gev_6d_pyaml.yaml",
    ],
    ids=["fodo_1gev_6d_pyaml.yaml"],
)
def test_dt4acc_twin_accelerator_instantiates_and_reads_rf(config_file: Path):
    from pyaml.accelerator import Accelerator

    accelerator = Accelerator.load(str(config_file))

    assert accelerator.live is not None
    assert "live" in accelerator.controls()

    rf = accelerator.live.get_rf_plant("RF")
    reference_frequency = rf.frequency.get()

    assert np.isfinite(reference_frequency)
    assert reference_frequency > 0.0
