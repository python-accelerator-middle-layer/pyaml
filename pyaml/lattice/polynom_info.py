"""
Class providing polynom information
"""

class PolynomInfo:
    """
    Polynom information
    """

    def __init__(self,attName:str,index:int):
        """
        Construct a polynom information object
        
        Parameters
        ----------
        attName : str
            Name of the AT element attribute ('PolynomA' or 'PolynomB')
        index : int
            Polynomial coefficients index (sarting from 0)
        """
        self.attName = attName
        self.index = index