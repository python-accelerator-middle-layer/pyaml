"""
Class for load CSV (x,y) curve
"""
from .Curve import Curve
import numpy as np

class CSVCurve(Curve):
    
    def __init__(self,file:str):
        # Load CSV curve
        self.curve = np.genfromtxt(file,delimiter=',',dtype=float)
        s = np.shape(self.curve)
        if len(s)!=2 or s[1]!=2:
            raise Exception(file + " wrong dimension")

    def get_curve(self) -> np.array:
        return self.curve

def factory_constructor(config: dict) -> CSVCurve:
   """Construct a CSVCurve from Yaml config file"""
   return CSVCurve(**config)
