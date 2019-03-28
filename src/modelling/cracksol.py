# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------
import numpy as num
import logging

from pyrocko.guts import Float, Object
from pyrocko.guts_array import Array

guts_prefix = 'modelling'

logger = logging.getLogger('pyrocko.modelling.cracksol')


class CrackSolutions(Object):
    pass


class GriffithCrack(CrackSolutions):
    width = Float.T(
        help='Width equals to 2*a',
        default=1.)

    poisson = Float.T(
        help='Poisson ratio',
        default=.25)

    shear_mod = Float.T(
        help='Shear modulus [Pa]',
        default=1.e9)

    stressdrop = Array.T(
        help='Stress drop array:'
             '[sig13_r - sig13_c, sig12_r - sig12_c, sig11_r - sig11_c]'
             '[dstress_Strike, dstress_Dip, dstress_Tensile]',
        default=num.array([0., 0., 0.]))

    @property
    def a(self):
        return self.width / 2.

    def disloc_modeI(self, x_obs):
        if type(x_obs) is not num.ndarray:
            x_obs = num.array(x_obs)

        disl = num.zeros((x_obs.shape[0], 3))
        disl[:, 2] = \
            self.stressdrop[2] * num.sqrt(self.a**2 - x_obs**2) * (
            2 * (1 - self.poisson)) / self.shear_mod

        return disl


__all__ = [
    'GriffithCrack']
