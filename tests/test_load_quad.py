import pytest
import json
import numpy as np
from scipy.constants import speed_of_light

from pyaml.configuration import load,set_root_folder
from pyaml.configuration import Factory
from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.quadrupole import Quadrupole
from pyaml.magnet.quadrupole import ConfigModel as QuadrupoleConfigModel
from pyaml.magnet.cfm_magnet import CombinedFunctionMagnet
from pyaml.control.abstract_impl import RWHardwareScalar,RWStrengthScalar,RWHardwareArray,RWStrengthArray

# TODO: Generate JSON pydantic schema for MetaConfigurator
#def test_json():
#    print(json.dumps(QuadrupoleConfigModel.model_json_schema(),indent=2))

@pytest.mark.parametrize("install_test_package", [{
    "name": "pyaml_external",
    "path": "tests/external"
}], indirect=True)
def test_quad_external_model(install_test_package, config_root_dir):
    set_root_folder(config_root_dir)
    cfg_hcorr_yaml = load("sr/custom_magnets/hidcorr.yaml")
    hcorr_with_external_model: HCorrector = Factory.depth_first_build(cfg_hcorr_yaml)
    strength = RWStrengthScalar(hcorr_with_external_model.model)
    hardware = RWHardwareScalar(hcorr_with_external_model.model)
    ref_corr = hcorr_with_external_model.attach(strength,hardware)
    ref_corr.strength.set(10.0)
    print(ref_corr.strength.get())
    Factory.clear()

@pytest.mark.parametrize(
    ("magnet_file", "install_test_package"),
    [
        ("sr/quadrupoles/QF1AC01.yaml", None),
        ("sr/quadrupoles/QF1AC01-IDENT.yaml", {"name": "tango", "path": "tests/dummy_cs/tango"}),
        ("sr/quadrupoles/QF1AC01.json", None),
    ],
    indirect=["install_test_package"],
)
def test_quad_linear(magnet_file, install_test_package, config_root_dir):
    set_root_folder(config_root_dir)
    cfg_quad = load(magnet_file)
    print(f"Current file: {config_root_dir}/{magnet_file}")
    quad:Quadrupole = Factory.depth_first_build(cfg_quad)
    strength = RWStrengthScalar(quad.model)
    hardware = RWHardwareScalar(quad.model)
    ref_quad = quad.attach(strength,hardware)
    ref_quad.model.set_magnet_rigidity(6e9 / speed_of_light)
    ref_quad.strength.set(0.7962)
    current = ref_quad.hardware.get()
    assert( np.abs(current-80.423276) < 1e-4 )
    sunit = ref_quad.strength.unit()
    hunit = ref_quad.hardware.unit()
    assert( sunit == "1/m" )
    assert( hunit == "A" )
    str = ref_quad.model.compute_strengths([current])
    assert( np.abs(str-0.7962) < 1e-6 )
    Factory.clear()

@pytest.mark.parametrize("magnet_file", [
    "sr/correctors/SH1AC01.yaml",
])
def test_combined_function_magnets(magnet_file, config_root_dir):
    set_root_folder(config_root_dir)
    cfg_sh = load(magnet_file)
    sh: CombinedFunctionMagnet = Factory.depth_first_build(cfg_sh)
    sh.model.set_magnet_rigidity(6e9 / speed_of_light)
    currents = RWHardwareArray(sh.model)
    strengths = RWStrengthArray(sh.model)
    sUnits = sh.model.get_strength_units()
    hUnits = sh.model.get_hardware_units()
    assert( sUnits[0] == 'rad' and sUnits[1] == 'rad' and sUnits[2] == 'm-1' )
    assert( hUnits[0] == 'A' and hUnits[1] == 'A' and hUnits[2] == 'A')
    ms = sh.attach(strengths,currents)
    hCorr = ms[0]
    vCorr = ms[1]
    sqCorr = ms[2]
    hCorr.strength.set(0.000020)
    vCorr.strength.set(-0.000015)
    sqCorr.strength.set(0.000100)
    currents = sh.model.compute_hardware_values([0.000020,-0.000015,0.000100])
    assert( np.abs(currents[0]-0.05913476) < 1e-8 )
    assert( np.abs(currents[1]-0.05132066) < 1e-8 )
    assert( np.abs(currents[2]+0.06253617) < 1e-8 )
    str = sh.model.compute_strengths(currents)
    assert( np.abs(str[0]-0.000020) < 1e-8 )
    assert( np.abs(str[1]+0.000015) < 1e-8 )
    assert( np.abs(str[2]-0.000100) < 1e-8 )
    Factory.clear()
