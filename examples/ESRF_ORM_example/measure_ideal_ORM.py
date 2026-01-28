from pathlib import Path

from pyaml.accelerator import Accelerator
from pyaml.tuning_tools.orbit_response_matrix import ConfigModel as ORM_ConfigModel
from pyaml.tuning_tools.orbit_response_matrix import OrbitResponseMatrix

parent_folder = Path(__file__).parent
config_path = parent_folder.parent.parent.joinpath(
    "tests", "config", "EBSOrbit.yaml"
).resolve()
sr = Accelerator.load(config_path)
eh = sr.design

eh.orm.measure()
eh.orm.save(parent_folder / Path("ideal_orm.json"))
eh.orm.save(parent_folder / Path("ideal_orm.yaml"), with_type="yaml")
eh.orm.save(parent_folder / Path("ideal_orm.npz"), with_type="npz")

ormdata = eh.get()
