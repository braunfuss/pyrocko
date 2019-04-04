# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------
import numpy as num
import logging

from pyrocko import moment_tensor as mt
from pyrocko.guts import Bool, Float, String, Timestamp
from pyrocko.gf import Source
from pyrocko.model import Location
from pyrocko.modelling import disloc_ext, okada_ext

guts_prefix = 'modelling'

logger = logging.getLogger('pyrocko.modelling.okada')

d2r = num.pi / 180.
r2d = 180. / num.pi
km = 1.0e3


class Cloneable(object):

    def __iter__(self):
        return iter(self.T.propnames)

    def __getitem__(self, k):
        if k not in self.keys():
            raise KeyError(k)

        return getattr(self, k)

    def __setitem__(self, k, v):
        if k not in self.keys():
            raise KeyError(k)

        return setattr(self, k, v)

    def clone(self, **kwargs):
        '''
        Make a copy of the object.

        A new object of the same class is created and initialized with the
        parameters of the object on which this method is called on. If
        ``kwargs`` are given, these are used to override any of the
        initialization parameters.
        '''

        d = dict(self)
        for k in d:
            v = d[k]
            if isinstance(v, Cloneable):
                d[k] = v.clone()

        d.update(kwargs)
        return self.__class__(**d)

    @classmethod
    def keys(cls):
        '''
        Get list of the source model's parameter names.
        '''

        return cls.T.propnames


class AnalyticalSource(Location, Cloneable):
    name = String.T(
        optional=True,
        default='')

    time = Timestamp.T(
        default=0.,
        help='source origin time',
        optional=True)

    def __init__(self, **kwargs):
        Location.__init__(self, **kwargs)

    @property
    def northing(self):
        return self.north_shift

    @property
    def easting(self):
        return self.east_shift

    update = Source.update


class AnalyticalRectangularSource(AnalyticalSource):
    '''
    Rectangular analytical source model
    '''

    strike = Float.T(
        default=0.0,
        help='strike direction in [deg], measured clockwise from north')

    dip = Float.T(
        default=90.0,
        help='dip angle in [deg], measured downward from horizontal')

    rake = Float.T(
        default=0.0,
        help='rake angle in [deg], '
             'measured counter-clockwise from right-horizontal '
             'in on-plane view')

    al1 = Float.T(
        default=0.,
        help='Distance "left" side to source point [m]')

    al2 = Float.T(
        default=0.,
        help='Distance "right" side to source point [m]')

    aw1 = Float.T(
        default=0.,
        help='Distance "lower" side to source point [m]')

    aw2 = Float.T(
        default=0.,
        help='Distance "upper" side to source point [m]')

    slip = Float.T(
        default=0.,
        help='Slip on the rectangular source area [m]',
        optional=True)

    @property
    def length(self):
        return num.abs(self.al1) + num.abs(self.al2)

    @property
    def width(self):
        return num.abs(self.aw1) + num.abs(self.aw2)


