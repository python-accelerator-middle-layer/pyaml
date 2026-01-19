from pathlib import Path

from pyaml.accelerator import Accelerator
from pyaml.tuning_tools.orbit_response_matrix import ConfigModel as ORM_ConfigModel
from pyaml.tuning_tools.orbit_response_matrix import OrbitResponseMatrix

parent_folder = Path(__file__).parent
config_path = parent_folder.joinpath("BESSY2Orbit.yaml").resolve()

sr = Accelerator.load(config_path)
element_holder = sr.design


orbit = element_holder.orbit
orm = OrbitResponseMatrix(
    cfg=ORM_ConfigModel(
        bpm_array_name=orbit.bpm_array_name,
        hcorr_array_name=orbit.hcorr_array_name,
        vcorr_array_name=orbit.vcorr_array_name,
        corrector_delta=1e-6,
    ),
    element_holder=element_holder,
)

orm.measure()
orm.save(parent_folder / Path("ideal_orm.json"))
