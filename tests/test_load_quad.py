import pytest
import json

import pyaml
from pyaml.configuration import load,set_root_folder
from pyaml.configuration import depthFirstBuild
from pyaml.magnet.quadrupole import Quadrupole
from pyaml.magnet.quadrupole import ConfigModel as QuadrupoleConfigModel
from pyaml.magnet.cfm_magnet import CombinedFunctionMagnet
from pyaml.magnet.linear_unitconv import LinearUnitConv


def test_json():
    print(json.dumps(QuadrupoleConfigModel.model_json_schema(),indent=2))

@pytest.mark.parametrize("install_test_package", [{
    "name": "pyaml_external",
    "path": "external"
}], indirect=True)
def test_quad_external_unit_conv(install_test_package):
    set_root_folder("./config")
    cfg_quad_yaml = load("sr/quadrupoles/QEXT.yaml")
    quad_with_external_unit_conv: Quadrupole = depthFirstBuild(cfg_quad_yaml)
    quad_with_external_unit_conv.strength.set(10.0)
    print(quad_with_external_unit_conv.strength.get())
    pyaml.configuration.factory._ALL_ELEMENTS.clear()

@pytest.mark.parametrize("magnet_file", [
    "sr/quadrupoles/QF1C01A.yaml",
    "sr/quadrupoles/QF1C01A.json",
])
def test_quad_linear(magnet_file):
    set_root_folder("./config")
    cfg_quad_yaml = load(magnet_file)
    quad:Quadrupole = depthFirstBuild(cfg_quad_yaml)
    uc: LinearUnitConv = quad.unitconv
    print(uc._curve[1])
    uc.set_magnet_rigidity(6e9 / 3e8)
    quad.strength.set(0.7962)
    print(f"Current={quad.current.get()}")
    print(f"Unit={quad.strength.unit()}")
    print(f"Unit={quad.current.unit()}")
    print(f"Strength={uc.compute_strengths([quad.current.get()])}")
    pyaml.configuration.factory._ALL_ELEMENTS.clear()

@pytest.mark.parametrize("magnet_file", [
    "sr/quadrupoles/SH1_C01A.yaml",
])
def test_combined_function_magnets(magnet_file):
    set_root_folder("./config")
    cfg_sh = load(magnet_file)
    sh: CombinedFunctionMagnet = depthFirstBuild(cfg_sh)
    sh.unitconv.set_magnet_rigidity(6e9 / 3e8)
    sh.multipole.set([0.000020, 0.000010, 0.000000])
    sh.A1.strength.set(0.0001)
    print(sh.multipole.get())
    pyaml.configuration.factory._ALL_ELEMENTS.clear()
