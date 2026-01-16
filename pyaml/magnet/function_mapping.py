from pyaml.magnet.hcorrector import HCorrector
from pyaml.magnet.octupole import Octupole
from pyaml.magnet.quadrupole import Quadrupole
from pyaml.magnet.sextupole import Sextupole
from pyaml.magnet.skewoctu import SkewOctu
from pyaml.magnet.skewquad import SkewQuad
from pyaml.magnet.skewsext import SkewSext
from pyaml.magnet.vcorrector import VCorrector

function_map: dict = {
    "B0": HCorrector,
    "A0": VCorrector,
    "B1": Quadrupole,
    "A1": SkewQuad,
    "B2": Sextupole,
    "A2": SkewSext,
    "B3": Octupole,
    "A3": SkewOctu,
}
