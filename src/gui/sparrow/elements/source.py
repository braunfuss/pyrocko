# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------
from __future__ import absolute_import, print_function, division

import string

import numpy as num

import vtk

from pyrocko.guts import Bool, Float, String, Object

from pyrocko import cake, gf
from pyrocko.gui.qt_compat import qw, qc

from pyrocko.gui.vtk_util import\
    ScatterPipe, make_multi_polyline, vtk_set_input
from .. import state as vstate
from .. import common
from pyrocko import geometry

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
        if cs == 'latlondepth':
            self.set_3doutline(polygons)
        elif cs == 'latlon':
            self.set_2doutline(polygons)

        actor = vtk.vtkActor()
        actor.SetMapper(self.mapper)

        prop = actor.GetProperty()
        prop.SetDiffuseColor(RGB)
        prop.SetOpacity(1.)

        self.actor = actor

    def set_3doutline(self, polygons):
        lines = []

        for ipoly, poly in enumerate(polygons):
            lines.append(poly.points)

        self._polyline_grid = make_multi_polyline(
            lines_latlondepth=lines)

        vtk_set_input(self.mapper, self._polyline_grid)

    def set_2doutline(self, polygons):
        lines = []

        for ipoly, poly in enumerate(polygons):
            lines.append(poly.points)

        self._polyline_grid = make_multi_polyline(
            lines_latlon=lines)

        vtk_set_input(self.mapper, self._polyline_grid)


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


class SourceSelection(Object):
    def __init__(self, sourcetype, **kwargs):
        sources = gf.source_classes
        for i, a in enumerate(sources):
            if a.__name__ is sourcetype:
                self.source = sources[i](**kwargs)


class SourceState(ElementState):
    visible = Bool.T(default=True)
    source_selection = SourceSelection(
        'RectangularSource',
        lat=0., lon=0., depth=10000., width=5000., length=20000.,
        strike=0., dip=45., rake=0., nucleation_x=0.,
        nucleation_y=0., anchor='top')

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

        # for il, label in enumerate(
        #     ['latitude', 'longitude', 'depth', 'width', 'length', 'strike',
        #      'dip', 'rake', 'nucleation_x', 'nucleation_y', 'anchor']):

        #     state.add_listener(upd, label)
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
        source = self._state.source_selection.source
        source.lat = pstate.lat
        source.lon = pstate.lon

        self._state.source_selection.source = source

        self.update()

    def update(self, *args):
        state = self._state

        if self._pipe:
            for pipe in self._pipe:
                self._parent.remove_actor(pipe.actor)
            self._pipe = []

        if self._pipe and not state.visible:
            for pipe in self._pipe:
                self._parent.remove_actor(pipe.actor)

        if state.visible:
            fault = self._state.source_selection.source
        #     fault = gf.RectangularSource(
        #         lat=state.latitude,
        #         lon=state.longitude,
        #         depth=state.depth,
        #         width=state.width,
        #         length=state.length,
        #         strike=state.strike,
        #         dip=state.dip,
        #         rake=state.rake,
        #         nucleation_x=state.nucleation_x * 0.01,
        #         nucleation_y=state.nucleation_y * 0.01,
        #         anchor=state.anchor)

            points = fault.outline(cs='latlondepth')
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

        self._parent.update_view()

    def _get_controls(self):
        if not self._controls:
            from ..state import \
                state_bind_checkbox, state_bind_slider, state_bind_combobox
            from pyrocko import gf

            frame = qw.QFrame()
            layout = qw.QGridLayout()
            frame.setLayout(layout)

            # def state_to_lineedit(state, attribute, widget):
            #     sel = getattr(state, attribute)

            #     widget.setText('%g' % sel)
            #     if sel:
            #         widget.selectAll()

            # def lineedit_to_state(widget, state, attribute):
            #     s = float(widget.text())
            #     try:
            #         setattr(state, attribute, s)
            #     except Exception:
            #         raise ValueError(
            #             'Value of %s needs to be a float or integer'
            #             % string.capwords(attribute))

            widget_value = {'lat': {'min': -90., 'max': 90., 'step': 1},
                            'lon':
                                {'min': -180., 'max': 180., 'step': 1},
                            'depth': {'min': 0., 'max': 2000000., 'step': 1},
                            'width': {'min': 0., 'max': 1000000., 'step': 1},
                            'length': {'min': 0., 'max': 2000000., 'step': 1},
                            'strike': {'min': -180., 'max': 180., 'step': 1},
                            'dip': {'min': 0., 'max': 90., 'step': 1},
                            'rake': {'min': -180., 'max': 180., 'step': 1},
                            'nucleation_x':
                                {'min': -100., 'max': 100., 'step': 1},
                            'nucleation_y':
                                {'min': -100., 'max': 100., 'step': 1}}

            for il, label in enumerate(widget_value.keys()):
                layout.addWidget(qw.QLabel(string.capwords(label)), il, 0)

                slider = qw.QSlider(qc.Qt.Horizontal)
                slider.setSizePolicy(
                    qw.QSizePolicy(
                        qw.QSizePolicy.Expanding, qw.QSizePolicy.Fixed))
                slider.setMinimum(widget_value[label]['min'])
                slider.setMaximum(widget_value[label]['max'])
                slider.setSingleStep(widget_value[label]['step'])
                slider.setPageStep(widget_value[label]['step'])
                layout.addWidget(slider, il, 1)
                slider.sliderMoved.connect(
                    lambda: setattr(self._state.source_selection.source, label, slider.value()))
                # state_bind_slider(self, self._state, label, slider)

                le = qw.QLineEdit()
                layout.addWidget(le, il, 2)

                # self._state_bind(
                #     [label], lineedit_to_state, le,
                #     [le.editingFinished, le.returnPressed], state_to_lineedit,
                #     attribute=label)

                # le.returnPressed.connect(lambda *args: le.selectAll())
                # setattr(self, label, le)

            il += 1
            layout.addWidget(qw.QLabel('Anchor'), il, 0)

            cb = qw.QComboBox()
            for i, s in enumerate(gf.RectangularSource.anchor.choices):
                cb.insertItem(i, s)
            layout.addWidget(cb, il, 1, 1, 2)
            # state_bind_combobox(self, self._state, 'anchor', cb)

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

        return self._controls


__all__ = [
    'SourceElement',
    'SourceState',
]
