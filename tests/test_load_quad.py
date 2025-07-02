from pathlib import Path

#from pyaml.configuration import set_root_folder, load_from_yaml, load_from_json
from pyaml.configuration import load
from pyaml.configuration import depthFirstBuild
from pyaml.magnet.quadrupole import Quadrupole
from pyaml.magnet.quadrupole import ConfigModel as QuadrupoleConfigModel

from pyaml.magnet.linear_unitconv import LinearUnitConv
from pyaml.magnet import cfm_magnet
import pprint as pp
import json
#set_root_folder(Path(__file__).parent.parent)

if False:
    print(json.dumps(QuadrupoleConfigModel.model_json_schema(),indent=2))
    quit()

if False:
    # To run this one, please run 'pip install .' first in tests/external
    cfg_quad_yaml = load("tests/config/sr/quadrupoles/QEXT.yaml")
    quadWithExt: Quadrupole = depthFirstBuild(cfg_quad_yaml[0])
    quadWithExt.strength.set(10.0)
    print(quadWithExt.strength.get())

#quad: Quadrupole = load_from_yaml("tests/config/sr/quadrupoles/QF1C01A.yaml")

cfg_quad_yaml = load("tests/config/sr/quadrupoles/QF1C01A.yaml")
quad:Quadrupole = depthFirstBuild(cfg_quad_yaml[0])
uc: LinearUnitConv = quad.unitconv
print(uc._curve[1])
quad.unitconv.set_magnet_rigidity(6e9 / 3e8)
quad.strength.set(0.7962)
print(f"Current={quad.current.get()}")
print(f"Unit={quad.strength.unit()}")
print(f"Unit={quad.current.unit()}")

cfg_quad_json = load("tests/config/sr/quadrupoles/QF1C01A.json")
quad2:Quadrupole = depthFirstBuild(cfg_quad_json[0])
uc: LinearUnitConv = quad2.unitconv
print(uc._curve[1])
uc.set_magnet_rigidity(6e9 / 3e8)
quad2.strength.set(0.7962)
print(f"Current={quad2.current.get()}")
print(f"Unit={quad2.strength.unit()}")
print(f"Unit={quad2.current.unit()}")

cfg = cfm_magnet.ConfigModel(name="S1C01", B0="S1C01-H", A0="S1C01-V", B1="S1C01-Q")
m = cfm_magnet.CombinedFunctionMagnet(cfg)
m.multipole.set([0, 0, 10])
m.b1.strength.set(20)
print(m.b1.name)

