"""PERSONA 2 - Capa 2: compuertas CMOS hechas solo con transistores.

Primitivas (con transistores directos): NOT, NAND, NOR.
Compuestas (con otras compuertas): AND, OR, XOR, XNOR.
Cada compuerta guarda sus transistores para poder mostrar la tabla
"qué transistor corresponde a qué compuerta".
"""
from .transistor import Transistor


class Compuerta:
    nombre = "?"

    def __init__(self):
        self.transistores = []  # transistores propios (solo primitivas)
        self.partes = []        # sub-compuertas (solo compuestas)

    def todos_los_transistores(self):
        lista = list(self.transistores)
        for parte in self.partes:
            lista += parte.todos_los_transistores()
        return lista

    def cantidad(self):
        return len(self.todos_los_transistores())


class NOT(Compuerta):
    nombre = "NOT"

    def __init__(self):
        super().__init__()
        self.p = Transistor("PMOS", "P1")
        self.n = Transistor("NMOS", "N1")
        self.transistores = [self.p, self.n]

    def evaluar(self, a):
        # Si el PMOS conduce, la salida se une a Vdd (1); si no, a tierra (0)
        return 1 if self.p.conduce(a) else 0


class NAND(Compuerta):
    nombre = "NAND"

    def __init__(self):
        super().__init__()
        # Pull-up: 2 PMOS en paralelo | Pull-down: 2 NMOS en serie
        self.p1, self.p2 = Transistor("PMOS", "P1"), Transistor("PMOS", "P2")
        self.n1, self.n2 = Transistor("NMOS", "N1"), Transistor("NMOS", "N2")
        self.transistores = [self.p1, self.p2, self.n1, self.n2]

    def evaluar(self, a, b):
        sube = self.p1.conduce(a) or self.p2.conduce(b)
        return 1 if sube else 0


class NOR(Compuerta):
    nombre = "NOR"

    def __init__(self):
        super().__init__()
        # Pull-up: 2 PMOS en serie | Pull-down: 2 NMOS en paralelo
        self.p1, self.p2 = Transistor("PMOS", "P1"), Transistor("PMOS", "P2")
        self.n1, self.n2 = Transistor("NMOS", "N1"), Transistor("NMOS", "N2")
        self.transistores = [self.p1, self.p2, self.n1, self.n2]

    def evaluar(self, a, b):
        sube = self.p1.conduce(a) and self.p2.conduce(b)
        return 1 if sube else 0


class AND(Compuerta):
    nombre = "AND"  # NAND + NOT = 6 transistores

    def __init__(self):
        super().__init__()
        self.nand, self.inv = NAND(), NOT()
        self.partes = [self.nand, self.inv]

    def evaluar(self, a, b):
        return self.inv.evaluar(self.nand.evaluar(a, b))


class OR(Compuerta):
    nombre = "OR"  # NOR + NOT = 6 transistores

    def __init__(self):
        super().__init__()
        self.nor, self.inv = NOR(), NOT()
        self.partes = [self.nor, self.inv]

    def evaluar(self, a, b):
        return self.inv.evaluar(self.nor.evaluar(a, b))


class XOR(Compuerta):
    nombre = "XOR"  # 4 NAND = 16 transistores

    def __init__(self):
        super().__init__()
        self.n1, self.n2, self.n3, self.n4 = NAND(), NAND(), NAND(), NAND()
        self.partes = [self.n1, self.n2, self.n3, self.n4]

    def evaluar(self, a, b):
        m = self.n1.evaluar(a, b)
        return self.n4.evaluar(self.n2.evaluar(a, m), self.n3.evaluar(b, m))


class XNOR(Compuerta):
    nombre = "XNOR"  # XOR + NOT

    def __init__(self):
        super().__init__()
        self.xor, self.inv = XOR(), NOT()
        self.partes = [self.xor, self.inv]

    def evaluar(self, a, b):
        return self.inv.evaluar(self.xor.evaluar(a, b))


def tabla_transistor_compuerta(compuerta):
    """Devuelve filas (compuerta, id transistor, tipo, etiqueta) para mostrar
    en la presentación/interfaz. TODO(Persona 2): agrupar por sub-compuerta."""
    filas = []
    for t in compuerta.todos_los_transistores():
        filas.append((compuerta.nombre, t.id, t.tipo, t.etiqueta))
    return filas
