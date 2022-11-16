"""
This file is part of the SpynWave package.
"""

import logging

# import re
# from functools import partial
# import numpy
# from collections import ChainMap
from itertools import product
# from inspect import signature

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import SequencerWidget
from pymeasure.display.inputs import ScientificInput

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SpinWaveSequencerWidget(QtWidgets.QWidget):
    """ This class takes/copies some methods from pymeasure sequencer. """

    # TODO: is this the best way, or better to copy the code
    queue_sequence = SequencerWidget.queue_sequence
    _check_queue_signature = SequencerWidget._check_queue_signature
    _get_properties = SequencerWidget._get_properties

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        self._check_queue_signature()

        self._inputs = self._parent.displays
        self._get_properties()  # TODO: is it useful to make a get/check function?
        self._setup_ui()
        self._layout()

    def _setup_ui(self):
        self.repeats_spinbox = QtWidgets.QSpinBox()
        self.repeats_spinbox.setMinimum(1)

        self.mirrored_checkbox = QtWidgets.QCheckBox()
        self.mirrored_checkbox.setTristate(False)

        self.field_inputs = SweepInputPanel("field", "frequency",
                                            self._parent.procedure_class.field_start,
                                            self._parent.procedure_class.field_stop,
                                            self._parent.procedure_class.rf_frequency)
        self.frequency_inputs = SweepInputPanel("frequency", "field",
                                                self._parent.procedure_class.frequency_start,
                                                self._parent.procedure_class.frequency_stop,
                                                self._parent.procedure_class.magnetic_field)
        # self.time_inputs = InputPanel()

        self.queue_button = QtWidgets.QPushButton("Queue sequence")
        self.queue_button.clicked.connect(self.queue_sequence)

    def _layout(self):
        time_tab = QtWidgets.QLabel("Time")

        self.pane_order = ["Field sweep", "Frequency sweep"]  # "Time sweep"

        self.pane_widget = QtWidgets.QTabWidget()
        self.pane_widget.setContentsMargins(0, 0, 0, 0)
        self.pane_widget.setStyleSheet("QTabWidget::pane { border: 0; }")
        self.pane_widget.tabBar().setVisible(False)
        self.pane_widget.addTab(self.field_inputs, "Field sweep")
        self.pane_widget.addTab(self.frequency_inputs, "Frequency sweep")
        self.pane_widget.addTab(time_tab, "Time sweep")

        form = QtWidgets.QFormLayout()
        form.addRow("Mirrored fields", self.mirrored_checkbox)
        form.addRow("Repeats", self.repeats_spinbox)

        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addLayout(form, 10)
        btn_box.addStretch(1)
        btn_box.addWidget(self.queue_button, 10)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(6)
        vbox.addWidget(self.pane_widget)
        vbox.addLayout(btn_box)
        self.setLayout(vbox)

    def set_pane_focus(self, pane_name):
        if pane_name in self.pane_order:
            index = self.pane_order.index(pane_name)
            self.pane_widget.setCurrentIndex(index)
            self.pane_widget.setVisible(True)
        else:
            self.pane_widget.setVisible(False)

    def get_sequence(self):
        """ Generate the sequence from the entered parameters. Returns a list of tuples; each tuple
        represents one measurement, containing dicts with the parameters for that measurement. This
        format is dictated by the queue_sequence method from the SequenceWidget.
        """

        sequence = [tuple()]



        if self.mirrored_checkbox.isChecked():
            sequence = [
                seq + ({"mirrored_field": val}, ) for val, seq in product([False, True], sequence)
            ]

        # Apply repeats
        sequence = sequence * self.repeats_spinbox.value()

        print(sequence)
        return sequence

    def get_sequence_from_tree(self):
        """ Method to implement to comply with other methods of the sequencer widget and with the
        estimator widget. Wraps around create_sequence.
        """
        return self.get_sequence()


class SweepInputPanel(QtWidgets.QWidget):
    def __init__(self, sweep_name, param_name, start_class, stop_class, param_class):
        self.sweep_name = sweep_name
        self.param_name = param_name
        self.start_class = start_class
        self.stop_class = stop_class
        self.param_class = param_class

        super().__init__()

        self._setup_ui()
        self._layout()

    def _setup_ui(self):
        self.first_param = ScientificInput(self.param_class)
        self.last_param = ScientificInput(self.param_class)

        self.first_start = ScientificInput(self.start_class)
        self.first_stop = ScientificInput(self.stop_class)
        self.last_start = ScientificInput(self.start_class)
        self.last_stop = ScientificInput(self.stop_class)

        self.interp_box = QtWidgets.QComboBox()
        self.interp_box.addItem("Linear")

        self.steps_box = QtWidgets.QSpinBox()
        self.steps_box.setMinimum(2)
        self.steps_box.setSuffix(" steps")

    def _layout(self):
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QtWidgets.QLabel(self.param_name.capitalize()), 0, 1)
        layout.addWidget(QtWidgets.QLabel(f"Start {self.sweep_name}"), 0, 3)
        layout.addWidget(QtWidgets.QLabel(f"Stop {self.sweep_name}"), 0, 4)

        layout.addWidget(QtWidgets.QLabel("First"), 1, 0)
        layout.addWidget(QtWidgets.QLabel("Last"), 3, 0)

        layout.addWidget(self.first_param, 1, 1)
        layout.addWidget(self.first_start, 1, 3)
        layout.addWidget(self.first_stop, 1, 4)
        layout.addWidget(self.last_param, 3, 1)
        layout.addWidget(self.last_start, 3, 3)
        layout.addWidget(self.last_stop, 3, 4)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.addStretch(1)
        # hbox.addWidget(self.interp_box)
        hbox.addWidget(QtWidgets.QLabel("Linear in"))
        hbox.addWidget(self.steps_box)
        hbox.addStretch(1)
        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addLayout(hbox)
        layout.addLayout(vbox, 2, 1, 1, 4)

        layout.addItem(QtWidgets.QSpacerItem(1, 1), 0, 2)
        layout.addItem(QtWidgets.QSpacerItem(1, 1), 1, 2)
        layout.addItem(QtWidgets.QSpacerItem(1, 1), 3, 2)
