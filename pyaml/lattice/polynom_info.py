"""
Class providing polynom information
"""

class PolynomInfo:
    """
    Polynom information

    Parameters
    ----------
    attName : str
        Name of the AT element attribute ('PolynomA' or 'PolynomB')
    index : int
        Index (sarting from 0)
    """
    def __init__(self,attName:str,index:int):
        self.attName = attName
        self.index = index