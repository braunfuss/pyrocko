from __future__ import division, print_function, absolute_import
import os
import numpy as num
import unittest

from pyrocko import util
from pyrocko.modelling import okada_ext, OkadaSource, DislocProcessor


d2r = num.pi / 180.
m2km = 1000.


show_plot = int(os.environ.get('MPL_SHOW', 0))


class OkadaTestCase(unittest.TestCase):

    def test_okada(self):
        n = 10

        north = num.linspace(0., 5., n)
        east = num.linspace(-5., 0., n)
        down = num.linspace(15., 5., n)

        strike = 100.
        dip = 50.
        al1 = 0.
        al2 = 0.5
        aw1 = 0.
        aw2 = 0.25
        poisson = 0.25

        nthreads = 0

        source_patches = num.zeros((n, 9))
        source_patches[:, 0] = north
        source_patches[:, 1] = east
        source_patches[:, 2] = down
        source_patches[:, 3] = strike
        source_patches[:, 4] = dip
        source_patches[:, 5] = al1
        source_patches[:, 6] = al2
        source_patches[:, 7] = aw1
        source_patches[:, 8] = aw2
        source_disl = num.random.random_sample((n, 3))

        receiver_coords = source_patches[:, :3].copy()

        results = okada_ext.okada(
            source_patches, source_disl, receiver_coords, poisson, nthreads)

        assert results.shape == tuple((n, 12))

    def test_okada_vs_disloc_single_Source(self):
        north = 0.
        east = 0.
        depth = 10.
        length = 50. * m2km
        width = 10. * m2km

        strike = 0.
        dip = 0.01
        rake = 0.
        slip = 1.0
        opening = 0.
        poisson = 0.25

        nthreads = 0

        al1 = -length / 2.
        al2 = length / 2.
        aw1 = -width
        aw2 = 0.

        source_patch = num.zeros((1, 9))
        source_patch[0, 0] = north
        source_patch[0, 1] = east
        source_patch[0, 2] = depth
        source_patch[0, 3] = strike
        source_patch[0, 4] = dip
        source_patch[0, 5] = al1
        source_patch[0, 6] = al2
        source_patch[0, 7] = aw1
        source_patch[0, 8] = aw2

        source_disl = num.zeros((1, 3))
        source_disl[:, 0] = num.cos(rake * d2r) * slip
        source_disl[:, 1] = num.sin(rake * d2r) * slip
        source_disl[:, 2] = opening

        nrec_north = 100
        nrec_east = 200
        rec_north = num.linspace(
            -2. * length + north, 2. * length + north, nrec_north)
        rec_east = num.linspace(
            -2. * length + east, 2. * length + east, nrec_east)
        nrec = nrec_north * nrec_east
        receiver_coords = num.zeros((nrec, 3))
        receiver_coords[:, 0] = num.tile(rec_north, nrec_east)
        receiver_coords[:, 1] = num.repeat(rec_east, nrec_north)

        segments = [OkadaSource(
            lat=0., lon=0.,
            north_shift=north, east_shift=east,
            depth=depth, length=length, width=width,
            strike=strike, dip=dip,
            rake=rake, slip=slip, opening=opening, nu=poisson)]

        res_ok2d = DislocProcessor.process(
            segments, num.array(receiver_coords[:, ::-1][:, 1:]))

        res_ok3d = okada_ext.okada(
            source_patch, source_disl, receiver_coords, poisson, nthreads)

        def compare_plot(param1, param2):
            import matplotlib.pyplot as plt

            valmin = num.min([param1, param2])
            valmax = num.max([param1, param2])

            def add_subplot(
                fig, param, ntot, n, sharedaxis=None, title='',
                    vmin=None, vmax=None):

                ax = fig.add_subplot(
                    ntot, 1, n, sharex=sharedaxis, sharey=sharedaxis)
                scat = ax.scatter(
                    receiver_coords[:, 1], receiver_coords[:, 0], s=20,
                    c=param, vmin=vmin, vmax=vmax, cmap='seismic',
                    edgecolor='none')
                fig.colorbar(scat, shrink=0.5, aspect=5)
                rect = plt.Rectangle((
                    -num.sin(strike * d2r) * length / 2.,
                    -num.cos(strike * d2r) * length / 2.),
                    num.cos(dip * d2r) * width, length,
                    angle=-strike, edgecolor='green', facecolor='None')
                ax.add_patch(rect)
                ax.set_title(title)
                plt.axis('equal')
                return ax

            fig = plt.figure()
            ax = add_subplot(
                fig, param1 - param2, 3, 1,
                title='Okada Surface minus Okada Halfspace')
            add_subplot(
                fig, param1, 3, 2, sharedaxis=ax,
                title='Okada Surface', vmin=valmin, vmax=valmax)
            add_subplot(
                fig, param2, 3, 3, sharedaxis=ax,
                title='Okada Halfspace', vmin=valmin, vmax=valmax)

            plt.show()

        if show_plot:
            compare_plot(res_ok2d['displacement.d'], res_ok3d[:, 2])

    def test_okada_vs_disloc(self):
        ref_lat = 0.
        ref_lon = 0.
        ref_depth = 10.

        nlength = 10
        nwidth = 8

        strike = 0.
        dip = 50.
        rake = 45.
        length = 0.5
        width = 0.25
        slip = 1.0
        opening = 0.5

        al1 = -length / 2.
        al2 = length / 2.
        aw1 = -width
        aw2 = 0.
        poisson = 0.25

        nthreads = 0

        npoints = nlength * nwidth
        source_patches = num.zeros((npoints, 9))

        for il in range(nlength):
            for iw in range(nwidth):
                idx = il * nwidth + iw
                source_patches[idx, 0] = \
                    num.cos(strike * d2r) * (
                        il * (num.abs(al1) + num.abs(al2)) + num.abs(al1)) - \
                    num.sin(strike * d2r) * num.cos(dip * d2r) * \
                    (iw * (num.abs(aw1) + num.abs(aw2)) + num.abs(aw1))
                source_patches[idx, 1] = \
                    num.sin(strike * d2r) * (
                        il * (num.abs(al1) + num.abs(al2)) + num.abs(al1)) - \
                    num.cos(strike * d2r) * num.cos(dip * d2r) * \
                    (iw * (num.abs(aw1) + num.abs(aw2)) + num.abs(aw1))
                source_patches[idx, 2] = \
                    ref_depth + num.sin(dip * d2r) * iw * (
                        num.abs(aw1) + num.abs(aw2)) + num.abs(aw1)

        receiver_coords = num.concatenate((
            source_patches[:, :2], num.zeros((npoints, 1))), axis=1)

        source_patches[:, 3] = strike
        source_patches[:, 4] = dip
        source_patches[:, 5] = al1
        source_patches[:, 6] = al2
        source_patches[:, 7] = aw1
        source_patches[:, 8] = aw2

        source_disl = num.zeros((npoints, 3))
        source_disl[:, 0] = num.cos(rake * d2r) * slip
        source_disl[:, 1] = num.sin(rake * d2r) * slip
        source_disl[:, 2] = opening

        res_ok3d = okada_ext.okada(
            source_patches, source_disl, receiver_coords, poisson, nthreads)

        segments = [OkadaSource(
            lat=ref_lat, lon=ref_lon,
            north_shift=source_patches[i, 0], east_shift=source_patches[i, 1],
            depth=source_patches[i, 2], length=length, width=width,
            strike=source_patches[i, 3], dip=source_patches[i, 4],
            rake=rake, slip=slip, opening=opening, nu=poisson)
            for i in range(source_patches.shape[0])]

        res_ok2d = DislocProcessor.process(
            segments, num.array(receiver_coords[:, ::-1][:, 1:]))

        def compare_plot(param1, param2):
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d import Axes3D

            def add_subplot(fig, param, ntot, n):
                ax = fig.add_subplot(ntot, 1, n, projection='3d')
                scat = ax.scatter(
                    receiver_coords[:, 1], receiver_coords[:, 0], zs=0,
                    zdir='z', s=20,
                    c=param, edgecolor='None')
                fig.colorbar(scat, shrink=0.5, aspect=5)

            fig = plt.figure()
            add_subplot(fig, param1 - param2, 3, 1)
            add_subplot(fig, param1, 3, 2)
            add_subplot(fig, param2, 3, 3)

            plt.show()

        if show_plot:
            compare_plot(res_ok2d['displacement.d'], res_ok3d[:, 2])


if __name__ == '__main__':
    util.setup_logging('test_okada', 'warning')
    unittest.main()
