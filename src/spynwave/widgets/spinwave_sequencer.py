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
from pymeasure.display.widgets import SequencerWidget, SequenceEvaluationException

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SpinWaveSequencerWidget(QtWidgets.QWidget):
    """ This class takes/copies some methods from pymeasure sequencer. """

    # TODO: is this the best way, or better to copy the code
    queue_sequence = SequencerWidget.queue_sequence
    _check_queue_signature = SequencerWidget._check_queue_signature

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        self._check_queue_signature()

        # self._get_properties()
        # self._setup_ui()
        # self._layout()


    def get_sequence(self):
        """ Generate the sequence from the entered parameters. Returns a list of tuples; each tuple
        represents one measurement, containing dicts with the parameters for that measurement. """

        # TODO: not sure if a list of dicts also works, or if it should be list of tuples of dicts.
        return [({'rf_frequency': 1}, {'magnetic_field': 0.5})]

    def get_sequence_from_tree(self):
        """ Method to implement to comply with other methods of the sequencer widget and with the
        estimator widget. Wraps around create_sequence.
        """
        return self.get_sequence()

