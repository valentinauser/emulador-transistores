import math
import random
import struct

import pytest

from emulador.ieee754 import (
    decodificar, codificar, mantisa_con_implicito, exponente_efectivo,
    cero, infinito, nan,
    float_add, float_sub, float_mul, float_div,
    TIPO_CERO, TIPO_DESNORMALIZADO, TIPO_NORMAL, TIPO_INFINITO, TIPO_NAN,
)
from emulador.utils import entero_a_bits, bits_a_entero


# --- Ayudas SOLO para tests (aquí sí se puede usar struct y operadores) ---

def bits_de_float(x):
    return entero_a_bits(struct.unpack("<I", struct.pack("<f", x))[0], 32)


def float_de_bits(bits):
    return struct.unpack("<f", struct.pack("<I", bits_a_entero(bits)))[0]


VALORES = [1.0, -2.5, 0.15625, 3.14159, 1e-3, 123456.789, -0.75, 1e30]


# --- decodificar / codificar ---

@pytest.mark.parametrize("x", VALORES)
def test_decodificar_campos(x):
    bits = bits_de_float(x)
    v = bits_a_entero(bits)
    signo, exp, mant, _ = decodificar(bits)
    assert signo == (v >> 31) & 1
    assert bits_a_entero(exp) == (v >> 23) & 0xFF
    assert bits_a_entero(mant) == v & 0x7FFFFF


@pytest.mark.parametrize("x", VALORES + [0.0, -0.0, 1e-45, float("inf"), float("nan")])
def test_codificar_es_inverso_de_decodificar(x):
    bits = bits_de_float(x)
    signo, exp, mant, _ = decodificar(bits)
    assert codificar(signo, exp, mant) == bits


def test_tipos():
    assert decodificar(bits_de_float(1.0))[3] == TIPO_NORMAL
    assert decodificar(bits_de_float(0.0))[3] == TIPO_CERO
    assert decodificar(bits_de_float(-0.0))[3] == TIPO_CERO
    assert decodificar(bits_de_float(1e-45))[3] == TIPO_DESNORMALIZADO
    assert decodificar(bits_de_float(float("inf")))[3] == TIPO_INFINITO
    assert decodificar(bits_de_float(float("-inf")))[3] == TIPO_INFINITO
    assert decodificar(bits_de_float(float("nan")))[3] == TIPO_NAN


def test_mantisa_con_implicito():
    _, _, mant, tipo = decodificar(bits_de_float(1.0))
    assert bits_a_entero(mantisa_con_implicito(mant, tipo)) == 1 << 23
    _, _, mant, tipo = decodificar(bits_de_float(1.5))
    assert bits_a_entero(mantisa_con_implicito(mant, tipo)) == 3 << 22
    _, _, mant, tipo = decodificar(bits_de_float(1e-45))
    assert bits_a_entero(mantisa_con_implicito(mant, tipo)) == 1


def test_exponente_efectivo():
    _, exp, _, tipo = decodificar(bits_de_float(1e-45))
    assert bits_a_entero(exponente_efectivo(exp, tipo)) == 1
    _, exp, _, tipo = decodificar(bits_de_float(1.0))
    assert bits_a_entero(exponente_efectivo(exp, tipo)) == 127


def test_resultados_especiales():
    assert cero(0) == bits_de_float(0.0)
    assert cero(1) == bits_de_float(-0.0)
    assert infinito(0) == bits_de_float(float("inf"))
    assert infinito(1) == bits_de_float(float("-inf"))
    assert nan() == bits_de_float(float("nan"))


def test_codificar_valida_tamanos():
    with pytest.raises(ValueError):
        decodificar([0] * 31)
    with pytest.raises(ValueError):
        codificar(0, [0] * 7, [0] * 23)
    with pytest.raises(ValueError):
        codificar(0, [0] * 8, [0] * 22)
    with pytest.raises(ValueError):
        codificar(2, [0] * 8, [0] * 23)


# --- Operaciones: suma, resta, multiplicación y división ---
# Se calcula el resultado esperado con Python (aquí sí se puede) y se compara
# bit a bit. Python trabaja en double y luego se redondea a float32: para
# + - * / el resultado es idéntico al de un float32 real.

def _i(x):
    """float -> entero de 32 bits."""
    return struct.unpack("<I", struct.pack("<f", x))[0]


def _esperado(op, fa, fb):
    try:
        return op(fa, fb)
    except ZeroDivisionError:               # x / 0.0
        if fa == 0 or fa != fa:
            return float("nan")
        negativo = (fa < 0) != (math.copysign(1.0, fb) < 0)
        return float("-inf") if negativo else float("inf")


def _verificar(resultado, esperado):
    if esperado != esperado:                # NaN: basta con que sea NaN
        assert decodificar(resultado)[3] == TIPO_NAN
        return
    try:
        bits = bits_de_float(esperado)
    except OverflowError:                   # no cabe en float32 -> infinito
        bits = infinito(1 if esperado < 0 else 0)
    assert resultado == bits


INF = float("inf")
BASICOS = [(1.5, 2.25), (-3.0, 1.0), (0.1, 0.2), (100.0, 0.5), (-7.5, -2.5)]
ESPECIALES = [
    (INF, 1.0), (INF, -INF), (INF, INF), (0.0, INF), (float("nan"), 1.0),
    (0.0, -0.0), (-0.0, -0.0), (1.0, 0.0), (0.0, 0.0), (5.0, -5.0),
    (3.4e38, 3.4e38),                       # overflow
    (1e-30, 1e-30), (1e-38, 1e-10),         # underflow
    (1e-45, 1.0), (1.1754942e-38, 1e-40),   # desnormalizados
    (16777216.0, 1.0), (1.0, 5.9604645e-08),
]
_azar = random.Random(754)
ALEATORIOS = (
    [(_azar.uniform(-100, 100), _azar.uniform(-100, 100)) for _ in range(12)]
    + [(float_de_bits(entero_a_bits(_azar.getrandbits(32), 32)),
        float_de_bits(entero_a_bits(_azar.getrandbits(32), 32))) for _ in range(12)]
)
PARES = [(_i(a), _i(b)) for a, b in BASICOS + ESPECIALES + ALEATORIOS]

OPERACIONES = {
    "suma": (float_add, lambda a, b: a + b),
    "resta": (float_sub, lambda a, b: a - b),
    "mul": (float_mul, lambda a, b: a * b),
    "div": (float_div, lambda a, b: a / b),
}


@pytest.mark.parametrize("nombre", list(OPERACIONES))
@pytest.mark.parametrize("ia,ib", PARES)
def test_operaciones(nombre, ia, ib):
    funcion, referencia = OPERACIONES[nombre]
    a32, b32 = entero_a_bits(ia, 32), entero_a_bits(ib, 32)
    fa, fb = float_de_bits(a32), float_de_bits(b32)
    _verificar(funcion(a32, b32), _esperado(referencia, fa, fb))