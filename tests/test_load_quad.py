
from pyaml.configuration import load,set_root_folder
from pyaml.configuration import depthFirstBuild
from pyaml.magnet.quadrupole import Quadrupole
from pyaml.magnet.quadrupole import ConfigModel as QuadrupoleConfigModel

from pyaml.magnet.linear_unitconv import LinearUnitConv
from pyaml.magnet.linear_cfm_unitconv import LinearCFMagnetUnitConv
from pyaml.magnet.cfm_magnet import CombinedFunctionMagnet
import pprint as pp
import json

set_root_folder("tests/config")

if False:
    print(json.dumps(QuadrupoleConfigModel.model_json_schema(),indent=2))
    quit()

if False:
    # To run this one, please run 'pip install .' first in tests/external
    cfg_quad_yaml = load("sr/quadrupoles/QEXT.yaml")
    quadWithExt: Quadrupole = depthFirstBuild(cfg_quad_yaml)
    quadWithExt.strength.set(10.0)    
    print(quadWithExt.strength.get())


if True:
    cfg_quad_yaml = load("sr/quadrupoles/QF1C01A.yaml")
    quad:Quadrupole = depthFirstBuild(cfg_quad_yaml)
    uc: LinearUnitConv = quad.unitconv
    print(uc._curve[1])
    quad.unitconv.set_magnet_rigidity(6e9 / 3e8)
    quad.strength.set(0.7962)
    print(f"Current={quad.current.get()}")
    print(f"Unit={quad.strength.unit()}")
    print(f"Unit={quad.current.unit()}")

if False:
    cfg_quad_json = load("sr/quadrupoles/QF1C01A.json")
    quad2:Quadrupole = depthFirstBuild(cfg_quad_json)
    uc: LinearUnitConv = quad2.unitconv
    print(uc._curve[1])
    uc.set_magnet_rigidity(6e9 / 3e8)
    quad2.strength.set(0.7962)
    print(f"Current={quad2.current.get()}")
    print(f"Unit={quad2.strength.unit()}")
    print(f"Unit={quad2.current.unit()}")
    print(f"Strength={uc.compute_strengths([quad2.current.get()])}")

cfg_sh = load("sr/quadrupoles/SH1_C01A.yaml")
sh:CombinedFunctionMagnet = depthFirstBuild(cfg_sh)
sh.unitconv.set_magnet_rigidity(6e9 / 3e8)
sh.multipole.set([0.000020,0.000010,0.000000])
sh.A1.strength.set(0.0001)
print(sh.multipole.get())
