from pyaml.pyaml import pyaml,PyAML
from pyaml.instrument import Instrument
import pyaml as pyaml_pkg
from pyaml.lattice.element_holder import MagnetType
from pyaml.arrays.magnet_array import MagnetArray
import numpy as np
import at

#def test_aml(config_root_dir):

ml:PyAML = pyaml("tests/config/EBSTune.yaml")
sr:Instrument = ml.get('sr')
sr.design.get_lattice().disable_6d()

quadForTune = sr.design.get_magnets("QForTune")

# Build tune response matrix
tune = sr.design.get_lattice().get_tune()
print(tune)
tunemat = np.zeros((len(quadForTune),2))

for idx,m in enumerate(quadForTune):
    str = m.strength.get()
    m.strength.set(str+1e-4)
    dq = sr.design.get_lattice().get_tune() - tune
    tunemat[idx] = dq*1e4
    m.strength.set(str)

# Compute correction matrix
correctionmat = np.linalg.pinv(tunemat.T)

# Correct tune
strs = quadForTune.strengths.get()
strs += np.matmul(correctionmat,[0.1,0.05]) # Ask for correction [dqx,dqy]
quadForTune.strengths.set(strs)
newTune = sr.design.get_lattice().get_tune()
print(newTune-tune) # Expect someting close to [0.1,0.05]

#pyaml.configuration.factory._ALL_ELEMENTS.clear()
