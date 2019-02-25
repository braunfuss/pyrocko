from __future__ import division, print_function, absolute_import
import numpy as num
import unittest

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from pyrocko import util
from pyrocko.modelling import okada_ext, OkadaSource, DislocProcessor


d2r = num.pi / 180.


class OkadaTestCase(unittest.TestCase):

    def test_okada(self):
        n = 10

        strike = 100.
        dip = 50.
        al1 = 0.
        al2 = 0.5
        aw1 = 0.
        aw2 = 0.25
        poisson = 0.25

        source_coords = num.random.random_sample((n, 3)) * 0.5
        coords_r = coords_s
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
        disl_s = num.random.random_sample((n, 3))

        results = okada_ext.okada(
            source_coords, orient_s, disl_s, coords_r, patch_geom, poisson)

        assert results.shape == tuple((n, 12)) 
        # print(results)


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
        slip = 0.2
        opening = 0.3

        al1 = length
        al2 = 0.
        aw1 = width
        aw2 = 0.
        poisson = 0.25

        npoints = nlength * nwidth
        coords_s = num.zeros((npoints, 3))

        for il in range(nlength):
            for iw in range(nwidth):
                idx = il * nwidth + iw
                coords_s[idx, 0] = \
                    num.cos(strike * d2r) * (il * (al1 + al2) + al1) - \
                    num.sin(strike * d2r) * num.cos(dip * d2r) * \
                    (iw * (aw1 + aw2) + aw1)
                coords_s[idx, 1] = \
                    num.sin(strike * d2r) * (il * (al1 + al2) + al1) - \
                    num.cos(strike * d2r) * num.cos(dip * d2r) * \
                    (iw * (aw1 + aw2) + aw1)
                coords_s[idx, 2] = \
                    ref_depth + num.sin(dip * d2r) * iw * (aw1 + aw2) + aw1

        coords_r = num.concatenate((
            coords_s[:, :2], num.zeros((npoints, 1))), axis=1)

        # fig = plt.figure()
        # ax = fig.add_subplot(111, projection='3d')
        # ax.scatter(
        #     coords_r[:, 1], coords_r[:, 0], zs=-coords_r[:, 2], zdir='z', s=20,
        #     c='blue')
        # ax.scatter(
        #     coords_s[:, 1], coords_s[:, 0], zs=-coords_s[:, 2], zdir='z', s=20,
        #     c='red')
        # plt.axis('equal')
        # plt.show()

        orient = num.zeros((npoints, 2))
        orient[:, 0] = strike
        orient[:, 1] = dip
        patch_geom = num.array([al1, al2, aw1, aw2])[num.newaxis, :]

        disl = num.zeros((npoints, 3))
        disl[:, 0] = -num.cos(rake * d2r) * slip
        disl[:, 1] = -num.sin(rake * d2r) * slip
        disl[:, 2] = opening

        res_ok3d = okada_ext.okada(
            coords_s, orient, disl, coords_r, patch_geom, poisson)

        segments = [OkadaSource(
            lat=ref_lat, lon=ref_lon,
            north_shift=coords_s[i, 0], east_shift=coords_s[i, 1],
            depth=coords_s[i, 2], length=length, width=width, slip=slip,
            strike=strike, dip=dip, rake=rake, nu=poisson)
            for i in range(coords_s.shape[0])]

        res_ok2d = DislocProcessor.process(
            segments, num.array(coords_r[:, ::-1][:, 1:]))

        fig = plt.figure()
        ax1 = fig.add_subplot(311, projection='3d')
        scat = ax1.scatter(
            coords_r[:, 1], coords_r[:, 0], zs=0, zdir='z', s=20,
            c=res_ok2d['displacement.e'] - res_ok3d[:, 0])
        fig.colorbar(scat, shrink=0.5, aspect=5)
        ax2 = fig.add_subplot(312, projection='3d')
        scat = ax2.scatter(
            coords_r[:, 1], coords_r[:, 0], zs=0, zdir='z', s=20,
            c=res_ok2d['displacement.e'])
        fig.colorbar(scat, shrink=0.5, aspect=5)
        ax3 = fig.add_subplot(313, projection='3d')
        scat = ax3.scatter(
            coords_r[:, 1], coords_r[:, 0], zs=0, zdir='z', s=20,
            c=res_ok3d[:, 0])
        fig.colorbar(scat, shrink=0.5, aspect=5)
        plt.show()


if __name__ == '__main__':
    util.setup_logging('test_okada', 'warning')
    unittest.main()
