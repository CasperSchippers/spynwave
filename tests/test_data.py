"""
This file is part of the SpynWave package.
"""

from spynwave.constants import look_for_file


def test_data_folder():
    file = look_for_file("config.yaml")
    print(file)
    file = look_for_file("magnet_calibration_in_plane.txt")
    print(file)
