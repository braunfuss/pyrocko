import math
import numpy as num
from pyrocko.guts import Object, String, Unicode, List, Int, SObject, Any, \
    Defer
from pyrocko import orthodrome as od
from pyrocko.util import num_full

guts_prefix = 'pf'


def nextpow2(i):
    return 2**int(math.ceil(math.log(i)/math.log(2.)))


def ncols(arr):
    return 1 if arr.ndim == 1 else arr.shape[1]


def nrows(arr):
    return arr.shape[0]


def resize_shape(shape, n):
    return (n, ) if len(shape) == 1 else (n, shape[1])


class DType(SObject):
    dummy_for = num.dtype


class SubHeader(Object):
    name = String.T()
    label = Unicode.T(optional=True)
    unit = Unicode.T(optional=True)
    dtype = DType.T(default=num.dtype('float64'), optional=True)
    default = Any.T(default=0.0)  # default_value


class Header(SubHeader):
    sub_headers = List.T(SubHeader.T())

    def get_ncols(self):
        return max(1, len(self.sub_headers))

    def default_array(self, nrows):
        val = self.dtype(self.default)
        if not self.sub_headers:
            return num_full((nrows,), val, dtype=self.dtype)
        else:
            return num_full((nrows, self.get_ncols()), val, dtype=self.dtype)


class Description(Object):
    name = String.T(optional=True)
    headers = List.T(Header.T())
    nrows = Int.T()
    ncols = Int.T()

    def __init__(self, table):
        Object.__init__(
            self,
            name=table._name,
            headers=table._headers,
            nrows=table.get_nrows(),
            ncols=table.get_ncols())


class Table(object):

    def __init__(self, name=None, nrows_capacity=None, nrows_capacity_min=0):
        self._name = name
        self._buffers = []
        self._arrays = []
        self._headers = []
        self._cols = {}
        self.recipes = []
        self.nrows_capacity_min = nrows_capacity_min
        self._nrows_capacity = 0
        if nrows_capacity is not None:
            self.set_nrows_capacity(max(nrows_capacity, nrows_capacity_min))

    def add_recipe(self, recipe):
        self.recipes.append(recipe)
        recipe._add_required_cols(self)

    def get_nrows(self):
        if not self._arrays:
            return 0
        else:
            return nrows(self._arrays[0])

    def get_nrows_capacity(self):
        return self._nrows_capacity

    def set_nrows_capacity(self, nrows_capacity_new):
        if self.get_nrows_capacity() != nrows_capacity_new:
            if self.get_nrows() > nrows_capacity_new:
                raise ValueError('new capacity too small to hold current data')

            new_buffers = []
            for buf in self._buffers:
                shape = resize_shape(buf.shape, nrows_capacity_new)
                new_buffers.append(num.zeros(shape, dtype=buf.dtype))

            ncopy = min(self.get_nrows(), nrows_capacity_new)

            new_arrays = []
            for arr, buf in zip(self._arrays, new_buffers):
                buf[:ncopy, ...] = arr[:ncopy, ...]
                new_arrays.append(buf[:ncopy, ...])

            self._buffers = new_buffers
            self._arrays = new_arrays
            self._nrows_capacity = nrows_capacity_new

    def get_ncols(self):
        return len(self._arrays)

    def add_col(self, header, array=None):
        nrows_current = self.get_nrows()
        if array is None:
            array = header.default_array(nrows_current)

        array = num.asarray(array)
        print(header.get_ncols(), ncols(array))

        assert header.get_ncols() == ncols(array)
        assert array.ndim in (1, 2)
        if self._arrays:
            assert nrows(array) == nrows_current

        if nrows_current == 0:
            nrows_current = nrows(array)
            self.set_nrows_capacity(
                max(nrows_current, self.nrows_capacity_min))

        iarr = len(self._arrays)

        shape = resize_shape(array.shape, self.get_nrows_capacity())
        if shape != array.shape:
            buf = num.zeros(shape, dtype=array.dtype)
            buf[:nrows_current, ...] = array[:, ...]
        else:
            buf = array

        self._buffers.append(buf)
        self._arrays.append(buf[:nrows_current, ...])
        self._headers.append(header)

        self._cols[header.name] = iarr, None

        for icol, sub_header in enumerate(header.sub_headers):
            self._cols[sub_header.name] = iarr, icol

    def add_cols(self, headers, arrays=None):
        if arrays is None:
            arrays = [None] * len(headers)

        for header, array in zip(headers, arrays):
            self.add_col(header, array)

    def add_rows(self, arrays):
        assert self.get_ncols() == len(arrays)

        nrows_add = nrows(arrays[0])
        nrows_current = self.get_nrows()
        nrows_new = nrows_current + nrows_add
        if self.get_nrows_capacity() < nrows_new:
            self.set_nrows_capacity(max(
                self.nrows_capacity_min, nextpow2(nrows_new)))

        new_arrays = []
        for buf, arr in zip(self._buffers, arrays):
            assert ncols(arr) == ncols(buf)
            assert nrows(arr) == nrows_add
            buf[nrows_current:nrows_new, ...] = arr[:, ...]
            new_arrays.append(buf[:nrows_new, ...])

        self._arrays = new_arrays

        for recipe in self.recipes:
            recipe._add_rows_handler(self, nrows_add)

    def get_col(self, name, mask=slice(None)):
        if name in self._cols:
            if isinstance(mask, str):
                mask = self.get_col(mask)

            iarr, icol = self._cols[name]
            if icol is None:
                return self._arrays[iarr][mask]
            else:
                return self._arrays[iarr][mask, icol]
        else:
            recipe = self.get_recipe_for_col(name)
            recipe._update_col(self, name)
            return recipe.get_table().get_col(name, mask)

    def has_col(self, name):
        return name in self._cols or \
            any(name in rec.get_col_names() for rec in self.recipes)

    def get_col_names(self):
        names = []
        for h in self._headers:
            names.append(h.name)
            for sh in h.sub_headers:
                names.append(sh.name)

        for recipe in self.recipies:
            names.extend(recipe.get_col_names())

        return names

    def get_recipe_for_col(self, name):
        for recipe in self.recipes:
            if recipe.has_col(name):
                return recipe

    def __str__(self):
        d = Description(self)
        d.validate()
        return str(Description(self))


