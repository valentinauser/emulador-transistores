from emulador.gates import NOT, NAND, NOR, AND, OR, XOR, XNOR
from emulador.adders import SumadorCompleto, SumadorN
from emulador.utils import entero_a_bits, bits_a_entero

PARES = [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_compuertas():
    for a, b in PARES:
        assert NAND().evaluar(a, b) == int(not (a and b))
        assert NOR().evaluar(a, b) == int(not (a or b))
        assert AND().evaluar(a, b) == (a & b)
        assert OR().evaluar(a, b) == (a | b)
        assert XOR().evaluar(a, b) == (a ^ b)
        assert XNOR().evaluar(a, b) == int(a == b)
    assert NOT().evaluar(0) == 1 and NOT().evaluar(1) == 0


def test_sumador_completo():
    sc = SumadorCompleto()
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                s, co = sc.sumar(a, b, c)
                assert s + 2 * co == a + b + c


def test_sumador_8_bits():
    s8 = SumadorN(8)
    for a, b in [(0, 0), (1, 1), (100, 55), (255, 1), (200, 100)]:
        res, co = s8.sumar(entero_a_bits(a, 8), entero_a_bits(b, 8))
        assert bits_a_entero(res) + 256 * co == a + b
