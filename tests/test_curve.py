from pyaml.configuration.csvcurve import CSVCurve,ConfigModel
from pyaml.configuration.curve import Curve
from pyaml.configuration import set_root_folder
import numpy as np


def curve_test(file:str,current:float,strength:float):

    curveConfig = ConfigModel(file=file)
    curve = CSVCurve(curveConfig)
    curveData = curve.get_curve()
    icurveData = Curve.inverse(curveData)
    x1 = np.interp( current , curveData[:, 0], curveData[:, 1] )
    assert( np.abs(x1-strength) < 1e-6 )
    y1 = np.interp( x1 , icurveData[:, 0], icurveData[:, 1] )
    assert( np.abs(y1-current) < 1e-6 )


def test_curve(config_root_dir):
    set_root_folder(config_root_dir)
    curve_test("sr/magnet_models/QF1_strength.csv",85,16.618788)
    curve_test("sr/magnet_models/QD2_strength.csv",87,-12.319894)