class Recipe(object):

    def __init__(self):
        self._table = None
        self._table = Table()

        self._required_headers = []
        self._headers = []
        self._col_update_map = {}

    def get_col_names(self):
        return [h.name for h in self._headers]

    def get_table(self):
        return self._table

    def _add_required_cols(self, table):
        for h in self._headers:
            if not table.has_col(h.name):
                table.add_col(h)

    def _update_col(self, table, name):
        if not self._table.has_col(name):
            self._col_update_map[name](table)

    def _add_rows_handler(self, table, nrows_added):
        pass

    def _register_required_cols(self, headers):
        self._required_headers.extend(headers)

    def _register_computed_cols(self, headers, updater):
        self._headers.extend(headers)
        for h in headers:
            self._col_update_map[h.name] = updater


class LocationRecipe(Recipe):

    def __init__(self):
        Recipe.__init__(self)

        self._register_required_cols(
            headers=[
                Header(name='c5', sub_headers=[
                    Header(name='ref_lat', unit='degrees'),
                    Header(name='ref_lon', unit='degrees'),
                    Header(name='north_shift', unit='m'),
                    Header(name='east_shift', unit='m'),
                    Header(name='depth', unit='m')])])

        self._register_computed_cols(
            headers=[
                Header(name='latlon', sub_headers=[
                    Header(name='lat', unit='degrees'),
                    Header(name='lon', unit='degrees')])],
            updater=self._update_latlon)

    def _add_rows_handler(self, table, nrows_added):
        Recipe._add_rows_handler(self, table, nrows_added)
        if self._table.has_col_group('latlon'):
            self._table.remove_col('latlon')

    def _update_latlon(self, table):
        lats, lons = od.ne_to_latlon(
            table.get_col('ref_lat'),
            table.get_col('ref_lon'),
            table.get_col('north_shift'),
            table.get_col('east_shift'))

        latlons = num.zeros((lats.size, 2))
        latlons[:, 0] = lats
        latlons[:, 1] = lons

        self._table.add_cols(
            self.__headers,
            [latlons],
            self.__group_headers)


class EventRecipe(LocationRecipe):

    def __init__(self):
        LocationRecipe.__init__(self)

        self._register_required_cols(
            headers=[
                Header(name='time', unit='s'),
                Header(name='magnitude')])
