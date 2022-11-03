"""
This file is part of the SpynWave package.
"""
import logging
from spynwave.drivers.anritsuMS4644B import AnritsuMS4644B

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class VNA(AnritsuMS4644B):
    def __init__(self, adapter, **kwargs):
        super().__init__(adapter, **kwargs)

    def startup(self, reset=False):
        self.id
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

        # Configure trigger for external (DAQmx) trigger
        self.trigger_source = "EXT"
        self.external_trigger_type = "CHAN"
        self.external_trigger_delay = 0
        self.external_trigger_edge = "POS"
        self.external_trigger_handshake = False


        self.ch_1.hold_function = "CONT"

        # self.data_drawing_enabled = False

        self.ch_1.frequency_start
        self.ch_1.frequency_stop
        self.ch_1.bandwidth
        self.ch_1.pt_1.power_level

    def shutdown(self):
        # 5A: stop counter and triggering tasks
        #     TODO: uitzoeken hoe dit werkt

        self.output_data_format = 1
        self.trigger_source = "AUTO"

        # Return control to front interface and enable data drawing
        self.data_drawing_enabled = True
        self.return_to_local()

        super().shutdown()
