"""
This file is part of the SpynWave package.
"""
import logging
import queue
from time import time, sleep
import numpy as np

from pymeasure.experiment import (
    Procedure, Parameter, FloatParameter, BooleanParameter,
    IntegerParameter, ListParameter, Metadata
)

from spynwave.drivers import InstrumentThread

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MixinFieldSweep:
    # TODO: see if we can update the field-limits/etc to the setup?
    field_start = FloatParameter(
        "Start field",
        default=0.,
        minimum=-0.660,
        maximum=+0.660,
        units="T",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_stop = FloatParameter(
        "Stop field",
        default=0.2,
        minimum=-0.660,
        maximum=+0.660,
        units="T",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_ramp_rate = FloatParameter(
        "Field sweep rate",
        default=0.005,
        minimum=0.,
        maximum=1.,
        units="T/s",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    # TODO: implement mirrored fields to generate a second measurement
    field_include_mirrored = BooleanParameter(
        "Include mirrored fields",
        default=False,
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_saturation_field = FloatParameter(
        "Saturation field",
        default=0.2,
        minimum=-0.660,
        maximum=+0.660,
        units="T",
        group_by="measurement_type",
        group_condition="Field sweep",
    )
    field_saturation_time = FloatParameter(
        "Saturation ",
        default=2,
        minimum=0,
        maximum=120,
        units="s",
        group_by="measurement_type",
        group_condition="Field sweep",
    )

    field_sweep_thread = None
    gauss_probe_thread = None
    vna_control_thread = None

    def startup_field_sweep(self):
        self.saturate_field()
        self.vna.prepare_cw_sweep(cw_frequency=self.rf_frequency)
        self.magnet.wait_for_stable_field(timeout=60, should_stop=self.should_stop)

        # Prepare the parallel methods for the sweep
        self.field_sweep_thread = FieldSweepThread(self, self.magnet, settings=dict(
            field_start=self.field_start,
            field_stop=self.field_stop,
            field_ramp_rate=self.field_ramp_rate,
            publish_data=False,
        ))
        self.gauss_probe_thread = GaussProbeThread(self, self.magnet, settings=dict(
            update_rate=0.05,
        ))
        self.vna_control_thread = VNAControlThread(self, self.vna, settings=dict(
            delay=0.001,
        ))

    def execute_field_sweep(self):
        self.field_sweep_thread.start()
        self.gauss_probe_thread.start()
        self.vna_control_thread.start()

        while not self.should_stop() and not self.field_sweep_thread.is_finished():
            if self.gauss_probe_thread.data_queue.empty():
                self.sleep(0.05)
                continue

            _, field = self.gauss_probe_thread.data_queue.get()

            data = {
                "Timestamp (s)": time(),
                "Field (T)": field,
                "Frequency (Hz)": self.rf_frequency,
            }

            self.emit("results", data)

        self.field_sweep_thread.stop()
        self.gauss_probe_thread.stop()
        self.vna_control_thread.stop()

    def shutdown_field_sweep(self):
        if self.field_sweep_thread is not None:
            try:
                self.field_sweep_thread.join(2)
            except RuntimeError as e:
                log.error(e)

        if self.gauss_probe_thread is not None:
            try:
                self.gauss_probe_thread.join(2)
            except RuntimeError as e:
                log.error(e)

        if self.vna_control_thread is not None:
            try:
                self.vna_control_thread.join(2)
            except RuntimeError as e:
                log.error(e)

    ####################
    # Helper functions #
    ####################

    def saturate_field(self):
        # Saturate the magnetic field (after saturation, go already to the starting field
        self.magnet.set_field(self.field_saturation_field)
        self.sleep(self.field_saturation_time)
        self.magnet.set_field(self.field_start)

    def parallel_cw_measurement(self):
        pass


class FieldSweepThread(InstrumentThread):
    def run(self):
        log.info("Field sweep Thread: start sweeping.")

        self.instrument.sweep_field(
            self.settings["field_start"],
            self.settings["field_stop"],
            self.settings["field_ramp_rate"],
            should_stop=self.should_stop,
            callback_fn=self.field_callback,
        )

        self.finished()
        log.info("Field sweep Thread: finished sweeping.")

    def field_callback(self, field):
        field = np.round(field, 10)  # rounding to remove float-rounding-errors
        progress = abs((field - self.settings["field_start"]) /
                       (self.settings["field_stop"] - self.settings["field_start"])) * 100

        if self.settings["publish_data"]:
            try:
                self.data_queue.put_nowait((time, field, progress))
            except queue.Full:
                log.warning("Field sweep Thread: data-queue is full, continuing without "
                            "putting field-data to the queue.")

        self.procedure.emit("progress", progress)


class GaussProbeThread(InstrumentThread):
    def run(self):
        log.info("Gauss probe Thread: start measuring")

        while not self.should_stop():
            field = self.instrument.measure_field()
            field = np.round(field, 10)  # rounding to remove float-rounding-errors
            self.data_queue.put((time(), field))
            sleep(self.settings["update_rate"])

        log.info("Gauss probe Thread: stopped measuring")


class VNAControlThread(InstrumentThread):
    def run(self):
        log.info("VNA control Thread: started & triggered measurement")
        self.instrument.trigger_measurement()
        sleep(self.settings['delay'])

        while not self.should_stop():
            if self.instrument.measurement_done():
                data = self.instrument.grab_data(CW_mode=True)
                self.data_queue.put((time, data))

                if not self.should_stop():
                    self.instrument.trigger_measurement()

            sleep(self.settings['delay'])
        log.info("VNA control Thread: started")
