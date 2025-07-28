import pytest
import json

import pyaml
from pyaml.configuration import load,set_root_folder
from pyaml.configuration import depthFirstBuild
from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.quadrupole import Quadrupole
from pyaml.magnet.quadrupole import ConfigModel as QuadrupoleConfigModel
from pyaml.magnet.cfm_magnet import CombinedFunctionMagnet
from pyaml.magnet.linear_model import LinearMagnetModel
from pyaml.control.abstract_impl import RWHardwareScalar,RWStrengthScalar
import pyaml as pyaml_pkg


def test_json():
    print(json.dumps(QuadrupoleConfigModel.model_json_schema(),indent=2))

@pytest.mark.parametrize("install_test_package", [{
    "name": "pyaml_external",
    "path": "tests/external"
}], indirect=True)
def test_quad_external_model(install_test_package, config_root_dir):
    set_root_folder(config_root_dir)

    cfg_hcorr_yaml = load("sr/custom_magnets/hidcorr.yaml")
    hcorr_with_external_model: HCorrector = depthFirstBuild(cfg_hcorr_yaml)
    strength = RWStrengthScalar(hcorr_with_external_model.model)
    hardware = RWHardwareScalar(hcorr_with_external_model.model)
    ref_corr = hcorr_with_external_model.attach(strength,hardware)
    ref_corr.strength.set(10.0)
    print(ref_corr.strength.get())
    pyaml.configuration.factory._ALL_ELEMENTS.clear()

@pytest.mark.parametrize("magnet_file", [
    "sr/quadrupoles/QF1C01A.yaml",
    "sr/quadrupoles/QF1C01A.json",
])
def test_quad_linear(magnet_file, config_root_dir):
    set_root_folder(config_root_dir)
    cfg_quad_yaml = load(magnet_file)
    print(f"Current file: {config_root_dir}/{magnet_file}")
    quad:Quadrupole = depthFirstBuild(cfg_quad_yaml)
    uc: LinearMagnetModel = quad.model
    print(uc._cfg.curve[1])
    uc.set_magnet_rigidity(6e9 / 3e8)
    quad.strength.set(0.7962)
    print(f"Current={quad.hardware.get()}")
    print(f"Unit={quad.strength.unit()}")
    print(f"Unit={quad.hardware.unit()}")
    print(f"Strength={uc.compute_strengths([quad.hardware.get()])}")
    pyaml.configuration.factory._ALL_ELEMENTS.clear()

@pytest.mark.parametrize("magnet_file", [
    "sr/correctors/SH1_C01A.yaml",
])
def test_combined_function_magnets(magnet_file, config_root_dir):
    set_root_folder(config_root_dir)
    cfg_sh = load(magnet_file)
    sh: CombinedFunctionMagnet = depthFirstBuild(cfg_sh)
    sh.model.set_magnet_rigidity(6e9 / 3e8)
    sh.multipole.set([0.000020, 0.000010, 0.000000])
    sh.A1.strength.set(0.0001)
    print(sh.multipole.get())
    pyaml_pkg.configuration.factory._ALL_ELEMENTS.clear()
