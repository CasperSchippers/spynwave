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
    parser.add_argument(
        "program",
        metavar="Program",
        nargs='?',
        action="store",
        choices=["psws", "magnet-calibration", "magcal"],
        default="PSWS",
        type=str.lower,
        help="Which program to execute, 'PSWS' or 'magnet-calibration' (or 'magcal')",
    )
    parser.add_argument(
        "-s", "-setup",
        action="store",
        choices=["in-plane", "out-of-plane", "cryo", "auto-detect"],
        default="auto-detect",
        help="Which setup (magnet) to use: 'in-plane', 'out-of-plane', or 'cryo' (black-hole); if"
             "'auto-detect', the software will automatically detect which magnet to use.",
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    if args.program.lower() == "psws":
        log.info("Starting PSWS program")
        from spynwave.interface import PSWSWindow as Window
    elif args.program in ("magnet-calibration", "magcal"):
        log.info("Starting magnet calibration program")
        from spynwave.magnet_calibration import MagnetCalibrationWindow as Window
    else:
        log.warning(f"Program {args.program} is not supported.")

    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    # Minimize console window
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
