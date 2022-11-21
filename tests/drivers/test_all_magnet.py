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
    # TODO: make this test

    # prevent communication
    Cls.__init__ = MagnetBase.__init__

    driv = Cls(mirror_fields=True)
    driv.set_field(0.001)



