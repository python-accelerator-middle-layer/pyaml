from pyaml.configuration import load
from pyaml.configuration import depthFirstBuild
import pprint as pp
from pyaml.magnet.LinearUnitConv import LinearUnitConv
from pyaml.magnet.Quadrupole import Quadrupole

cfg_quad = load("tests/config/sr/quadrupoles/QF1C01A.yaml")
#pp.pprint(cfg_quad)
quad:Quadrupole = depthFirstBuild(cfg_quad[0])
uc:LinearUnitConv = quad.unitconv
print(uc.curve[0])

#cfg_quad2 = load("tests/config/sr/quadrupoles/QF1C01A_2.yaml")
#pp.pprint(cfg_quad2)

#cfg_quad3 = load("tests/config/sr/quadrupoles/QF1C01A.json")
#pp.pprint(cfg_quad3)

#quad: Quadrupole = build(cfg_quad[0])
#print(quad)
#quad.strength.set(0.2)




