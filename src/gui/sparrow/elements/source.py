# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------
from __future__ import absolute_import, print_function, division

import string

import numpy as num

import vtk

from pyrocko.guts import Bool

from pyrocko import gf
from pyrocko.gui.qt_compat import qw, qc

from pyrocko.gui.vtk_util import\
    make_multi_polyline, vtk_set_input
from .. import state as vstate
from pyrocko.gui.talkie import Talkie

from .base import Element, ElementState

guts_prefix = 'sparrow'


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
    def __init__(self, polygons, RGB, cs='latlondepth'):

        self.mapper = vtk.vtkDataSetMapper()
        self._polyline_grid = {}

        lines = []

        for ipoly, poly in enumerate(polygons):
            lines.append(poly.points)

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


class Polygon(object):
    def __init__(self, points):
        self.points = points

    def refine_polygon_points(self, cs='latlondepth'):
        import math
        import pyrocko.orthodrome as od

        points = self.points
        refined_points = []

        for i in range(len(points) - 1):
            azim, dist = od.azidist_numpy(
                points[i, 0], points[i, 1], points[i + 1, 0], points[i + 1, 1])

            if cs == 'latlondepth':
                delta_z = points[i + 1, 2] - points[i, 2]
                total_dist = math.sqrt(dist**2 + (delta_z / 111.)**2)

            elif cs == 'latlon':
                total_dist = dist

            numint = int(math.ceil(total_dist))

            for ii in range(numint):
                factor = float(ii) / float(numint)

                if cs == 'latlondepth':
                    point = [None] * 3

                    point[:2] = od.azidist_to_latlon(
                        points[i, 0], points[i, 1], azim, dist * factor)
                    point[2] =\
                        points[i, 2] + delta_z * factor

                elif cs == 'latlon':
                    point = [None] * 2

                    point[:] = od.azidist_to_latlon(
                        points[i, 0], points[i, 1], azim, dist * factor)

                refined_points.append(point)

        refined_points.append(points[-1][:])

        self.points = num.array(refined_points)


class ProxySource(ElementState):
    pass


for source_cls in [gf.RectangularSource, gf.DCSource]:

    cls_name = 'Proxy' + source_cls.__name__

    class proxy_source_cls(ProxySource):
        class_name = cls_name

    proxy_source_cls.__name__ = cls_name
    vars()[cls_name] = proxy_source_cls

    for prop in source_cls.T.properties:
        proxy_source_cls.T.add_property(prop.name, prop)


ProxyRectangularSource._name = 'RectangularSource'

ProxyRectangularSource._ranges = {
    'lat': {'min': -90., 'max': 90., 'step': 1, 'ini': 0.},
    'lon': {'min': -180., 'max': 180., 'step': 1, 'ini': 0.},
    'depth': {'min': 0., 'max': 2000000., 'step': 1, 'ini': 10000.},
    'width': {'min': 0., 'max': 1000000., 'step': 1, 'ini': 30000.},
    'length': {'min': 0., 'max': 2000000., 'step': 1, 'ini': 100000.},
    'strike': {'min': -180., 'max': 180., 'step': 1, 'ini': 0.},
    'dip': {'min': 0., 'max': 90., 'step': 1, 'ini': 45.},
    'rake': {'min': -180., 'max': 180., 'step': 1, 'ini': 0.}}#,
    # 'nucleation_x': {'min': -100., 'max': 100., 'step': 1, 'ini': 0.},
    # 'nucleation_y': {'min': -100., 'max': 100., 'step': 1, 'ini': 0.}}


