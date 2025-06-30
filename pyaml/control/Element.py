from pydantic import BaseModel
from typing import Optional

class Element(BaseModel):
    """
    Class providing access to one element of a physical or simulated lattice

    Attributes:
    name (str): The name identifying the element in configuration file
    """
    
    name : str
