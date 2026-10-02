"""PERSONA 3 - Capa 3: sumadores (aritmética entera con compuertas).

Se construyen UNA vez (así el contador de transistores es real) y luego
se reutilizan para varias operaciones.
"""
from .gates import XOR, AND, OR


class SemiSumador:
    def __init__(self):
        self.xor, self.and_ = XOR(), AND()
        self.partes = [self.xor, self.and_]

    def sumar(self, a, b):
        return self.xor.evaluar(a, b), self.and_.evaluar(a, b)  # (suma, acarreo)


class SumadorCompleto:
    def __init__(self):
        self.s1, self.s2, self.or_ = SemiSumador(), SemiSumador(), OR()
        self.partes = [self.s1, self.s2, self.or_]

    def sumar(self, a, b, cin):
        s, c1 = self.s1.sumar(a, b)
        s, c2 = self.s2.sumar(s, cin)
        return s, self.or_.evaluar(c1, c2)


class SumadorN:
    """Sumador de N bits en cascada (ripple-carry)."""

    def __init__(self, n):
        self.n = n
        self.celdas = [SumadorCompleto() for _ in range(n)]

    def sumar(self, a_bits, b_bits, cin=0):
        resultado, acarreo = [], cin
        for i in range(self.n):
            s, acarreo = self.celdas[i].sumar(a_bits[i], b_bits[i], acarreo)
            resultado.append(s)
        return resultado, acarreo

    def restar(self, a_bits, b_bits):
        # TODO(Persona 3): A - B = A + (NOT B) + 1 (complemento a 2).
        # Necesita N compuertas NOT/XOR para invertir B y cin = 1.
        raise NotImplementedError

    def flags(self, a_bits, b_bits, resultado, acarreo):
        # TODO(Persona 3): acarreo, overflow, cero, negativo (como en alu_8bits.py)
        raise NotImplementedError
