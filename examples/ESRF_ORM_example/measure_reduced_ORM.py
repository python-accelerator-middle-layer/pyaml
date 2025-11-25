from pathlib import Path

from pyaml.accelerator import Accelerator
from pyaml.tuning_tools.orbit_response_matrix import ConfigModel as ORM_ConfigModel
from pyaml.tuning_tools.orbit_response_matrix import OrbitResponseMatrix

parent_folder = Path(__file__).parent
config_path = parent_folder.parent.parent.joinpath(
    "tests", "config", "EBSOrbit.yaml"
).resolve()
sr = Accelerator.load(config_path)
element_holder = sr.design

orm = OrbitResponseMatrix(
    cfg=ORM_ConfigModel(
        bpm_array_name="BPM",
        hcorr_array_name="HCorr",
        vcorr_array_name="VCorr",
        corrector_delta=1e-6,
    ),
    element_holder=element_holder,
)

hcorr = element_holder.get_magnets("HCorr")
vcorr = element_holder.get_magnets("VCorr")
corrector_names = (
    hcorr["SJ2A*"].names()
    + hcorr["SF2A*"].names()
    + hcorr["SI2A*"].names()
    + vcorr["SJ2A*"].names()
    + vcorr["SF2A*"].names()
    + vcorr["SI2A*"].names()
)

orm.measure(corrector_names=corrector_names)
orm.save(parent_folder / Path("reduced_orm.json"))

ormdata = orm.get()
