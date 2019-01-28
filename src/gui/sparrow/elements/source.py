# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------
from __future__ import absolute_import, print_function, division

import string

import numpy as num

import vtk

from pyrocko.guts import Bool, Float, Object, String

from pyrocko import cake, geometry, gf
from pyrocko.gui.qt_compat import qw, qc, fnpatch

from pyrocko.gui.vtk_util import\
    make_multi_polyline, ArrowPipe, PolygonPipe, ScatterPipe, vtk_set_input
from .. import state as vstate
from .. import common

from .base import Element, ElementState

guts_prefix = 'sparrow'


d2r = num.pi / 180.


map_anchor = {
    'center': (0.0, 0.0),
    'center_left': (-1.0, 0.0),
    'center_right': (1.0, 0.0),
    'top': (0.0, -1.0),
    'top_left': (-1.0, -1.0),
    'top_right': (1.0, -1.0),
    'bottom': (0.0, 1.0),
    'bottom_left': (-1.0, 1.0),
    'bottom_right': (1.0, 1.0)}


class SourceOutlinesPipe(object):
    def __init__(self, geometry, RGB, cs='latlondepth'):

        self.mapper = vtk.vtkDataSetMapper()
        self._polyline_grid = {}

        lines = []

        latlon = geometry.outline.vertices.get_col('latlon')
        depth = geometry.outline.vertices.get_col('depth')

        points = num.concatenate(
            (latlon, depth.reshape(len(depth), 1)),
            axis=1)
        points = num.concatenate((points, points[0].reshape(1, -1)), axis=0)

        lines.append(points)

        if cs == 'latlondepth':
            self._polyline_grid = make_multi_polyline(
                lines_latlondepth=lines)
        elif cs == 'latlon':
            self._polyline_grid = make_multi_polyline(
                lines_latlon=lines)

        vtk_set_input(self.mapper, self._polyline_grid)

        actor = vtk.vtkActor()
        actor.SetMapper(self.mapper)

        prop = actor.GetProperty()
        prop.SetDiffuseColor(RGB)
        prop.SetOpacity(1.)

        self.actor = actor


class ProxySource(ElementState):
    pass


for source_cls in [gf.RectangularSource]:

    cls_name = 'Proxy' + source_cls.__name__

    class proxy_source_cls(ProxySource):
        class_name = cls_name

        def __init__(self, **kwargs):
            ProxySource.__init__(self)
            for key, value in self._ranges.iteritems():
                setattr(self, key, value['ini'])

            if kwargs is not None:
                for it in kwargs.items():
                    setattr(self, it[0], it[1])

    proxy_source_cls.__name__ = cls_name
    vars()[cls_name] = proxy_source_cls

    for prop in source_cls.T.properties:
        proxy_source_cls.T.add_property(prop.name, prop)


ProxyRectangularSource._name = 'RectangularSource'

ProxyRectangularSource._ranges = {
    'lat': {'min': -90., 'max': 90., 'step': 1, 'ini': 0.},
    'lon': {'min': -180., 'max': 180., 'step': 1, 'ini': 0.},
    'depth': {'min': 0., 'max': 600000., 'step': 1000, 'ini': 10000.},
    'width': {'min': 0., 'max': 500000., 'step': 1000, 'ini': 10000.},
    'length': {'min': 0., 'max': 1000000., 'step': 1000, 'ini': 50000.},
    'strike': {'min': -180., 'max': 180., 'step': 1, 'ini': 0.},
    'dip': {'min': 0., 'max': 90., 'step': 1, 'ini': 45.},
    'rake': {'min': -180., 'max': 180., 'step': 1, 'ini': 0.},
    'nucleation_x':
        {'min': -100., 'max': 100., 'step': 1, 'ini': 0., 'fac': .01},
    'nucleation_y':
        {'min': -100., 'max': 100., 'step': 1, 'ini': 0., 'fac': .01},
    'slip': {'min': 0., 'max': 1000., 'step': 1, 'ini': 1., 'fac': .01}}


