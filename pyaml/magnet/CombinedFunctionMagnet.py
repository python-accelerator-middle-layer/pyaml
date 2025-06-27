from .Magnet import Magnet
from .Quadrupole import Quadrupole
from .UnitConv import UnitConv
from pyaml.control import Abstract
from pyaml.configuration.Factory import validate
from pyaml.lattice.RWArray import RWArray

class CombinedFunctionMagnet(Magnet):
    """CombinedFunctionMagnet class"""    
    @validate
    def __init__(self, name:str, H:str=None,V:str=None,Q:str=None,SQ:str=None,S:str=None,O:str=None, unitconv: UnitConv = None):
        super().__init__(name)

        self.unitconv = unitconv

        # TODO Count number of defined strength
        # TODO Check that UnitConv is coherent (number of strengths same as number of defined single function magnet)
        self.multipole : Abstract.ReadWriteFloatArray = RWArray(name,self.unitconv,3) 

        idx = 0
        #Create single function magnet
        if H is not None:
            #self.horz = HorizontalCorrector(H)  # TODO implement HorizontalCorrector
            #self.horz.setSource(self.multipole,idx)
            idx+=1 

        if V is not None:
            #self.vert = VerticalCorrector(V) # TODO implement VerticalCorrector
            #self.setSource(self.multipole,idx)
            idx+=1 

        if Q is not None:
            self.quad = Quadrupole(Q)
            self.quad.setSource(self.multipole,idx)
            idx+=1 

    def __repr__(self):
        return "%s(name=%s, unitconv=%s)" % (
            self.__class__.__name__, self.name, self.unitconv)

def factory_constructor(config: dict) -> CombinedFunctionMagnet:
   """Construct a Quadrupole from Yaml config file"""
   return CombinedFunctionMagnet(**config)
