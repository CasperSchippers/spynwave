"""
This file is part of the SpynWave package.
"""

import sys
import logging
import argparse
import ctypes

from pymeasure.display.Qt import QtWidgets


# Initialize logger & log to file
log = logging.getLogger("")
log.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("SpynWave.log", "a")
file_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s : %(message)s (%(levelname)s)",
    datefmt="%m/%d/%Y %I:%M:%S %p"
))
file_handler.setLevel(logging.INFO)
log.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s : %(message)s (%(levelname)s)",
    datefmt="%m/%d/%Y %I:%M:%S %p"
))
console_handler.setLevel(logging.DEBUG)
log.addHandler(console_handler)

# Register as separate software
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("fna.MeasurementSoftware.SpynWave")


def parse_args():
    parser = argparse.ArgumentParser(
        prog='SpynWave',
        description='Measurement software for propagating spin-wave spectroscopy',
        epilog='Developed by Casper Schippers',
    )

    alt_programs = parser.add_mutually_exclusive_group()
    alt_programs.add_argument(
        "-m", "--magnet-cal",
        action="store_true",
        dest="calibrate_magnet",
        help="Run the magnet-calibration software",
    )
    alt_programs.add_argument(
        "-i", "--init",
        action="store_true",
        dest="initialize",
        help="Initialize the software after installation; creates shortcut on the desktop and "
             "places the config and calibration files in an accessible place",
    )
    # TODO: find out how to propagate this info
    # parser.add_argument(
    #     "-s", "-setup",
    #     action="store",
    #     choices=["in-plane", "out-of-plane", "cryo", "auto-detect"],
    #     default="auto-detect",
    #     help="Which setup (magnet) to use: 'in-plane', 'out-of-plane', or 'cryo' (black-hole); if"
    #          "'auto-detect', the software will automatically detect which magnet to use.",
    # )
    args = parser.parse_args()

    return args


def main():
    args = parse_args()

    if args.initialize:
        log.info("Initialize software")
        return
    elif args.calibrate_magnet:
        log.info("Starting magnet calibration program")
        from spynwave.magnet_calibration import MagnetCalibrationWindow as Window
    else:
        log.info("Starting PSWS program")
        from spynwave.interface import PSWSWindow as Window

    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    # Minimize console window
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
