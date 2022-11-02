"""
This file is part of the SpynWave package.
"""
import logging
from spynwave.drivers.anritsuMS4644B import AnritsuMS4644B

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class VNA(AnritsuMS4644B):
    """
        Check error after every sent command


    """





    def __init__(self, adapter, **kwargs):
        super().__init__(adapter, **kwargs)

    def startup(self, reset=False):
        # LabVIEW startup sequence
        # ~~~~~~~~~~~~~~~~~~~~~~~~
        # 1: VNA.lvlib:Start.vi
        #     1A:Anritsu.lvlib:Initialize.vi
        #         Query ID
        #         *IDN --> id

        #         if reset:
        #         *RST --> reset()
        if reset:
            self.reset()

        #         Default setup commands:
        #         *ESE 60;*SRE 48;*CLS;:FORM:BORD NORM;
        #         # HEADER OFF - instrument no longer returns headers with responses to queries
        #         # *ESE 60 - enables command, execution, query, and device errors in event status register
        #         # *SRE 48 - enables message available, standard event bits in the status byte
        #         # *CLS - clears status

        #     1B: DAQmx series create counter and trigger task
        #         TODO: Uitzoeken hoe dit werkt

        #     1C: Anritsu.lvlib:Configure active channel.vi
        #         for channel 1
        #         :DISP:WIND%d:ACT;
        self.active_channel = 1

        #     1D: Anritsu.lvlib:Configure application type.vi
        #         for channel 1
        #         for transmission/reflection (TRAN)
        #         :CALC%d:APPL:MEAS:TYP %s;
        self.ch_1.application_type = "TRAN"

        #     1E: Anritsu.lvlib:Configure trigger.vi
        #         for trigger source:external
        #         :TRIG:SOUR EXT;
        #         :TRIG:EXT:TYP CHAN;
        #         :TRIG:EXT:DEL 0.000000;
        #         :TRIG:EXT:EDG POS;
        #         :TRIG:EXT:HAND OFF;
        self.trigger_source = "EXT"
        self.external_trigger_type = "CHAN"
        self.external_trigger_delay = 0
        self.external_trigger_edge = "POS"
        self.external_trigger_handshake = False


        #     1F: Anritsu.lvlib:Configure hold function.vi
        #         for channel 1
        #         for continue (CONT)
        #         :SENS%d:HOLD:FUNC %s;

        #     1G (disabled): write to VNA
        #         DD0

        # 2: VNA get freq range VI
        #     :SENS%d:FREQ:STAR?;
        #     :SENS%d:FREQ:STOP?;

        # 3: VNA query IF bandwidth
        #     :SENS%d:BWID?;

        # 4: VNA query power
        #     for source 1 and port 1
        #     SOUR%d:POW:PORT%d?;


    def shutdown(self):
        # 5: VNA stop
        #     5A: stop counter and triggering tasks
        #         TODO: uitzoeken hoe dit werkt
        #     5B: write to VNA
        #         FDH1;TIN
        #     5C (disabled): write to VNA
        #         DD1
        #     5D: return to local
        self.return_to_local()
        super().shutdown()
