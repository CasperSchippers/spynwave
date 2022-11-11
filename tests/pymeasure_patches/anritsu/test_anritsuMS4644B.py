"""
This file is part of the SpynWave package.
"""

import pytest

from pymeasure.test import expected_protocol

from spynwave.pymeasure_patches.anritsuMS4644B import AnritsuMS4644B


def test_init():
    with expected_protocol(
        AnritsuMS4644B,
        [],
    ) as instr:
        pass


def test_channel_number_of_traces():
    # Test first level channel
    with expected_protocol(
        AnritsuMS4644B,
        [(":CALC6:PAR:COUN 16", None),
         (":CALC2:PAR:COUN?", "4")],
    ) as instr:
        instr.ch_6.number_of_traces = 16
        assert instr.ch_2.number_of_traces == 4


def test_channel_port_power_level():
    # Test second level channel (port in channel)
    with expected_protocol(
        AnritsuMS4644B,
        [(":SOUR6:POW:PORT1 3.0e0", None),
         (":SOUR2:POW:PORT4?", "-1.5E1")],
    ) as instr:
        instr.ch_6.pt_1.power_level = 3.
        assert instr.ch_2.pt_4.power_level == -15.

    # power_level = Channel.control(
    #     "SOUR{{ch}}:POW:PORT{pt}?", "SOUR{{ch}}:POW:PORT{pt} %g",

# Test second level channel (trace in channel)

