"""
This file is part of the SpynWave package.
"""

import logging
from time import sleep
from abc import ABCMeta, abstractmethod

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MagnetBase(metaclass=ABCMeta):
    power_supply = None
    gauss_meter = None

    mirror_fields = False
    measurement_type = None

    def __init__(self, mirror_fields=False, measurement_type=None):
        self.mirror_fields = mirror_fields
        self.measurement_type = measurement_type

    @abstractmethod
    def startup(self):
        pass

    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def set_field(self, field):
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

    @property
    @abstractmethod
    def measurement_delay(self):
        pass

    @property
    @abstractmethod
    def field_ramp_rate(self):
        pass

