"""
This file is part of the SpynWave package.
"""

import logging
import math
from time import time, sleep

from pyvisa.errors import VisaIOError, VI_ERROR_TMO
import numpy as np

try:
    import u12  # LabJack library from labjackpython
except ImportError:
    u12 = None  # Happens if the dll is not installed

from spynwave.constants import config
from spynwave.drivers.magnet_base import MagnetBase
from spynwave.drivers.magnet_lakeshore421 import LakeShore421Mixin

# TODO: should be updated on pymeasure
from spynwave.pymeasure_patches.sm12013 import SM12013

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MagnetInPlane(LakeShore421Mixin, MagnetBase):
    """ This class represents the magnet that is used on the crystat/blackhole spinwave setup.

    It uses a Delta-Elektronika SM120-13 unipolar power supply, router via a home-built switchbox
    (which is controlled using a labjack U12). The setup features a LakeShore 421 Gauss meter to
    probe the magnetic field.

    """
    name = "in-plane magnet"
    labjack = None

    max_field = config[name]["max field"]

    max_current = config[name]["power-supply"]["max current"]
    max_voltage = config[name]["power-supply"]["max voltage"]
    current_ramp_rate = config[name]["power-supply"]["current ramp rate"]
    max_current_step = config[name]["power-supply"]["max current step"]
    last_current = 0  # attribute to store the last applied current

    field_ramp_rate = current_ramp_rate * max_field / max_current

    polarity = 0
    bitSelect_positive = 2**config[name]["labjack"]["positive polarity bit"]
    bitSelect_negative = 2**config[name]["labjack"]["negative polarity bit"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.power_supply = SM12013(
            config["general"]["visa-prefix"] + config[self.name]["power-supply"]["address"]
        )
        self._clear_powersupply_buffer()
        self.max_current = self.power_supply.max_current
        self.max_voltage = self.power_supply.max_voltage

        self.labjack = u12.U12(id=config[self.name]["labjack"]["ID"])
        # Set the correct channels on the labjack to output channels for controlling the polarity
        self.labjack.digitalIO(
            trisD=self.bitSelect_positive + self.bitSelect_negative,
            trisIO=0,
            stateD=0,
            stateIO=0,
            updateDigital=True
        )

    def startup(self):
        # Prepare current supply and labjack for magnetic field
        self.last_current = self.power_supply.current
        # self.power_supply.voltage
        # self.power_supply.ask("SE:DI:DA?")  # TODO: not sure what this does

        self.power_supply.ramp_to_zero(self.current_ramp_rate)
        self.power_supply.write("REM:CV")  # VS "LOC:CV"
        self.power_supply.write("REM:CC")  # VS "LOC:CC"

        self.power_supply.voltage = self.max_voltage
        self.power_supply.current = 0
        # TODO: the labview code does not use SO:FU:RSD but SO:FU:OUTP; see what the difference is
        # Now both are used in the enable and disable methods
        self.power_supply.enable()

        # Set polarity to positive
        self._set_polarity(+1)

        self.startup_lakeshore()

    def _set_current(self, current, controlled=True):
        """ Set a current to the power-supply
        :param controlled: Boolean that controls the method for setting the current, if True a slow
            but safe and stable approach is used, if False a faster approach (for use in sweeps)
        """
        if controlled:
            self._set_current_controlled(current)
        else:
            self._set_current_quick(current)

        return current

    def _set_current_controlled(self, current):
        """ Apply a specified current by nicely ramping to this current. """
        polarity = self._current_polarity(current)

        if self._polarity_needs_changing(polarity):
            self.power_supply.ramp_to_zero(self.current_ramp_rate)
            self.last_current = 0
            self._set_polarity(polarity)

        self.power_supply.ramp_to_current(abs(current), self.current_ramp_rate)
        self.last_current = self.power_supply.current

    def _set_current_quick(self, current):
        """ Apply a specified current by instantly setting the current to the power supply.
        A few check are performed to ensure no breakage of the instruments.
        """
        if abs(abs(current) - abs(self.last_current)) > self.max_current_step:
            raise ValueError(f"Step in current too large: from {self.last_current} A to"
                             f"{abs(current)} A; maximum step-size is {self.max_current_step} A")

        polarity = self._current_polarity(current)
        if self._polarity_needs_changing(polarity):
            self._set_polarity(polarity)

        self.power_supply.current = abs(current)
        self.last_current = abs(current)

    @staticmethod
    def _current_polarity(current):
        return int(math.copysign(1, current))

    def _polarity_needs_changing(self, polarity):
        return polarity != self.polarity

    def _set_polarity(self, polarity):
        if self.power_supply.current > self.max_current_step:
            self.power_supply.ramp_to_zero(self.current_ramp_rate)

        self.power_supply.disable()

        while not self.power_supply.measure_current == 0.:
            sleep(0.1)

        self._labjack_polarity_pulse(polarity)
        self.power_supply.enable()

    def _labjack_polarity_pulse(self, polarity):
        self.labjack.pulseOut(
            bitSelect=self.bitSelect_positive if polarity >= 0 else self.bitSelect_negative,
            numPulses=1,
            timeB1=250,  # Pulse length (~us)
            timeC1=1,
            timeB2=1,
            timeC2=1,
            lowFirst=False,
        )
        self.polarity = polarity

    def _get_set_current(self):
        current = self.power_supply.current
        return self.polarity * current

    def sweep_field(self, start, stop, ramp_rate, update_delay=0.1,
                    sleep_fn=lambda x: sleep(x), should_stop=lambda: False,
                    callback_fn=lambda x: None):
        # Check if fields are within bounds
        self._field_to_current(start)
        self._field_to_current(stop)

        sweep_duration = abs((start - stop) / ramp_rate)
        number_of_updates = math.ceil(sweep_duration / update_delay)
        field_list = np.linspace(start, stop, number_of_updates + 1)

        t0 = 0
        for field in field_list:
            if (delay := update_delay + (t0 - time())) > 0:
                sleep_fn(delay)
            else:
                log.debug(f"Setting field took {-delay} longer than update delay "
                          f"({update_delay - delay}s vs {update_delay} s")
            t0 = time()

            self.set_field(field, controlled=False)
            callback_fn(field)
            if should_stop():
                break

    def _clear_powersupply_buffer(self):
        timeout = self.power_supply.adapter.connection.timeout
        try:
            self.power_supply.adapter.connection.timeout = 10
            while True:
                log.debug(self.power_supply.adapter.read())
        except VisaIOError as exc:
            if not exc.error_code == VI_ERROR_TMO:
                raise exc
        finally:
            self.power_supply.adapter.connection.timeout = timeout

    def shutdown(self):
        if self.power_supply is not None:
            self.power_supply.shutdown()

        # TODO: shutdown labjack?
        self.shutdown_lakeshore()