class SourceState(ElementState):
    visible = Bool.T(default=True)
    source_selection = ProxySource.T(default=ProxyRectangularSource())  # noqa

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

    def _state_bind(self, *args, **kwargs):
        vstate.state_bind(self, self._state, *args, **kwargs)

    def bind_state(self, state):
        upd = self.update
        self._listeners.append(upd)
        state.add_listener(upd, 'source_selection')
        state.add_listener(upd, 'visible')
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
        pass

    def open_file_save_dialog(self):
        pass

    def update_loc(self, *args):
        pstate = self._parent.state
        state = self._state

        source = state.source_selection
        source.lat = pstate.lat
        source.lon = pstate.lon

        self._state.source_selection.source = source

        self.update()

    def update_source(self, *args):
        source = self._state.source_selection

        source_new = ProxyRectangularSource()

        for propname in source_new.T.propnames:
            setattr(source_new, propname, source.__dict__[propname])


    def update(self, *args):
        state = self._state
        source = state.source_selection

        source_list = gf.source_classes

        if self._pipe:
            for pipe in self._pipe:
                self._parent.remove_actor(pipe.actor)
            self._pipe = []

        if self._pipe and not state.visible:
            for pipe in self._pipe:
                self._parent.remove_actor(pipe.actor)

        if state.visible:
            for i, a in enumerate(source_list):
                if a.__name__ is source._name:
                    fault = a(
                        **{prop: source.__dict__[prop]
                            for prop in source.T.propnames})
                    polygon = Polygon(
                        fault.outline(cs='latlondepth'))
                    polygon.refine_polygon_points(cs='latlondepth')
                    self._pipe.append(
                        SourceOutlinesPipe(
                            [polygon], (1., 1., 1.),
                            cs='latlondepth'))
                    self._parent.add_actor(self._pipe[-1].actor)

                    self._pipe.append(
                        SourceOutlinesPipe(
                            [polygon], (.6, .6, .6),
                            cs='latlon'))
                    self._parent.add_actor(self._pipe[-1].actor)

        self._parent.update_view()


    # def update_old(self, *args):
    #     state = self._state

    #     if self._pipe:
    #         for pipe in self._pipe:
    #             self._parent.remove_actor(pipe.actor)
    #         self._pipe = []

    #     if self._pipe and not state.visible:
    #         for pipe in self._pipe:
    #             self._parent.remove_actor(pipe.actor)

    #     if state.visible:

    #         # fault = 
    #         polygon = Polygon(
    #             fault.outline(cs='latlondepth'))
    #         polygon.refine_polygon_points(cs='latlondepth')
    #         self._pipe.append(
    #             SourceOutlinesPipe(
    #                 [polygon], (1., 1., 1.),
    #                 cs='latlondepth'))
    #         self._parent.add_actor(self._pipe[-1].actor)

    #         self._pipe.append(
    #             SourceOutlinesPipe(
    #                 [polygon], (.6, .6, .6),
    #                 cs='latlon'))
    #         self._parent.add_actor(self._pipe[-1].actor)

            # for point, color in zip((
            #         (state.nucleation_x * 0.01, state.nucleation_y * 0.01),
            #         map_anchor[state.anchor]),
            #         (num.array([[1., 0., 0.]]), num.array([[0., 0., 1.]]))):

            #     points = geometry.latlondepth2xyz(
            #         fault.points_on_source(
            #             [point[0]], [point[1]],
            #             cs='latlondepth'),
            #         planetradius=cake.earthradius)

            #     vertices = geometry.arr_vertices(points)
            #     self._pipe.append(ScatterPipe(vertices))
            #     self._pipe[-1].set_colors(color)
            #     self._parent.add_actor(self._pipe[-1].actor)

        # self._parent.update_view()

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
                sel = getattr(state.source_selection, attribute)

                widget.setText('%g' % sel)
                if sel:
                    widget.selectAll()

            def lineedit_to_state(widget, state, attribute):
                s = float(widget.text())
                try:
                    setattr(state.source_selection, attribute, s)
                except Exception:
                    raise ValueError(
                        'Value of %s needs to be a float or integer'
                        % string.capwords(attribute))

            self._state.listerners = []

            for il, label in enumerate(source.T.propnames):
                if label in source._ranges.keys():

                    layout.addWidget(qw.QLabel(string.capwords(label)), il, 0)

                    slider = qw.QSlider(qc.Qt.Horizontal)
                    slider.setSizePolicy(
                        qw.QSizePolicy(
                            qw.QSizePolicy.Expanding, qw.QSizePolicy.Fixed))
                    slider.setMinimum(source._ranges[label]['min'])
                    slider.setMaximum(source._ranges[label]['max'])
                    # slider.setSingleStep(source._ranges[label]['step'])
                    # slider.setPageStep(source._ranges[label]['step'])
                    # slider.setValue(source._ranges[label]['ini'])
                    # slider.setValue(
                    #     (source._ranges[label]['max'] +
                    #         source._ranges[label]['min']) * 0.5)
                    layout.addWidget(slider, il, 1)
                    state_bind_slider(
                        self, self._state.source_selection, label, slider)

                    le = qw.QLineEdit()
                    layout.addWidget(le, il, 2)

                    self._state_bind(
                        [label], lineedit_to_state, le,
                        [le.editingFinished, le.returnPressed],
                        state_to_lineedit, attribute=label)

                    le.returnPressed.connect(lambda *args: le.selectAll())
                    # setattr(self._state.source_selection, label, le)

            il += 1
            layout.addWidget(qw.QLabel('Anchor'), il, 0)

            cb = qw.QComboBox()
            for i, s in enumerate(gf.RectangularSource.anchor.choices):
                cb.insertItem(i, s)
            layout.addWidget(cb, il, 1, 1, 2)
            state_bind_combobox(
                self, self._state.source_selection, 'anchor', cb)

            il += 1
            pb = qw.QPushButton('Move source here')
            layout.addWidget(pb, il, 0)
            pb.clicked.connect(self.update_loc)

            pb = qw.QPushButton('Load')
            layout.addWidget(pb, il, 1)
            pb.clicked.connect(self.open_file_load_dialog)

            pb = qw.QPushButton('Save')
            layout.addWidget(pb, il, 2)
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
        self.bind_state(self._state)

        return self._controls


__all__ = [
    'SourceElement',
    'SourceState',
]
