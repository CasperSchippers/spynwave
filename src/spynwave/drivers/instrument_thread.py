"""
This file is part of the SpynWave package.
"""

import logging
import queue
from time import time

from pymeasure.thread import StoppableThread, InterruptableEvent

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class InstrumentThread(StoppableThread):
    def __init__(self, procedure, instrument, **kwargs):
        super().__init__()
        self.procedure = procedure
        self.instrument = instrument
        self.settings = kwargs

        self._finished = InterruptableEvent()
        self.data_queue = queue.Queue()

        # TODO: Check whether this is required in within the thread
        global log
        log = logging.getLogger()

    def put_datapoint(self, data):
        """ Here the data is timestamped and added to the queue for processing and storing. """

        if not isinstance(data, dict):
            raise TypeError("data should be formatted as a dict with {'column': value} pairs.")

        self.data_queue.put((time(), data))

    def get_datapoint(self):
        if not self.data_queue.empty():
            return self.data_queue.get()
        else:
            return False

    def finished(self):
        self._finished.set()

    def is_finished(self):
        return self._finished.is_set()

    def run(self):
        raise NotImplementedError("Should be implemented for a specific purpose")

    def shutdown(self, timeout=2):
        if self.is_alive():
            try:
                self.join(timeout)
            except RuntimeError as exc:
                log.error(exc)
