import json

from pydantic import BaseModel, ConfigDict

from .manager import ConfigurationManager

# Define the main class name for this module
PYAMLCLASS = "CfgDict"


class ConfigModel(BaseModel):
    """
    Configuration model for random dict

    Parameters
    ----------
    cfg_dict : dict
        The dict
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    cfg_dict: dict


class CfgDict(object):
    """
    Class allowing to have a dict in a configuration of an object
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a ConfigDict

        Parameters
        ----------
        config: dict
            Configuration dict
        """
        self._config = ConfigurationManager.strip_internal_metadata(cfg.cfg_dict)

    def get(self) -> dict:
        """
        Returns config dict
        """
        return self._config

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, json.dumps(self._config))
