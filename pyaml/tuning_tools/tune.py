from .. import PyAMLException
from ..common.element import ElementConfigModel, Element
from ..common.constants import ACTION_APPLY,ACTION_RESTORE
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..common.element_holder import ElementHolder
    from ..arrays.magnet_array import MagnetArray

try:
    from typing import Self  # Python 3.11+
except ImportError:
    from typing_extensions import Self  # Python 3.10 and earlier
import numpy as np
from pydantic import BaseModel, ConfigDict
from collections.abc import Callable
import json
from datetime import datetime
import time

# Define the main class name for this module
PYAMLCLASS = "Tune"

class ConfigModel(ElementConfigModel):

    quad_array: str
    """Array name of quad used to adjust the tune"""
    betatron_tune: str 
    """Name of the diagnostic pyaml device for measuring the tune"""
    delta: float
    """Delta strength used to get the response matrix"""

class TuneResponse(object):

    def __init__(self,parent:"Tune"):
        self.__parent = parent
        self.__respmatrix:np.array = None
        self.__date:str = None
        self.__correctionmat:np.array = None

    def __set_resp_map(self,mat):
        self.__respmatrix = mat
        self.__correctionmat = np.linalg.pinv(mat.T)

    def measure(self,callback:Callable | None = None):
        """
        Measure tune response matrix

        Parameters
        ----------
        callback: Callable
            tune_callback(step:int,action:int,m:Magnet,dtune:np.array)
            Callback executed after each strength setting. The magnet and step are passed as input arguement of the callback.
            If the callback return false, then the process is aborted. 
        """
        quads = self.quads() # Returns attached quad devices
        tunemat = np.zeros((len(quads), 2))
        initial_tune = self.__parent.get()
        delta = self.__parent._cfg.delta # TODO: handle delta array
        aborted = False

        for idx, m in enumerate(quads):
            str = m.strength.get()
            # apply strength
            m.strength.set(str + delta)

            if callback and not callback(idx,ACTION_APPLY,m,[np.nan,np.nan]):
                aborted = True
                break

            tune = self.__parent.get()
            dq = tune - initial_tune
            tunemat[idx] = dq / delta

            # Restore strength
            m.strength.set(str)
            if callback and not callback(idx,ACTION_RESTORE,m,tunemat[idx]):
                aborted = True
                break

        if not aborted:
            self.__set_resp_map(tunemat)
            now = datetime.now()
            self.__date = now.strftime("%m/%d/%Y, %H:%M:%S")

    def save_json(self,filename:str):
        """
        Save tune response matrix

        Parameters
        ----------
        filename: str
            File name to save
        """
        if self.__respmatrix is None:
            raise PyAMLException("TuneResponse.save(): no matrix loaded or measured")
        d = {"date":self.__date,"input_names":self.quads().names(), "input_delta":self.__parent._cfg.delta, "matrix":self.__respmatrix.tolist()}
        with open(filename, 'w') as f:
            json.dump(d, f)

    def load_json(self,filename:str):
        """
        Load tune response matrix

        Parameters
        ----------
        filename: str
            File name to load
        """
        with open(filename) as f:
            d = json.load(f)
        self.__date = d["date"]
        self.__input_names = d["input_names"]
        delta = d["input_delta"]
        self.__set_resp_map(np.array(d["matrix"]))

    def get(self) -> np.array:
        """
        Return tune response matrix
        """
        return self.__respmatrix

    def correct(self,dtune:np.array) -> np.array:
        """
        Return delta strengths for tune correction

        Parameters
        ----------
        dtune: np.array
            Delta tune
        """
        if self.__respmatrix is None:
            raise PyAMLException("TuneResponse.correct(): no matrix loaded or measured")
        return np.matmul(self.__correctionmat, dtune)
    
    def quads(self) -> "MagnetArray":
        """
        Returns quads used for tune correction
        """
        a_name = self.__parent._cfg.quad_array
        return self.__parent._peer.get_magnets(a_name)

class Tune(Element):
    """
    Class providing tune response matrix measurement and tune adjustment
    """

    def __init__(self, cfg: ConfigModel):
        """
        Construct a Tune adjustmenet object.

        Parameters
        ----------
        cfg : ConfigModel
            Configuration for the tune adjustement.
        """
        super().__init__(cfg.name)
        self._cfg = cfg
        self.__tm = None
        self.__tr:TuneResponse = None

    def get(self):
        """
        Return the betatron tune
        """
        self.check_peer()
        if not self.__tm:
            # Lazily attach the tune monitor
            self.__tm = self._peer.get_betatron_tune_monitor(self._cfg.betatron_tune)
        return self.__tm.tune.get()
    
    def set(self,tune:np.array,iter:int = 1,wait_time:float = 0.):
        """
        Sets the tune

        Parameters
        ----------
        tune: np.array
            Tune setpoint
        iter_nb: int
            Number of iteration
        wait_time: float
            Time to wait in second between 2 iterations
        """
        for _ in range(iter):
            diff_tune = tune - self.get()
            str = self.__tr.quads().strengths.get()
            str += self.__tr.correct(diff_tune)
            self.__tr.quads().strengths.set(str)
            time.sleep(wait_time)
    
    @property
    def response(self) -> TuneResponse:
        return self.__tr

    def attach(
        self,
        peer:"ElementHolder",
    ) -> Self:
        """
        Create a new reference to attach this tune object to a simulator
        or a control systemand.
        """
        obj = self.__class__(self._cfg)
        obj._peer = peer
        obj.__tr = TuneResponse(obj)
        return obj
