import os
from pathlib import Path

import numpy as np
import pytest

QF_001 = "QF_001_f2013521b99e4a76bed1db7ec67464b0"
QF_001_STRENGTH = "AN01-AR/EM-QP/QF.01/magnetic_strength"
RF_REFERENCE_FREQUENCY = "simulator/ringsimulator/ringsimulator/reference_frequency"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PYAML_DT4ACC_INTEGRATION") != "1",
        reason="dt4acc Apptainer integration test is opt-in",
    ),
]


def _readback_value(device_access):
    return float(device_access.readback())


@pytest.mark.parametrize(
    "config_file",
    [
        Path(__file__).parent / "data" / "fodo_1gev_6d_pyaml.yaml",
        Path(__file__).parent / "data" / "fodo_1gev_6d_pyaml-oa.yaml",
    ],
    ids=["tango-pyaml", "pyaml-cs-oa"],
)
def test_dt4acc_twin_accelerator_instantiates_and_reads_live_values(config_file: Path):
    from pyaml.accelerator import Accelerator

    accelerator = Accelerator.load(str(config_file))

    assert accelerator.live is not None
    assert "live" in accelerator.controls()

    accelerator.live.get_rf_plant("RF")

    reference_frequency = _readback_value(accelerator.live.get_device_access(RF_REFERENCE_FREQUENCY))

    assert np.isfinite(reference_frequency), f"RF reference frequency is not finite: {reference_frequency!r}"
    assert reference_frequency > 0.0, f"RF reference frequency should be positive, got {reference_frequency!r}"

    accelerator.live.get_magnet(QF_001)
    magnetic_strength = _readback_value(accelerator.live.get_device_access(QF_001_STRENGTH))

    assert np.isfinite(magnetic_strength), f"{QF_001} magnetic strength is not finite: {magnetic_strength!r}"
    assert magnetic_strength > 0.0, f"{QF_001} magnetic strength should be positive, got {magnetic_strength!r}"
