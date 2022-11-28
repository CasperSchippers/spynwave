"""
This file is part of the SpynWave package.
"""


import pytest
from unittest.mock import MagicMock

from spynwave import drivers
from spynwave.drivers.magnet_base import MagnetBase
from spynwave.drivers.magnet_lakeshore421 import LakeShore421Mixin

# Collect all magnets
magnets = []
for driver in dir(drivers):
    if driver.startswith("Magnet") and driver not in ["Magnet", "MagnetBase"]:
        Driver = getattr(drivers, driver)
        if issubclass(Driver, MagnetBase):
            magnets.append(Driver)


@pytest.mark.parametrize("Cls", magnets)
def test_overridden_methods(Cls):
    not_overridable_methods = ["set_field"]

    for method in not_overridable_methods:
        assert getattr(Cls, method) == getattr(MagnetBase, method), \
            f"method {method} should not be overridden."

    if issubclass(Cls, LakeShore421Mixin):
        not_overridable_methods = [
            "startup_lakeshore", "_gauss_meter_set_fast_mode", "measure_field", "measurement_delay",
        ]
        for method in not_overridable_methods:
            assert getattr(Cls, method) == getattr(LakeShore421Mixin, method), \
                f"method {method} should not be overridden."


@pytest.mark.parametrize("Cls", magnets)
def test_mirror_fields(Cls):

    test_value = 0.001

    # prevent communication
    Cls.__init__ = MagnetBase.__init__

    # Test non-mirrored field
    instr = Cls(mirror_fields=False)
    instr._set_field = MagicMock(return_value=(+test_value, +10 * test_value))
    assert instr.set_field(test_value) == (+test_value, +10 * test_value)
    instr._set_field.assert_called_with(+test_value)

    # Test mirrored field
    instr = Cls(mirror_fields=True)
    instr._set_field = MagicMock(return_value=(-test_value, -10 * test_value))
    assert instr.set_field(test_value) == (-test_value, -10 * test_value)
    instr._set_field.assert_called_with(-test_value)
