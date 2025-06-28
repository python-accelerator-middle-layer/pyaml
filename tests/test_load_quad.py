from pyaml.configuration import load
from pyaml.configuration import depthFirstBuild
import pprint as pp
from pyaml.magnet.LinearUnitConv import LinearUnitConv
from pyaml.magnet.Quadrupole import Quadrupole
from pyaml.magnet.CombinedFunctionMagnet import CombinedFunctionMagnet

# To run this one, please run pip install . first in tests/external
cfg_quad = load("tests/config/sr/quadrupoles/QEXT.yaml")
quadWithExt:Quadrupole = depthFirstBuild(cfg_quad[0])
quadWithExt.strength.set([10.0]);

cfg_quad = load("tests/config/sr/quadrupoles/QF1C01A.yaml")
#pp.pprint(cfg_quad)
quad:Quadrupole = depthFirstBuild(cfg_quad[0])
uc:LinearUnitConv = quad.unitconv
print(uc.curve[1])

m =  CombinedFunctionMagnet("S1C01",H="S1C01-H",V="S1C01-V",Q="S1C01-Q")
m.multipole.set([0,0,10])
m.quad.strength.set(20)
print(m.quad.name)
#cfg_quad2 = load("tests/config/sr/quadrupoles/QF1C01A_2.yaml")
#pp.pprint(cfg_quad2)

#cfg_quad3 = load("tests/config/sr/quadrupoles/QF1C01A.json")
#pp.pprint(cfg_quad3)

#quad: Quadrupole = build(cfg_quad[0])
#print(quad)
#quad.strength.set(0.2)




