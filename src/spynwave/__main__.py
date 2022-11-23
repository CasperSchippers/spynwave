"""
This file is part of the SpynWave package.
"""

import sys
import logging

from pymeasure.display.Qt import QtWidgets
from pymeasure.log import setup_logging

from spynwave.interface import Window


# Initialize logger & log to file


log = logging.getLogger("")

file_handler = logging.FileHandler("SpynWave.log", "a")
file_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s : %(message)s (%(levelname)s)",
    datefmt="%m/%d/%Y %I:%M:%S %p"
))
log.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s : %(message)s (%(levelname)s)",
    datefmt="%m/%d/%Y %I:%M:%S %p"
))
console_handler.setLevel(logging.DEBUG)
log.addHandler(console_handler)


def main():
    log.info("__main__.py")
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
