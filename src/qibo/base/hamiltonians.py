import numpy as np # TODO: Remove this when you create `NumpyLocalHamiltonian`
from qibo import gates
from qibo.config import raise_error, EINSUM_CHARS


class Hamiltonian(object):
    """Abstract Hamiltonian operator using full matrix representation.

    Args:
        nqubits (int): number of quantum bits.
        matrix (np.ndarray): Matrix representation of the Hamiltonian in the
            computational basis as an array of shape
            ``(2 ** nqubits, 2 ** nqubits)``.
    """
    NUMERIC_TYPES = None
    ARRAY_TYPES = None
    K = None # calculation backend (numpy or TensorFlow)

    def __init__(self, nqubits, matrix):
        if not isinstance(nqubits, int):
            raise_error(RuntimeError, "nqubits must be an integer but is "
                                            "{}.".format(type(nqubits)))
        if nqubits < 1:
            raise_error(ValueError, "nqubits must be a positive integer but is "
                                    "{}".format(nqubits))
        shape = tuple(matrix.shape)
        if shape != 2 * (2 ** nqubits,):
            raise_error(ValueError, "The Hamiltonian is defined for {} qubits "
                                    "while the given matrix has shape {}."
                                    "".format(nqubits, shape))

        self.nqubits = nqubits
        self.matrix = matrix
        self._eigenvalues = None
        self._eigenvectors = None
        self._exp = {"a": None, "result": None}

    def _calculate_exp(self, a): # pragma: no cover
        # abstract method
        raise_error(NotImplementedError)

    def eigenvalues(self):
        """Computes the eigenvalues for the Hamiltonian."""
        if self._eigenvalues is None:
            self._eigenvalues = self.K.linalg.eigvalsh(self.matrix)
        return self._eigenvalues

    def eigenvectors(self):
        """Computes a tensor with the eigenvectors for the Hamiltonian."""
        if self._eigenvectors is None:
            self._eigenvalues, self._eigenvectors = self.K.linalg.eigh(self.matrix)
        return self._eigenvectors

    def exp(self, a):
        """Computes a tensor corresponding to exp(-1j * a * H).

        Args:
            a (complex): Complex number to multiply Hamiltonian before
                exponentiation.
        """
        if self._exp.get("a") != a:
            self._exp["a"] = a
            self._exp["result"] = self._calculate_exp(a) # pylint: disable=E1111
        return self._exp.get("result")

    def expectation(self, state, normalize=False): # pragma: no cover
        """Computes the real expectation value for a given state.

        Args:
            state (array): the expectation state.
            normalize (bool): If ``True`` the expectation value is divided
                with the state's norm squared.

        Returns:
            Real number corresponding to the expectation value.
        """
        # abstract method
        raise_error(NotImplementedError)

    def _eye(self, n=None):
        if n is None:
            n = int(self.matrix.shape[0])
        return self.K.eye(n, dtype=self.matrix.dtype)

    def __add__(self, o):
        """Add operator."""
        if isinstance(o, self.__class__):
            if self.nqubits != o.nqubits:
                raise_error(RuntimeError, "Only hamiltonians with the same "
                                          "number of qubits can be added.")
            new_matrix = self.matrix + o.matrix
            return self.__class__(self.nqubits, new_matrix)
        elif isinstance(o, self.NUMERIC_TYPES):
            return self.__class__(self.nqubits, self.matrix + o * self._eye())
        else:
            raise_error(NotImplementedError, "Hamiltonian addition to {} not "
                                             "implemented.".format(type(o)))

    def __radd__(self, o):
        """Right operator addition."""
        return self.__add__(o)

    def __sub__(self, o):
        """Subtraction operator."""
        if isinstance(o, self.__class__):
            if self.nqubits != o.nqubits:
                raise_error(RuntimeError, "Only hamiltonians with the same "
                                          "number of qubits can be subtracted.")
            new_matrix = self.matrix - o.matrix
            return self.__class__(self.nqubits, new_matrix)
        elif isinstance(o, self.NUMERIC_TYPES):
            return self.__class__(self.nqubits, self.matrix - o * self._eye())
        else:
            raise_error(NotImplementedError, "Hamiltonian subtraction to {} "
                                             "not implemented.".format(type(o)))

    def __rsub__(self, o):
        """Right subtraction operator."""
        if isinstance(o, self.__class__): # pragma: no cover
            # impractical case because it will be handled by `__sub__`
            if self.nqubits != o.nqubits:
                raise_error(RuntimeError, "Only hamiltonians with the same "
                                          "number of qubits can be added.")
            new_matrix = o.matrix - self.matrix
            return self.__class__(self.nqubits, new_matrix)
        elif isinstance(o, self.NUMERIC_TYPES):
            return self.__class__(self.nqubits, o * self._eye() - self.matrix)
        else:
            raise_error(NotImplementedError, "Hamiltonian subtraction to {} "
                                             "not implemented.".format(type(o)))

    def _real(self, o):
        """Calculates real part of number or tensor."""
        return o.real

    def __mul__(self, o):
        """Multiplication to scalar operator."""
        if isinstance(o, self.NUMERIC_TYPES) or isinstance(o, self.ARRAY_TYPES):
            new_matrix = self.matrix * o
            r = self.__class__(self.nqubits, new_matrix)
            if self._eigenvalues is not None:
                if self._real(o) >= 0:
                    r._eigenvalues = o * self._eigenvalues
                else:
                    r._eigenvalues = o * self._eigenvalues[::-1]
            if self._eigenvectors is not None:
                if self._real(o) > 0:
                    r._eigenvectors = self._eigenvectors
                elif o == 0:
                    r._eigenvectors = self._eye(int(self._eigenvectors.shape[0]))
            return r
        else:
            raise_error(NotImplementedError, "Hamiltonian multiplication to {} "
                                             "not implemented.".format(type(o)))

    def __rmul__(self, o):
        """Right scalar multiplication."""
        return self.__mul__(o)

    def __matmul__(self, o):
        """Matrix multiplication with other Hamiltonians or state vectors."""
        if isinstance(o, self.__class__):
            new_matrix = self.K.matmul(self.matrix, o.matrix)
            return self.__class__(self.nqubits, new_matrix)
        elif isinstance(o, self.ARRAY_TYPES):
            rank = len(tuple(o.shape))
            if rank == 1: # vector
                return self.K.matmul(self.matrix, o[:, self.K.newaxis])[:, 0]
            elif rank == 2: # matrix
                return self.K.matmul(self.matrix, o)
            else:
                raise_error(ValueError, "Cannot multiply Hamiltonian with "
                                        "rank-{} tensor.".format(rank))
        else:
            raise_error(NotImplementedError, "Hamiltonian matmul to {} not "
                                             "implemented.".format(type(o)))


