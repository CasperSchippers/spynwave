import logging

from pymeasure.instruments import Instrument, Channel
from pymeasure.instruments.validators import (
    strict_discrete_set,
    strict_range
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class MeasurementChannel(Channel):
    def activate(self):
        self.write(":DISP:WIND{ch}:ACT")

    application_type = Channel.control(
        ":CALC{ch}:APPL:MEAS:TYP?", ":CALC{ch}:APPL:MEAS:TYP %s",
        """ A string property that controls the application type of the specified channel. Valid
        values are TRAN (for transmission/reflection), NFIG (for noise figure measurement), PULS
        (for PulseView). Can be set.""",
        values=["TRAN", "NFIG", "PULS"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    def check_errors(self):
        return self.parent.check_errors()


class AnritsuMS4644B(Instrument):
    """ A class representing the Anritsu MS4644B Vector Network Analyzer (VNA).

    """
    CHANNELS = 16
    CHANNEL_LIST = list(range(1, CHANNELS+1))

    def __init__(self, adapter, **kwargs):
        super().__init__(
            adapter,
            "Anritsu MS4644B Vector Network Analyzer",
            **kwargs,
        )

        for ch in self.CHANNEL_LIST:
            self.add_child(MeasurementChannel, ch)


    def check_errors(self):
        """ Read all errors from the instrument.

        :return: list of error entries
        """
        errors = []
        while True:
            err = self.values("SYST:ERR?")
            if err[0] != "No Error":
                log.error(f"{self.name}: {err[0]}")
                print(err)  # TODO: remove this line
                errors.append(err)
            else:
                break
        return errors

    def return_to_local(self):
        """ Set instrument to local operation. """
        self.write("RTL")

    active_channel = Instrument.control(
        ":DISP:WIND:ACT?",":DISP:WIND%d:ACT",
        """ An integer property that controls the active channel. This property can be set.
        """,
        validator=strict_discrete_set,
        values=CHANNEL_LIST,
        cast=int,
        check_get_errors=True,
        check_set_errors=True,
    )

    trigger_source = Instrument.control(
        ":TRIG:SOUR?", ":TRIG:SOUR %s",
        """ A string property that controls the source of the sweep/measurement triggering. Can be 
        set; valid values are:

        =====   ==================================================
        value   description
        =====   ==================================================
        AUTO    Automatic triggering
        MAN     Manual triggering
        EXTT    Triggering from rear panel BNC via the GPIB parser
        EXT     External triggering port
        REM     Remote triggering
        =====   ==================================================
        """,
        values=["AUTO", "MAN", "EXTT", "EXT", "REM"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    external_trigger_type = Instrument.control(
        ":TRIG:EXT:TYP?", ":TRIG:EXT:TYP %s",
        """ A string property that controls the source of the sweep/measurement triggering. Can be
        set; valid values are POIN (for point), SWE (for sweep), CHAN (for channel), and ALL.
        """,
        values=["POIN", "SWE", "CHAN", "ALL"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )

    external_trigger_delay = Instrument.control(
        ":TRIG:EXT:DEL?", ":TRIG:EXT:DEL %g",
        """ A float property that controls the the delay time of the external trigger. Can be
        set; valid values are between 0 [s] and 10[s] in steps of 1e-9 [s] (i.e. 1 ns).
        """,
        values=[0, 10],
        validator=strict_range,
        check_get_errors=True,
        check_set_errors=True,
    )

    external_trigger_edge = Instrument.control(
        ":TRIG:EXT:EDG?", ":TRIG:EXT:EDG %s",
        """ A string property that controls the which edge is used for triggering of the external
        trigger. Can be set; valid values are POS (for positive or leading edge) or NEG (for
        negative or trailing edge).
        """,
        values=["POS", "NEG"],
        validator=strict_discrete_set,
        check_get_errors=True,
        check_set_errors=True,
    )


    external_trigger_handshake = Instrument.control(
        ":TRIG:EXT:HAND?", ":TRIG:EXT:HAND %s",
        """ A boolean property that controls status of the external trigger handshake. Can be set.
        """,
        values={True: 1, False: 0},
        map_values=True,
        check_get_errors=True,
        check_set_errors=True,
    )