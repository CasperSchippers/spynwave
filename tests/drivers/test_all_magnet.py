"""
This file is part of the SpynWave package.
"""


import pytest
from unittest.mock import MagicMock

from spynwave import drivers
from spynwave.drivers.magnet_base import MagnetBase

# Collect all magnets

magnets = []
for driver in dir(drivers):
    if driver.startswith("Magnet"):
        Cls = getattr(drivers, driver)
        if issubclass(Cls, MagnetBase):
            magnets.append(Cls)


@pytest.mark.parametrize("Cls", magnets)
def test_mirror_fields(Cls):
    # TODO: maybe this is better if patched or mocked

    # prevent communication
    Cls.__init__ = MagnetBase.__init__
    Cls._set_current = staticmethod(lambda v: True)
    Cls._ramp_current = staticmethod(lambda v: True)

    test_value = 0.001

    instr = Cls(mirror_fields=False)
    assert test_value == + instr.set_field(test_value)

    instr = Cls(mirror_fields=True)
    assert test_value == - instr.set_field(test_value)



