"""Test :class:`qibo.abstractions.gates.M` as standalone and as part of circuit."""
import pytest
import numpy as np
import qibo
from qibo import models, gates


def assert_result(result, decimal_samples=None, binary_samples=None,
                  decimal_frequencies=None, binary_frequencies=None):
    if decimal_frequencies is not None:
        assert result.frequencies(False) == decimal_frequencies
    if binary_frequencies is not None:
        assert result.frequencies(True) == binary_frequencies
    if decimal_samples is not None:
        np.testing.assert_allclose(result.samples(False), decimal_samples)
    if binary_samples is not None:
        np.testing.assert_allclose(result.samples(True), binary_samples)


@pytest.mark.parametrize("nqubits,targets",
                         [(2, [1]), (3, [1]), (4, [1, 3]), (5, [0, 3, 4]),
                          (6, [1, 3]), (4, [0, 2])])
def test_measurement_collapse(backend, nqubits, targets):
    from qibo.tests_new.test_core_gates import random_state
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    initial_state = random_state(nqubits)
    gate = gates.M(*targets, collapse=True)
    final_state = gate(np.copy(initial_state), nshots=1)
    results = gate.result.binary[0]
    slicer = nqubits * [slice(None)]
    for t, r in zip(targets, results):
        slicer[t] = r
    slicer = tuple(slicer)
    initial_state = initial_state.reshape(nqubits * (2,))
    target_state = np.zeros_like(initial_state)
    target_state[slicer] = initial_state[slicer]
    norm = (np.abs(target_state) ** 2).sum()
    target_state = target_state.ravel() / np.sqrt(norm)
    np.testing.assert_allclose(final_state, target_state)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("nqubits,targets",
                         [(2, [1]), (3, [1]), (4, [1, 3]), (5, [0, 3, 4])])
def test_measurement_collapse_density_matrix(backend, nqubits, targets):
    from qibo.tests_new.test_core_gates_density_matrix import random_density_matrix
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    initial_rho = random_density_matrix(nqubits)
    gate = gates.M(*targets, collapse=True)
    gate.density_matrix = True
    final_rho = gate(np.copy(initial_rho), nshots=1)
    results = gate.result.binary[0]
    target_rho = np.reshape(initial_rho, 2 * nqubits * (2,))
    if isinstance(results, int):
        results = len(targets) * [results]
    for q, r in zip(targets, results):
        slicer = 2 * nqubits * [slice(None)]
        slicer[q], slicer[q + nqubits] = 1 - r, 1 - r
        target_rho[tuple(slicer)] = 0
        slicer[q], slicer[q + nqubits] = r, 1 - r
        target_rho[tuple(slicer)] = 0
        slicer[q], slicer[q + nqubits] = 1 - r, r
        target_rho[tuple(slicer)] = 0
    target_rho = np.reshape(target_rho, initial_rho.shape)
    target_rho = target_rho / np.trace(target_rho)
    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("effect", [False, True])
def test_measurement_result_parameters(backend, effect):
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    c = models.Circuit(2)
    if effect:
        c.add(gates.X(0))
    output = c.add(gates.M(0, collapse=True))
    c.add(gates.RX(1, theta=np.pi * output / 4))

    target_c = models.Circuit(2)
    if effect:
        target_c.add(gates.X(0))
        target_c.add(gates.RX(1, theta=np.pi / 4))
    np.testing.assert_allclose(c(), target_c())
    qibo.set_backend(original_backend)


def test_measurement_result_parameters_random(backend):
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    from qibo import K
    from qibo.tests_new.test_core_gates import random_state
    initial_state = random_state(3)
    K.set_seed(123)
    c = models.Circuit(3)
    output = c.add(gates.M(1, collapse=True))
    c.add(gates.RX(2, theta=np.pi * output / 4))
    result = c(initial_state=np.copy(initial_state))

    K.set_seed(123)
    collapse = gates.M(1, collapse=True)
    target_state = collapse(np.copy(initial_state))
    if int(output.binary[0, 0]):
        target_state = gates.RX(2, theta=np.pi / 4)(target_state)
    np.testing.assert_allclose(result, target_state)
    qibo.set_backend(original_backend)
