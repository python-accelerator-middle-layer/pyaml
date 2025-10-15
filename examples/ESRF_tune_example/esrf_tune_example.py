from pyaml.pyaml import pyaml,PyAML
from pyaml.instrument import Instrument
from pyaml.configuration.factory import Factory
import numpy as np
import os


# Get the directory of the current script
script_dir = os.path.dirname(__file__)

# Go up one level and then into 'data'
relative_path = os.path.join(script_dir, '..', '..', 'tests', 'config','EBSTune.yaml')

# Normalize the path (resolves '..')
absolute_path = os.path.abspath(relative_path)

ml:PyAML = pyaml(absolute_path)
sr:Instrument = ml.get('sr')
sr.design.get_lattice().disable_6d()

quadForTuneDesign = sr.design.get_magnets("QForTune")
quadForTuneLive = sr.live.get_magnets("QForTune")

# Build tune response matrix
tune = sr.design.get_lattice().get_tune()
print(tune)
tunemat = np.zeros((len(quadForTuneDesign),2))

for idx,m in enumerate(quadForTuneDesign):
     str = m.strength.get()
     m.strength.set(str+1e-4)
     dq = sr.design.get_lattice().get_tune() - tune
     tunemat[idx] = dq*1e4
     m.strength.set(str)

# Compute correction matrix
correctionmat = np.linalg.pinv(tunemat.T)

# Correct tune
strs = quadForTuneDesign.strengths.get()
strs += np.matmul(correctionmat,[0.1,0.05]) # Ask for correction [dqx,dqy]
quadForTuneDesign.strengths.set(strs)
newTune = sr.design.get_lattice().get_tune()
diffTune = newTune-tune
print(diffTune)
assert( np.abs(diffTune[0]-0.1) < 1e-3 )
assert( np.abs(diffTune[1]-0.05) < 1e-3 )

if False:
    # Correct the tune on live (need a Virutal Accelerator)
    quadForTuneLive = sr.live.get_magnets("QForTune")
    strs = quadForTuneLive.strengths.get()
    strs += np.matmul(correctionmat,[0.1,0.05]) # Ask for correction [dqx,dqy]
    quadForTuneLive.strengths.set(strs)


Factory.clear()
