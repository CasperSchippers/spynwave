"""
This file is part of the SpynWave package.
"""

import pytest

try:
    from pymeasure.test import expected_protocol
except ImportError:
    pytest.skip('Only works with pymeasure 0.11 (which is not yet on pypi)',
                allow_module_level=True)

from spynwave.pymeasure_patches.lakeshore475 import LakeShore475


def test_init():
    with expected_protocol(
        LakeShore475,
        [],
    ):
        pass


def test_field_unit():
    with expected_protocol(
        LakeShore475,
        [("UNIT 1", None),
         ("UNIT?", "2")],
    ) as instr:
        instr.unit = "G"
        assert instr.unit == "T"


def test_temperature_unit():
    with expected_protocol(
        LakeShore475,
        [("TUNIT 1", None),
         ("TUNIT?", "2")],
    ) as instr:
        instr.temperature_unit = "C"
        assert instr.temperature_unit == "K"


def test_probe_type():
    with expected_protocol(
        LakeShore475,
        [("TYPE?", "40"),
         ("TYPE?", "42")],
    ) as instr:
        assert instr.probe_type == "High Sensitivity"
        assert instr.probe_type == "Ultra-High Sensitivity"


def test_field_control_enabled():
    with expected_protocol(
        LakeShore475,
        [("CMODE 0", None),
         ("CMODE?", "1")],
    ) as instr:
        instr.field_control_enabled = False
        assert instr.field_control_enabled is True


def test_field_setpoint():
    with expected_protocol(
        LakeShore475,
        [("CSETP 0.3", None),
         ("CSETP?", "2000")],
    ) as instr:
        instr.field_setpoint = 0.3
        assert instr.field_setpoint == 2000

