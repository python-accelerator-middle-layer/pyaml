from typing import Optional

from pydantic import BaseModel, ConfigDict

PYAMLCLASS = "ResponseMatrix"


class ConfigModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    matrix: list[list[float]]
    input_names: Optional[list[str]]
    output_names: list[str]
    rf_response: Optional[list[float]]


class ResponseMatrix(object):
    def __init__(self, cfg: ConfigModel):
        self._cfg = cfg

        # self.matrix = cfg.matrix
        # self.input_names = cfg.input_names
        # self.output_names = cfg.output_names
        # self.rf_response = cfg.rf_response
