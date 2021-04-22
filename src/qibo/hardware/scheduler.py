import numpy as np
from concurrent.futures import ThreadPoolExecutor, Future
from qibo import K
from qibo.config import raise_error
from qibo.hardware import pulses
from qibo.hardware.circuit import PulseSequence


class TaskScheduler:
    """Scheduler class for organizing FPGA calibration and pulse sequence execution."""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._pi_trig = None # NIY
        self._qubit_config = None

    def fetch_config(self):
        """Fetches the qubit configuration data

        Returns:
            List of dicts representing qubit metadata or false if data is not ready yet
        """
        if self._qubit_config is None:
            raise_error(RuntimeError, "Cannot fetch qubit configuration "
                                      "because calibration is not complete.")
        return self._qubit_config

    def poll_config(self):
        """Blocking command to wait until qubit calibration is complete."""
        raise_error(NotImplementedError)

    def config_ready(self):
        """Checks if qubit calibration is complete.

        Returns:
            Boolean flag representing status of qubit calibration complete
        """
        return self._qubit_config is not None

    def execute_pulse_sequence(self, pulse_sequence, nshots):
        """Submits a pulse sequence to the queue for execution.

        Args:
            pulse_sequence: Pulse sequence object.
            shots: Number of trials.

        Returns:
            concurrent.futures.Future object representing task status
        """
        if not isinstance(pulse_sequence, PulseSequence):
            raise_error(TypeError, "Pulse sequence {} has invalid type."
                                   "".format(pulse_sequence))
        if not isinstance(nshots, int) or nshots < 1:
            raise_error(ValueError, "Invalid number of shots {}.".format(nshots))
        future = self._executor.submit(self._execute_pulse_sequence,
                                       pulse_sequence=pulse_sequence,
                                       nshots=nshots)
        return future

    @staticmethod
    def _execute_pulse_sequence(pulse_sequence, nshots):
        wfm = pulse_sequence.compile()
        K.experiment.upload(wfm)
        K.experiment.start()
        # NIY
        #self._pi_trig.trigger(shots, delay=50e6)
        # OPC?
        K.experiment.stop()
        res = K.experiment.download()
        return res

    def execute_batch_sequence(self, pulse_batch, nshots):
        if not isinstance(nshots, int) or nshots < 1:
            raise_error(ValueError, "Invalid number of shots {}.".format(nshots))
        future = self._executor.submit(self._execute_batch_sequence,
                                       pulse_batch=pulse_batch,
                                       nshots=nshots)
        return future

    @staticmethod
    def _execute_batch_sequence(pulse_batch, nshots):
        wfm = pulse_batch[0].compile()
        steps = len(pulse_batch)
        sample_size = len(wfm[0])
        wfm_batch = np.zeros((K.experiment.static.nchannels, steps, sample_size))
        for i in range(steps):
            wfm = pulse_batch[i].compile()
            for j in range(K.experiment.static.nchannels):
                wfm_batch[j, i] = wfm[j]

        K.experiment.upload_batch(wfm_batch, nshots)
        K.experiment.start_batch(steps)
        K.experiment.stop()
        res = K.experiment.download()
        return res

        
