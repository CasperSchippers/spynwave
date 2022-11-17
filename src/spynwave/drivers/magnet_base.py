"""
This file is part of the SpynWave package.
"""

import logging
from abc import ABCMeta, abstractmethod

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetBase(metaclass=ABCMeta):
    power_supply = None
    gauss_meter = None

    mirror_fields = False

    def __init__(self, mirror_fields=False):
        self.mirror_fields = mirror_fields

    @abstractmethod
    def startup(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def set_field(self, field):
        # TODO: implement test to ensure that all magnets respect the mirror_fields property
        pass

    @abstractmethod
    def measure_field(self):
        pass

    @abstractmethod
    def sweep_field(self, start, stop, ramp_rate, update_delay=0.1,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: True):
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

