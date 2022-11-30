"""
This file is part of the SpynWave package.
"""

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.inputs import IntegerInput, ListInput, ScientificInput


def patched_layout_inputs_widget(self):
    layout = QtWidgets.QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)

    self.labels = {}
    parameters = self._procedure.parameter_objects()

    for name in self._inputs:
        widget = getattr(self, name)

        if not isinstance(getattr(self, name), self.NO_LABEL_INPUTS):
            label = QtWidgets.QLabel(self)
            label.setText("%s:" % parameters[name].name)
            self.labels[name] = label

            if isinstance(widget, (IntegerInput, ScientificInput, ListInput, )):
                sublayout = QtWidgets.QHBoxLayout()
                sublayout.setContentsMargins(0, 0, 0, 0)
                sublayout.addWidget(label)
                sublayout.addWidget(widget)
                layout.addLayout(sublayout)
            else:
                layout.addWidget(label)
                layout.addWidget(widget)
        else:
            layout.addWidget(widget)

    self.setLayout(layout)
