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

orm.measure()
orm.save(parent_folder / Path("ideal_orm.json"))
orm.save(parent_folder / Path("ideal_orm.yaml"), with_type="yaml")
orm.save(parent_folder / Path("ideal_orm.npz"), with_type="npz")

ormdata = orm.get()
