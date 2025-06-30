"""
Class for load CSV (x,y) curve
"""
from .Curve import Curve
import numpy as np

class CSVCurve(Curve):

    file : str
    
    def __init__(self, **data):
        super().__init__(**data)

        # Load CSV curve
        self._curve = np.genfromtxt(self.file,delimiter=',',dtype=float)
        _s = np.shape(self._curve)
        if len(_s)!=2 or _s[1]!=2:
            raise Exception(self.file + " wrong dimension")

    def get_curve(self) -> np.array:
        return self._curve
    
def factory_constructor(config: dict) -> CSVCurve:
   """Construct a CSVCurve from Yaml config file"""
   return CSVCurve(**config)
