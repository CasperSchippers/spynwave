"""
This file is part of the SpynWave package.
"""

import logging
import queue
from time import time, sleep
import numpy as np
from pyvisa import VisaIOError
from pyvisa.constants import VI_ERROR_TMO

from spynwave.drivers import InstrumentThread

# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class FieldSweepThread(InstrumentThread):
    def run(self):
        log.info("Field sweep Thread: start sweeping.")
        try:
            self.instrument.sweep_field(
                self.settings["start"],
                self.settings["stop"],
                self.settings["ramp_rate"],
                should_stop=self.should_stop,
                callback_fn=self.callback,
            )
        except Exception as exc:
            log.error(exc)
            raise exc
        finally:
            self.finished()

        log.info("Field sweep Thread: finished sweeping.")

    def callback(self, field):
        field = np.round(field, 10)  # rounding to remove float-rounding-errors
        progress = abs((field - self.settings["start"]) /
                       (self.settings["stop"] - self.settings["start"])) * 100

        if self.settings["publish_data"]:
            try:
                self.data_queue.put_nowait((time, {"Field (T)": field}))
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
            try:
                field = self.instrument.measure_field()
            except VisaIOError as exc:
                if not exc.error_code == VI_ERROR_TMO:
                    raise exc
                continue

            field = np.round(field, 10)  # rounding to remove float-rounding-errors
            self.put_datapoint({"Field (T)": field})

        log.info("Gauss probe Thread: stopped measuring")


class DCSweepThread(InstrumentThread):
    def run(self):
        log.info("Source-meter sweep Thread: start sweeping")

        try:
            self.instrument.sweep(
                self.settings["start"],
                self.settings["stop"],
                self.settings["ramp_rate"],
                regulate=self.settings["regulate"],
                should_stop=self.should_stop,
                callback_fn=self.callback,
            )
        except Exception as exc:
            log.error(exc)
            raise exc
        finally:
            self.finished()

        log.info("Source-meter sweep Thread: stopped sweeping")

    def callback(self, value, data):
        progress = abs((value - self.settings["start"]) /
                       (self.settings["stop"] - self.settings["start"])) * 100

        if self.settings["publish_data"]:
            data["DC resistance (ohm)"] = data["DC voltage (V)"] / data["DC current (A)"]
            self.put_datapoint(data)

        self.procedure.emit("progress", progress)


class SourceMeterThread(InstrumentThread):
    def run(self):
        log.info("Source-meter Thread: start measuring")

        while not self.should_stop():
            try:
                data = self.instrument.measure()
            except VisaIOError as exc:
                if not exc.error_code == VI_ERROR_TMO:
                    raise exc
                continue

            self.put_datapoint(data)

            sleep(self.settings['delay'])

        log.info("Source-meter Thread: stopped measuring")


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
