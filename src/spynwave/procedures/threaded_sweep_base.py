"""
This file is part of the SpynWave package.
"""

import logging

from spynwave.drivers import DataThread

# Setup logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.NullHandler())


class ThreadedSweepBase:
    _threads = []

    _sweep_thread = None
    _data_thread = None

    def threads_startup(self, data_producing_threads, sweep_thread=None, **kwargs):
        if not isinstance(data_producing_threads, (list, tuple)):
            data_producing_threads = [data_producing_threads]

        # store threads in thread-list, while omitting any None-types
        self._threads = [thread for thread in data_producing_threads if thread is not None]

        # Create a data-thread
        data_queues = [thread.data_queue for thread in self._threads]
        self._data_thread = DataThread(self, data_queues=data_queues, **kwargs)
        # Ensure this is started first and stopped last
        self._threads.insert(0, self._data_thread)

        if sweep_thread is not None:
            self._sweep_thread = sweep_thread
            # Ensure the sweep thread is in the threads-list and is started last and stopped first
            if sweep_thread in self._threads:
                self._threads.remove(sweep_thread)

            self._threads.append(sweep_thread)

    def threads_start(self):
        for thread in self._threads:
            thread.start()

    def threads_stop(self):
        for thread in self._threads[::-1]:
            thread.stop()

    def threads_shutdown(self):
        for thread in self._threads[::-1]:
            thread.shutdown()

    def threads_sweep_finished(self):
        if self._sweep_thread is not None:
            return self._sweep_thread.is_finished()
        else:
            raise ValueError("No sweep thread defined; cannot check whether sweep finished.")

    def threads_data_processed(self):
        if self._data_thread is not None:
            return self._data_thread.all_data_processed()
        else:
            raise ValueError("No sweep thread defined; cannot check whether sweep finished.")