"""PERSONA 3 - Divisor (Algoritmo de restauración para enteros sin signo)."""

from .adders import SumadorN, RegistroDesplazamiento

class Divisor:
    def __init__(self, n):
        self.n = n
        self.sumador = SumadorN(n)
        # Instanciamos los registros de hardware lógicos Q y A
        self.reg_q = RegistroDesplazamiento(n)
        self.reg_a = RegistroDesplazamiento(n)

    def dividir(self, dividendo, divisor):
        # Inicializamos los registros lógicos
        self.reg_q.cargar(dividendo)
        self.reg_a.cargar([0] * self.n)
        
        for _ in range(self.n):
            # 1. Shift Left combinado de A y Q
            # El bit más significativo de Q sale e ingresa como LSB en A
            msb_q = self.reg_q.desplazar_izquierda(0)
            self.reg_a.desplazar_izquierda(msb_q)
            
            # Leemos el valor actual de A para operarlo
            a_actual = self.reg_a.leer()
            
            # 2. A = A - Divisor (usando el sumador en modo resta)
            a_resta, _ = self.sumador.restar(a_actual, divisor)
            
            # 3. Verificamos el signo de la resta (MSB del resultado)
            if a_resta[-1] == 1:
                # Restauración: Descartamos la resta, el registro A no cambia
                # El registro Q ya introdujo un 0 lógico en su shift anterior, no hacemos nada.
                pass
            else:
                # Éxito: actualizamos físicamente el registro A
                self.reg_a.cargar(a_resta)
                
                # Seteamos el bit LSB de Q a 1 lógico
                q_actual = self.reg_q.leer()
                q_actual[0] = 1
                self.reg_q.cargar(q_actual)
                
        # Retorna tupla de listas lógicas (cociente, residuo)
        return self.reg_q.leer(), self.reg_a.leer()