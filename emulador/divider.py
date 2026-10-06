"""PERSONA 3 - Divisor (Algoritmo de restauración para enteros sin signo)."""

from .adders import SumadorN, RegistroDesplazamiento
from .gates import Compuerta

class Divisor(Compuerta):
    def __init__(self, n):
        super().__init__()
        self.nombre = f"Divisor{n}"
        self.n = n
        # El acumulador A y el restador requieren n + 1 bits en división por restauración
        self.sumador = SumadorN(n + 1)
        self.partes = [self.sumador]
        # Instanciamos los registros de hardware lógicos Q (n bits) y A (n + 1 bits)
        self.reg_q = RegistroDesplazamiento(n)
        self.reg_a = RegistroDesplazamiento(n + 1)

    def dividir(self, dividendo, divisor):
        if len(dividendo) != self.n or len(divisor) != self.n:
            raise ValueError(f"Los operandos deben tener {self.n} bits")
        if not any(divisor):
            raise ZeroDivisionError("División por cero no permitida")

        # El divisor se extiende a n + 1 bits con un 0 en el MSB
        divisor_ext = list(divisor) + [0]

        # Inicializamos los registros lógicos
        self.reg_q.cargar(dividendo)
        self.reg_a.cargar([0] * (self.n + 1))
        
        for _ in range(self.n):
            # 1. Shift Left combinado de A y Q
            # El bit más significativo de Q sale e ingresa como LSB en A
            msb_q = self.reg_q.desplazar_izquierda(0)
            self.reg_a.desplazar_izquierda(msb_q)
            
            # Leemos el valor actual de A para operarlo
            a_actual = self.reg_a.leer()
            
            # 2. A = A - Divisor (usando el sumador de n+1 bits en modo resta)
            a_resta, _ = self.sumador.restar(a_actual, divisor_ext)
            
            # 3. Verificamos el signo de la resta (bit n+1, es decir MSB)
            if a_resta[-1] == 1:
                # Restauración: Descartamos la resta, el registro A no cambia
                # El registro Q ya introdujo un 0 lógico en su shift anterior.
                pass
            else:
                # Éxito: actualizamos físicamente el registro A
                self.reg_a.cargar(a_resta)
                
                # Seteamos el bit LSB de Q a 1 lógico
                q_actual = self.reg_q.leer()
                q_actual[0] = 1
                self.reg_q.cargar(q_actual)
                
        # Retorna tupla de listas lógicas (cociente de n bits, residuo de n bits)
        return self.reg_q.leer(), self.reg_a.leer()[:self.n]