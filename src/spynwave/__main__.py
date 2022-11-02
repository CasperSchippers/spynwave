import os
import sys
import logging

from pymeasure.display.Qt import QtWidgets

from spynwave.interface import Window


# Initialize logger & log to file
log = logging.getLogger("")
file_handler = logging.FileHandler("SpynWave.log", "a")
file_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s : %(message)s (%(levelname)s)",
    datefmt="%m/%d/%Y %I:%M:%S %p"
))
log.addHandler(file_handler)


def main():
    log.info("__main__.py")
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
