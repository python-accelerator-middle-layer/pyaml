from pathlib import Path

from pyaml.configuration import set_root_folder, load_from_yaml, load_from_json
from pyaml.magnet import CombinedFunctionMagnet, Quadrupole, LinearUnitConv

set_root_folder(Path(__file__).parent.parent)

if False:
    # To run this one, please run 'pip install .' first in tests/external
    cfg_quad_yaml = load("tests/config/sr/quadrupoles/QEXT.yaml")
    quadWithExt: Quadrupole = depthFirstBuild(cfg_quad_yaml[0])
    quadWithExt.strength.set(10.0)
    print(quadWithExt.strength.get())

quad: Quadrupole = load_from_yaml("tests/config/sr/quadrupoles/QF1C01A.yaml")
uc: LinearUnitConv = quad.unitconv
print(uc._curve[1])
uc.set_magnet_rigidity(6e9 / 3e8)
quad.strength.set(0.7962)
print(f"Current={quad.current.get()}")
print(f"Unit={quad.strength.unit()}")
print(f"Unit={quad.current.unit()}")

quad2: Quadrupole = load_from_json("tests/config/sr/quadrupoles/QF1C01A.json")
uc: LinearUnitConv = quad2.unitconv
print(uc._curve[1])
uc.set_magnet_rigidity(6e9 / 3e8)
quad2.strength.set(0.7962)
print(f"Current={quad2.current.get()}")
print(f"Unit={quad2.strength.unit()}")
print(f"Unit={quad2.current.unit()}")

cfg = CombinedFunctionMagnet.Config(name="S1C01", H="S1C01-H", V="S1C01-V", Q="S1C01-Q")
m = CombinedFunctionMagnet.CombinedFunctionMagnet(cfg)
m.multipole.set([0, 0, 10])
m.quad.strength.set(20)
print(m.quad.name)
