"""
This file is part of the SpynWave package.
"""

import logging
import queue
from time import time, sleep
import numpy as np

from spynwave.drivers import InstrumentThread

# Setup logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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

        last_time = 0

        while not self.should_stop():
            if (sleeptime := -(time() - last_time - self.instrument.measurement_delay)) > 0:
                sleep(sleeptime)

            last_time = time()
            field = self.instrument.measure_field()

            field = np.round(field, 10)  # rounding to remove float-rounding-errors
            self.put_datapoint({"Field (T)": field})

        log.info("Gauss probe Thread: stopped measuring")


class VNAControlThread(InstrumentThread):
    def run(self):
        # try:
        #     # Obtain lock to prevent other communication with VNA
        #     self.instrument.vectorstar.adapter.connection.lock_excl()

        self.instrument.trigger_measurement()

        log.info("VNA control Thread: started & locked & triggered measurement")

        sleep(self.settings['delay'])

        first_datapoint = True

        while not self.should_stop():
            if self.instrument.measurement_done():
                data = self.instrument.grab_data(CW_mode=True, headerless=True)

                if not first_datapoint:
                    self.put_datapoint(data)
                else:
                    first_datapoint = False

                if not self.should_stop():
                    self.instrument.trigger_measurement()

            sleep(self.settings['delay'])

        # finally:
        #     pass
            # Release lock of VNA
            # self.instrument.vectorstar.adapter.connection.unlock()

        log.info("VNA control Thread: stopped")