class OkadaSource(AnalyticalRectangularSource):
    '''
    Rectangular Okada source model
    '''

    opening = Float.T(
        default=0.,
        help='Opening of the plane in [m]',
        optional=True)

    poisson = Float.T(
        default=0.25,
        help='Poisson\'s ratio, typically 0.25',
        optional=True)

    shearmod = Float.T(
        default=32e9,
        help='Shear modulus along the plane [Pa]',
        optional=True)

    @property
    def lamb(self):
        '''
        Calculation of first Lame's parameter

        According to Mueller (2007), the first Lame parameter lambda can be
        determined from the formulation for the poisson ration nu:
        nu = lambda / (2 * (lambda + mu))
        with the shear modulus mu
        '''

        return (2 * self.poisson * self.shearmod) / (1 - 2 * self.poisson)

    @property
    def seismic_moment(self):
        '''
        Scalar Seismic moment

        Code copied from Kite
        Disregarding the opening (as for now)
        We assume a shear modulus of :math:`\mu = 36 \mathrm{GPa}`
        and :math:`M_0 = \mu A D`

        .. important ::

            We assume a perfect elastic solid with :math:`K=\\frac{5}{3}\\mu`

            Through :math:`\\mu = \\frac{3K(1-2\\nu)}{2(1+\\nu)}` this leads to
            :math:`\\mu = \\frac{8(1+\\nu)}{1-2\\nu}`

        :return: Seismic moment release
        :rtype: float
        '''

        if self.poisson and not self.shearmod:
            self.shearmod = (8. * (1 + self.poisson)) / (1 - 2. * self.poisson)
            mu = self.shearmod
        else:
            mu = 32e9  # GPa

        A = self.length * self.width
        return mu * A * self.slip

    @property
    def moment_magnitude(self):
        '''
        Moment magnitude from Seismic moment

        Copied from Kite. Returns the moment magnitude
        We assume :math:`M_\\mathrm{w} = {\\frac{2}{3}}\\log_{10}(M_0) - 10.7`

        :returns: Moment magnitude
        :rtype: float
        '''

        return 2. / 3 * num.log10(self.seismic_moment * 1e7) - 10.7

    def disloc_source(self, dsrc=None):
        '''
        Build array for disloc_ext input

        :param dsrc: optional, :py:class:`numpy.ndarray`
        :type dsrc: array containing source information, which will be
        overwritten

        :return: array of the source data as input for disloc_ext
        :rtype: py:class:`numpy.ndarray`, ``(1, 10)``
        '''

        if dsrc is None or dsrc.shape != tuple(9, ):
            dsrc = num.empty(10)

        dip = self.dip
        if self.dip == 90.:
            dip -= 1e-2

        dsrc[0] = self.length
        dsrc[1] = self.width
        dsrc[2] = self.depth
        dsrc[3] = -dip
        dsrc[4] = self.strike - 180.
        dsrc[5] = self.easting
        dsrc[6] = self.northing

        ss_slip = num.cos(self.rake * d2r) * self.slip
        ds_slip = num.sin(self.rake * d2r) * self.slip
        dsrc[7] = -ss_slip  # SS Strike-Slip
        dsrc[8] = -ds_slip  # DS Dip-Slip
        dsrc[9] = self.opening  # TS Tensional-Slip

        return dsrc

    def source_patch(self):
        '''
        Build source information array for okada_ext.okada input

        :return: array of the source data as input for okada_ext.okada
        :rtype: py:class:`numpy.ndarray`, ``(1, 9)``
        '''

        source_patch = num.empty(9)

        source_patch[0] = self.northing
        source_patch[1] = self.easting
        source_patch[2] = self.depth
        source_patch[3] = self.strike
        source_patch[4] = self.dip
        source_patch[5] = self.al1
        source_patch[6] = self.al2
        source_patch[7] = self.aw1
        source_patch[8] = self.aw2

        return source_patch

    def source_disloc(self):
        '''
        Build source dislocation for okada_ext.okada input

        :return: array of the source dislocation data as input for
        okada_ext.okada
        :rtype: py:class:`numpy.ndarray`, ``(1, 3)``
        '''

        source_disl = num.empty(3)

        source_disl[0] = num.cos(self.rake * d2r) * self.slip
        source_disl[1] = num.sin(self.rake * d2r) * self.slip
        source_disl[2] = self.opening

        return source_disl

    def get_parameters_array(self):
        return num.array([self.__getattribute__(p) for p in self.parameters])

    def set_parameters_array(self, parameter_arr):
        if parameter_arr.size != len(self.parameters):
            raise AttributeError('Invalid number of parameters, %s has %d'
                                 ' parameters'
                                 % self.__name__, len(self.parameters))
        for ip, param in enumerate(self.parameters):
            self.__setattr__(param, parameter_arr[ip])

    def discretize(self, nlength, nwidth):
        '''
        Discretize the given fault by nlength * nwidth fault patches

        Discretizing the fault into several sub faults. Nlength is number of
        points in strike direction, nwidth in down dip direction along the
        fault. Fault orientation, slip and elastic parameters are kept.

        :param nlength: Number of discrete points in faults strike direction
        :type nlength: int
        :param nwidth: Number of discrete points in faults down-dip direction
        :type nwidth: int

        :return: Discrete fault patches
        :rtype: list of :py:class:`pyrocko.modelling.OkadaSource` objects
        '''

        il = num.repeat(num.arange(0, nlength, 1), nwidth)
        iw = num.tile(num.arange(0, nwidth, 1), (1, nlength))

        patch_length = self.length / nlength
        patch_width = self.width / nwidth
        al1 = -patch_length / 2.
        al2 = patch_length / 2.
        aw1 = -patch_width / 2.
        aw2 = patch_width / 2.

        source_points = num.zeros((nlength * nwidth, 3))
        source_points[:, 0] = (
            il - 1) * patch_length + num.abs(al1)
        source_points[:, 1] = (
            iw - 1) * patch_width + num.abs(aw1)

        source_points[:, 0] += self.al1
        source_points[:, 1] -= self.aw2

        rotmat = num.asarray(
            mt.euler_to_matrix(self.dip * d2r, self.strike * d2r, 0.0))

        source_points_rot = num.dot(rotmat.T, source_points.T).T
        source_points_rot[:, 0] += self.northing
        source_points_rot[:, 1] += self.easting
        source_points_rot[:, 2] += self.depth

        kwargs = {
            prop: getattr(self, prop) for prop in self.T.propnames
            if prop not in [
                'north_shift', 'east_shift', 'depth',
                'al1', 'al2', 'aw1', 'aw2']}

        return [OkadaSource(
            north_shift=coord[0], east_shift=coord[1],
            depth=coord[2], al1=al1, al2=al2, aw1=aw1, aw2=aw2,
            **kwargs)
            for coord in source_points_rot]

    @property
    def segments(self):
        yield self


