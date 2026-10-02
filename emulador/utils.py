"""Convención del equipo: un número en bits es una LISTA de 0/1 con el
índice 0 = bit MENOS significativo (LSB). Ej: 6 en 4 bits -> [0, 1, 1, 0]
"""


def entero_a_bits(valor, n):
    return [(valor >> i) & 1 for i in range(n)]


def bits_a_entero(bits):
    return sum(b << i for i, b in enumerate(bits))


def bits_a_texto(bits):
    """Texto con el MSB a la izquierda, como se lee normalmente."""
    return "".join(str(b) for b in reversed(bits))
