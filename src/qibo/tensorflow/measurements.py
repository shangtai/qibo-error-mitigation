# -*- coding: utf-8 -*-
# @authors: S. Efthymiou
import numpy as np
import tensorflow as tf
from qibo.base import measurements as base_measurements
from typing import Dict, Set, Tuple


class GateResult(base_measurements.GateResult):

    @staticmethod
    def _convert_to_binary(x: tf.Tensor, n: int) -> tf.Tensor:
        _range = tf.range(n - 1, -1, -1, dtype=tf.int64)
        return tf.math.mod(tf.bitwise.right_shift(x[:, tf.newaxis], _range), 2)

    @staticmethod
    def _convert_to_decimal(x: tf.Tensor, n: int) -> tf.Tensor:
        _range = tf.range(n - 1, -1, -1, dtype=tf.int64)
        _range = tf.math(2, _range)[:, tf.newaxis]
        return tf.matmul(x, _range)[0]

    @staticmethod
    def _calculate_counts(decimal_samples: tf.Tensor) -> Tuple[np.ndarray]:
        return np.unique(decimal_samples.numpy(), return_counts=True)


class CircuitResult(base_measurements.CircuitResult):

    @staticmethod
    def _calculate_register_results(register_qubits: Dict[str, Set[int]],
                                    gate_result: GateResult
                                    ) -> Dict[str, GateResult]:
        results = {}
        for name, qubit_set in register_qubits.items():
            qubit_tuple = tuple(sorted(qubit_set))
            slicer = tuple(gate_result.qubit_map[q] for q in qubit_tuple)
            samples = gate_result.binary_samples[:, slicer]
            results[name] = GateResult(qubit_tuple, binary_samples=samples)
        return results
