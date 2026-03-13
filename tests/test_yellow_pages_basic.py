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
    .

Tools:
    DEFAULT_ORBIT_CORRECTION (pyaml.tuning_tools.orbit)
    DEFAULT_ORBIT_RESPONSE_MATRIX (pyaml.tuning_tools.orbit_response_matrix)
    DEFAULT_DISPERSION (pyaml.tuning_tools.dispersion)
    .

Diagnostics:
    BETATRON_TUNE (pyaml.diagnostics.tune_monitor)
    ."""


def test_load_conf_with_code():
    parent_folder = Path(__file__).parent
    config_path = parent_folder.joinpath("config", "EBSOrbit.yaml").resolve()

    sr: Accelerator = Accelerator.load(config_path)
    str_repr = str(sr.yellow_pages)
    print(str_repr)
    assert ebs_orbit_str_repr == str_repr
