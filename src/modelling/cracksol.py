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

    shearmod = Float.T(
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

    def _disloc_infinite2d_along_x1(self, x1_obs):
        factor1 = num.tile(
            (1. - self.poisson) / self.shearmod, (1, 3))
        factor1[0] *= 1. / (1. - self.poisson)

        factor2 = num.tile(
            1. / (2. * self.shearmod), (1, 3))
        factor2[0] = 0.

        crack_el = x1_obs > 0.
        x1_obs = x1_obs[crack_el, num.newaxis]

        stressdrop2 = num.array([
            0., -self.stressdrop[2], self.stressdrop[1]])

        disl = num.zeros((x1_obs.shape[0], 3))

        disl[crack_el, :] = \
            self.stressdrop * factor1 * (
                num.sqrt(num.tile(x1_obs, (1, 3))**2 + self.a**2) -
                num.abs(x1_obs))

        disl[crack_el, :] += \
            stressdrop2 * factor2 * (
                num.abs(x1_obs - num.sqrt(
                    (x1_obs**2 + self.a**2) / (x1_obs**2))))

        return disl

    def _disloc_infinite2d_along_x2(self, x2_obs):
        crack_el = (x2_obs >= -self.a) & (x2_obs <= self.a)

        disl = num.zeros((x2_obs.shape[0], 3))
        if self.stressdrop[0] != 0.:
            # Mode III Shearing
            factor_in = 2. / self.shearmod

            disl[crack_el, 0] = \
                self.stressdrop[0] * factor_in * num.sqrt(
                    self.a**2 - x2_obs[crack_el]**2)

        elif self.stressdrop[1] != 0.:
            # Mode II Shearing
            factor = (1. - 2 * self.poisson) / (2. * self.shearmod)

            disl[crack_el, 1] = \
                self.stressdrop[1] * factor * x2_obs[crack_el]

            sign = num.sign(x2_obs)

            disl[~crack_el, 1] = \
                self.stressdrop[1] * factor * self.a * sign[~crack_el] * (
                    num.abs(x2_obs[~crack_el] / self.a) -
                    num.sqrt(x2_obs[~crack_el]**2 / self.a**2 - 1.))

        elif self.stressdrop[2] != 0.:
            # Mode I Opening
            disl[crack_el, 2] = \
                2. * (1. - self.poisson) / self.shearmod * \
                self.stressdrop[2] * num.sqrt(self.a**2 - x2_obs[crack_el]**2)

        return disl

    def disloc_infinite2d(self, x1_obs, x2_obs):
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

        if type(x1_obs) is not num.ndarray:
            x1_obs = num.array(x1_obs)
        if type(x2_obs) is not num.ndarray:
            x2_obs = num.array(x2_obs)

        if (x1_obs == 0.).all():
            return self._disloc_infinite2d_along_x2(x2_obs)
        elif (x2_obs == 0.).all():
            return self._disloc_infinite2d_along_x1(x1_obs)

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

        # factor = num.tile(24. / (7. * num.pi * self.shearmod), (1, 3))
        factor = num.array([4. / (self.shearmod * num.pi)])
        factor = num.append(
            factor, num.tile(
                4. * (1. - self.poisson) / (self.shearmod * num.pi), (1, 2)))

        crack_el = (x_obs > -self.a) | (x_obs < self.a)

        disl = num.zeros((x_obs.shape[0], 3))
        disl[crack_el] = \
            self.stressdrop * num.sqrt(
            self.a**2 - num.tile(x_obs[crack_el, num.newaxis], (1, 3))**2) * \
            factor

        return disl


__all__ = [
    'GriffithCrack']
