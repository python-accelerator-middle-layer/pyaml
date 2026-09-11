import os
from pathlib import Path

import numpy as np
import pytest
import yaml
from pyaml_test_lattice import configurations, lattices

from pyaml.accelerator import Accelerator
from pyaml.configuration import ConfigurationManager

QF_001 = "QF_001"
QF_001_STRENGTH = "AN01-AR/EM-QP/QF.01/magnetic_strength"
RF_REFERENCE_FREQUENCY = "simulator/ringsimulator/ringsimulator/reference_frequency"
EXAMPLES_ROOT = Path(__file__).parent.parent.parent / "examples" / "use_cases" / "config"

FODO_LATTICE_KEY = "fodo_1gev_6d.json"
FODO_1GEV_6D_TANGO_PYAML_CONFIG_KEY = "pyaml/tango/tango-pyaml/fodo_1gev_6d_pyaml.yaml"
FODO_1GEV_6D_CS_OA_CONFIG_KEY = "pyaml/tango/pyaml-cs-oa/fodo_1gev_6d_pyaml-oa.yaml"
FODO_1GEV_6D_CONFIGS = [
    FODO_1GEV_6D_TANGO_PYAML_CONFIG_KEY,
    FODO_1GEV_6D_CS_OA_CONFIG_KEY,
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


def _load_fragment(config_key: str) -> dict:
    """Load one pyaml-test-lattice merged config fragment as a plain dict.

    Bypasses pyaml's own YAML loader (which auto-loads any bare
    ``*.yaml``/``*.json`` string value as a nested file relative to the
    parent file's directory) since the lattice file ships under a different
    package subtree (``data/lattice``) than the config fragment
    (``data/configuration``). The ``lattice`` and ``catalog`` references are
    resolved explicitly instead.
    """
    config_path = Path(configurations[config_key])
    fragment = yaml.safe_load(config_path.read_text())

    fragment["simulators"][0]["lattice"] = str(Path(lattices[FODO_LATTICE_KEY]))

    catalog_name = fragment["controls"][0]["catalog"]
    catalog_path = config_path.parent / catalog_name
    fragment["controls"][0]["catalog"] = yaml.safe_load(catalog_path.read_text())

    return fragment


def _build_accelerator(config_key: str):
    configuration_manager: ConfigurationManager = ConfigurationManager()
    configuration_manager.add(_load_fragment(config_key))

    return Accelerator.from_dict(configuration_manager.to_dict())


@pytest.mark.parametrize("config_key", FODO_1GEV_6D_CONFIGS, ids=["tango-pyaml", "pyaml-cs-oa"])
def test_dt4acc_twin_accelerator_instantiates_and_reads_live_values(config_key: str):
    accelerator = _build_accelerator(config_key)

    assert accelerator.live is not None
    assert "live" in accelerator.controls()

    accelerator.live.rf.get("RF")

    reference_frequency = _readback_value(accelerator.live.get_device_access(RF_REFERENCE_FREQUENCY))

    assert np.isfinite(reference_frequency), f"RF reference frequency is not finite: {reference_frequency!r}"
    assert reference_frequency > 0.0, f"RF reference frequency should be positive, got {reference_frequency!r}"

    accelerator.live.magnet.get(QF_001)
    magnetic_strength = _readback_value(accelerator.live.get_device_access(QF_001_STRENGTH))

    assert np.isfinite(magnetic_strength), f"{QF_001} magnetic strength is not finite: {magnetic_strength!r}"
    assert magnetic_strength > 0.0, f"{QF_001} magnetic strength should be positive, got {magnetic_strength!r}"


@pytest.mark.parametrize("config_key", FODO_1GEV_6D_CONFIGS, ids=["tango-pyaml", "pyaml-cs-oa"])
def test_dt4acc_twin_reads_all_declared_magnetic_strengths(config_key: str):
    accelerator = _build_accelerator(config_key)
    magnets = [magnet for magnet in accelerator.live.magnets.get() if magnet.get_model_name() == magnet.get_name()]
    combined_function_magnets = accelerator.live.combined_function_magnet.all()

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
        (EXAMPLES_ROOT / "bessy2", "bessy2.yaml"),
        (EXAMPLES_ROOT / "soleil_ii", "p.yaml"),
    ],
    ids=["bessy_ii", "soleil_ii"],
)
def test_examples_can_be_loaded(root_folder: Path, config_file: str):
    accelerator: Accelerator = Accelerator.load(str(root_folder / config_file))
    assert accelerator.yellow_pages is not None


