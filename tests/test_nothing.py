import numpy as np
from scipy.interpolate import make_smoothing_spline
import matplotlib.pyplot as plt

curve = np.genfromtxt("tests/config/sr/unitconv/QF1_strength.csv", delimiter=",", dtype=float)
len = np.shape(curve)[0]
x = curve[:,0]
y = curve[:,1]
lamba = 0

spl = make_smoothing_spline(x, y, lam=lamba)
xnew = x[len-1]/2

plt.plot(xnew, spl(xnew), 'o', label=fr'$\lambda=${lamba}')
plt.plot(x, y, 'o')
plt.legend()

plt.show()
