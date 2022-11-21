"""
This file is part of the SpynWave package.
"""


class Channel:
    placeholder = "ch"

    def __init__(self, parent, id):
        self.parent = parent
        self.id = id
        super().__init__()
