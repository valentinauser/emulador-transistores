"""PERSONA 4 - Unidad IEEE 754 (32 bits): 1 signo | 8 exponente | 23 mantisa.

Regla: las operaciones deben usar adders / multiplier / divider (transistores),
NO los operadores +, -, *, / de Python. 'struct' solo se usa en tests.
"""

SESGO = 127


def decodificar(bits32):
    """TODO(P4): separar (signo, exponente, mantisa) y detectar casos
    especiales (cero, infinito, NaN, desnormalizado)."""
    raise NotImplementedError


def codificar(signo, exponente, mantisa):
    """TODO(P4): armar los 32 bits."""
    raise NotImplementedError


def float_add(a32, b32):
    """TODO(P4): alinear exponentes -> sumar mantisas -> normalizar -> redondear."""
    raise NotImplementedError


def float_sub(a32, b32):
    """TODO(P4): invertir signo de b y llamar float_add."""
    raise NotImplementedError


def float_mul(a32, b32):
    """TODO(P4): signo XOR, sumar exponentes - sesgo, multiplicar mantisas."""
    raise NotImplementedError


def float_div(a32, b32):
    """TODO(P4): signo XOR, restar exponentes + sesgo, dividir mantisas."""
    raise NotImplementedError