class LocalHamiltonian(object):
    """Local Hamiltonian operator used for Trotterized time evolution.

    The Hamiltonian represented by this class has the form of Eq. (57) in
    `arXiv:1901.05824 <https://arxiv.org/abs/1901.05824>`_.

    Args:
        *parts (dict): Dictionary whose values are
            :class:`qibo.base.hamiltonians.Hamiltonian` objects representing
            the h operators of Eq. (58) in the reference. The keys of the
            dictionary are tuples of qubit ids (int) that represent the targets
            of each h term.


    Example:
        ::

            from qibo import matrices, hamiltonians
            # Create h term for critical TFIM Hamiltonian
            matrix = -np.kron(matrices.Z, matrices.Z) - np.kron(matrices.X, matrices.I)
            term = hamiltonians.Hamiltonian(2, matrix)
            # TFIM with periodic boundary conditions is translationally
            # invariant and therefore the same term can be used for all qubits
            # Create even and odd Hamiltonian parts (Eq. (43))
            even_part = {(0, 1): term, (2, 3): term}
            odd_part = {(1, 2): term, (3, 0): term}
            # Create a ``LocalHamiltonian`` object using these parts
            h = hamiltonians.LocalHamiltonian(even_part, odd_part)
    """

    def __init__(self, *parts):
        self.dtype = None
        self.parts = parts
        self.terms_set = set() # set of all terms unique
        all_targets = set()
        for targets, term in self:
            self.dense_class = term.__class__
            if not issubclass(type(term), Hamiltonian):
                raise_error(TypeError, "Invalid term type {}.".format(type(term)))
            if len(targets) != term.nqubits:
                raise_error(ValueError, "Term targets {} but supports {} qubits."
                                        "".format(targets, term.nqubits))
            all_targets |= set(targets)
            self.terms_set.add(term)
            if self.dtype is None:
                self.dtype = term.matrix.dtype
            else:
                if term.matrix.dtype != self.dtype:
                    raise_error(TypeError, "Terms of different types {} and {} "
                                            "were given.".format(
                                              term.matrix.dtype, self.dtype))
        self.nqubits = len(all_targets)
        self.term_gates = {}
        self._dt = None
        self._circuit = None

    @classmethod
    def from_single_term(cls, nqubits, term):
        """Creates Local Hamiltonian for translationally invariant models.

        It is assumed that the system has periodic boundary conditions and
        the local term acts on two qubits.

        Args:
            nqubits (int): Number of qubits in the system.
            term (:class:`qibo.base.hamiltonians.Hamiltonian`): Hamiltonian
                object representing the local operator. The total Hamiltonian
                is sum of this term acting on each of the qubits.
        """
        # TODO: Add check that `term` acts on two qubits
        even_terms = {(2 * i, (2 * i + 1) % nqubits): term
                       for i in range(nqubits // 2 + nqubits % 2)}
        odd_terms = {(2 * i + 1, (2 * i + 2) % nqubits): term
                     for i in range(nqubits // 2)}
        return cls(even_terms, odd_terms)

    def __iter__(self):
        """Helper iteration method to loop over the Hamiltonian terms."""
        # TODO: Use this iterator in all places where this loop is used.
        for part in self.parts:
            for targets, term in part.items():
                yield targets, term

    def dense_hamiltonian(self):
        # TODO: Move this to a NumpyLocalHamiltonian
        if 2 * self.nqubits > len(EINSUM_CHARS): # pragma: no cover
            # case not tested because it only happens in large examples
            raise_error(NotImplementedError, "Not enough einsum characters.")

        matrix = np.zeros(2 * self.nqubits * (2,), dtype=self.dtype)
        chars = EINSUM_CHARS[:2 * self.nqubits]
        # TODO: Use `__iter__` for this loop because it is used many times
        for targets, term in self:
            tmat = term.matrix.reshape(2 * term.nqubits * (2,))
            n = self.nqubits - len(targets)
            emat = np.eye(2 ** n, dtype=self.dtype).reshape(2 * n * (2,))
            # TODO: Perhaps use `itertools.chain` to concatenate generators
            tc = ("".join((chars[i] for i in targets)) +
                  "".join((chars[i + self.nqubits] for i in targets)))
            ec = "".join((c for c in chars if c not in tc))
            matrix += np.einsum(f"{tc},{ec}->{chars}", tmat, emat)

        matrix = matrix.reshape(2 * (2 ** self.nqubits,))
        return self.dense_class(self.nqubits, matrix)

    def _create_circuit(self, dt):
        """Creates circuit that implements the Trotterized evolution."""
        from qibo.models import Circuit
        self._circuit = Circuit(self.nqubits)
        for targets, term in self:
            gate = gates.Unitary(term.exp(dt / 2.0), *targets)
            if term in self.term_gates:
                self.term_gates[term].add(gate)
            else:
                self.term_gates[term] = {gate}
            self._circuit.add(gate)
        for part in self.parts[::-1]:
            for targets, term in part.items():
                gate = gates.Unitary(term.exp(dt / 2.0), *targets)
                self.term_gates[term].add(gate)
                self._circuit.add(gate)

    def __mul__(self, o):
        """Multiplication to scalar operator."""
        new_parts = []
        new_terms = {term: o * term for term in self.terms_set}
        new_parts = ({targets: new_terms[term]
                      for targets, term in part.items()}
                     for part in self.parts)
        return self.__class__(*new_parts)

    def __rmul__(self, o):
        """Right scalar multiplication."""
        return self.__mul__(o)

    def circuit(self, dt):
        """Circuit implementing second order Trotter time step.

        Args:
            dt (float): Time step to use for Trotterization.

        Returns:
            :class:`qibo.base.circuit.BaseCircuit` that implements a single
            time step of the second order Trotterized evolution.
        """
        if dt != self._dt:
            self._dt = dt
            if self._circuit is None:
                self._create_circuit(dt)
            else:
                self._circuit.set_parameters({
                    gate: term.exp(dt / 2.0)
                    for term, term_gates in self.term_gates.items()
                    for gate in term_gates
                    })
        return self._circuit
