# http://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------
from __future__ import absolute_import

import zipfile
import os.path as op

# import re
# try:
#     from urllib2 import urlopen
# except ImportError:
#     from urllib.request import urlopen

import numpy as num

from pyrocko import util, config
from . import tile, dataset

citation = '''
Farr, T. G., and M. Kobrick, 2000, Shuttle Radar Topography Mission produces a
wealth of data. Eos Trans. AGU, 81:583-585.

Farr, T. G. et al., 2007, The Shuttle Radar Topography Mission, Rev. Geophys.,
45, RG2004, doi:10.1029/2005RG000183. (Also available online at
http://www2.jpl.nasa.gov/srtm/SRTM_paper.pdf)

Kobrick, M., 2006, On the toes of giants-How SRTM was born, Photogramm. Eng.
Remote Sens., 72:206-210.

Rosen, P. A. et al., 2000, Synthetic aperture radar interferometry, Proc. IEEE,
88:333-382.
'''


class AuthenticationRequired(Exception):
    pass


class SRTMGL3(dataset.TiledGlobalDataset):

    def __init__(
            self,
            name='SRTMGL3',
            data_dir=op.join(op.dirname(__file__), 'data', 'SRTMGL3'),
            raw_data_url='https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL3.003/'
                         '2000.02.11'):

        dataset.TiledGlobalDataset.__init__(
            self,
            name,
            432001, 216001, 1201, 1201,
            num.dtype('>i2'),
            data_dir=data_dir,
            citation=citation,
            region=(-180., 180., -60., 60.))

        self.raw_data_url = raw_data_url
        self._available_tilenames = None
        self.config = config.config()

    def tilename(self, itx, ity):
        itx -= 180
        ity -= 90
        if ity >= 0:
            s = 'N%02i' % ity
        else:
            s = 'S%02i' % -ity

        if itx >= 0:
            s += 'E%03i' % itx
        else:
            s += 'W%03i' % -itx

        return s

    def available_tilenames(self):
        if self._available_tilenames is None:
            fpath = op.join(self.data_dir, 'available.list')
            if op.exists(fpath):
                with open(fpath, 'r') as f:
                    available = [s.strip() for s in f.readlines()]

            else:
                util.ensuredirs(fpath)

                # remote structure changed, we would have to clawl through
                # many pages. Now keeping tile index here:
                self.download_file(
                    'https://data.pyrocko.org/scratch/available.list', fpath)

                # url = self.raw_data_url + '/'
                # f = urlopen(url)
                # data = f.read().decode()
                # available = re.findall(
                #     r'([NS]\d\d[EW]\d\d\d)\.SRTMGL3\.hgt', data)
                #
                # f.close()
                #
                # with open(fpath, 'w') as f:
                #     f.writelines('%s\n' % s for s in available)

            self._available_tilenames = set(available)

        return self._available_tilenames

    def tilefilename(self, tilename):
        return tilename + '.SRTMGL3.hgt.zip'

    def tilepath(self, tilename):
        fn = self.tilefilename(tilename)
        return op.join(self.data_dir, fn)

    def download_tile(self, tilename):
        import requests

        fpath = self.tilepath(tilename)
        fn = self.tilefilename(tilename)
        url = self.raw_data_url + '/' + fn
        if self.config.earthdata_credentials:
            cred = self.config.earthdata_credentials
        else:
            raise AuthenticationRequired(
                '\n\nRegister at https://urs.earthdata.nasa.gov/users/new'
                ' and provide credentials in your local ~/.pyrocko/config.pf'
                ' as follows:\n' +
                'earthdata_credentials: [username, password]')

        try:
            # we have to follow the oauth redirect here...
            r = requests.get(url, auth=cred)
            self.download_file(
                r.url, fpath, username=cred[0], password=cred[1])
        except Exception as e:
            if hasattr(e.response, 'status_code'):
                if e.response.status_code == 401:
                    raise AuthenticationRequired(
                        '\n\nWe could not login to earthdata given the'
                        ' credentials in ~/.pyrocko/config.pf!\n'
                        'Register at https://urs.earthdata.nasa.gov/users/new'
                        ' and provide credentials in your local '
                        ' ~/.pyrocko/config.pf as follows:\n' +
                        'earthdata_credentials: [username, password]')
                else:
                    raise e

    def download(self):
        for tn in self.available_tilenames():
            fpath = self.tilepath(tn)
            if not op.exists(fpath):
                self.download_tile(tn)

    def get_tile(self, itx, ity):
        tn = self.tilename(itx, ity)
        if tn not in self.available_tilenames():
            return None
        else:
            fpath = self.tilepath(tn)
            if not op.exists(fpath):
                self.download_tile(tn)

            zipf = zipfile.ZipFile(fpath, 'r')
            rawdata = zipf.read(tn + '.hgt')
            zipf.close()
            data = num.fromstring(rawdata, dtype=self.dtype)
            assert data.size == self.ntx * self.nty
            data = data.reshape(self.nty, self.ntx)[::-1, ::]
            return tile.Tile(
                self.xmin + itx*self.stx,
                self.ymin + ity*self.sty,
                self.dx, self.dx, data)


if __name__ == '__main__':
    import sys

    util.setup_logging('pyrocko.topo.srtmgl3', 'info')

    if len(sys.argv) != 2:
        sys.exit('usage: python -m pyrocko.topo.srtmgl3 download')

    if sys.argv[1] == 'download':
        srtmgl3 = SRTMGL3()
        srtmgl3.download()
