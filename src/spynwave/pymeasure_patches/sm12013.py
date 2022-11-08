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

# TODO: should be changed to pymeasure import
from spynwave.pymeasure_patches.sm_series import SMFamily


class SM12013(SMFamily):
    """ This class represents the family of SM power supplies by Delta Elektronika.

    .. code-block:: python

        source = SM12013("GPIB::8")

        source.ramp_to_zero(1)               # Set output to 0 before enabling
        source.enable()                      # Enables the output
        source.current = 1                   # Sets a current of 1 Amps

    """

    VOLTAGE_RANGE = [0, 120]
    CURRENT_RANGE = [0, 13]

    voltage = VOLTAGE_RANGE
    current = CURRENT_RANGE
    max_voltage = VOLTAGE_RANGE
    max_current = CURRENT_RANGE


