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

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_discrete_set, \
    truncated_discrete_set

from spynwave.pymeasure_patches.lakeshore400_series import LakeShore400Family


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
        "CSETP?", "CSETP %f",
        """ A bool property that controls whether the field control mode is enabled. Can be set.
        """,
    )

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
