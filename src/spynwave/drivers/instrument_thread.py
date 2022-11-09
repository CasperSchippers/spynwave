"""
This file is part of the SpynWave package.
"""

import logging
import queue

from pymeasure.thread import StoppableThread, InterruptableEvent

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class InstrumentThread(StoppableThread):
    def __init__(self, procedure, instrument, settings=None):
        super().__init__()
        self.procedure = procedure
        self.instrument = instrument
        self.settings = settings

        self._finished = InterruptableEvent()
        self.data_queue = queue.Queue()

        # TODO: uitzoeken of dit nodig is
        global log
        log = logging.getLogger()

    def finished(self):
        self._finished.set()

    def is_finished(self):
        return self._finished.is_set()

    def run(self):
        raise NotImplementedError("Should be implemented for a specific purpose")