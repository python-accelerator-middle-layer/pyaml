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
        Polynomial coefficients index (sarting from 0)
    """

    def __init__(self, attName: str, index: int, sign: float = 1.0):
        """
        Construct a polynom information object
        """
        self.attName = attName
        self.index = index
        self.sign = sign
