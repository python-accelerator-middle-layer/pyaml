import json

from .manager import ConfigurationManager


class CfgDict(object):
    """
    Class allowing to have a dict in a configuration of an object
    """

    def __init__(self, config: dict):
        """
        Construct a ConfigDict

        Parameters
        ----------
        config: dict
            Configuration dict
        """
        self._config = ConfigurationManager.strip_internal_metadata(config)

    def get(self) -> dict:
        """
        Returns config dict
        """
        return self._config

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, json.dumps(self._config))
