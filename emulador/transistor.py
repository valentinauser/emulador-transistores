class Transistor:
    total = 0  # contador global de transistores emulados

    def __init__(self, tipo, etiqueta=""):
        assert tipo in ("NMOS", "PMOS"), "tipo debe ser NMOS o PMOS"
        self.tipo = tipo
        self.etiqueta = etiqueta
        self.activo = False  # ¿conducía en la última evaluación?
        Transistor.total += 1
        self.id = Transistor.total

    def conduce(self, gate):
        """True si el transistor deja pasar corriente con ese valor en gate."""
        if self.tipo == "NMOS":
            estado = gate == 1
        else:  # PMOS
            estado = gate == 0
        self.activo = estado  # guardamos el último estado
        return estado

    @classmethod
    def reiniciar(cls):
        cls.total = 0
