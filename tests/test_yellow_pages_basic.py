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
    BPM                   (pyaml.arrays.bpm_array)                size=320
    HCorr                 (pyaml.arrays.magnet_array)             size=288
    VCorr                 (pyaml.arrays.magnet_array)             size=288
    Skews                 (pyaml.arrays.magnet_array)             size=288
    Sext                  (pyaml.arrays.magnet_array)             size=180
    .

Tools:
    CHROMATICITY_MONITOR (pyaml.diagnostics.chromaticity_monitor)
    DEFAULT_CHROMATICITY_RESPONSE_MATRIX (pyaml.tuning_tools.chromaticity_response_matrix)
    DEFAULT_CHROMATICITY_CORRECTION (pyaml.tuning_tools.chromaticity)
    DEFAULT_ORBIT_CORRECTION (pyaml.tuning_tools.orbit)
    DEFAULT_ORBIT_RESPONSE_MATRIX (pyaml.tuning_tools.orbit_response_matrix)
    DEFAULT_DISPERSION (pyaml.tuning_tools.dispersion)
    .

Diagnostics:
    BETATRON_TUNE (pyaml.diagnostics.tune_monitor)
    ."""


def test_load_conf_with_code(accelerator_from_config):
    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()

    sr: Accelerator = accelerator_from_config(config_path)
    str_repr = str(sr.yellow_pages)
    print(str_repr)
    assert ebs_orbit_str_repr == str_repr
