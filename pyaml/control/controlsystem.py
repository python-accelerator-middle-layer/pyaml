from abc import ABCMeta, abstractmethod
from ..lattice.element_holder import ElementHolder
from ..lattice.element import Element
from ..control.abstract_impl import RWHardwareScalar,RWHardwareArray,RWStrengthScalar,RWStrengthArray
from ..magnet.magnet import Magnet
from ..magnet.cfm_magnet import CombinedFunctionMagnet

class ControlSystem(ElementHolder,metaclass=ABCMeta):
    """
    Abstract class providing access to a control system float variable
    """

    def __init__(self):
        ElementHolder.__init__(self)

    @abstractmethod
    def init_cs(self):
        """Initialize control system"""
        pass

    @abstractmethod
    def name(self) -> str:
        """Return control system name (i.e. live)"""
        pass

    def set_energy(self,E:float):
        """
        Sets the energy on magnets belonging to this control system
        
        Parameters
        ----------
        E : float
            Energy in eV
        """
        for m in self.get_all_magnets().items():
            m[1].set_energy(E)
    
    def fill_device(self,elements:list[Element]):
        """
        Fill device of this control system with Element coming from the configuration file
        
        Parameters
        ----------
        elements : list[Element]
            List of elements coming from the configuration file to attach to this control system
        """           
        for e in elements:
          if isinstance(e,Magnet):
            current = RWHardwareScalar(e.model)
            strength = RWStrengthScalar(e.model)
            # Create a unique ref for this control system
            m = e.attach(strength,current)
            self.add_magnet(str(m),m)
          elif isinstance(e,CombinedFunctionMagnet):
            self.add_magnet(str(e),e)
            currents = RWHardwareArray(e.model)
            strengths = RWStrengthArray(e.model)
            # Create unique refs of each function for this control system
            ms = e.attach(strengths,currents)
            for m in ms:
              self.add_magnet(str(m),m)
