"""
This file is part of the SpynWave package.
"""


import pytest
from unittest.mock import MagicMock

from spynwave import drivers

# Collect all magnets

magnets = []
for driver in dir(drivers):
    if driver.startswith("Magnet"):
        magnets.append(driver)


@pytest.mark.parametrize("cls", magnets)
def test_mirror_fields(cls):
    # TODO: make this test
    print(cls)
