from __future__ import division, print_function, absolute_import
import numpy as num
import unittest

from pyrocko import util
from pyrocko.modelling import okada_ext


class OkadaTestCase(unittest.TestCase):

    def test_okada(self):
        strike = 100.
        dip = 50.
        al1 = 0.
        al2 = 0.5
        aw1 = 0.
        aw2 = 0.25
        poisson = 0.25

        coords_s = num.random.random_sample((3, 10)) * 100.
        coords_r = coords_s
        orient = num.zeros((2, 10))
        orient[0, :] = strike
        orient[1, :] = dip
        patch_geom = num.array([al1, al2, aw1, aw2])[:, num.newaxis]

        disl = num.random.random_sample((3, 10))

        results = okada_ext.okada(
            coords_s, orient, disl, coords_r, patch_geom, poisson)

        print(results)
        assert results.shape[0] == 12

if __name__ == '__main__':
    util.setup_logging('test_okada', 'warning')
    unittest.main()
