import os
from pathlib import Path

import numpy as np
import pytest

QF_001 = "QF_001_f2013521b99e4a76bed1db7ec67464b0"

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
def test_dt4acc_twin_accelerator_instantiates_and_reads_live_values(config_file: Path):
    from pyaml.accelerator import Accelerator

    accelerator = Accelerator.load(str(config_file))

    assert accelerator.live is not None
    assert "live" in accelerator.controls()

    rf = accelerator.live.get_rf_plant("RF")
    reference_frequency = rf.frequency.get()

    assert np.isfinite(reference_frequency), f"RF reference frequency is not finite: {reference_frequency!r}"

    quadrupole = accelerator.live.get_magnet(QF_001)
    magnetic_strength = quadrupole.strength.get()

    assert np.isfinite(magnetic_strength), f"{QF_001} magnetic strength is not finite: {magnetic_strength!r}"
    assert magnetic_strength > 0.0, f"{QF_001} magnetic strength should be positive, got {magnetic_strength!r}"
