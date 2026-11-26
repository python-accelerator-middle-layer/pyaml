import os

import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from tests.integration.fodo_fixtures import build_fodo_accelerator

FODO_1GEV_6D_EPICS_CONFIG_KEY = "pyaml/epics/pyaml-cs-oa/fodo_1gev_6d_pyaml-epics.yaml"

# PV prefix the EPICS twin was started with (start_dt4acc_twin.sh --prefix).
EPICS_PREFIX = os.environ.get("PYAML_DT4ACC_EPICS_PREFIX", "pyaml-it")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PYAML_DT4ACC_INTEGRATION") != "1",
        reason="dt4acc Apptainer integration test is opt-in",
    ),
]


def _build_accelerator() -> Accelerator:
    # The twin publishes "<prefix>:QF_001:Cm:rdbk" while the fixture declares
    # "QF_001:Cm:rdbk", so the pyaml-cs-oa control system adds "<prefix>:".
    return build_fodo_accelerator(
        FODO_1GEV_6D_EPICS_CONFIG_KEY,
        control_overrides={"prefix": f"{EPICS_PREFIX}:"},
    )


def test_epics_twin_accelerator_instantiates_and_reads_live_values():
    # Build the accelerator from the FODO EPICS fixture, with its "live" EPICS control system.
    accelerator = _build_accelerator()

    assert accelerator.live is not None
    assert "live" in accelerator.controls()

    # Read the RF frequency through the RF plant.
    rf_frequency = float(accelerator.live.rf.get("RF").frequency.get())

    assert np.isfinite(rf_frequency), f"RF frequency is not finite: {rf_frequency!r}"
    assert rf_frequency > 0.0, f"RF frequency should be positive, got {rf_frequency!r}"

    # Read one focusing quadrupole strength.
    qf_strength = float(accelerator.live.magnet.get("QF_001").strength.get())

    assert np.isfinite(qf_strength), f"QF_001 strength is not finite: {qf_strength!r}"
    assert qf_strength > 0.0, f"QF_001 strength should be positive, got {qf_strength!r}"


def test_epics_twin_reads_all_declared_magnetic_strengths():
    # Build the accelerator and collect the single-function magnets and the combined function magnets.
    # Magnets created by a combined function magnet (COR_001.hcorrector, ...) are read through their parent.
    accelerator = _build_accelerator()
    magnets = [magnet for magnet in accelerator.live.magnets.get() if magnet.get_model_name() == magnet.get_name()]
    combined_function_magnets = accelerator.live.combined_function_magnet.all()

    assert magnets
    assert combined_function_magnets

    # Read every strength and collect all failures, so one run reports every unavailable PV.
    failures = []
    for magnet in magnets:
        try:
            value = float(magnet.strength.get())
        except Exception as exc:  # noqa: BLE001 - report all unavailable PVs at once.
            failures.append(f"{magnet.get_name()}: {type(exc).__name__}: {exc}")
            continue

        if not np.isfinite(value):
            failures.append(f"{magnet.get_name()}: non-finite value {value!r}")

    for magnet in combined_function_magnets:
        try:
            values = np.asarray(magnet.strengths.get(), dtype=float)
        except Exception as exc:  # noqa: BLE001 - report all unavailable PVs at once.
            failures.append(f"{magnet.get_name()}: {type(exc).__name__}: {exc}")
            continue

        if not np.all(np.isfinite(values)):
            failures.append(f"{magnet.get_name()}: non-finite values {values!r}")

    assert not failures, "Magnetic strength readback failures:\n" + "\n".join(failures)


def test_epics_twin_reads_bpm_positions():
    # Build the accelerator and collect every declared BPM.
    accelerator = _build_accelerator()
    bpms = accelerator.live.diagnostic.bpm.all()

    assert bpms

    # Read the (x, y) position of every BPM and collect all failures.
    failures = []
    for bpm in bpms:
        try:
            positions = np.asarray(bpm.positions.get(), dtype=float)
        except Exception as exc:  # noqa: BLE001 - report all unavailable PVs at once.
            failures.append(f"{bpm.get_name()}: {type(exc).__name__}: {exc}")
            continue

        if not np.all(np.isfinite(positions)):
            failures.append(f"{bpm.get_name()}: non-finite positions {positions!r}")

    assert not failures, "BPM position readback failures:\n" + "\n".join(failures)
