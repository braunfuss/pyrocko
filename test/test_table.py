from __future__ import division, print_function, absolute_import
import numpy as num
import unittest

from pyrocko import table, util


class TableTestCase(unittest.TestCase):

    def test_table(self):

        t = table.Table()

        npoints = 10
        coords = num.random.random(size=(npoints, 3))
        times = num.random.random(size=npoints)

        t.add_cols([
            table.Header(name='coords', sub_headers=[
                table.SubHeader(name=name) for name in ['x', 'y', 'z']]),
            table.Header(name='t')],
            [coords, times])

        t.add_rows([coords, times])

        print(t)
        for c, i in [('x', 0), ('y', 1), ('z', 2)]:
            assert num.all(t.get_col('coords')[:, i] == t.get_col(c))


if __name__ == '__main__':
    util.setup_logging('test_table', 'warning')
    unittest.main()
