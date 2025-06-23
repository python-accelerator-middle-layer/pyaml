class Element(object):
    """
    Class providing access to one element of a physical or simulated lattice

    Attributes:
    name (str): The name identifying the element in configuration file
    hardware_name (str): The name identifying the element in the control system (ie: a PV or a tango attribute name)
    model_name (str): The name identifying the element in the model
    """

    def __init__(self,name=None,hardware_name=None):
        self.name = name
        self.hardware_name = hardware_name
