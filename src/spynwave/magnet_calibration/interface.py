"""
This file is part of the SpynWave package.
"""

import os
import sys
import logging

from pyvisa import VisaIOError
from pyvisa.constants import VI_ERROR_TMO

from pymeasure.display.Qt import QtWidgets, QtCore, QtGui
from pymeasure.display.windows import ManagedWindow

from pymeasure.experiment import Results, unique_filename

from spynwave.magnet_calibration.procedure import MagnetCalibrationProcedure
from spynwave.pymeasure_patches.pandas_formatter import CSVFormatterPandas


# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class MagnetCalibrationWindow(ManagedWindow):
    def __init__(self):
        super().__init__(
            procedure_class=MagnetCalibrationProcedure,
            inputs=(
                "AB_filename_base",
                "symmetric_currents",
                "max_current",
                "min_current",
                "current_steps",
                "dwell_time",
                "number_of_sweeps",
            ),
            x_axis="Current (A)",
            y_axis="Field (T)",
            displays=(
                "min_current",
                "max_current",
                "symmetric_currents",
            ),
            sequencer=False,
            inputs_in_scrollarea=True,
            directory_input=True,
        )

        self._setup_log_widget()

        # self.update_inputs_from_vna()

        self.directory_line.setText(os.getcwd())

        self.resize(1200, 900)

    def queue(self, procedure=None):
        if procedure is None:
            procedure = self.make_procedure()

        folder = self.directory
        filename = procedure.AB_filename_base

        if procedure.symmetric_currents:
            procedure.min_current = -procedure.max_current


        procedure.set_parameters({
            "AA_folder": folder,
        })

        filename = unique_filename(
            folder,
            prefix=filename,
            ext="txt",
            datetimeformat="",
            procedure=procedure
        )

        results = Results(procedure, filename)

        # Can be changed when the CSVFormatterPandas is merged
        results.formatter = CSVFormatterPandas(
            columns=results.procedure.DATA_COLUMNS,
            delimiter=results.DELIMITER,
            line_break=results.LINE_BREAK
            )

        experiment = self.new_experiment(results)
        self.manager.queue(experiment)

    def new_curve(self, *args, **kwargs):
        curve = super().new_curve(*args, **kwargs, connect="finite")
        if curve is not None:
            curve.setSymbol("o")
            curve.setSymbolPen(curve.pen)
        return curve

    #################################################################
    # Methods below extend the ManagedWindow with custom components #
    #################################################################

    def _setup_log_widget(self):
        """ Adjust the log-widget.
        Sets the logging level to INFO, adds blinking functionality and color-coding for warning-
        and error-messages.

        """
        self.log_widget.handler.setLevel(logging.INFO)

        self._blink_qtimer = QtCore.QTimer()
        self._blink_color = None
        self._blink_state = False

        self.tabs.tabBar().setIconSize(QtCore.QSize(12, 12))

        # Connect a bunch of slots
        # For the blinking
        self._blink_qtimer.timeout.connect(self._blink)
        # For stopping the blinking
        self.tabs.tabBar().currentChanged.connect(self._blink_stop)
        # For starting the blinking
        self.log_widget.handler.connect(self._blink_log_widget)

        # Replace the message-handler to color error and warning lines
        self.log_widget.handler.connect(self._append_to_log)
        self.log_widget.handler.emitter.record.disconnect(self.log_widget.view.appendPlainText)

    def _append_to_log(self, message):
        if not ("(ERROR)" in message or "(WARNING)" in message):
            return self.log_widget.view.appendPlainText(message)

        color = "Red" if "(ERROR)" in message else "DarkOrange"

        html_message = f"<font color=\"{color}\">{message}</font>"\
            .replace("\r\n", "<br>  ")\
            .replace("\n", "<br>  ")\
            .replace("\r", "<br>  ")\
            .replace("  ", "&nbsp;&nbsp;")\
            .replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")

        return self.log_widget.view.appendHtml(html_message)

    def _blink(self):
        if self._blink_state:
            self.tabs.tabBar().setTabTextColor(
                self.tabs.indexOf(self.log_widget),
                QtGui.QColor("black")
            )
        else:
            self.tabs.tabBar().setTabTextColor(
                self.tabs.indexOf(self.log_widget),
                QtGui.QColor(self._blink_color)
            )

        self._blink_state = not self._blink_state

    def _blink_stop(self, index):
        if index == self.tabs.indexOf(self.log_widget):
            self._blink_qtimer.stop()
            self._blink_state = True
            self._blink()

            self._blink_color = None
            self.tabs.setTabIcon(self.tabs.indexOf(self.log_widget), QtGui.QIcon())

    def _blink_log_widget(self, message: str):
        if not ("(ERROR)" in message or "(WARNING)" in message):
            return

        # Check if the current tab is actually the log-tab
        if self.tabs.currentIndex() == self.tabs.indexOf(self.log_widget):
            self._blink_stop(self.tabs.currentIndex())
            return

        # Define color and icon based on severity
        # If already red, this should not be updated
        if not self._blink_color == "red":
            self._blink_color = "red" if "(ERROR)" in message else "darkorange"

            pixmapi = QtWidgets.QStyle.StandardPixmap.SP_MessageBoxCritical if \
                "(ERROR)" in message else QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning

            icon = self.style().standardIcon(pixmapi)
            self.tabs.setTabIcon(self.tabs.indexOf(self.log_widget), icon)

        # Start timer
        self._blink_qtimer.start(500)


def main():
    log.info("__main__.py")
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
