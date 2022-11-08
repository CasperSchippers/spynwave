"""
This file is part of the SpynWave package.
"""
import logging
from time import time, sleep
from io import StringIO

import pandas as pd

# TODO: should be contributed to pymeasure
from spynwave.pymeasure_patches.anritsuMS4644B import AnritsuMS4644B

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class VNA:
    vectorstar = None
    def __init__(self, adapter, use_DAQmx=False, **kwargs):

        self.vectorstar = AnritsuMS4644B(adapter, **kwargs)

        self.use_DAQmx = use_DAQmx
        if self.use_DAQmx:
            NotImplementedError("Using DAQmx to trigger measurements is not yet implemented.")

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

        if self.use_DAQmx:
            # Configure trigger for external (DAQmx) trigger
            self.vectorstar.trigger_source = "EXT"
            self.vectorstar.external_trigger_type = "CHAN"
            self.vectorstar.external_trigger_delay = 0
            self.vectorstar.external_trigger_edge = "POS"
            self.vectorstar.external_trigger_handshake = False
        else:
            self.vectorstar.trigger_source = "REM"
            self.vectorstar.remote_trigger_type = "CHAN"

        self.vectorstar.ch_1.hold_function = "CONT"

        # self.vectorstar.data_drawing_enabled = False

        # self.vectorstar.ch_1.frequency_start
        # self.vectorstar.ch_1.frequency_stop
        # self.vectorstar.ch_1.bandwidth
        # self.vectorstar.ch_1.pt_1.power_level

    def set_measurement_ports(self, measurement_ports):
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

    def general_measurement_settings(self, power_level, bandwidth):
        self.vectorstar.bandwidth_enhancer_enabled = True
        self.vectorstar.ch_1.bandwidth = bandwidth

        self.vectorstar.ch_1.pt_1.power_level = power_level

    def configure_averaging(self, enabled, average_count, averaging_type):
        self.vectorstar.ch_1.averaging_enabled = enabled
        self.vectorstar.ch_1.average_count = average_count
        self.vectorstar.ch_1.average_type = {"point-by-point": "POIN", "sweep-by-sweep": "SWE"}[averaging_type]

    def reset_to_measure(self):
        self.vectorstar.ch_1.tr_1.activate()
        self.vectorstar.ch_1.clear_average_count()
        self.vectorstar.clear()

    def prepare_field_sweep(self, cw_frequency):
        self.vectorstar.ch_1.cw_mode_enabled = True

        self.vectorstar.ch_1.frequency_CW = cw_frequency

    def prepare_frequency_sweep(self, frequency_start, frequency_stop, frequency_points):
        self.vectorstar.ch_1.cw_mode_enabled = False

        self.vectorstar.ch_1.frequency_start = frequency_start
        self.vectorstar.ch_1.frequency_stop = frequency_stop
        self.vectorstar.ch_1.number_of_points = frequency_points

    def trigger_frequency_sweep(self):
        log.info("Triggering frequency sweep.")
        if self.use_DAQmx:
            NotImplementedError("Triggering using DAQmx not yet implemented")
        else:
            sleep(0.5)
            self.vectorstar.trigger_continuous()

    def grab_data(self):
        # TODO: check if this can be done using SCPI commands

        # Set output format
        self.vectorstar.datablock_header_format = 1
        self.vectorstar.datafile_numeric_format = "ASC"
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

        #Format the data
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
        # 5A: stop counter and triggering tasks
        #     TODO: uitzoeken hoe dit werkt

        if self.vectorstar is not None:
            self.vectorstar.datablock_header_format = 1
            self.vectorstar.trigger_source = "AUTO"

            # Return control to front interface and enable data drawing
            if not self.vectorstar.data_drawing_enabled:
                self.vectorstar.data_drawing_enabled = True
            self.vectorstar.return_to_local()
            self.vectorstar.shutdown()
