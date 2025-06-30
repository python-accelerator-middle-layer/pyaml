from pyaml.configuration import load
from pyaml.configuration import depthFirstBuild
import pprint as pp
from pyaml.magnet.LinearUnitConv import LinearUnitConv
from pyaml.magnet.Quadrupole import Quadrupole
from pyaml.magnet.CombinedFunctionMagnet import CombinedFunctionMagnet

if False:
    # To run this one, please run 'pip install .' first in tests/external
    cfg_quad_yaml = load("tests/config/sr/quadrupoles/QEXT.yaml")
    quadWithExt:Quadrupole = depthFirstBuild(cfg_quad_yaml[0])
    quadWithExt.strength.set(10.0)
    print(quadWithExt.strength.get())

cfg_quad_yaml = load("tests/config/sr/quadrupoles/QF1C01A.yaml")
#pp.pprint(cfg_quad)
quad:Quadrupole = depthFirstBuild(cfg_quad_yaml[0])
uc:LinearUnitConv = quad.unitconv
print(uc._curve[1])
uc.set_magnet_rigidity( 6e9/3e8 )
quad.strength.set(0.7962)
print(f"Current={quad.current.get()}")
print(f"Unit={quad.strength.unit()}")
print(f"Unit={quad.current.unit()}")

cfg_quad_json = load("tests/config/sr/quadrupoles/QF1C01A.json")
#pp.pprint(cfg_quad_json)
quad2:Quadrupole = depthFirstBuild(cfg_quad_json[0])
uc:LinearUnitConv = quad2.unitconv
print(uc._curve[1])
uc.set_magnet_rigidity( 6e9/3e8 )
quad2.strength.set(0.7962)
print(f"Current={quad2.current.get()}")
print(f"Unit={quad2.strength.unit()}")
print(f"Unit={quad2.current.unit()}")


m =  CombinedFunctionMagnet("S1C01",H="S1C01-H",V="S1C01-V",Q="S1C01-Q")
m.multipole.set([0,0,10])
m.quad.strength.set(20)
print(m.quad.name)




