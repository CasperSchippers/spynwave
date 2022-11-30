"""
This file is part of the SpynWave package.
"""

import logging

import numpy as np
from itertools import product

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import SequencerWidget
from pymeasure.display.inputs import ScientificInput

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class SpynWaveSequencerWidget(QtWidgets.QWidget):
    """ This class takes/copies some methods from pymeasure sequencer. """

    # TODO: is this the best way, or better to copy the code
    queue_sequence = SequencerWidget.queue_sequence
    _check_queue_signature = SequencerWidget._check_queue_signature
    _get_properties = SequencerWidget._get_properties

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        self._check_queue_signature()

        self._inputs = self._parent.displays
        self._get_properties()  # TODO: is it useful to make a get/check function?
        self._setup_ui()
        self._layout()

    def _setup_ui(self):
        self.repeats_spinbox = QtWidgets.QSpinBox()
        self.repeats_spinbox.setMinimum(1)

        self.paramscan_checkbox = QtWidgets.QCheckBox()
        self.paramscan_checkbox.setTristate(False)
        self.paramscan_checkbox.stateChanged.connect(self.toggle_tabwidget)

        self.mirrored_checkbox = QtWidgets.QCheckBox()
        self.mirrored_checkbox.setTristate(False)

        self.field_inputs = SweepInputPanel(self._parent.procedure_class,
                                            "field", "frequency",
                                            "rf_frequency")
        self.frequency_inputs = SweepInputPanel(self._parent.procedure_class,
                                                "frequency", "field",
                                                "magnetic_field")
        # self.time_inputs = InputPanel()

        self.queue_button = QtWidgets.QPushButton("Queue sequence")
        self.queue_button.clicked.connect(self.queue_sequence)

    def _layout(self):
        time_tab = QtWidgets.QLabel("Time")

        self.pane_order = ["Field sweep", "Frequency sweep"]  # "Time sweep"

        self.pane_widget = QtWidgets.QTabWidget()
        self.pane_widget.setContentsMargins(0, 0, 0, 0)
        self.pane_widget.setStyleSheet("QTabWidget::pane { border: 0; }")
        self.pane_widget.tabBar().setVisible(False)
        self.pane_widget.addTab(self.field_inputs, "Field sweep")
        self.pane_widget.addTab(self.frequency_inputs, "Frequency sweep")
        self.pane_widget.addTab(time_tab, "Time sweep")

        self.toggle_tabwidget(self.paramscan_checkbox.checkState())

        form = QtWidgets.QFormLayout()
        form.addRow("Scan parameter", self.paramscan_checkbox)
        form.addRow("Mirrored fields", self.mirrored_checkbox)
        form.addRow("Repeats", self.repeats_spinbox)

        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addLayout(form, 10)
        btn_box.addStretch(1)
        btn_box.addWidget(self.queue_button, 10)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(6)
        vbox.addWidget(self.pane_widget)
        vbox.addLayout(btn_box)
        self.setLayout(vbox)

    def set_pane_focus(self, pane_name):
        if pane_name in self.pane_order:
            index = self.pane_order.index(pane_name)
            self.pane_widget.setCurrentIndex(index)
            self.pane_widget.setVisible(True)
        else:
            self.pane_widget.setVisible(False)

    def toggle_tabwidget(self, state):
        self.pane_widget.setEnabled(state == 2)

    def update_dc_inputs(self, *args):
        for idx in range(self.pane_widget.count()):
            wdg = self.pane_widget.widget(idx)
            if hasattr(wdg, "dc_toggle_enabled"):
                wdg.dc_toggle_enabled(*args)

    def update_dc_label(self, *args):
        for idx in range(self.pane_widget.count()):
            wdg = self.pane_widget.widget(idx)
            if hasattr(wdg, "dc_update_label"):
                wdg.dc_update_label(*args)

    def get_sequence(self):
        """ Generate the sequence from the entered parameters. Returns a list of tuples; each tuple
        represents one measurement, containing dicts with the parameters for that measurement. This
        format is dictated by the queue_sequence method from the SequenceWidget.
        """

        sequence = [tuple()]

        if self.pane_widget.isVisible() and self.paramscan_checkbox.checkState() == 2:
            if hasattr(self.pane_widget.currentWidget(), "get_sequence"):
                sequence = self.pane_widget.currentWidget().get_sequence()

        if self.mirrored_checkbox.checkState() == 2:
            sequence = [
                seq + ({"mirrored_field": val}, ) for val, seq in product([False, True], sequence)
            ]

        # Apply repeats
        repeats = self.repeats_spinbox.value()
        sequence = [s for s in sequence for _ in range(repeats)]

        return sequence

    def get_sequence_from_tree(self):
        """ Method to implement to comply with other methods of the sequencer widget and with the
        estimator widget. Wraps around create_sequence.
        """
        return self.get_sequence()


