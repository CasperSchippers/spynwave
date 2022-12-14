"""
This file is part of the SpynWave package.
"""

import sys
import logging
import argparse

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


def parse_args():
    parser = argparse.ArgumentParser(
        prog='SpynWave',
        description='Measurement software for propagating spin-wave spectroscopy',
        epilog='Developed by Casper Schippers',
    )

    alt_programs = parser.add_mutually_exclusive_group()
    alt_programs.add_argument(
        "-M", "--magnet-cal",
        action="store_true",
        dest="calibrate_magnet",
        help="Run the magnet-calibration software",
    )
    alt_programs.add_argument(
        "-I", "--init",
        action="store_true",
        # nargs="?",
        # default="green",
        dest="initialize",
        help="Initialize the software after installation; creates shortcut on the desktop and "
             "places the config and calibration files in an accessible place",
    )

    # TODO: future option
    # alt_programs.add_argument(
    #     "-U", "--update",
    #     action="store_true",
    #     dest="update",
    #     help="Update the software by pulling a new version from the gitlab server",
    # )

    # TODO: future option / is this useful?
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
        from spynwave.initialization import initialize_measurement_software
        return initialize_measurement_software()
    elif args.calibrate_magnet:
        log.info("Starting magnet calibration program")
        from spynwave.magnet_calibration import MagnetCalibrationWindow as Window
    else:
        log.info("Starting PSWS program")
        from spynwave.interface import PSWSWindow as Window

    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
