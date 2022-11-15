"""
This file is part of the SpynWave package.
"""

import logging
import queue

import pandas as pd
from time import sleep

from pymeasure.thread import StoppableThread, InterruptableEvent

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class DataThread(StoppableThread):
    static_data = {}
    _should_really_stop = False

    def __init__(self, procedure, data_queues, static_data=None, time_column="Timestamp (s)"):
        super().__init__()
        self._static_data_queue = queue.Queue()
        self._all_data_processed = InterruptableEvent()

        self.procedure = procedure

        self.data_structs = [DataStructure(q) for q in data_queues]

        self.get_new_static_data(static_data)
        self.time_column = time_column

        # TODO: uitzoeken of dit nodig is
        global log
        log = logging.getLogger()

    def set_all_data_processed(self):
        self._all_data_processed.set()

    def all_data_processed(self):
        return self._all_data_processed.is_set()

    def update_static_data(self, new_data):
        assert isinstance(new_data, dict), "Static data should be supplied as a dict."
        self._static_data_queue.put(new_data)

    def get_new_static_data(self, new_data=None):
        if new_data is None:
            while not self._static_data_queue.empty():
                new_data = self._static_data_queue.get()

        if new_data is not None:
            assert isinstance(new_data, dict), "Static data should be supplied as a dict."
            self.static_data = new_data

    def emit_data(self, data):
        self.procedure.emit("results", data | self.static_data)

    def matching_possible(self):
        """ Check if all structs sufficient data for matching
        """
        return all(s.could_be_merged() for s in self.data_structs)

    def get_matched_data(self):
        # V2: assuming that the first column is the slowest one
        # TODO: generalise this a bit
        mainstruct = self.data_structs[0]
        matching_time, midpoint = mainstruct.get_matching_timedata()

        # Perform check that this is going to work out
        for struct in self.data_structs:
            if struct.index_until_timestamp(midpoint) == 0:
                log.info("Not all columns have sufficient data for matching")
                # TODO: maybe here we need to see if we need to drop the datapoint of the mainstruct
                return None

        matched_data = []
        for struct in self.data_structs:
            idx = struct.index_until_timestamp(midpoint)
            _, data = struct.pop_first_n_datapoints(idx)
            matched_data.append(pd.DataFrame(data).mean().to_dict())

        data = {k: v for d in matched_data for k, v in d.items()}
        data[self.time_column] = matching_time
        return data

    def data_available(self):
        return any([s.data_available for s in self.data_structs])

    def should_stop(self):
        should_stop = super().should_stop() and self._should_really_stop
        self._should_really_stop = super().should_stop()

        return should_stop

    def run(self):
        while not self.should_stop():
            self.get_new_static_data()

            for struct in self.data_structs:
                struct.pull_data_from_queue()

            while self.matching_possible():
                data = self.get_matched_data()

                if data is not None:
                    self.emit_data(data)

            # Need a sleep to ensure smooth function of the GUI
            sleep(0.001)

        self.set_all_data_processed()


class DataStructure:
    def __init__(self, data_queue):
        self.queue = data_queue
        self.time_lst = []
        self.data_lst = []

    def data_available(self):
        return not self.queue.empty()

    def pull_data_from_queue(self):
        while self.data_available():
            t, d = self.queue.get()
            self.time_lst.append(t)
            self.data_lst.append(d)

    def could_be_merged(self):
        assert self.time_lst == sorted(self.time_lst)
        assert len(self.time_lst) == len(self.data_lst)
        return len(self.time_lst) >= 2

    # def first_datapoint_before_timestamp(self, timestamp):
    #     if len(self.time_lst) == 0:
    #         return False
    #
    #     return self.time_lst[0] < timestamp

    # def get_first_datapoint(self):
    #     return self.time_lst.pop(0), self.data_lst.pop(0)

    def index_until_timestamp(self, timestamp):
        for idx, time_value in enumerate(self.time_lst):
            if time_value > timestamp:
                return idx

    # def collect_data_before_timestamp(self, timestamp):
    #     dataset = []
    #     while self.first_datapoint_before_timestamp(timestamp):
    #         dataset.append(self.get_first_datapoint()[1])  # This discards the timestamp
    #     return dataset

    def get_first_interval(self):
        # TODO: can maybe be used to generalise this a bit
        if not self.could_be_merged():
            return False

        return abs(self.time_lst[1] - self.time_lst[0])

    def get_matching_timedata(self):
        if not self.could_be_merged():
            return None

        return self.time_lst[0], (self.time_lst[0] + self.time_lst[1]) / 2

    def get_first_n_datapoints(self, idx):
        return self.time_lst[:idx], self.data_lst[:idx]

    def remove_first_n_datapoints(self, idx):
        del self.time_lst[:idx]
        del self.data_lst[:idx]

    def pop_first_n_datapoints(self, idx):
        data = self.get_first_n_datapoints(idx)
        self.remove_first_n_datapoints(idx)
        return data
