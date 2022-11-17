"""
This file is part of the SpynWave package.
"""

import logging
from abc import ABCMeta, abstractmethod

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetBase(metaclass=ABCMeta):
    @abstractmethod
    def startup(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def set_field(self):
        pass

    @abstractmethod
    def measure_field(self):
        pass

    @abstractmethod
    def sweep_field(self):
        pass

    @abstractmethod
    def wait_for_stable_field(self):
        pass

    # TODO: functions that should be generalised
    @abstractmethod
    def gauss_meter_set_fast_mode(self):
        pass

    # TODO: properties that should be generalised

    @property
    @abstractmethod
    def gauss_meter_delay(self):
        pass

    @property
    @abstractmethod
    def current_ramp_rate(self):
        pass

