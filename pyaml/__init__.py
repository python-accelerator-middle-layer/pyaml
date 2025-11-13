"""
pyAML package
~~~~~~~~~~~~~

pyAML
"""

__title__ = "pyAML"
__description__ = "Python Accelerator Middle Layer"
__url__ = "https://github.com/python-accelerator-middle-layer/pyaml"
__version__ = "0.1.0"
__author__ = "pyAML collaboration"
__author_email__ = ""

import logging.config
import os
from pyaml.common.exception import PyAMLException
from pyaml.common.exception import PyAMLConfigException

__all__ = [__version__, PyAMLException, PyAMLConfigException]


config_file = os.getenv("PYAML_LOG_CONFIG", "pyaml_logging.conf")

if os.path.exists(config_file):
    logging.config.fileConfig(config_file, disable_existing_loggers=False)

logger = logging.getLogger("pyaml")
level = os.getenv("PYAML_LOG_LEVEL", "").upper()
if len(level)>0:
    logger.setLevel(getattr(logging, level, logging.WARNING))
