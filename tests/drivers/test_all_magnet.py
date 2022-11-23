"""
This file is part of the SpynWave package.
"""


import pytest

from spynwave import drivers
from spynwave.drivers.magnet_base import MagnetBase
from spynwave.drivers.magnet_lakeshore421 import LakeShore421Mixin

# Collect all magnets
magnets = []
for driver in dir(drivers):
    if driver.startswith("Magnet") and not driver == "Magnet":
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
    # TODO: maybe this is better if patched or mocked

    # prevent communication
    Cls.__init__ = MagnetBase.__init__
    Cls._set_field = staticmethod(lambda v: v)

    test_value = 0.001

    instr = Cls(mirror_fields=False)
    assert test_value == + instr.set_field(test_value)

    instr = Cls(mirror_fields=True)
    assert test_value == - instr.set_field(test_value)
