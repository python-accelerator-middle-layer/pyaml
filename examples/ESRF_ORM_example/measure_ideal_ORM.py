from pyaml.accelerator import Accelerator
from pyaml.external.pySC_interface import pySCInterface
from pyaml.external.pySC import pySC 
from pyaml.external.pySC.pySC.apps import measure_ORM
from pathlib import Path
import numpy as np
import json


config_path = Path(__file__).parent.parent.parent.joinpath('tests','config','EBSOrbit.yaml').resolve()
sr = Accelerator.load(config_path)
ebs = sr.design

kick_delta = 1e-6

interface = pySCInterface(element_holder=ebs)
corrector_names = ebs.get_magnets('HCorr').names() + ebs.get_magnets('VCorr').names()
bpm_names = ebs.get_bpms('BPM').names()

generator = measure_ORM(interface=interface, corrector_names=corrector_names, delta=kick_delta, skip_save=True)

#pySC.disable_pySC_rich()
for code, measurement in generator:
    pass

response_data = measurement.response_data # contains also pre-processed data
RM = pySC.ResponseMatrix(matrix=response_data.matrix, input_names=response_data.input_names, output_names=bpm_names)
#output_names (bpm names) are actually not used anywhere, but useful metadata.
json.dump(RM.model_dump(), open(Path(__file__).parent.joinpath('ideal_orm.json'),'w'), indent=2)