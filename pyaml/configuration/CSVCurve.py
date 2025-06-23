"""
Class for load CSV curve
"""

class CSVCurve(object):
    def __init__(self,fileName:str):
        pass

def factory_constructor(config: dict) -> CSVCurve:
   """Construct a CSVCurve from Yaml config file"""
   return CSVCurve(**config)
