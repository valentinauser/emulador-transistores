"""PERSONA 2 - Capa 2: compuertas CMOS hechas solo con transistores.

Primitivas (con transistores directos): NOT, NAND, NOR.
Compuestas (con otras compuertas): AND, OR, XOR, XNOR.
Cada compuerta guarda sus transistores para poder mostrar la tabla
"qué transistor corresponde a qué compuerta".

En CMOS cada primitiva tiene dos redes:
  - pull-up   (PMOS): si conduce, la salida se conecta a Vdd  -> 1
  - pull-down (NMOS): si conduce, la salida se conecta a tierra -> 0
Siempre debe conducir UNA sola de las dos (ver _salida).
"""
from .transistor import Transistor


def _salida(sube, baja):
    """Resuelve la salida a partir de las dos redes.
    Si conducen las dos hay cortocircuito; si no conduce ninguna, la salida
    queda flotando. Ambos casos indican un error de diseño."""
    assert sube != baja, "cortocircuito o salida flotante: revisar conexiones"
    return 1 if sube else 0


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
    nombre = "NOT"  # 2 transistores

    def __init__(self):
        super().__init__()
        self.p = Transistor("PMOS", "P1")
        self.n = Transistor("NMOS", "N1")
        self.transistores = [self.p, self.n]

    def evaluar(self, a):
        sube = self.p.conduce(a)
        baja = self.n.conduce(a)
        return _salida(sube, baja)


class NAND(Compuerta):
    nombre = "NAND"  # 4 transistores

    def __init__(self):
        super().__init__()
        # Pull-up: 2 PMOS en paralelo | Pull-down: 2 NMOS en serie
        self.p1, self.p2 = Transistor("PMOS", "P1"), Transistor("PMOS", "P2")
        self.n1, self.n2 = Transistor("NMOS", "N1"), Transistor("NMOS", "N2")
        self.transistores = [self.p1, self.p2, self.n1, self.n2]

    def evaluar(self, a, b):
        # Se evalúan los 4 primero (sin cortocircuitar 'or'/'and')
        # para que todos actualicen su estado 'activo'
        p1, p2 = self.p1.conduce(a), self.p2.conduce(b)
        n1, n2 = self.n1.conduce(a), self.n2.conduce(b)
        sube = p1 or p2    # paralelo: basta uno
        baja = n1 and n2   # serie: deben conducir ambos
        return _salida(sube, baja)


class NOR(Compuerta):
    nombre = "NOR"  # 4 transistores

    def __init__(self):
        super().__init__()
        # Pull-up: 2 PMOS en serie | Pull-down: 2 NMOS en paralelo
        self.p1, self.p2 = Transistor("PMOS", "P1"), Transistor("PMOS", "P2")
        self.n1, self.n2 = Transistor("NMOS", "N1"), Transistor("NMOS", "N2")
        self.transistores = [self.p1, self.p2, self.n1, self.n2]

    def evaluar(self, a, b):
        p1, p2 = self.p1.conduce(a), self.p2.conduce(b)
        n1, n2 = self.n1.conduce(a), self.n2.conduce(b)
        sube = p1 and p2   # serie: deben conducir ambos
        baja = n1 or n2    # paralelo: basta uno
        return _salida(sube, baja)


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
    nombre = "XNOR"  # XOR + NOT = 16 + 2 = 18 transistores

    def __init__(self):
        super().__init__()
        self.xor, self.inv = XOR(), NOT()
        self.partes = [self.xor, self.inv]

    def evaluar(self, a, b):
        return self.inv.evaluar(self.xor.evaluar(a, b))


def tabla_transistor_compuerta(compuerta, ruta=None):
    """Devuelve filas (ruta, id transistor, tipo, etiqueta) para mostrar
    en la presentación/interfaz, agrupadas por sub-compuerta.
    Ejemplo de ruta: 'XOR/NAND2' o 'AND/NOT2'."""
    ruta = ruta or compuerta.nombre
    filas = [(ruta, t.id, t.tipo, t.etiqueta) for t in compuerta.transistores]
    for i, parte in enumerate(compuerta.partes, 1):
        filas += tabla_transistor_compuerta(parte, f"{ruta}/{parte.nombre}{i}")
    return filas
