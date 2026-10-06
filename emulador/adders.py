"""PERSONA 3 - Capa 3: sumadores, comparadores y registros.

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
        # Compuertas para inversión en resta (A XOR 1 = NOT A)
        self.inversores = [XOR() for _ in range(n)]
        # Compuerta para cálculo de overflow (Cin_MSB XOR Cout_MSB)
        self.xor_overflow = XOR()
        self._cin_msb = 0

    def sumar(self, a_bits, b_bits, cin=0):
        resultado, acarreo = [], cin
        for i in range(self.n):
            if i == self.n - 1:
                self._cin_msb = acarreo  # Acarreo de entrada al MSB
                
            s, acarreo = self.celdas[i].sumar(a_bits[i], b_bits[i], acarreo)
            resultado.append(s)
        return resultado, acarreo

    def restar(self, a_bits, b_bits):
        # A - B = A + (NOT B) + 1 (complemento a 2).
        b_invertido = []
        for i in range(self.n):
            bit_inv = self.inversores[i].evaluar(b_bits[i], 1)
            b_invertido.append(bit_inv)
            
        # Sumamos con acarreo inicial en 1
        return self.sumar(a_bits, b_invertido, cin=1)

    def flags(self, resultado, acarreo):
        c = acarreo  # Carry
        v = self.xor_overflow.evaluar(self._cin_msb, acarreo) # Overflow
        n = resultado[-1] # Negative (MSB)
        
        # Zero flag
        z = 1
        for bit in resultado:
            if bit == 1:
                z = 0
                break
        return c, v, z, n


class ComparadorN:
    """Comparador de N bits basado en la unidad de resta."""
    def __init__(self, n):
        self.n = n
        self.restador = SumadorN(n)

    def comparar(self, a_bits, b_bits):
        resultado, acarreo = self.restador.restar(a_bits, b_bits)
        _, _, z, n_flag = self.restador.flags(resultado, acarreo)
        
        igual = z
        menor_que = n_flag 
        mayor_que = 1 if (igual == 0 and menor_que == 0) else 0
        
        return igual, menor_que, mayor_que


class RegistroDesplazamiento:
    """Registro lógico de hardware que almacena N bits y permite desplazamientos."""
    def __init__(self, n):
        self.n = n
        self.bits = [0] * n 

    def cargar(self, valor_bits):
        if len(valor_bits) != self.n:
            raise ValueError(f"El valor debe tener {self.n} bits")
        self.bits = valor_bits[:]

    def desplazar_izquierda(self, bit_entrada=0):
        msb_salida = self.bits[-1]
        self.bits = [bit_entrada] + self.bits[:-1]
        return msb_salida

    def leer(self):
        return self.bits[:]