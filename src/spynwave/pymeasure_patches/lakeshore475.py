#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2022 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

from time import time, sleep
import math

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_range

from spynwave.pymeasure_patches.lakeshore400_series import LakeShore400Family


def joined_list_validator(validators):
    def validator(value, values):
        if len(value) != len(values):
            raise ValueError("The length of the provided list does not match the expected length "
                             f"({len(values)}).")
        return [vld(val, vals) for vld, val, vals in zip(validators, value, values)]

    return validator

class LakeShore475(LakeShore400Family):
    """
    Represents the Lake Shore 475 DSP Gaussmeter and provides a high-level interface for interacting
    with the instrument.
    .. code-block:: python

        gaussmeter = LakeShore475("COM1")
        gaussmeter.unit = "T"               # Set units to Tesla
        gaussmeter.auto_range = True        # Turn on auto-range
        gaussmeter.fast_mode = True         # Turn on fast-mode


    A delay of 50 ms is ensured between subsequent writes, as the instrument cannot correctly
    handle writes any faster.
    """

    UNITS = {"G": 1, "T": 2, "Oe": 3, "A/m": 4}
    TEMPUNITS = {"C": 1, "K": 2}
    PROBE_TYPES = {"High Sensitivity": 40,
                   "High Stability": 41,
                   "Ultra-High Sensitivity": 42,
                   "User prog. cable/High Sensitivity": 50,
                   "User prog. cable/High Stability": 51,
                   "User prog. cable/Ultra-High Sensitivity": 52, }

    def __init__(self, adapter, baud_rate=9600, **kwargs):
        super().__init__(adapter, "Lake Shore 475 DSP Gaussmeter", baud_rate=baud_rate)

    # Modify dynamic properties

    unit_values = UNITS
    unit_set_command = "UNIT %d"
    unit_map_values = True

    probe_type_values = PROBE_TYPES

    field_range_raw_values = range(6)

    front_panel_brightness_values = range(5)

    temperature_unit = Instrument.control(
        "TUNIT?", "TUNIT %d",
        """ A string property that controls the temperature units used by the gaussmeter.
        Valid values are C (Celcius) and K (Kelvin). Can be set. """,
        values=TEMPUNITS,
        map_values=True,
    )

    field_control_enabled = Instrument.control(
        "CMODE?", "CMODE %d",
        """ A bool property that controls whether the field control mode is enabled. Can be set.
        """,
        values={True: 1, False: 0},
        map_values=True,
    )

    field_setpoint = Instrument.control(
        "CSETP?", "CSETP %G",
        """ A float property that controls magnetic field setpoint in the presently selected units.
        Can be set.
        """,
    )

    field_control_parameters = Instrument.control(
        "CPARAM?", "CPARAM %s",
        """ A list property that controls the field control parameters. The list consists of 4 float
        values: [P-value, I-value, ramp-rate, control slope limit]: the proportional value for the
        PI controller (between 0.01 and 1000), the integral value for the PI controller (between
        0.0001 and 1000), the field ramp rate (in the presently selected units/minute; if 0, ramping
        is turned off), and the control slope limit of the analog output (in V/minute, between 0.01
        and 1000). Can be set. 
        """,
        set_process=lambda l: ",".join(["%G" % v for v in l]),
        values=[(1e-2, 1e3), (1e-4, 1e3), (0, math.inf), (1e-2, 1e3)],
        validator=joined_list_validator([strict_range] * 4),
    )

    @property
    def field_ramp_rate(self):
        """ A float property that controls the field ramp rate, in the presently selected
        units/minute. If set to 0, field ramping is turned off. Can be set; note that setting the
        value asks and writes the `field_control_parameters` property.
        """
        return self.field_control_parameters[2]

    @field_ramp_rate.setter
    def field_ramp_rate(self, ramp_rate):
        values = self.field_control_parameters
        values[2] = ramp_rate
        self.field_control_parameters = values

    field_setpoint_ramping = Instrument.measurement(
        "RAMPST?",
        """ A bool property that checks whether the field control set point is presently being
        ramped.
        """,
        values={True: 1, False: 0},
        map_values=True,
    )

    # TODO: do I need to use this command, or the more complicated version of the 421
    field = Instrument.measurement(
        "RDGFIELD?",
        """ A float property that returns the magnetic field in the present units.
        """,
    )

    temperature = Instrument.measurement(
        "RDGFIELD?",
        """ A float property that returns the temperature in the present units.
        """,
    )
