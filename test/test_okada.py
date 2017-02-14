import unittest
import numpy as num
from pyrocko import okada_ext
from common import Benchmark

benchmark = Benchmark()


class TestOkada(unittest.TestCase):

    def test_okada(self):
        nstations = 800**2
        nmodels = 1  # noqa

        stations = num.zeros((nstations, 2))
        stations[:, 0] = (num.random.rand(nstations)-.5) * 20 * 2
        stations[:, 1] = (num.random.rand(nstations)-.5) * 20 * 2

        models = num.zeros((nmodels, 10))
        models[:, 0] = 5.  # length
        models[:, 1] = 2.  # width
        models[:, 2] = 5.  # depth
        models[:, 3] = 0.  # Dip
        models[:, 4] = 40.  # Strike
        models[:, 5] = (num.random.rand(nmodels) - .5) * 10  # X
        models[:, 6] = (num.random.rand(nmodels) - .5) * 10  # Y
        models[:, 7] = 0.  # SS Strike-Slip
        models[:, 8] = 1.  # DS Dip-Slip
        models[:, 9] = 0.  # TS Tensional-Slip

        nu = 1.2512

        @benchmark
        def run_okada(nthreads):
            return okada_ext.disloc(models, stations, nu, nthreads)

        r = run_okada(12)

        # self.plot_disloc(stations, r)

    def tearDown(self):
        print benchmark

    @staticmethod
    def plot_disloc(stations, result):
        import matplotlib.pyplot as plt
        fig = plt.figure()
        ax = fig.gca()
        ax.tricontourf(stations[:, 0], stations[:, 1], result[:, 2])
        plt.show()


if __name__ == '__main__':
    unittest.main()
