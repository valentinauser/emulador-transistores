"""PERSONA 3 - Capa 3: sumadores, comparadores y registros.

Se construyen UNA vez (así el contador de transistores es real) y luego
se reutilizan para varias operaciones.
"""
from .gates import Compuerta, XOR, AND, OR

class SemiSumador(Compuerta):
    nombre = "SemiSumador"

    def __init__(self):
        super().__init__()
        self.xor, self.and_ = XOR(), AND()
        self.partes = [self.xor, self.and_]

    def sumar(self, a, b):
        return self.xor.evaluar(a, b), self.and_.evaluar(a, b)  # (suma, acarreo)


class SumadorCompleto(Compuerta):
    nombre = "SumadorCompleto"

    def __init__(self):
        super().__init__()
        self.s1, self.s2, self.or_ = SemiSumador(), SemiSumador(), OR()
        self.partes = [self.s1, self.s2, self.or_]

    def sumar(self, a, b, cin):
        s, c1 = self.s1.sumar(a, b)
        s, c2 = self.s2.sumar(s, cin)
        return s, self.or_.evaluar(c1, c2)


class SumadorN(Compuerta):
    """Sumador de N bits en cascada (ripple-carry)."""
    def __init__(self, n):
        super().__init__()
        self.nombre = f"Sumador{n}"
        self.n = n
        self.celdas = [SumadorCompleto() for _ in range(n)]
        # Compuertas para inversión en resta (A XOR 1 = NOT A)
        self.inversores = [XOR() for _ in range(n)]
        # Compuerta para cálculo de overflow (Cin_MSB XOR Cout_MSB)
        self.xor_overflow = XOR()
        self.partes = list(self.celdas) + list(self.inversores) + [self.xor_overflow]
        self._cin_msb = 0

    def sumar(self, a_bits, b_bits, cin=0):
        if len(a_bits) != self.n or len(b_bits) != self.n:
            raise ValueError(f"Las listas de bits deben tener longitud {self.n}")
        resultado, acarreo = [], cin
        for i in range(self.n):
            if i == self.n - 1:
                self._cin_msb = acarreo  # Acarreo de entrada al MSB
                
            s, acarreo = self.celdas[i].sumar(a_bits[i], b_bits[i], acarreo)
            resultado.append(s)
        return resultado, acarreo

    def restar(self, a_bits, b_bits):
        # A - B = A + (NOT B) + 1 (complemento a 2).
        if len(a_bits) != self.n or len(b_bits) != self.n:
            raise ValueError(f"Las listas de bits deben tener longitud {self.n}")
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
        z = 1 if not any(resultado) else 0
        return c, v, z, n


class ComparadorN(Compuerta):
    """Comparador de N bits basado en la unidad de resta."""
    def __init__(self, n):
        super().__init__()
        self.nombre = f"Comparador{n}"
        self.n = n
        self.restador = SumadorN(n)
        self.xor_signo = XOR()
        self.partes = [self.restador, self.xor_signo]

    def comparar(self, a_bits, b_bits, con_signo=False):
        resultado, acarreo = self.restador.restar(a_bits, b_bits)
        _, v, z, n_flag = self.restador.flags(resultado, acarreo)
        
        igual = z
        if con_signo:
            # En complemento a 2 con signo: A < B <=> N XOR V = 1
            menor_que = self.xor_signo.evaluar(n_flag, v)
        else:
            # Sin signo: A < B <=> Cout == 0 (hubo borrow)
            menor_que = 1 if acarreo == 0 else 0
            
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

    def desplazar_derecha(self, bit_entrada=0):
        lsb_salida = self.bits[0]
        self.bits = self.bits[1:] + [bit_entrada]
        return lsb_salida

    def leer(self):
        return self.bits[:]