@pytest.mark.parametrize("config_key", [FODO_1GEV_6D_TANGO_PYAML_CONFIG_KEY])
def deactivated_test_orbit_correction(config_key: str):
    try:
        accelerator = _build_accelerator(config_key)
        control_mode = accelerator.live
        bpms = control_mode.bpms.get("bpms")
        orbit_response_matrix = control_mode.get_orm_tuning("DEFAULT_ORBIT_RESPONSE_MATRIX")
        orbit_correction = control_mode.get_orbit_tuning("DEFAULT_ORBIT_CORRECTION")
        orbit_response_matrix.measure()
        ormdata = orbit_response_matrix.get()
        orbit_response_matrix.save("orm.json")
        orbit_correction.load("orm.json")
        std_kick = 1e-6
        hcorr = control_mode.magnets.get("hcorrectors")
        vcorr = control_mode.magnets.get("vcorrectors")
        print(f"HCORR={hcorr.strengths.get()}")
        print(f"VCORR={vcorr.strengths.get()}")
        ref_h, ref_v = bpms.positions.get().T
        reference = np.concat((ref_h, ref_v))
        # mangle orbit
        hcorr.strengths.set(hcorr.strengths.get() + std_kick * np.random.normal(size=len(hcorr)))
        vcorr.strengths.set(vcorr.strengths.get() + std_kick * np.random.normal(size=len(vcorr)))
        positions_bc = bpms.positions.get()
        std_bc = np.std(positions_bc, axis=0)
        print(f"R.m.s. orbit before correction H: {1e6 * std_bc[0]: .1f} µm, V: {1e6 * std_bc[1]: .1f} µm.")
        orbit_correction.correct(reference=reference)
    finally:
        import time

        from tango import DevFailed, DeviceProxy

        simulator = DeviceProxy("simulator/ringsimulator/ringsimulator")
        try:
            print("Reset the simulator")
            simulator.Reinit()
            print("Reset done")
        except DevFailed:
            time.sleep(3)


@pytest.mark.parametrize("config_key", [FODO_1GEV_6D_TANGO_PYAML_CONFIG_KEY])
def deactivated_test_chromaticity_measurement(config_key: str):
    # Deactivated like test_orbit_correction above: pyaml-test-lattice's current fixture
    # (as of commit 9d753c73) does not yet define BPMs/correctors or tuning tools
    # (chromaticity/orbit/tune response matrix), which this test requires.
    try:
        from pyaml.common.constants import Action

        accelerator = _build_accelerator(config_key)
        control_mode = accelerator.live
        chromaticity_measurement = control_mode.get_chromaticity_monitor("DEFAULT_CHROMATICITY_MEASUREMENT")

        def chroma_callback(action: int, cb_data: dict):
            if action == Action.MEASURE:
                print(f"Chromaticy measurement: #{cb_data['step']} RF={cb_data['rf']} Tune={cb_data['tune']}")
            return True

        accelerator.design.get_lattice().disable_6d()
        alphac = accelerator.design.get_lattice().get_mcf()
        accelerator.design.get_lattice().enable_6d()
        chromaticity_measurement.measure(
            callback=chroma_callback,
            do_plot=True,
            alphac=alphac,
            fit_order=2,
            n_step=5,
            sleep_between_meas=2.0,
            sleep_between_step=2.0,
        )
    finally:
        import time

        from tango import DevFailed, DeviceProxy

        simulator = DeviceProxy("simulator/ringsimulator/ringsimulator")
        try:
            print("Reset the simulator")
            simulator.Reset()
            print("Reset done")
        except DevFailed:
            time.sleep(3)
