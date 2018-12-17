# https://pyrocko.org - GPLv3
#
# The Pyrocko Developers, 21st Century
# ---|P------/S----------~Lg----------
from __future__ import absolute_import, print_function, division

import string

import numpy as num

from pyrocko.guts import Bool, Float, String

from pyrocko import cake, gf
from pyrocko.gui.qt_compat import qw, qc

from pyrocko.gui.vtk_util import PolygonPipe
from .. import state as vstate
from pyrocko import geometry

from .base import Element, ElementState

guts_prefix = 'sparrow'


class SourceState(ElementState):
    visible = Bool.T(default=True)
    width = Float.T(default=5000.)
    length = Float.T(default=10000.)
    strike = Float.T(default=0.)
    dip = Float.T(default=45.)
    rake = Float.T(default=0.)
    nucleation_x = Float.T(default=0.)
    nucleation_y = Float.T(default=0.)
    anchor = String.T(default='top')

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
        self._pipe = None
        self._controls = None
        self._points = num.array([])

    def _state_bind(self, *args, **kwargs):
        vstate.state_bind(self, self._state, *args, **kwargs)

    def bind_state(self, state):
        upd = self.update
        self._listeners.append(upd)
        for il, label in enumerate(
            ['width', 'length', 'strike', 'dip', 'rake',
             'nucleation_x', 'nucleation_y', 'anchor']):

            state.add_listener(upd, label)

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
                self._parent.remove_actor(self._pipe.actor)
                self._pipe = None

            if self._controls:
                self._parent.remove_panel(self._controls)
                self._controls = None

            self._parent.update_view()
            self._parent = None

    def update(self, *args):
        state = self._state

        if self._pipe:
            self._parent.remove_actor(self._pipe.actor)
            self._pipe = None

        if self._pipe and not state.visible:
            self._parent.remove_actor(self._pipe.actor)

        if state.visible:
            fault = gf.RectangularSource(
                width=state.width,
                length=state.length,
                strike=state.strike,
                dip=state.dip,
                rake=state.rake,
                nucleation_x=state.nucleation_x,
                nucleation_y=state.nucleation_y,
                anchor=state.anchor).outline(cs='latlondepth')
            points = geometry.latlondepth2xyz(
                fault,
                planetradius=cake.earthradius)

            vertices = geometry.arr_vertices(points)
            faces = geometry.arr_faces([[i for i in range(len(points))]])
            self._pipe = PolygonPipe(
                vertices,
                faces)
            self._parent.add_actor(self._pipe.actor)

        self._parent.update_view()

    def _get_controls(self):
        if not self._controls:
            from ..state import \
                state_bind_checkbox, state_bind_slider, state_bind_combobox
            from pyrocko import gf

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

            widget_value = {'width': {'min': 0., 'max': 1000000., 'step': 1},
                            'length': {'min': 0., 'max': 2000000., 'step': 1},
                            'strike': {'min': 0., 'max': 359., 'step': 1},
                            'dip': {'min': 0., 'max': 90., 'step': 1},
                            'rake': {'min': 0., 'max': 359., 'step': 1},
                            'nucleation_x':
                                {'min': -1., 'max': 1., 'step': 0.01},
                            'nucleation_y':
                                {'min': -1., 'max': 1., 'step': 0.01}}

            for il, label in enumerate([
                    'width', 'length', 'strike',
                    'dip', 'rake', 'nucleation_x',
                    'nucleation_y']):
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
                state_bind_slider(self, self._state, label, slider)

                le = qw.QLineEdit()
                layout.addWidget(le, il, 2)

                self._state_bind(
                    [label], lineedit_to_state, le,
                    [le.editingFinished, le.returnPressed], state_to_lineedit,
                    attribute=label)

                le.returnPressed.connect(lambda *args: le.selectAll())
                setattr(self, label, le)

            il += 1
            layout.addWidget(qw.QLabel('Anchor'), il, 0)

            cb = qw.QComboBox()
            for i, s in enumerate(gf.RectangularSource.anchor.choices):
                cb.insertItem(i, s)
            layout.addWidget(cb, il, 1, 1, 2)
            state_bind_combobox(self, self._state, 'anchor', cb)

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