class OkadaSegment(OkadaSource):
    enabled = Bool.T(
        default=True,
        optional=True)


class DislocationInverter(object):
    '''
    Toolbox for Boundary Element Method (BEM) and dislocation inversion based
    on okada_ext.okada
    '''

    @staticmethod
    def get_coef_mat(source_patches_list, pure_shear=False):
        '''
        Build coefficient matrix for given source_patches

        The BEM for a fault and the determination of the slip distribution from
        the stress drop is based on the relation stress = coef_mat * displ.
        Here the coefficient matrix is build and filled based on the
        okada_ext.okada displacements and partial displacement
        differentiations.

        :param source_patches_list: list of all OkadaSources, which shall be
            used for BEM
        :type source_patches_list: list of
            py:class:`pyrocko.modelling.OkadaSource`
        :param pure_shear: Flag, if also opening mode shall be taken into
            account (False) or the fault is described as pure shear (True).
        :type pure_shear: optional, Bool

        :return: coefficient matrix for all sources
        :rtype: :py:class:`numpy.ndarray`,
            ``(source_patches_list.shape[0] * 3,
            source_patches.shape[] * 3(2))``
        '''

        source_patches = num.array([
            src.source_patch() for src in source_patches_list])
        receiver_coords = source_patches[:, :3].copy()

        npoints = len(source_patches_list)

        if pure_shear:
            n_eq = 2
        else:
            n_eq = 3

        coefmat = num.zeros((npoints * n_eq, npoints * n_eq))

        def get_normal(strike, dip):
            return num.array([
                -num.sin(strike * d2r) * num.sin(dip * d2r),
                num.cos(strike * d2r) * num.sin(dip * d2r),
                -num.cos(dip * d2r)])

        unit_disl = 1.
        disl_cases = {
            'strikeslip': {
                'slip': unit_disl,
                'opening': 0.,
                'rake': 0.},
            'dipslip': {
                'slip': unit_disl,
                'opening': 0.,
                'rake': 90.},
            'tensileslip': {
                'slip': 0.,
                'opening': unit_disl,
                'rake': 0.}
        }

        for idisl, case_type in enumerate([
                'strikeslip', 'dipslip', 'tensileslip'][:n_eq]):
            case = disl_cases[case_type]
            source_disl = num.array([
                case['slip'] * num.cos(case['rake'] * d2r),
                case['slip'] * num.sin(case['rake'] * d2r),
                case['opening']])

            for isource, source in enumerate(source_patches):
                results = okada_ext.okada(
                    source[num.newaxis, :].copy(),
                    source_disl[num.newaxis, :].copy(),
                    receiver_coords,
                    source_patches_list[isource].lamb,
                    source_patches_list[isource].shearmod,
                    0)

                eps = \
                    0.5 * (
                        results[:, 3:] +
                        results[:, [3, 6, 9, 4, 7, 10, 5, 8, 11]])

                diag_ind = [0, 4, 8]
                dilatation = num.sum(eps[:, diag_ind], axis=1)[:, num.newaxis]
                lamb = source_patches_list[isource].lamb
                mu = source_patches_list[isource].shearmod
                kron = num.zeros_like(eps)
                kron[:, diag_ind] = 1.

                stress = kron * lamb * dilatation + 2. * mu * eps

                normal = num.tile(get_normal(
                    source_patches_list[isource].strike,
                    source_patches_list[isource].dip), (stress.shape[0], 1))

                coefmat[::n_eq, isource * n_eq + idisl] = \
                    num.sum(stress[:, :3] * normal, axis=1) / unit_disl
                coefmat[1::n_eq, isource * n_eq + idisl] = \
                    num.sum(stress[:, 3:6] * normal, axis=1) / unit_disl
                if n_eq == 3:
                    coefmat[2::n_eq, isource * n_eq + idisl] = \
                        num.sum(stress[:, 6:] * normal, axis=1) / unit_disl

        return coefmat

    @staticmethod
    def get_coef_mat_slow(source_patches_list, pure_shear=False):
        '''
        Build coefficient matrix for given source_patches (Slow version)

        The BEM for a fault and the determination of the slip distribution from
        the stress drop is based on the relation stress = coef_mat * displ.
        Here the coefficient matrix is build and filled based on the
        okada_ext.okada displacements and partial displacement
        differentiations.

        :param source_patches_list: list of all OkadaSources, which shall be
            used for BEM
        :type source_patches_list: list of
            py:class:`pyrocko.modelling.OkadaSource`
        :param pure_shear: Flag, if also opening mode shall be taken into
            account (False) or the fault is described as pure shear (True).
        :type pure_shear: optional, Bool

        :return: coefficient matrix for all sources
        :rtype: :py:class:`numpy.ndarray`,
            ``(source_patches_list.shape[0] * 3,
            source_patches.shape[] * 3(2))``
        '''

        source_patches = num.array([
            src.source_patch() for src in source_patches_list])
        receiver_coords = source_patches[:, :3].copy()

        npoints = len(source_patches_list)

        if pure_shear:
            n_eq = 2
        else:
            n_eq = 3

        coefmat = num.zeros((npoints * n_eq, npoints * n_eq))

        def get_normal(strike, dip):
            return num.array([
                -num.sin(strike * d2r) * num.sin(dip * d2r),
                num.cos(strike * d2r) * num.sin(dip * d2r),
                -num.cos(dip * d2r)])

        unit_disl = 1.
        disl_cases = {
            'strikeslip': {
                'slip': unit_disl,
                'opening': 0.,
                'rake': 0.},
            'dipslip': {
                'slip': unit_disl,
                'opening': 0.,
                'rake': 90.},
            'tensileslip': {
                'slip': 0.,
                'opening': unit_disl,
                'rake': 0.}
        }

        for idisl, case_type in enumerate([
                'strikeslip', 'dipslip', 'tensileslip'][:n_eq]):
            case = disl_cases[case_type]
            source_disl = num.array([
                case['slip'] * num.cos(case['rake'] * d2r),
                case['slip'] * num.sin(case['rake'] * d2r),
                case['opening']])

            for isource, source in enumerate(source_patches):
                results = okada_ext.okada(
                    source[num.newaxis, :],
                    source_disl[num.newaxis, :],
                    receiver_coords,
                    source_patches_list[isource].lamb,
                    source_patches_list[isource].mu,
                    0)

                for irec in range(receiver_coords.shape[0]):
                    eps = num.zeros((3, 3))
                    for m in range(3):
                        for n in range(3):
                            eps[m, n] = 0.5 * (
                                results[irec][m * 3 + n + 3] +
                                results[irec][n * 3 + m + 3])

                    stress_tens = num.zeros((3, 3))
                    dilatation = num.sum([eps[i, i] for i in range(3)])

                    for m, n in zip([0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 2, 2]):
                        if m == n:
                            stress_tens[m, n] = \
                                source_patches_list[isource].lamb * \
                                dilatation + \
                                2. * source_patches_list[isource].shearmod * \
                                eps[m, n]

                        else:
                            stress_tens[m, n] = \
                                2. * source_patches_list[isource].shearmod * \
                                eps[m, n]
                            stress_tens[n, m] = stress_tens[m, n]

                    normal = get_normal(
                        source_patches_list[isource].strike,
                        source_patches_list[isource].dip)

                    for isig in range(n_eq):
                        tension = num.sum(stress_tens[isig, :] * normal)
                        coefmat[irec * n_eq + isig, isource * n_eq + idisl] = \
                            tension / unit_disl

        return coefmat

    @staticmethod
    def get_disloc_lsq(
            stress_field, coef_mat=None, source_list=None, **kwargs):
        '''
        Least square inversion to get displacement from stress

        Follows approach for Least-Square Inversion published in Menke (1989)
        to calculate displacements on a fault with several segments from a
        given stress field. If not done, the coefficient matrix is determined
        within the code.

        :param stress_field: Array containing the stress change [Pa] for each
            source patch (order: [
            src1 dstress_Strike, src1 dstress_Dip, src1 dstress_Tensile,
            src2 dstress_Strike, ...])
        :type stress_field: :py:class:`numpy.ndarray`, ``(n_sources * 3, )``
        :param coef_mat: Coefficient matrix to connect source patches
            displacement and the resulting stress field
        :type coef_mat: optional, :py:class:`numpy.ndarray`,
            ``(source_patches_list.shape[0] * 3,
            source_patches.shape[] * 3(2)``
        :param source_list: list of all OkadaSources, which shall be
            used for BEM
        :type source_list: optional, list of
            py:class:`pyrocko.modelling.OkadaSource`

        :return: inverted displacements (u_strike, u_dip , u_tensile) for each
            source patch. order: [
            patch1 u_Strike, patch1 u_Dip, patch1 u_Tensile,
            patch2 u_Strike, ...]
        :rtype: :py:class:`numpy.ndarray`, ``(n_sources * 3, 1)``
        '''

        if source_list and not coef_mat:
            coef_mat = DislocationInverter.get_coef_mat(
                source_list, **kwargs)

        if not (coef_mat is None):
            if stress_field.shape[0] == coef_mat.shape[0]:
                return num.linalg.multi_dot([num.linalg.inv(
                    num.dot(coef_mat.T, coef_mat)), coef_mat.T, stress_field])


class ProcessorProfile(dict):
    pass


class AnalyticalSourceProcessor(object):
    pass


class DislocProcessor(AnalyticalSourceProcessor):

    @staticmethod
    def process(sources, coords, nthreads=0):
        result = {
            'processor_profile': dict(),
            'displacement.n': num.zeros((coords.shape[0])),
            'displacement.e': num.zeros((coords.shape[0])),
            'displacement.d': num.zeros((coords.shape[0])),
        }

        src_nu = set(src.poisson for src in sources)

        for nu in src_nu:
            src_arr = num.vstack([src.disloc_source() for src in sources
                                  if src.poisson == nu])
            res = disloc_ext.disloc(src_arr, coords, nu, nthreads)
            result['displacement.e'] += res[:, 0]
            result['displacement.n'] += res[:, 1]
            result['displacement.d'] += -res[:, 2]

        return result


__all__ = [
    'AnalyticalSourceProcessor',
    'DislocProcessor',
    'AnalyticalSource',
    'AnalyticalRectangularSource',
    'OkadaSource',
    'DislocationInverter']
