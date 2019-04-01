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


class GriffithCrack(Object):
    '''
    Analytical Griffith crack model
    '''

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
             '[sigi3_r - sigi3_c, sigi2_r - sigi2_c, sigi1_r - sigi1_c]'
             '[dstress_Strike, dstress_Dip, dstress_Tensile]',
        default=num.array([0., 0., 0.]))

    @property
    def a(self):
        '''
        Half width of the crack
        '''

        return self.width / 2.

    def disloc_infinite2d(self, x_obs):
        '''
        Calculation of dislocation at crack surface along x2 axis

        Follows equations by Pollard and Segall (1987) to calculate
        displacements for an infinite 2D crack extended in x3 direction,
        opening in x1 direction and the crack extending in x2 direction.

        :param x_obs: Observation point coordinates along x2-axis.
            If x_obs < -self.a or x_obs > self.a, output dislocations are zero
        :type x_obs: :py:class:`numpy.ndarray`, ``(N,)``

        :return: dislocations at each observation point in strike, dip and
            tensile direction.
        :rtype: :py:class:`numpy.ndarray`, ``(N, 3)``
        '''

        if type(x_obs) is not num.ndarray:
            x_obs = num.array(x_obs)

        factor = num.array([2. / self.shear_mod])
        factor = num.append(
            factor, num.tile(
                2. * (1. - self.poisson) / self.shear_mod, (1, 2)))

        crack_el = (x_obs > -self.a) | (x_obs < self.a)

        disl = num.zeros((x_obs.shape[0], 3))
        disl[crack_el, :] = \
            self.stressdrop * num.sqrt(
            self.a**2 - num.tile(x_obs[crack_el, num.newaxis], (1, 3))**2) * \
            factor

        return disl

    def disloc_circular(self, x_obs):
        '''
        Calculation of dislocation at crack surface along x2 axis

        Follows equations by Pollard and Segall (1987) to calculate
        displacements for a circulat crack extended in x2 and x3 direction and
        opening in x1 direction.

        :param x_obs: Observation point coordinates along axis through crack
            centre. If x_obs < -self.a or x_obs > self.a, output dislocations
            are zero
        :type x_obs: :py:class:`numpy.ndarray`, ``(N,)``

        :return: dislocations at each observation point in strike, dip and
            tensile direction.
        :rtype: :py:class:`numpy.ndarray`, ``(N, 3)``
        '''

        if type(x_obs) is not num.ndarray:
            x_obs = num.array(x_obs)

        # factor = num.tile(24. / (7. * num.pi * self.shear_mod), (1, 3))
        factor = num.array([4. / (self.shear_mod * num.pi)])
        factor = num.append(
            factor, num.tile(
                4. * (1. - self.poisson) / (self.shear_mod * num.pi), (1, 2)))

        crack_el = (x_obs > -self.a) | (x_obs < self.a)

        disl = num.zeros((x_obs.shape[0], 3))
        disl[crack_el] = \
            self.stressdrop * num.sqrt(
            self.a**2 - num.tile(x_obs[crack_el, num.newaxis], (1, 3))**2) * \
            factor

        return disl


__all__ = [
    'GriffithCrack']
