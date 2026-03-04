# ruff: noqa: E501
from pathlib import Path

from pyaml.accelerator import Accelerator

ebs_orbit_str_repr = """Controls:
    live
    .

Simulators:
    design
    .

Arrays:
    BPM        (pyaml.arrays.bpm_array.BPMArray)       size=320
    HCorr      (pyaml.arrays.magnet_array.MagnetArray) size=288
    Skews      (pyaml.arrays.magnet_array.MagnetArray) size=288
    VCorr      (pyaml.arrays.magnet_array.MagnetArray) size=288
    .

Tools:
    DEFAULT_DISPERSION (pyaml.tuning_tools.dispersion.Dispersion)
    DEFAULT_ORBIT_CORRECTION (pyaml.tuning_tools.orbit.Orbit)
    DEFAULT_ORBIT_RESPONSE_MATRIX (pyaml.tuning_tools.orbit_response_matrix.OrbitResponseMatrix)
    .

Diagnostics:
    BETATRON_TUNE (pyaml.diagnostics.tune_monitor.BetatronTuneMonitor)
    ."""


def test_load_conf_with_code():
    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()

    sr: Accelerator = Accelerator.load(config_path)
    str_repr = str(sr.yellow_pages)
    assert ebs_orbit_str_repr == str_repr
