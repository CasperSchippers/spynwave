"""
This file is part of the SpynWave package.
"""
import logging
import pandas as pd
from io import StringIO

# TODO: should be contributed to pymeasure
from spynwave.pymeasure_patches.anritsuMS4644B import AnritsuMS4644B

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class VNA(AnritsuMS4644B):
    def __init__(self, adapter, use_DAQmx=False, **kwargs):
        super().__init__(adapter, **kwargs)

        self.use_DAQmx = use_DAQmx
        if self.use_DAQmx:
            NotImplementedError("Using DAQmx to trigger measurements is not yet implemented.")

    def startup(self, reset=False):
        # self.id
        if reset:
            self.reset()

        # *ESE 60: enables command, execution, query, and device errors in event status register
        self.event_status_enable_bits = 60
        # *SRE 48: enables message available, standard event bits in the status byte
        self.service_request_enable_bits = 48
        self.clear()
        self.binary_data_byte_order = "NORM"

        # 1B: DAQmx series create counter and trigger task
        #     TODO: Uitzoeken hoe dit werkt

        # Configure single active channel for transmission/reflection measurements
        self.number_of_channels = 1
        self.active_channel = 1
        self.ch_1.application_type = "TRAN"

        if self.use_DAQmx:
            # Configure trigger for external (DAQmx) trigger
            self.trigger_source = "EXT"
            self.external_trigger_type = "CHAN"
            self.external_trigger_delay = 0
            self.external_trigger_edge = "POS"
            self.external_trigger_handshake = False
        else:
            self.trigger_source = "REM"
            self.remote_trigger_type = "CHAN"

        self.ch_1.hold_function = "CONT"

        # self.data_drawing_enabled = False

        # self.ch_1.frequency_start
        # self.ch_1.frequency_stop
        # self.ch_1.bandwidth
        # self.ch_1.pt_1.power_level

    def set_measurement_ports(self, measurement_ports):
        if measurement_ports == "2-port":
            self.ch_1.number_of_traces = 4
            self.ch_1.display_layout = "R2C2"
            self.ch_1.tr_1.measurement_parameter = "S11"
            self.ch_1.tr_2.measurement_parameter = "S12"
            self.ch_1.tr_3.measurement_parameter = "S21"
            self.ch_1.tr_4.measurement_parameter = "S22"

        else:  # 1-port measurement
            self.ch_1.number_of_traces = 1
            self.ch_1.display_layout = "R1C1"
            self.ch_1.tr_1.measurement_parameter = measurement_ports[-3:]

    def general_measurement_settings(self, power_level, bandwidth):
        self.bandwidth_enhancer_enabled = True
        self.ch_1.bandwidth = bandwidth

        self.ch_1.pt_1.power_level = power_level

    def configure_averaging(self, enabled, average_count, averaging_type):
        self.ch_1.averaging_enabled = enabled
        self.ch_1.average_count = average_count
        self.ch_1.average_type = {"point-by-point": "POIN", "sweep-by-sweep": "SWE"}[averaging_type]

    def reset_to_measure(self):
        self.ch_1.tr_1.activate()
        self.ch_1.clear_average_count()
        self.clear()

    def prepare_field_sweep(self):
        raise NotImplementedError("Field sweep not yet implemented")

    def prepare_frequency_sweep(self, frequency_start, frequency_stop, frequency_points):
        self.ch_1.cw_mode_enabled = False

        self.ch_1.frequency_start = frequency_start
        self.ch_1.frequency_stop = frequency_stop
        self.ch_1.number_of_points = frequency_points

    def trigger_frequency_sweep(self):
        if self.use_DAQmx:
            NotImplementedError("Triggering using DAQmx not yet implemented")
        else:
            self.trigger_continuous()

    def grab_data(self):
        # TODO: check if this can be done using SCPI commands

        # Set output format
        self.datablock_header_format = 2
        self.datafile_numeric_format = "ASC"
        self.datafile_include_heading = True
        self.datafile_frequency_unit = "HZ"
        self.datafile_parameter_format = "REIM"

        # Check for errors before continuing
        self.check_errors()

        if self.datablock_header_format == 2:
            # Output the S2P file data.
            raw = self.ask("OS2P")
        else:
            self.write("OS2P")

            # Determine the amount of bytes to read from the buffer
            length = int(self.read_bytes(2).decode('ascii')[1])
            length = int(self.read_bytes(length).decode('ascii')) + 1

            # Read the data
            raw = self.read_bytes(length).decode('ascii')

        self.check_errors()

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

        self.datablock_header_format = 1
        self.trigger_source = "AUTO"

        # Return control to front interface and enable data drawing
        if not self.data_drawing_enabled:
            self.data_drawing_enabled = True
        self.return_to_local()

        super().shutdown()
