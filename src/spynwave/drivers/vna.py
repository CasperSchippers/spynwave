"""
This file is part of the SpynWave package.
"""
import logging
import struct
from time import sleep
from io import StringIO

import pandas as pd
import nidaqmx.constants
import nidaqmx
import pyvisa.constants

from spynwave.constants import config

# TODO: should be contributed to pymeasure
from spynwave.pymeasure_patches.anritsuMS4644B import AnritsuMS4644B

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class VNA:
    vectorstar = None
    trigger_task = None
    counter_task = None
    counter_task_reference = 0

    cached_average_count = 0
    cached_measurement_port = "2-port"

    def __init__(self, use_DAQmx=None, **kwargs):

        self.vectorstar = self.connect_vectorstar(**kwargs)

        if use_DAQmx is not None:
            self.use_DAQmx = use_DAQmx
        else:
            self.use_DAQmx = config["vna"]["vectorstar"]["use daqmx trigger"]

        if self.use_DAQmx:
            try:
                self.trigger_task = nidaqmx.Task("Trigger task")
                self.trigger_task.do_channels.add_do_chan(config['vna']['daqmx']["trigger line"])
                self.trigger_task.write(False)

                self.counter_task = nidaqmx.Task("Counter task")
                channel = self.counter_task.ci_channels.add_ci_count_edges_chan(
                    config['vna']['daqmx']["counter channel"], edge=nidaqmx.constants.Edge.FALLING)
                channel.ci_count_edges_term = config['vna']['daqmx']["counter edge"]
                self.counter_task.start()

                self.daqmx_update_reference_count()

            except Exception as exc:
                if not (isinstance(exc, nidaqmx.errors.DaqError) and
                        str(exc).startswith("Device cannot be accessed.")):
                    self.shutdown_daqmx()
                    raise exc
                log.info("Could not find DAQmx, attemping measurement without it.")
                self.use_DAQmx = False

    @staticmethod
    def connect_vectorstar(**kwargs):
        vectorstar = AnritsuMS4644B(
            config['general']['visa-prefix'] + config['vna']['vectorstar']['address'],
            **kwargs
        )

        return vectorstar

    def startup(self, reset=False):
        # self.id
        if reset:
            self.vectorstar.reset()

        # *ESE 60: enables command, execution, query, and device errors in event status register
        self.vectorstar.event_status_enable_bits = 60
        # *SRE 48: enables message available, standard event bits in the status byte
        self.vectorstar.service_request_enable_bits = 48
        self.vectorstar.clear()
        self.vectorstar.binary_data_byte_order = "NORM"

        # 1B: DAQmx series create counter and trigger task
        #     TODO: Uitzoeken hoe dit werkt

        # Configure single active channel for transmission/reflection measurements
        self.vectorstar.number_of_channels = 1
        self.vectorstar.active_channel = 1
        self.vectorstar.ch_1.application_type = "TRAN"

        self.vectorstar.ch_1.hold_function = "CONT"

        # self.vectorstar.data_drawing_enabled = False

        # self.vectorstar.ch_1.frequency_start
        # self.vectorstar.ch_1.frequency_stop
        # self.vectorstar.ch_1.bandwidth
        # self.vectorstar.ch_1.pt_1.power_level

    def set_measurement_ports(self, measurement_ports):
        self.cached_measurement_port = measurement_ports

        if measurement_ports == "2-port":
            self.vectorstar.ch_1.number_of_traces = 4
            self.vectorstar.ch_1.display_layout = "R2C2"
            self.vectorstar.ch_1.tr_1.measurement_parameter = "S11"
            self.vectorstar.ch_1.tr_2.measurement_parameter = "S12"
            self.vectorstar.ch_1.tr_3.measurement_parameter = "S21"
            self.vectorstar.ch_1.tr_4.measurement_parameter = "S22"

        else:  # 1-port measurement
            self.vectorstar.ch_1.number_of_traces = 1
            self.vectorstar.ch_1.display_layout = "R1C1"
            self.vectorstar.ch_1.tr_1.measurement_parameter = measurement_ports[-3:]

        self.vectorstar.check_errors()

    def general_measurement_settings(self, power_level, bandwidth):
        self.vectorstar.bandwidth_enhancer_enabled = True
        self.vectorstar.ch_1.bandwidth = bandwidth

        self.vectorstar.ch_1.pt_1.power_level = power_level

        self.vectorstar.check_errors()

    def configure_averaging(self, enabled, average_count=None, averaging_type=None):
        self.vectorstar.ch_1.averaging_enabled = enabled
        if enabled:
            if average_count is not None:
                self.vectorstar.ch_1.average_count = average_count
            if averaging_type is not None:
                self.vectorstar.ch_1.average_type = {
                    "point-by-point": "POIN",
                    "sweep-by-sweep": "SWE",
                }[averaging_type]

        self.vectorstar.check_errors()

    def configure_external_trigger(self):
        if self.use_DAQmx:
            # Configure trigger for external (DAQmx) trigger
            self.vectorstar.trigger_source = "EXT"
            self.vectorstar.external_trigger_type = "CHAN"
            self.vectorstar.external_trigger_delay = 0
            self.vectorstar.external_trigger_edge = "POS"
            self.vectorstar.external_trigger_handshake = True
        else:
            self.vectorstar.trigger_source = "REM"
            self.vectorstar.remote_trigger_type = "CHAN"

        self.vectorstar.check_errors()

    def configure_internal_trigger(self):
        self.vectorstar.trigger_source = "AUTO"

        self.vectorstar.check_errors()

    def reset_to_measure(self):
        self.vectorstar.ch_1.tr_1.activate()
        self.vectorstar.ch_1.clear_average_count()

        # Prepare internals of class for measurement
        if self.use_DAQmx:
            self.daqmx_update_reference_count()
        self.cached_average_count = self.vectorstar.ch_1.average_count

        self.vectorstar.clear()

        self.vectorstar.check_errors()

    def prepare_cw_sweep(self, cw_frequency, headerless=False):
        self.vectorstar.ch_1.cw_mode_enabled = True
        self.vectorstar.ch_1.frequency_CW = cw_frequency
        self.vectorstar.ch_1.cw_number_of_points = 1

        if self.use_DAQmx:
            self.configure_averaging(False)
            self.configure_external_trigger()
        else:
            self.configure_averaging(True, 1, "sweep-by-sweep")
            self.configure_internal_trigger()

        if headerless:
            self.vectorstar.datablock_header_format = 2
            self.vectorstar.datablock_numeric_format = "8byte"

        self.vectorstar.check_errors()

    def prepare_frequency_sweep(self, frequency_start, frequency_stop, frequency_stepsize):
        self.vectorstar.ch_1.cw_mode_enabled = False

        frequency_span = frequency_stop - frequency_start
        frequency_points = int(round(frequency_span / frequency_stepsize))

        self.vectorstar.ch_1.frequency_start = frequency_start
        self.vectorstar.ch_1.frequency_stop = frequency_stop
        self.vectorstar.ch_1.number_of_points = frequency_points

        self.configure_internal_trigger()

        self.vectorstar.check_errors()

    def trigger_measurement(self):
        # TODO: check why this is not stable, especially for frequency sweeps
        log.log(0, f"Triggering measurement using {'DAQmx' if self.use_DAQmx else 'SCPI'}.")
        if self.use_DAQmx:
            self.daqmx_update_reference_count()
            self.trigger_task.write(True)
            sleep(0.05)
            self.trigger_task.write(False)
        else:
            # When nog using the DAQmx, the system "triggers" by resetting the average count
            self.reset_average_count()
            # sleep(0.01)
            # self.vectorstar.trigger_continuous()

    def reset_average_count(self):
        return self.vectorstar.ch_1.clear_average_count()

    def daqmx_update_reference_count(self):
        if not self.use_DAQmx:
            raise NotImplementedError("Method only used with DAQmx.")

        self.counter_task_reference = self.daqmx_measurement_count(False)

    def daqmx_measurement_count(self, corrected=True):
        if not self.use_DAQmx:
            raise NotImplementedError("Method only used with DAQmx.")

        count = self.counter_task.read()
        if corrected:
            return count - self.counter_task_reference
        else:
            return count

    def measurement_done(self, use_DAQmx=True):
        if self.use_DAQmx and use_DAQmx:
            return bool(self.daqmx_measurement_count())
        else:
            return self.averages_done() >= self.cached_average_count

    def averages_done(self):
        return self.vectorstar.ch_1.average_sweep_count

    def grab_data(self, CW_mode=False, **kwargs):
        if CW_mode:
            return self.grab_data_OSC(**kwargs)
        else:
            return self.grab_data_S2P()

    def grab_data_OSC(self, headerless=False):
        params = {
            "1-port: S11": ["S11"],
            "1-port: S22": ["S22"],
            "2-port": ["S11", "S21", "S12", "S22"],
        }[self.cached_measurement_port]

        command = ";".join([f"O{p}C" for p in params])
        self.vectorstar.write(command)

        number_of_traces = 4 if self.cached_measurement_port == "2-port" else 1

        data = {}

        if headerless:
            number_of_values = number_of_traces * 2
            number_of_bytes = number_of_values * 8 + number_of_traces
            # TODO: why the + number_of_traces (or +8 according to labview)
            raw = self.vectorstar.read_bytes(number_of_bytes)
            for param in params:
                subset = raw[:16]
                data.update({
                    param + " real": struct.unpack(">d", subset[:8])[0],
                    param + " imag": struct.unpack(">d", subset[8:])[0],
                })
                raw = raw[17:]

        else:
            for param in params:
                length = int(self.vectorstar.read_bytes(2).decode('latin')[1])
                length = int(self.vectorstar.read_bytes(length).decode('latin')) + 1

                # Read the data
                raw = self.vectorstar.read_bytes(length).decode('latin').strip("; ").split(',')

                data.update({
                    param + " real": float(raw[0]),
                    param + " imag": float(raw[1]),
                })

        return data

    def grab_data_S2P(self):
        # TODO: check if this can be done using SCPI commands

        # Set output format
        self.vectorstar.datablock_header_format = 1
        self.vectorstar.datablock_numeric_format = "ASCII"
        self.vectorstar.datafile_include_heading = True
        self.vectorstar.datafile_frequency_unit = "HZ"
        self.vectorstar.datafile_parameter_format = "REIM"

        # Check for errors before continuing
        self.vectorstar.check_errors()

        if self.vectorstar.datablock_header_format == 2:
            # Output the S2P file data.
            raw = self.vectorstar.ask("OS2P")
        else:
            self.vectorstar.write("OS2P")

            # Determine the amount of bytes to read from the buffer
            length = int(self.vectorstar.read_bytes(2).decode('latin')[1])
            length = int(self.vectorstar.read_bytes(length).decode('latin')) + 1

            # Read the data
            raw = self.vectorstar.read_bytes(length).decode('latin')

        self.vectorstar.check_errors()

        # Format the data
        filtered = []
        for line in raw.split("\n"):
            if not (line.startswith("!") or line.startswith("#")) or line.startswith("! FREQ"):
                filtered.append(line.strip("! "))
        filtered = "\n".join(filtered)

        data = pd.read_csv(StringIO(filtered), delim_whitespace=True).rename(columns={
            "FREQ.HZ": "Frequency (Hz)",
            "S11RE": "S11 real",
            "S11IM": "S11 imag",
            "S21RE": "S21 real",
            "S21IM": "S21 imag",
            "S12RE": "S12 real",
            "S12IM": "S12 imag",
            "S22RE": "S22 real",
            "S22IM": "S22 imag",
        })

        return data

    def shutdown(self):
        self.shutdown_daqmx()
        self.shutdown_vectorstar()

    def shutdown_vectorstar(self):
        if self.vectorstar is not None:
            self.vectorstar.check_errors()

            if not (self.vectorstar.adapter.connection.lock_state ==
                    pyvisa.constants.AccessModes.no_lock):
                self.vectorstar.adapter.connection.unlock()

            self.vectorstar.datablock_format = ""
            self.vectorstar.datablock_header_format = 1
            self.vectorstar.trigger_source = "AUTO"

            # Return control to front interface and enable data drawing
            if not self.vectorstar.data_drawing_enabled:
                self.vectorstar.data_drawing_enabled = True

            self.vectorstar.check_errors()

            self.vectorstar.return_to_local()
            self.vectorstar.shutdown()

    def shutdown_daqmx(self):
        if self.trigger_task is not None:
            self.trigger_task.close()

        if self.counter_task is not None:
            self.counter_task.close()
