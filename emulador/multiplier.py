"""PERSONA 3 - Multiplicador (tipo array de sumas)."""

from .adders import SumadorN
from .gates import AND

class Multiplicador:
    def __init__(self, n):
        self.n = n
        # Matriz de compuertas AND para generar productos parciales
        self.ands = [[AND() for _ in range(n)] for _ in range(n)]
        # N sumadores encadenados para acumular los productos
        self.sumadores = [SumadorN(n) for _ in range(n)]

    def multiplicar(self, a_bits, b_bits):
        producto = [0] * (2 * self.n)
        acumulador = [0] * self.n
        
        for i in range(self.n):
            producto_parcial = []
            for j in range(self.n):
                pp_bit = self.ands[i][j].evaluar(a_bits[j], b_bits[i])
                producto_parcial.append(pp_bit)
            
            res_suma, cout = self.sumadores[i].sumar(acumulador, producto_parcial)
            
            # El LSB baja al producto final
            producto[i] = res_suma[0]
            
            # Shift lógico a la derecha del acumulador metiendo el acarreo
            acumulador = res_suma[1:] + [cout]
            
        for i in range(self.n):
            producto[self.n + i] = acumulador[i]
            
        return producto