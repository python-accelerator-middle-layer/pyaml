import os
from pathlib import Path

import numpy as np
import pytest

from pyaml.accelerator import Accelerator
from pyaml.configuration import ConfigurationManager

QF_001 = "QF_001_314d440dcc3348c687785c80e67fce27"
QF_001_STRENGTH = "AN01-AR/EM-QP/QF.01/magnetic_strength"
RF_REFERENCE_FREQUENCY = "simulator/ringsimulator/ringsimulator/reference_frequency"
EXAMPLES_ROOT = Path(__file__).parent.parent.parent / "examples"
FODO_1GEV_6D_ROOT = Path(__file__).parent / "data" / "fodo_1gev_6d"
FODO_1GEV_6D_CONFIGS = [
    (
        FODO_1GEV_6D_ROOT,
        {
            "accelerator": "fodo_1gev_6d_pyaml_accelerator.yaml",
            "simulator": "fodo_1gev_6d_pyaml_simulators.yaml",
            "control_system": "fodo_1gev_6d_pyaml_tango_controls.yaml",  # tango-pyaml
            "arrays": "fodo_1gev_6d_pyaml_arrays.yaml",
            "bpm_devices": "fodo_1gev_6d_pyaml_devices_bpms.yaml",
            "bends_devices": "fodo_1gev_6d_pyaml_devices_bends.yaml",
            "correctors_devices": "fodo_1gev_6d_pyaml_devices_correctors.yaml",
            "quadrupoles_devices": "fodo_1gev_6d_pyaml_devices_quadrupoles.yaml",
            "sextupoles_devices": "fodo_1gev_6d_pyaml_devices_sextupoles.yaml",
            "diagnostic_devices": "fodo_1gev_6d_pyaml_devices_diagnostics.yaml",
            "rf_devices": "fodo_1gev_6d_pyaml_devices_rf.yaml",
        },
    ),
    (
        FODO_1GEV_6D_ROOT,
        {
            "accelerator": "fodo_1gev_6d_pyaml_accelerator.yaml",
            "simulator": "fodo_1gev_6d_pyaml_simulators.yaml",
            "control_system": "fodo_1gev_6d_pyaml_cs_oa_controls.yaml",  # pyaml-cs-oa
            "arrays": "fodo_1gev_6d_pyaml_arrays.yaml",
            "bpm_devices": "fodo_1gev_6d_pyaml_devices_bpms.yaml",
            "bends_devices": "fodo_1gev_6d_pyaml_devices_bends.yaml",
            "correctors_devices": "fodo_1gev_6d_pyaml_devices_correctors.yaml",
            "quadrupoles_devices": "fodo_1gev_6d_pyaml_devices_quadrupoles.yaml",
            "sextupoles_devices": "fodo_1gev_6d_pyaml_devices_sextupoles.yaml",
            "diagnostic_devices": "fodo_1gev_6d_pyaml_devices_diagnostics.yaml",
            "rf_devices": "fodo_1gev_6d_pyaml_devices_rf.yaml",
        },
    ),
]
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PYAML_DT4ACC_INTEGRATION") != "1",
        reason="dt4acc Apptainer integration test is opt-in",
    ),
]


def _readback_value(device_access):
    return float(device_access.readback())


def _build_accelerator(root_folder: Path, config_files: dict[str, str]):
    configuration_manager: ConfigurationManager = ConfigurationManager()
    for config_file in config_files.values():
        configuration_manager.add(str(root_folder / config_file))

    return Accelerator.from_dict(configuration_manager.to_dict())


@pytest.mark.parametrize(
    ("root_folder", "config_files"),
    FODO_1GEV_6D_CONFIGS,
    ids=["tango-pyaml", "pyaml-cs-oa"],
)
def test_dt4acc_twin_accelerator_instantiates_and_reads_live_values(root_folder: Path, config_files: dict[str, str]):
    accelerator = _build_accelerator(root_folder, config_files)

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


@pytest.mark.parametrize(
    ("root_folder", "config_files"),
    FODO_1GEV_6D_CONFIGS,
    ids=["tango-pyaml", "pyaml-cs-oa"],
)
def test_dt4acc_twin_reads_all_declared_magnetic_strengths(root_folder: Path, config_files: dict[str, str]):
    accelerator = _build_accelerator(root_folder, config_files)
    magnets = [magnet for magnet in accelerator.live.get_all_magnets() if magnet.get_model_name() == magnet.get_name()]
    combined_function_magnets = accelerator.live.get_all_cfm_magnets()

    assert magnets or combined_function_magnets

    failures = []
    for magnet in magnets:
        try:
            value = float(magnet.strength.get())
        except Exception as exc:  # noqa: BLE001 - report all unavailable Tango attributes at once.
            failures.append(f"{magnet.get_name()}: {type(exc).__name__}: {exc}")
            continue

        if not np.isfinite(value):
            failures.append(f"{magnet.get_name()}: non-finite value {value!r}")

    for magnet in combined_function_magnets:
        try:
            values = np.asarray(magnet.strengths.get(), dtype=float)
        except Exception as exc:  # noqa: BLE001 - report all unavailable Tango attributes at once.
            failures.append(f"{magnet.get_name()}: {type(exc).__name__}: {exc}")
            continue

        if not np.all(np.isfinite(values)):
            failures.append(f"{magnet.get_name()}: non-finite values {values!r}")

    assert not failures, "Magnetic strength readback failures:\n" + "\n".join(failures)


@pytest.mark.parametrize(
    ("root_folder", "config_file"),
    [
        (EXAMPLES_ROOT / "BESSY2_example", "BESSY2Tune.yaml"),
        (EXAMPLES_ROOT / "BESSY2_example", "BESSY2Orbit.yaml"),
        (EXAMPLES_ROOT / "SOLEIL_examples", "p.yaml"),
    ],
    ids=["bessy_ii_tune", "bessy_ii_orbit", "soleil_ii"],
)
def test_examples_can_be_loaded(root_folder: Path, config_file: str):
    accelerator: Accelerator = Accelerator.load(str(root_folder / config_file))
    assert accelerator.yellow_pages is not None