class ProxyConfig(Object):
    deltas = num.array([1000., 1000.])
    deltat = Float.T(default=0.5)
    rho = Float.T(default=2800)
    vs = Float.T(default=3600)

    def get_shear_moduli(self, *args, **kwargs):
        points = kwargs.get('points')
        return num.ones(len(points)) * num.power(self.vs, 2) * self.rho


class ProxyStore(Object):
    def __init__(self, **kwargs):
        config = ProxyConfig()
        if kwargs:
            config.deltas = kwargs.get('deltas', config.deltas)
            config.deltat = kwargs.get('deltat', config.deltat)
            config.rho = kwargs.get('rho', config.rho)
            config.vs = kwargs.get('vs', config.vs)

        self.config = config
        self.mode = String.T(default='r')
        self._f_data = None
        self._f_index = None


parameter_label = {
    'Time (s)': 'times'}


class SourceState(ElementState):
    visible = Bool.T(default=True)
    source_selection = ProxySource.T(default=ProxyRectangularSource())  # noqa
    deltat = Float.T(default=0.5)
    display_parameter = String.T(default='Time (s)')

    @classmethod
    def get_name(self):
        return 'Source'

    def create(self):
        element = SourceElement()
        element.bind_state(self)
        return element


class SourceElement(Element):

    def __init__(self):
        Element.__init__(self)
        self._parent = None
        self._pipe = []
        self._controls = None
        self._points = num.array([])

    def _state_bind_source(self, *args, **kwargs):
        vstate.state_bind(self, self._state.source_selection, *args, **kwargs)

    def _state_bind_store(self, *args, **kwargs):
        vstate.state_bind(self, self._state, *args, **kwargs)

    def bind_state(self, state):
        upd = self.update
        self._listeners.append(upd)
        state.add_listener(upd, 'source_selection')
        state.add_listener(upd, 'visible')
        state.add_listener(upd, 'deltat')
        state.add_listener(upd, 'display_parameter')
        self._state = state

    def unbind_state(self):
        self._listeners = []

    def get_name(self):
        return 'Source'

    def set_parent(self, parent):
        self._parent = parent
        self._parent.add_panel(
            self.get_name(), self._get_controls(), visible=True)
        self.update()

    def unset_parent(self):
        self.unbind_state()
        if self._parent:
            if self._pipe:
                for pipe in self._pipe:
                    self._parent.remove_actor(pipe.actor)
                self._pipe = []

            if self._controls:
                self._parent.remove_panel(self._controls)
                self._controls = None

            self._parent.update_view()
            self._parent = None

    def open_file_load_dialog(self):
        caption = 'Select one file to open'
        fns, _ = fnpatch(qw.QFileDialog.getOpenFileNames(
            self._parent, caption, options=common.qfiledialog_options))

        if fns:
            self.load_file(str(fns[0]))
        else:
            return

    def load_file(self, path):
        loaded_source = gf.load(filename=path)
        source = ProxyRectangularSource(
            **{prop: getattr(loaded_source, prop)
                for prop in loaded_source.T.propnames
                if getattr(loaded_source, prop)})

        self._parent.remove_panel(self._controls)
        self._controls = None
        self._state.source_selection = source
        self._parent.add_panel(
            self.get_name(), self._get_controls(), visible=True)

        self.update()

    def open_file_save_dialog(self, fn=None):
        caption = 'Choose a file name to write source'
        if not fn:
            fn, _ = fnpatch(qw.QFileDialog.getSaveFileName(
                self._parent, caption, options=common.qfiledialog_options))
        if fn:
            self.save_file(str(fn))

    def save_file(self, path):
        source = self._state.source_selection
        source2dump = gf.RectangularSource(
            **{prop: getattr(source, prop) for prop in source.T.propnames})

        if path.split('.')[-1].lower() in ['xml']:
            source2dump.dump_xml(filename=path)
        else:
            source2dump.dump(filename=path)

    def update_loc(self, *args):
        pstate = self._parent.state
        state = self._state

        source = state.source_selection
        source.lat = pstate.lat
        source.lon = pstate.lon

        self._state.source_selection.source = source

        self.update()

    def update_raster(self, fault_geometry, param):
        patches = fault_geometry.patches

        vertices = geometry.arr_vertices(
            patches.vertices.get_col('xyz'))

        values = patches.faces.get_col(parameter_label[param])
        faces = [list(face) for face in patches.faces.get_col('patch_faces')]
        faces = num.array(faces)

        self._pipe.append(
            PolygonPipe(
                vertices, faces,
                values=values, cluster=True, cbar_title=param))

        if isinstance(self._pipe[-1].actor, list):
            for actor in self._pipe[-1].actor:
                self._parent.add_actor(actor)
        else:
            self._parent.add_actor(self._pipe[-1].actor)

    def update_rake_arrow(self, fault):
        source = self._state.source_selection
        rake = source.rake * d2r
        slip_norm = source.slip / (
            source._ranges['slip']['max'] * source._ranges['slip']['fac'])

        nucl_x = source.nucleation_x
        nucl_y = source.nucleation_y

        endpoint = [None] * 2
        endpoint[0] = nucl_x + num.cos(rake) * slip_norm
        endpoint[1] = nucl_y + num.sin(-rake) * slip_norm

        points = geometry.latlondepth2xyz(
            fault.points_on_source(
                points_x=[nucl_x, endpoint[0]],
                points_y=[nucl_y, endpoint[1]],
                cs='latlondepth'),
            planetradius=cake.earthradius)
        vertices = geometry.arr_vertices(points)
        self._pipe.append(ArrowPipe(vertices[0], vertices[1]))
        self._parent.add_actor(self._pipe[-1].actor)

    def update(self, *args):
        state = self._state
        source = state.source_selection
        source_list = gf.source_classes

        store = ProxyStore(
            deltat=self._state.deltat)
        store.config.deltas = num.array(
            [(store.config.deltat * store.config.vs) + 1] * 2)

        if self._pipe:
            for pipe in self._pipe:
                try:
                    self._parent.remove_actor(pipe.actor)
                except Exception:
                    for actor in pipe.actor:
                        self._parent.remove_actor(actor)

            self._pipe = []

        if state.visible:
            for i, a in enumerate(source_list):
                if a.__name__ is source._name:
                    fault = a(
                        **{prop: source.__dict__[prop]
                            for prop in source.T.propnames})
                    fault_geometry = fault.geometry(store)

                    fault_geometry.refine_outline(0.1)
                    self._pipe.append(
                        SourceOutlinesPipe(
                            fault_geometry, (1., 1., 1.),
                            cs='latlondepth'))
                    self._parent.add_actor(self._pipe[-1].actor)

                    self._pipe.append(
                        SourceOutlinesPipe(
                            fault_geometry, (.6, .6, .6),
                            cs='latlon'))
                    self._parent.add_actor(self._pipe[-1].actor)

                    for point, color in zip((
                            (source.nucleation_x,
                             source.nucleation_y),
                            map_anchor[source.anchor]),
                            (num.array([[1., 0., 0.]]),
                             num.array([[0., 0., 1.]]))):

                        points = geometry.latlondepth2xyz(
                            fault.points_on_source(
                                points_x=[point[0]], points_y=[point[1]],
                                cs='latlondepth'),
                            planetradius=cake.earthradius)

                        vertices = geometry.arr_vertices(points)
                        self._pipe.append(ScatterPipe(vertices))
                        self._pipe[-1].set_colors(color)
                        self._parent.add_actor(self._pipe[-1].actor)

                    self.update_raster(fault_geometry, state.display_parameter)
                    self.update_rake_arrow(fault)

        self._parent.update_view()

    def _get_controls(self):
        if not self._controls:
            from ..state import \
                state_bind_checkbox, state_bind_slider, state_bind_combobox
            from pyrocko import gf
            source = self._state.source_selection

            frame = qw.QFrame()
            layout = qw.QGridLayout()
            frame.setLayout(layout)

            def state_to_lineedit(state, attribute, widget):
                sel = getattr(state, attribute)

                widget.setText('%g' % sel)
                if sel:
                    widget.selectAll()

            def lineedit_to_state(widget, state, attribute):
                s = float(widget.text())
                try:
                    setattr(state, attribute, s)
                except Exception:
                    raise ValueError(
                        'Value of %s needs to be a float or integer'
                        % string.capwords(attribute))

            for il, label in enumerate(source.T.propnames):
                if label in source._ranges.keys():

                    layout.addWidget(qw.QLabel(string.capwords(label)), il, 0)

                    slider = qw.QSlider(qc.Qt.Horizontal)
                    slider.setSizePolicy(
                        qw.QSizePolicy(
                            qw.QSizePolicy.Expanding, qw.QSizePolicy.Fixed))
                    slider.setMinimum(source._ranges[label]['min'])
                    slider.setMaximum(source._ranges[label]['max'])
                    slider.setSingleStep(source._ranges[label]['step'])
                    slider.setPageStep(source._ranges[label]['step'])
                    layout.addWidget(slider, il, 1)
                    try:
                        state_bind_slider(
                            self, self._state.source_selection, label, slider,
                            factor=source._ranges[label]['fac'])
                    except Exception:
                        state_bind_slider(
                            self, self._state.source_selection, label, slider)

                    le = qw.QLineEdit()
                    layout.addWidget(le, il, 2)

                    self._state_bind_source(
                        [label], lineedit_to_state, le,
                        [le.editingFinished, le.returnPressed],
                        state_to_lineedit, attribute=label)

            for label, name in zip(
                    ['GF dt'], ['deltat']):
                il += 1
                layout.addWidget(qw.QLabel(label), il, 0)
                slider = qw.QSlider(qc.Qt.Horizontal)
                slider.setSizePolicy(
                    qw.QSizePolicy(
                        qw.QSizePolicy.Expanding, qw.QSizePolicy.Fixed))
                slider.setMinimum(1.)
                slider.setMaximum(1000.)
                slider.setSingleStep(1)
                slider.setPageStep(1)
                layout.addWidget(slider, il, 1)
                state_bind_slider(
                    self, self._state, name, slider, factor=0.01)

                le = qw.QLineEdit()
                layout.addWidget(le, il, 2)

                self._state_bind_store(
                    [name], lineedit_to_state, le,
                    [le.editingFinished, le.returnPressed],
                    state_to_lineedit, attribute=name)

            il += 1
            layout.addWidget(qw.QLabel('Anchor'), il, 0)

            cb = qw.QComboBox()
            for i, s in enumerate(gf.RectangularSource.anchor.choices):
                cb.insertItem(i, s)
            layout.addWidget(cb, il, 1, 1, 2)
            state_bind_combobox(
                self, self._state.source_selection, 'anchor', cb)

            il += 1
            layout.addWidget(qw.QLabel('Display Parameter'), il, 0)

            cb = qw.QComboBox()
            for i, s in enumerate(['Time (s)']):
                cb.insertItem(i, s)
            layout.addWidget(cb, il, 1, 1, 2)
            state_bind_combobox(
                self, self._state, 'display_parameter', cb)

            il += 1
            pb = qw.QPushButton('Move source here')
            layout.addWidget(pb, il, 2)
            pb.clicked.connect(self.update_loc)

            pb = qw.QPushButton('Load')
            layout.addWidget(pb, il, 0)
            pb.clicked.connect(self.open_file_load_dialog)

            pb = qw.QPushButton('Save')
            layout.addWidget(pb, il, 1)
            pb.clicked.connect(self.open_file_save_dialog)

            il += 1
            cb = qw.QCheckBox('Show')
            layout.addWidget(cb, il, 0)
            state_bind_checkbox(self, self._state, 'visible', cb)

            pb = qw.QPushButton('Remove')
            layout.addWidget(pb, il, 1)
            pb.clicked.connect(self.unset_parent)

            il += 1
            layout.addWidget(qw.QFrame(), il, 0, 1, 3)

        self._controls = frame

        return self._controls


__all__ = [
    'SourceElement',
    'SourceState',
]
