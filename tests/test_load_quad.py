import json

import numpy as np
import pytest
from scipy.constants import speed_of_light

from pyaml import PyAMLException
from pyaml.accelerator import Accelerator
from pyaml.configuration import Factory, get_root_folder, set_root_folder
from pyaml.configuration.fileloader import load
from pyaml.control.abstract_impl import (
    RWHardwareArray,
    RWHardwareScalar,
    RWStrengthArray,
    RWStrengthScalar,
)
from pyaml.magnet.cfm_magnet import CombinedFunctionMagnet
from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.identity_model import IdentityMagnetModel
from pyaml.magnet.quadrupole import ConfigModel as QuadrupoleConfigModel
from pyaml.magnet.quadrupole import Quadrupole

# TODO: Generate JSON pydantic schema for MetaConfigurator
# def test_json():
#    print(json.dumps(QuadrupoleConfigModel.model_json_schema(),indent=2))


@pytest.mark.parametrize(
    "install_test_package",
    [
        {"name": "pyaml_external", "path": "tests/external"},
        {"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"},
    ],
    indirect=True,
)
def test_quad_external_model(install_test_package, config_root_dir):
    set_root_folder(config_root_dir)
    cfg_hcorr_yaml = load("sr/custom_magnets/hidcorr.yaml")
    cs = Factory.build_object(
        {
            "type": "tango.pyaml.controlsystem",
            "name": "live",
            "tango_host": "ebs-simu-3:10000",
        }
    )
    hcorr_with_external_model: HCorrector = Factory.depth_first_build(
        cfg_hcorr_yaml, False
    )
    dev = cs.attach(hcorr_with_external_model.model.get_devices())[0]
    strength = RWStrengthScalar(hcorr_with_external_model.model, dev)
    hardware = RWHardwareScalar(hcorr_with_external_model.model, dev)
    ref_corr = hcorr_with_external_model.attach(cs, strength, hardware)
    ref_corr.hardware.set(10.0)
    assert ref_corr.strength.get() == 1.0
    assert ref_corr.hardware.get() == 10.0
    ref_corr.strength.set(10.0)
    assert ref_corr.strength.get() == 10.0
    assert ref_corr.hardware.get() == 100.0
    Factory.clear()


@pytest.mark.parametrize(
    ("magnet_file", "install_test_package"),
    [
        ("sr/quadrupoles/QF1AC01.yaml", None),
        (
            "sr/quadrupoles/QF1AC01-IDENT-STRGTH.yaml",
            {"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"},
        ),
        (
            "sr/quadrupoles/QF1AC01-IDENT-HW.yaml",
            {"name": "tango-pyaml", "path": "tests/dummy_cs/tango-pyaml"},
        ),
        ("sr/quadrupoles/QF1AC01.json", None),
    ],
    indirect=["install_test_package"],
)
def test_quad_linear(magnet_file, install_test_package, config_root_dir):
    set_root_folder(config_root_dir)
    cfg_quad = load(magnet_file)
    print(f"Current file: {config_root_dir}/{magnet_file}")
    cs = Factory.build_object(
        {
            "type": "tango.pyaml.controlsystem",
            "name": "live",
            "tango_host": "ebs-simu-3:10000",
        }
    )
    quad: Quadrupole = Factory.depth_first_build(cfg_quad, False)
    dev = cs.attach(quad.model.get_devices())[0]
    hardware = RWHardwareScalar(quad.model, dev) if quad.model.has_hardware() else None
    strength = RWStrengthScalar(quad.model, dev) if quad.model.has_physics() else None
    ref_quad = quad.attach(cs, strength, hardware)
    ref_quad.model.set_magnet_rigidity(6e9 / speed_of_light)

    try:
        ref_quad.strength.set(0.7962)
        sunit = ref_quad.strength.unit()
        assert sunit == "1/m"
    except Exception as ex:
        if not quad.model.has_physics():
            assert "has no model that supports physics units" in str(ex)
            ref_quad.hardware.set(80.423276)
        else:
            raise ex

    try:
        current = ref_quad.hardware.get()
        assert np.abs(current - 80.423276) < 1e-4
        hunit = ref_quad.hardware.unit()
        assert hunit == "A"
    except Exception as ex:
        if not quad.model.has_hardware():
            assert "has no model that supports hardware units" in str(ex)
        else:
            raise ex

    Factory.clear()


@pytest.mark.parametrize(
    "magnet_file",
    [
        "sr/correctors/SH1AC01.yaml",
    ],
)
def test_combined_function_magnets(magnet_file, config_root_dir):
    set_root_folder(config_root_dir)
    cfg_sh = load(magnet_file)
    cs = Factory.build_object(
        {
            "type": "tango.pyaml.controlsystem",
            "name": "live",
            "tango_host": "ebs-simu-3:10000",
        }
    )
    sh: CombinedFunctionMagnet = Factory.depth_first_build(cfg_sh, False)
    sh.model.set_magnet_rigidity(6e9 / speed_of_light)
    devs = cs.attach(sh.model.get_devices())
    currents = RWHardwareArray(sh.model, devs)
    strengths = RWStrengthArray(sh.model, devs)
    sUnits = sh.model.get_strength_units()
    hUnits = sh.model.get_hardware_units()
    assert sUnits[0] == "rad" and sUnits[1] == "rad" and sUnits[2] == "m-1"
    assert hUnits[0] == "A" and hUnits[1] == "A" and hUnits[2] == "A"
    ms = sh.attach(cs, strengths, currents)
    hCorr = ms[1]
    vCorr = ms[2]
    sqCorr = ms[3]
    hCorr.strength.set(0.000020)
    vCorr.strength.set(-0.000015)
    sqCorr.strength.set(0.000100)
    currents = sh.model.compute_hardware_values([0.000020, -0.000015, 0.000100])
    assert np.abs(currents[0] - 0.05913476) < 1e-8
    assert np.abs(currents[1] - 0.05132066) < 1e-8
    assert np.abs(currents[2] + 0.06253617) < 1e-8
    str = sh.model.compute_strengths(currents)
    assert np.abs(str[0] - 0.000020) < 1e-8
    assert np.abs(str[1] + 0.000015) < 1e-8
    assert np.abs(str[2] - 0.000100) < 1e-8
    Factory.clear()
