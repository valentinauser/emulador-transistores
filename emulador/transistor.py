"""PERSONA 2 - Capa 1: el transistor.

Modelo a nivel lógico (interruptor controlado por la compuerta/gate):
  - NMOS conduce cuando gate = 1
  - PMOS conduce cuando gate = 0
Cada Transistor creado suma 1 al contador global (requisito n >= 100).
"""


class Transistor:
    total = 0  # contador global de transistores emulados

    def __init__(self, tipo, etiqueta=""):
        assert tipo in ("NMOS", "PMOS"), "tipo debe ser NMOS o PMOS"
        self.tipo = tipo
        self.etiqueta = etiqueta
        Transistor.total += 1
        self.id = Transistor.total

    def conduce(self, gate):
        """True si el transistor deja pasar corriente con ese valor en gate."""
        return gate == 1 if self.tipo == "NMOS" else gate == 0

    @classmethod
    def reiniciar(cls):
        cls.total = 0