SAFE_FUNCTIONS = {
    'range': range,
    'sorted': sorted,
    'list': list,
    'arange': np.arange,
    'linspace': np.linspace,
    'arccos': np.arccos,
    'arcsin': np.arcsin,
    'arctan': np.arctan,
    'arctan2': np.arctan2,
    'ceil': np.ceil,
    'cos': np.cos,
    'cosh': np.cosh,
    'degrees': np.degrees,
    'e': np.e,
    'exp': np.exp,
    'fabs': np.fabs,
    'floor': np.floor,
    'fmod': np.fmod,
    'frexp': np.frexp,
    'hypot': np.hypot,
    'ldexp': np.ldexp,
    'log': np.log,
    'log10': np.log10,
    'modf': np.modf,
    'pi': np.pi,
    'power': np.power,
    'radians': np.radians,
    'sin': np.sin,
    'sinh': np.sinh,
    'sqrt': np.sqrt,
    'tan': np.tan,
    'tanh': np.tanh,
}


class SequenceEvaluationException(Exception):
    """Raised when the evaluation of a sequence string goes wrong."""
    pass


class SweepInputPanel(QtWidgets.QWidget):
    dc_param = "dc_voltage"

    def __init__(self, procedure, sweep_name, param_name,
                 param_class_name):
        self.procedure = procedure
        self.sweep_name = sweep_name
        self.param_name = param_name
        self.param_class_name = param_class_name

        super().__init__()

        self._setup_ui()
        self._layout()

    def _setup_ui(self):
        param_class = getattr(self.procedure, self.param_class_name)
        start_class = getattr(self.procedure, self.sweep_name + "_start")
        stop_class = getattr(self.procedure, self.sweep_name + "_end")

        self.first_param = ScientificInput(param_class)
        self.final_param = ScientificInput(param_class)

        self.first_start = ScientificInput(start_class)
        self.first_stop = ScientificInput(stop_class)
        self.final_start = ScientificInput(start_class)
        self.final_stop = ScientificInput(stop_class)

        self.interp_box = QtWidgets.QComboBox()
        self.interp_box.addItem("Linear")

        self.steps_box = QtWidgets.QSpinBox()
        self.steps_box.setMinimum(2)
        self.steps_box.setSuffix(" steps")

        self.dc_line = QtWidgets.QLineEdit()
        self.dc_label = QtWidgets.QLabel("V")

    def _layout(self):
        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_row = QtWidgets.QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.addWidget(QtWidgets.QLabel(self.param_name.capitalize()))
        header_row.addSpacing(10)
        header_row.addWidget(QtWidgets.QLabel(f"Start {self.sweep_name}"))
        header_row.addWidget(QtWidgets.QLabel(f"Stop {self.sweep_name}"))

        first_row = QtWidgets.QHBoxLayout()
        first_row.setContentsMargins(0, 0, 0, 0)
        first_row.addWidget(self.first_param)
        first_row.addSpacing(10)
        first_row.addWidget(self.first_start)
        first_row.addWidget(self.first_stop)

        final_row = QtWidgets.QHBoxLayout()
        final_row.setContentsMargins(0, 0, 0, 0)
        final_row.addWidget(self.final_param)
        final_row.addSpacing(10)
        final_row.addWidget(self.final_start)
        final_row.addWidget(self.final_stop)

        interp_row = QtWidgets.QHBoxLayout()
        interp_row.setContentsMargins(0, 0, 0, 0)
        interp_row.addStretch(1)
        # hbox.addWidget(self.interp_box)
        interp_row.addWidget(QtWidgets.QLabel("Linear in"))
        interp_row.addWidget(self.steps_box)
        interp_row.addStretch(2)

        dc_row = QtWidgets.QHBoxLayout()
        dc_row.setContentsMargins(0, 0, 0, 0)
        dc_row.addWidget(self.dc_line)
        dc_row.addWidget(self.dc_label)

        layout.addRow(" ", header_row)
        layout.addRow("First", first_row)
        layout.addRow(" ", interp_row)
        layout.addRow("Last", final_row)
        layout.addRow("DC", dc_row)

    def dc_toggle_enabled(self, state):
        self.dc_line.setEnabled(state)
        self.dc_label.setEnabled(state)

    def dc_update_label(self, regulate):
        self.dc_param = "dc_" + regulate.lower()
        self.dc_label.setText("V" if self.dc_param == "dc_voltage" else "mA")

    def get_sequence(self):
        param_first = self.first_param.value()
        first_start = self.first_start.value()
        first_stop = self.first_stop.value()
        param_final = self.final_param.value()
        final_start = self.final_start.value()
        final_stop = self.final_stop.value()

        interpolation = self.interp_box.currentText()
        steps = self.steps_box.value()

        if interpolation == "Linear":
            param_list = np.linspace(param_first, param_final, steps)
            start_list = np.linspace(first_start, final_start, steps)
            stop_list = np.linspace(first_stop, final_stop, steps)
        else:
            raise NotImplementedError(f"Interpolation method {interpolation} not implemented.")

        dc_list = self.get_dc_sequence()

        param_step = abs(param_list[1] - param_list[0])

        sequence = []
        for dc_value in dc_list:
            for param, start, stop in zip(param_list, start_list, stop_list):
                param_set = (
                    {self.param_class_name: param},
                    {self.sweep_name + "_start": start},
                    {self.sweep_name + "_end": stop},
                    {self.param_name + "_start": param_first},
                    {self.param_name + "_end": param_final},
                    ({self.param_name + "_step": param_step} if  # Quick and dirty fix
                        not self.param_name == "field" else
                        {self.param_name + "_ramp_rate": param_step * 10})
                )

                if dc_value is not None:
                    param_set += ({self.dc_param: dc_value}, )

                sequence.append(param_set)

        return sequence

    def get_dc_sequence(self):
        string = self.dc_line.text()
        values = [None]

        if len(string) > 0:
            try:
                values = self.eval_string(string)
            except SequenceEvaluationException:
                pass

        return values

    # Method taken from the pymeasure sequencer, copied to prevent future issues
    @staticmethod
    def eval_string(string):
        """
        Evaluate the given string. The string is evaluated using a list of
        pre-defined functions that are deemed safe to use, to prevent the
        execution of malicious code. For this purpose, also any built-in
        functions or global variables are not available.

        :param string: String to be interpreted.
        """

        evaluated_string = None
        if len(string) > 0:
            try:
                evaluated_string = eval(
                    string, {"__builtins__": None}, SAFE_FUNCTIONS
                )
            except TypeError as exc:
                log.warning(f"TypeError, likely a typo in one of the functions: {exc}")
                raise SequenceEvaluationException()
            except SyntaxError as exc:
                log.warning(f"SyntaxError, likely unbalanced brackets: {exc}")
                raise SequenceEvaluationException()
            except ValueError as exc:
                log.warning(f"ValueError, likely wrong function argument: {exc}")
                raise SequenceEvaluationException()
        else:
            log.warning("No sequence entered")
            raise SequenceEvaluationException("No sequence entered")

        evaluated_string = np.array(evaluated_string)
        return evaluated_string
