"""
This file is part of the SpynWave package.
"""

import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class SourceMeter:
    def __int__(self):
        pass

    def startup(self):
        pass

    def shutdown(self):
        pass
