from __future__ import division, print_function, absolute_import
from builtins import range

import unittest
import logging
import os

import numpy as num
from pyrocko import gf, util
from pyrocko.modelling import DislocationInverter


logger = logging.getLogger('pyrocko.test.test_gf_source_types')

km = 1e3


show_plot = int(os.environ.get('MPL_SHOW', 0))


class GFSourceTypesTestCase(unittest.TestCase):

    def test_rectangular_source(self):
        # WIP
        nsrc = 5
        rect_sources = []

        for n in range(nsrc):
            src = gf.RectangularSource(
                lat=0., lon=0.,
                anchor='bottom',
                north_shift=5000., east_shift=9000., depth=4. * km,
                width=2. * km, length=8. * km,
                dip=0., rake=0., strike=(180. / nsrc + 1) * n,
                slip=1.)
            rect_sources.append(src)

    @staticmethod
    def plot_rectangular_source(src, store):
        from matplotlib import pyplot as plt
        from matplotlib.patches import Polygon
        ax = plt.gca()
        ne = src.outline(cs='xy')
        p = Polygon(num.fliplr(ne), fill=False, color='r', alpha=.7)
        ax.add_artist(p)

        mt = src.discretize_basesource(store)
        ax.scatter(mt.east_shifts, mt.north_shifts, alpha=1)
        ax.scatter(src.east_shift, src.north_shift, color='r')

        plt.axis('equal')
        plt.show()

    def test_stressdrop_source(self):
        store_id = 'crust2_dd'

        if not os.path.exists(store_id):
            gf.ws.download_gf_store(site='kinherd', store_id=store_id)

        engine = gf.LocalEngine(store_superdirs=['.'])
        store = engine.get_store(store_id)

        pdr = gf.PseudoDynamicRupture(
            length=20000., width=10000., depth=2000.,
            anchor='top', gamma=0.8, dip=90., strike=0.)

        points, _, vr, times = pdr.discretize_time(
            store,
            factor=2.,
            nucleation_x=0.,
            nucleation_y=0.)
        assert times.shape == vr.shape
        assert points.shape[0] == times.shape[0] * times.shape[1]

        _, source_disc, times_interp = pdr.discretize_okada(
            store=store,
            factor=10.,
            interpolation='nearest_neighbor',
            nucleation_x=0.,
            nucleation_y=0.)
        assert len(source_disc) == (
            times_interp.shape[0] * times_interp.shape[1])

        stress_field = num.zeros((len(source_disc) * 3, 1))
        stress_field[2::3] = -0.5e6

        time = num.max(times_interp) * 0.5

        disloc_est = pdr.get_okada_slip(
            stress_field=stress_field,
            times=times_interp,
            source_list=source_disc,
            t=time)

        coef_mat = DislocationInverter.get_coef_mat(source_disc)

        disloc_est2 = pdr.get_okada_slip(
            stress_field=stress_field,
            times=times_interp,
            coef_mat=coef_mat,
            t=time)
        assert (disloc_est2 == disloc_est).all()

        if show_plot:
            level = num.arange(0., 15., 1.5)

            import matplotlib.pyplot as plt
            x_val = points[:times.shape[1], 0]
            y_val = points[::times.shape[1], 2]

            plt.gcf().add_subplot(1, 1, 1, aspect=1.0)
            plt.imshow(
                vr,
                extent=[
                    num.min(x_val), num.max(x_val),
                    num.max(y_val), num.min(y_val)])
            plt.contourf(x_val, y_val, times, level, cmap='gray', alpha=0.7)
            plt.colorbar(label='Rupture Propagation Time [s]')
            plt.show()

            x_val = num.array([
                src.northing for src in source_disc])[:times_interp.shape[1]]
            y_val = num.array([
                src.depth for src in source_disc])[::times_interp.shape[1]]

            plt.gcf().add_subplot(1, 1, 1, aspect=1.0)
            im = plt.imshow(
                disloc_est[2::3].reshape(y_val.shape[0], x_val.shape[0]),
                extent=[
                    num.min(x_val), num.max(x_val),
                    num.max(y_val), num.min(y_val)])
            plt.contourf(
                x_val, y_val,
                times_interp,
                level,
                cmap='gray', alpha=0.5)
            plt.colorbar(im, label='Opening [m] after %.2f s' % time)
            plt.show()


if __name__ == '__main__':
    util.setup_logging('test_gf_source_types', 'warning')
    unittest.main(defaultTest='GFSourceTypesTestCase')
