"""
This file is part of the SpynWave package.
"""

import logging

# import re
# from functools import partial
# import numpy
# from collections import ChainMap
# from itertools import product
# from inspect import signature

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import SequencerWidget

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

        self.queue_button = QtWidgets.QPushButton("Queue sequence")
        self.queue_button.clicked.connect(self.queue_sequence)

    def _layout(self):
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addWidget(self.queue_button)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(6)
        vbox.addLayout(btn_box)
        self.setLayout(vbox)

    def get_sequence(self):
        """ Generate the sequence from the entered parameters. Returns a list of tuples; each tuple
        represents one measurement, containing dicts with the parameters for that measurement. This
        format is dictated by the queue_sequence method from the SequenceWidget.
        """

        return [({'rf_frequency': 1}, {'magnetic_field': 0.5})]

    def get_sequence_from_tree(self):
        """ Method to implement to comply with other methods of the sequencer widget and with the
        estimator widget. Wraps around create_sequence.
        """
        return self.get_sequence()
