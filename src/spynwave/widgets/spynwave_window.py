"""
This file is part of the SpynWave package.
"""

import os
import logging
import ctypes

from pymeasure.display.Qt import QtWidgets, QtCore, QtGui
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment.parameters import Parameter
from pymeasure.display.inputs import IntegerInput, ListInput, ScientificInput

from spynwave.widgets import SpynWaveSequencerWidget


# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())

# Register as separate software
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("fna.MeasurementSoftware.SpynWave")


class SpynWaveWindowBase(ManagedWindow):
    def __init__(self, *args, filename_input=True, **kwargs):
        self.filename_input = filename_input

        kwargs.setdefault("inputs_in_scrollarea", True)
        kwargs.setdefault("directory_input", True)

        super().__init__(*args, **kwargs)

        # Ensure the normal plot-widget is always the first tab and open on start
        if (number_of_tabs := len(self.widget_list)) > 2:
            self.tabs.tabBar().moveTab(number_of_tabs - 2, 0)
            self.tabs.setCurrentIndex(0)

        self._setup_log_widget()
        self.directory_line.setText(os.getcwd())
        self.resize(1200, 900)

        # Minimize console window
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)

    def new_curve(self, *args, **kwargs):
        curve = super().new_curve(*args, **kwargs, connect="finite")

        if curve is not None:
            if isinstance(curve, (list, tuple)):
                for c in curve:
                    c.setSymbol("o")
                    c.setSymbolPen(c.pen)
            else:
                curve.setSymbol("o")
                curve.setSymbolPen(curve.pen)

        return curve

    def _setup_ui(self):
        """ Re-implementation of the _setup_ui method to include customization.
        This includes a customized sequencer, a changed inputs-widget layout, a filename-input
        """
        if use_sequencer := self.use_sequencer:
            self.sequencer = SpynWaveSequencerWidget(parent=self)

        # Temporarily disable the use-sequencer, such that no new sequencer-widget is instantiated
        self.use_sequencer = False
        super()._setup_ui()
        self.use_sequencer = use_sequencer

        # Link the measurement-type drop-box to the visible pane
        if self.use_sequencer:
            self.inputs.measurement_type.currentTextChanged.connect(self.sequencer.set_pane_focus)
            self.sequencer.set_pane_focus(self.inputs.measurement_type.currentText())

        # Update the layout of the inputs widget
        self._change_layout_inputs()

        if self.filename_input:
            filename_name = "Filename"
            filename_default = "Data"

            # Search for an input with
            for key in self.procedure_class.__dict__.keys():
                if "filename" in key and type(getattr(self.procedure_class, key)) == Parameter:
                    filename_name = getattr(self.procedure_class, key).name
                    filename_default = getattr(self.procedure_class, key).default
                    break

            self.filename_label = QtWidgets.QLabel(self)
            self.filename_label.setText(filename_name)
            self.filename_line = QtWidgets.QLineEdit(parent=self)
            self.filename_line.setText(filename_default)

    def _layout(self):
        """ Re-implementation of the _layout method to include customization.
        Includes placement of the filename-input
        """
        super()._layout()

        if self.filename_input:
            vbox = self.directory_label.parent().layout()
            vbox.insertWidget(1, self.filename_label)
            vbox.insertWidget(2, self.filename_line)


    @property
    def filename(self):
        if not self.filename_input:
            raise ValueError("No directory input in the ManagedWindow")
        return self.filename_line.text()

    def _change_layout_inputs(self):
        old_layout = self.inputs.layout()

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        for name in self.inputs._inputs:
            widget = getattr(self.inputs, name)

            # Remove from old layout
            old_layout.removeWidget(widget)

            if name in self.inputs.labels:
                label = self.inputs.labels[name]

                # Remove from old layout
                old_layout.removeWidget(label)

                if isinstance(widget, (IntegerInput, ScientificInput, ListInput, )):
                    sublayout = QtWidgets.QHBoxLayout()
                    sublayout.setContentsMargins(0, 0, 0, 0)
                    sublayout.addWidget(label)
                    sublayout.addWidget(widget)
                    layout.addLayout(sublayout)
                else:
                    layout.addWidget(label)
                    layout.addWidget(widget)
            else:
                layout.addWidget(widget)

        # Remove the old layout
        QtCore.QObjectCleanupHandler().add(old_layout)

        self.inputs.setLayout(layout)

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
