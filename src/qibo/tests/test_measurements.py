import collections
import numpy as np
import pytest
from qibo import gates, models
from typing import Optional


def assert_results(result,
                   decimal_samples: Optional[np.ndarray] = None,
                   binary_samples: Optional[np.ndarray] = None,
                   decimal_frequencies: Optional[collections.Counter] = None,
                   binary_frequencies: Optional[collections.Counter] = None):
  if decimal_samples is not None:
      np.testing.assert_allclose(result.samples(False).numpy(), decimal_samples)
  if binary_samples is not None:
      np.testing.assert_allclose(result.samples(True).numpy(), binary_samples)
  if decimal_frequencies is not None:
      assert result.frequencies(False) == collections.Counter(decimal_frequencies)
  if binary_frequencies is not None:
      assert result.frequencies(True) == collections.Counter(binary_frequencies)


def test_convert_to_binary():
    """Check that `_convert_to_binary` method works properly."""
    # Create a result object to access `_convert_to_binary`
    state = np.zeros(4)
    state[0] = 1
    state = state.reshape((2, 2))
    result = gates.M(0)(state, nshots=100)

    import itertools
    nbits = 5
    binary_samples = result._convert_to_binary(np.arange(2 ** nbits),
                                               nbits).numpy()
    target_samples = np.array(list(itertools.product([0, 1], repeat=nbits)))
    np.testing.assert_allclose(binary_samples, target_samples)


def test_measurement_gate():
    """Check that measurement gate works when called on the state |00>."""
    state = np.zeros(4)
    state[0] = 1
    state = state.reshape((2, 2))
    result = gates.M(0)(state, nshots=100)
    assert_results(result,
                   decimal_samples=np.zeros((100,)),
                   binary_samples=np.zeros((100, 1)),
                   decimal_frequencies={0: 100},
                   binary_frequencies={"0": 100})


def test_measurement_gate2():
    """Check that measurement gate works when called on the state |11>."""
    state = np.zeros(4)
    state[-1] = 1
    state = state.reshape((2, 2))
    result = gates.M(1)(state, nshots=100)
    assert_results(result,
                   decimal_samples=np.ones((100,)),
                   binary_samples=np.ones((100, 1)),
                   decimal_frequencies={1: 100},
                   binary_frequencies={"1": 100})


def test_multiple_qubit_measurement_gate():
    """Check that multiple qubit measurement gate works when called on |10>."""
    state = np.zeros(4)
    state[2] = 1
    state = state.reshape((2, 2))
    print([state[0, 0], state[0, 1], state[1, 0], state[1, 1]])
    result = gates.M(0, 1)(state, nshots=100)

    target_binary_samples = np.zeros((100, 2))
    target_binary_samples[:, 0] = 1
    assert_results(result,
                   decimal_samples=2 * np.ones((100,)),
                   binary_samples=target_binary_samples,
                   decimal_frequencies={2: 100},
                   binary_frequencies={"10": 100})


def test_controlled_measurement_error():
    """Check that using `controlled_by` in measurements raises error."""
    with pytest.raises(NotImplementedError):
        m = gates.M(0).controlled_by(1)


def test_measurement_circuit():
    """Check that measurement gate works as part of circuit."""
    c = models.Circuit(2)
    c.add(gates.M(0))

    measurements = c(nshots=100).samples(False).numpy()
    target_measurements = np.zeros_like(measurements)
    assert measurements.shape == (100,)
    np.testing.assert_allclose(measurements, target_measurements)


def test_multiple_qubit_measurement_circuit():
    """Check that multiple measurement gates fuse correctly."""
    c = models.Circuit(2)
    c.add(gates.X(0))
    c.add(gates.M(0))
    c.add(gates.M(1))

    measurements = c(nshots=100).samples(False).numpy()
    target_measurements = 2 * np.ones_like(measurements)
    assert measurements.shape == (100,)
    np.testing.assert_allclose(measurements, target_measurements)

    final_state = c.final_state.numpy()
    target_state = np.zeros_like(final_state)
    target_state[2] = 1
    np.testing.assert_allclose(final_state, target_state)


def test_multiple_measurement_gates_circuit():
    """Check that measurement gates with different number of targets."""
    c = models.Circuit(4)
    c.add(gates.X(1))
    c.add(gates.X(2))
    c.add(gates.M(0, 1))
    c.add(gates.M(2))
    c.add(gates.X(3))

    measurements = c(nshots=100).samples(False).numpy()
    target_measurements = 3 * np.ones_like(measurements)
    assert measurements.shape == (100,)
    np.testing.assert_allclose(measurements, target_measurements)

    final_state = c.final_state.numpy()
    c = models.Circuit(4)
    c.add(gates.X(1))
    c.add(gates.X(2))
    c.add(gates.X(3))
    target_state = c().numpy()
    np.testing.assert_allclose(final_state, target_state)


def test_measurement_compiled_circuit():
    """Check that measurement gates work when compiling the circuit."""
    c = models.Circuit(2)
    c.add(gates.X(0))
    c.add(gates.M(0))
    c.add(gates.M(1))
    c.compile()

    measurements = c(nshots=100).samples(False).numpy()
    target_measurements = 2 * np.ones_like(measurements)
    assert measurements.shape == (100,)
    np.testing.assert_allclose(measurements, target_measurements)

    final_state = c.final_state.numpy()
    target_state = np.zeros_like(final_state)
    target_state[2] = 1
    np.testing.assert_allclose(final_state, target_state)
